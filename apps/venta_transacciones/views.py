from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from urllib3 import request  #  Asegúrate de importar esto
from .models import *
from .serializers import *
import stripe
from django.conf import settings

# ViewSet para Venta
class VentaViewSet(viewsets.ModelViewSet):
    queryset = Venta.objects.all().order_by('id')
    serializer_class = VentaSerializer
    permission_classes = [IsAuthenticated]

# ViewSet para DetalleVenta
class DetalleVentaViewSet(viewsets.ModelViewSet):
    queryset = DetalleVenta.objects.all().order_by('id')
    serializer_class = DetalleVentaSerializer
    permission_classes = [IsAuthenticated]

# ViewSet para Carrito
class CarritoViewSet(viewsets.ModelViewSet):
    queryset = Carrito.objects.all().order_by('id')
    serializer_class = CarritoSerializer
    permission_classes = [IsAuthenticated]

# ViewSet para DetalleCarrito
class DetalleCarritoViewSet(viewsets.ModelViewSet):
    queryset = DetalleCarrito.objects.all().order_by('id')
    serializer_class = DetalleCarritoSerializer
    permission_classes = [IsAuthenticated]




# Configurar Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class PagoViewSet(viewsets.ModelViewSet):
    queryset = Pago.objects.all()
    serializer_class = PagoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PagoCreateSerializer
        return PagoSerializer
    
    def perform_create(self, serializer):
        serializer.save(residente=self.request.user.residente)


class PagoViewSet(viewsets.ModelViewSet):
    queryset = Pago.objects.all()
    serializer_class = PagoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PagoCreateSerializer
        return PagoSerializer
    
    def perform_create(self, serializer):
        serializer.save(residente=self.request.user.residente)

    @action(detail=False, methods=['post'])
    def crear_payment_intent(self, request):
        """
        Crear un PaymentIntent de Stripe vinculado a una venta.
        Espera 'venta_id' en el body.
        """
        try:
            venta_id = request.data.get('venta_id')
            if not venta_id:
                return Response({'error': 'venta_id es requerido'}, status=status.HTTP_400_BAD_REQUEST)
            
            venta = Venta.objects.get(id=venta_id)
            monto_centavos = int(float(venta.total_venta) * 100)
            
            intent = stripe.PaymentIntent.create(
                amount=monto_centavos,
                currency='usd',
                metadata={'venta_id': venta.id}
            )
            
            pago = Pago.objects.create(
                venta=venta,
                monto=venta.total_venta,
                metodo_pago='stripe',
                estado='pendiente',
                stripe_payment_intent_id=intent.id,
                stripe_client_secret=intent.client_secret
            )
            
            return Response({
                'payment_intent_id': intent.id,
                'client_secret': intent.client_secret,
                'pago_id': pago.id,
                'monto': float(venta.total_venta),
                'venta_id': venta.id
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    
@action(detail=False, methods=['post'])
def confirmar_pago(self, request):
    """Confirmar el pago de una venta desde el backend (sin Stripe)"""
    try:
        venta_id = request.data.get('venta_id')
        if not venta_id:
            return Response({'error': 'venta_id es requerido'}, status=status.HTTP_400_BAD_REQUEST)

        venta = Venta.objects.get(id=venta_id)
        pago = Pago.objects.filter(venta=venta, estado='pendiente').order_by('-id').first()

        if pago:
            pago.estado = 'completado'
            pago.metodo_pago = 'efectivo'
            pago.save()
        else:
            pago = Pago.objects.create(
                venta=venta,
                monto=venta.total_venta,
                metodo_pago='efectivo',
                estado='completado'
            )

        return Response({
            'message': 'Pago confirmado exitosamente',
            'pago_id': pago.id,
            'venta_id': venta.id,
            'estado': 'completado'
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
