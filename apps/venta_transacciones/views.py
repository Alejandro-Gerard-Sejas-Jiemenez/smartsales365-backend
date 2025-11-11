from django.db import transaction
from django.shortcuts import render, get_object_or_404
from django.conf import settings
import stripe

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError

from .models import *
from .serializers import *
from apps.catalogo.models import Producto

# ViewSet para Venta
class VentaViewSet(viewsets.ModelViewSet):
    queryset = Venta.objects.select_related('cliente__usuario').prefetch_related('detalles__producto').all().order_by('-fecha_venta')
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve' or self.action == 'mis_compras':
            return VentaReadSerializer
        return VentaSerializer
    
    @action(detail=False, methods=['get'])
    def mis_compras(self, request):
        """Obtiene el historial de compras del cliente autenticado"""
        user = request.user
        
        if not hasattr(user, 'cliente'):
            return Response(
                {'detail': 'El usuario no tiene un perfil de cliente asociado.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener ventas del cliente con sus detalles
        ventas = Venta.objects.filter(
            cliente=user.cliente
        ).select_related(
            'cliente__usuario'
        ).prefetch_related(
            'detalles__producto'
        ).order_by('-fecha_venta')
        
        print(f"🔍 Ventas encontradas: {ventas.count()}")
        for venta in ventas:
            print(f"📦 Venta {venta.id}: {venta.detalles.count()} detalles")
        
        # Serializar las ventas
        serializer = self.get_serializer(ventas, many=True)
        print(f"📋 Datos serializados: {serializer.data}")
        return Response(serializer.data, status=status.HTTP_200_OK)


# --- ViewSet para DetalleVenta (Solo Lectura) ---
class DetalleVentaViewSet(viewsets.ReadOnlyModelViewSet):
    # --- Tomado de 'Incoming' (versión mía) ---
    queryset = DetalleVenta.objects.all().order_by('id')
    serializer_class = DetalleVentaSerializer
    permission_classes = [permissions.IsAuthenticated]

# ViewSet para Carrito
class CarritoViewSet(viewsets.ModelViewSet):
    # --- FUSIONADO: Tomado de 'HEAD' (Alejandro) pero MODIFICADO ---
    serializer_class = CarritoSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Solo mostrar carritos del usuario autenticado (si es cliente)
        user = self.request.user
        if hasattr(user, 'cliente'):
            # Optimizar con select_related y prefetch_related
            # CORREGIDO: 'detalles' es el related_name correcto
            return Carrito.objects.filter(cliente=user.cliente).select_related(
                'cliente', 'cliente__usuario'
            ).prefetch_related(
                'detalles__producto'
            ).order_by('id')
        return Carrito.objects.none()
    
    @action(detail=False, methods=['post'])
    def vaciar_carrito(self, request):
        """Elimina todos los productos del carrito del usuario"""
        user = request.user
        
        if not hasattr(user, 'cliente'):
            return Response(
                {'detail': 'El usuario no tiene un perfil de cliente asociado.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener el carrito del cliente
        carrito = Carrito.objects.filter(cliente=user.cliente).first()
        
        if not carrito:
            return Response(
                {'detail': 'No hay carrito para vaciar'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Eliminar todos los detalles del carrito
        DetalleCarrito.objects.filter(carrito=carrito).delete()
        
        # CORREGIDO: Eliminada la lógica de 'carrito.total'
        
        return Response(
            {'detail': 'Carrito vaciado exitosamente'}, 
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'])
    @transaction.atomic # Añadido para seguridad
    def crear_venta_desde_carrito(self, request):
        """Crea una venta a partir del carrito actual del usuario"""
        user = request.user
        
        if not hasattr(user, 'cliente'):
            return Response(
                {'detail': 'El usuario no tiene un perfil de cliente asociado.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener el carrito del cliente
        carrito = Carrito.objects.filter(cliente=user.cliente).first()
        
        if not carrito:
            return Response(
                {'detail': 'No hay carrito disponible'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verificar que el carrito tenga productos
        detalles_carrito = DetalleCarrito.objects.filter(carrito=carrito)
        
        if not detalles_carrito.exists():
            return Response(
                {'detail': 'El carrito está vacío'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calcular el total desde los detalles del carrito
        total_calculado = sum(detalle.subtotal for detalle in detalles_carrito)
        
        # Crear la venta
        venta = Venta.objects.create(
            cliente=user.cliente,
            total=total_calculado,
            metodo_entrada='carrito',
            tipo_venta='online'
        )
        
        # Crear los detalles de la venta desde el carrito
        for detalle_carrito in detalles_carrito:
            DetalleVenta.objects.create(
                venta=venta,
                producto=detalle_carrito.producto,
                cantidad=detalle_carrito.cantidad,
                precio_unitario=detalle_carrito.precio_unitario,
                subtotal=detalle_carrito.subtotal
            )
        
        # Recargar la venta con sus detalles y productos relacionados
        venta = Venta.objects.prefetch_related('detalles__producto').get(id=venta.id)
        
        # Vaciar el carrito después de crear la venta
        detalles_carrito.delete()
        carrito.estado = 'Convertido'
        carrito.save()
        
        # Serializar la venta con VentaReadSerializer para incluir todos los detalles
        serializer = VentaReadSerializer(venta)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def create(self, request, *args, **kwargs):
        user = request.user

        if not hasattr(user, 'cliente'):
            raise ValidationError({'detail': 'El usuario no tiene un perfil de cliente asociado.'})

        # Verificar si ya existe un carrito
        carrito_existente = Carrito.objects.filter(cliente=user.cliente).first()
        if carrito_existente:
            # Si ya existe, devolvemos ese carrito como JSON (no error)
            serializer = self.get_serializer(carrito_existente)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Si no existe, creamos uno nuevo
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(cliente=user.cliente)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

# ViewSet para DetalleCarrito
class DetalleCarritoViewSet(viewsets.ModelViewSet):
    # --- FUSIONADO: Tomado de 'HEAD' (compañero) pero MODIFICADO ---
    serializer_class = DetalleCarritoSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Solo mostrar detalles de carritos del usuario autenticado
        user = self.request.user
        if hasattr(user, 'cliente'):
            # CORREGIDO: 'carrito__cliente'
            return DetalleCarrito.objects.filter(carrito__cliente=user.cliente).order_by('id')
        return DetalleCarrito.objects.none()
    
    def perform_create(self, serializer):
        # Obtener o crear carrito del cliente autenticado
        user = self.request.user
        
        # Verificar que el usuario tenga un cliente asociado
        if not hasattr(user, 'cliente'):
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'detail': 'El usuario no tiene un perfil de cliente asociado.'})
        
        # Obtener o crear el carrito activo
        carrito, created = Carrito.objects.get_or_create(
            cliente=user.cliente,
            estado='Activo',
            defaults={'origen': 'FlutterApp'}
        )
        
        # Obtener el producto y calcular precios
        from apps.catalogo.models import Producto
        producto_id = self.request.data.get('producto')
        cantidad = int(self.request.data.get('cantidad', 1))
        
        producto = Producto.objects.get(id=producto_id)
        
        # Verificar si el producto ya existe en el carrito
        detalle_existente = DetalleCarrito.objects.filter(
            carrito=carrito,
            producto=producto
        ).first()
        
        if detalle_existente:
            # Si ya existe, incrementar la cantidad
            detalle_existente.cantidad += cantidad
            
            # Validar stock total en carrito
            if producto.stock_actual < detalle_existente.cantidad:
                raise ValidationError({'detail': f'Stock insuficiente. Ya tiene {detalle_existente.cantidad - cantidad} en el carrito. Disponible: {producto.stock_actual}'})

            detalle_existente.subtotal = detalle_existente.precio_unitario * detalle_existente.cantidad
            detalle_existente.save()
            
            # CORREGIDO: Eliminada la lógica de 'carrito.total'
            
            # Retornar - no continuar con el save del serializer
            return
        
        # Si no existe, crear uno nuevo
        precio_unitario = producto.precio_venta
        subtotal = precio_unitario * cantidad
        
        # Guardar el detalle del carrito
        serializer.save(
            carrito=carrito,
            precio_unitario=precio_unitario,
            subtotal=subtotal
        )
        
        # CORREGIDO: Eliminada la lógica de 'carrito.total'
    
    def partial_update(self, request, *args, **kwargs):
        """Actualizar la cantidad de un detalle del carrito"""
        detalle = self.get_object()
        nueva_cantidad = request.data.get('cantidad')
        
        if nueva_cantidad is None:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'detail': 'La cantidad es requerida'})
        
        nueva_cantidad = int(nueva_cantidad)
        
        if nueva_cantidad <= 0:
            # Si la cantidad es 0 o negativa, eliminar el detalle
            detalle.delete()
            
            # CORREGIDO: Eliminada la lógica de 'carrito.total'
            
            return Response({'detail': 'Producto eliminado del carrito'}, status=status.HTTP_204_NO_CONTENT)
        
        # Actualizar cantidad y subtotal
        detalle.cantidad = nueva_cantidad
        detalle.subtotal = detalle.precio_unitario * nueva_cantidad
        detalle.save()
        
        # CORREGIDO: Eliminada la lógica de 'carrito.total'
        
        serializer = self.get_serializer(detalle)
        return Response(serializer.data)




# Configurar Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class PagoViewSet(viewsets.ModelViewSet):
    queryset = Pago.objects.all()
    serializer_class = PagoSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PagoCreateSerializer
        return PagoSerializer

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
        except Venta.DoesNotExist:
            return Response({'error': 'Venta no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def confirmar_pago(self, request):
        """Confirmar el pago después de que Stripe lo procese exitosamente"""
        try:
            payment_intent_id = request.data.get('payment_intent_id')
            if not payment_intent_id:
                return Response({'error': 'payment_intent_id es requerido'}, status=status.HTTP_400_BAD_REQUEST)

            # Verificar el estado del pago en Stripe
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            if intent.status != 'succeeded':
                return Response({
                    'error': 'El pago no ha sido completado',
                    'status': intent.status
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Buscar el pago en la base de datos
            pago = Pago.objects.filter(stripe_payment_intent_id=payment_intent_id).first()
            
            if not pago:
                return Response({'error': 'Pago no encontrado'}, status=status.HTTP_404_NOT_FOUND)
            
            # Actualizar el estado del pago
            pago.estado = 'completado'
            pago.save()
            
            # Vaciar el carrito del cliente
            venta = pago.venta
            if hasattr(venta, 'cliente'):
                carrito = Carrito.objects.filter(cliente=venta.cliente).first()
                if carrito:
                    DetalleCarrito.objects.filter(carrito=carrito).delete()
                    carrito.total = 0
                    carrito.save()

            return Response({
                'message': 'Pago confirmado exitosamente',
                'pago_id': pago.id,
                'venta_id': venta.id,
                'estado': 'completado'
            })
        except Venta.DoesNotExist:
            return Response({'error': 'Venta no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
