from django.db import transaction
from django.shortcuts import get_object_or_404
from django.conf import settings
import stripe

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError # Usamos la de DRF

from .models import *
from .serializers import *
from apps.catalogo.models import Producto

# --- ViewSet para Venta (CU-10) ---
class VentaViewSet(viewsets.ModelViewSet):
    # --- FUSIONADO ---
    queryset = Venta.objects.select_related('cliente__usuario').prefetch_related('detalles__producto').all().order_by('-fecha_venta')
    permission_classes = [permissions.IsAuthenticated] 

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve':
            return VentaReadSerializer
        return VentaSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        
        detalles_data = request.data.pop('detalles', [])
        if not detalles_data:
            return Response({"error": "La venta debe tener al menos un producto."}, status=status.HTTP_400_BAD_REQUEST)

        total_calculado = 0
        productos_a_actualizar = []
        detalles_a_crear = []

        try:
            for item in detalles_data:
                producto = Producto.objects.select_for_update().get(id=item['producto_id'])
                cantidad_pedida = int(item['cantidad'])

                if cantidad_pedida <= 0:
                    raise ValidationError(f"La cantidad para {producto.nombre} debe ser mayor a 0.")
                
                if producto.stock_actual < cantidad_pedida:
                    raise ValidationError(f"Stock insuficiente para '{producto.nombre}'. Disponible: {producto.stock_actual}, Pedido: {cantidad_pedida}")

                producto.stock_actual -= cantidad_pedida
                productos_a_actualizar.append(producto)

                subtotal = producto.precio_venta * cantidad_pedida
                total_calculado += subtotal
                
                detalles_a_crear.append(
                    DetalleVenta(
                        producto=producto, 
                        cantidad=cantidad_pedida, 
                        precio_unitario=producto.precio_venta, 
                        subtotal=subtotal
                    )
                )

            venta_serializer = VentaSerializer(data=request.data)
            venta_serializer.is_valid(raise_exception=True)
            # Guardamos la venta con el total calculado
            venta = venta_serializer.save(total=total_calculado)

            for detalle in detalles_a_crear:
                detalle.venta = venta
            
            DetalleVenta.objects.bulk_create(detalles_a_crear)
            
            Producto.objects.bulk_update(productos_a_actualizar, ['stock_actual'])

            read_serializer = VentaReadSerializer(venta)
            return Response(read_serializer.data, status=status.HTTP_201_CREATED)

        except Producto.DoesNotExist:
            return Response({"error": "Uno de los productos no existe."}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Error inesperado: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def mis_compras(self, request):
        # --- FUSIONADO: Tomado de 'HEAD' (versión del Alejandro) ---
        # Esta es la lógica para que el cliente vea sus compras en la App Móvil.
        user = request.user
        
        if not hasattr(user, 'cliente'):
            return Response(
                {'detail': 'El usuario no tiene un perfil de cliente asociado.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ventas = Venta.objects.filter(
            cliente=user.cliente
        ).select_related(
            'cliente__usuario'
        ).prefetch_related(
            'detalles__producto'
        ).order_by('-fecha_venta')
        
        # Usamos VentaReadSerializer (que es más completo)
        serializer = VentaReadSerializer(ventas, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# --- ViewSet para DetalleVenta (Solo Lectura) ---
class DetalleVentaViewSet(viewsets.ReadOnlyModelViewSet):
    # --- Tomado de 'Incoming' (versión mía) ---
    queryset = DetalleVenta.objects.all().order_by('id')
    serializer_class = DetalleVentaSerializer
    permission_classes = [permissions.IsAuthenticated]

# --- ViewSet para Carrito (CU-11, Lógica Móvil) ---
class CarritoViewSet(viewsets.ModelViewSet):
    # --- FUSIONADO: Tomado de 'HEAD' (Alejandro) pero MODIFICADO ---
    serializer_class = CarritoSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'cliente'):
            return Carrito.objects.filter(cliente=user.cliente).select_related(
                'cliente', 'cliente__usuario'
            ).prefetch_related(
                'detalles__producto' # CORREGIDO: 'detalles' en lugar de 'detallecarrito_set'
            ).order_by('id')
        return Carrito.objects.none()
    
    @action(detail=False, methods=['post'])
    def vaciar_carrito(self, request):
        user = request.user
        if not hasattr(user, 'cliente'):
            return Response({'detail': 'El usuario no tiene un perfil de cliente asociado.'}, status=status.HTTP_400_BAD_REQUEST)
        
        carrito = Carrito.objects.filter(cliente=user.cliente).first()
        if not carrito:
            return Response({'detail': 'No hay carrito para vaciar'}, status=status.HTTP_404_NOT_FOUND)
        
        DetalleCarrito.objects.filter(carrito=carrito).delete()
        
        # CORREGIDO: Eliminada la lógica de 'carrito.total = 0'
        
        return Response(
            {'detail': 'Carrito vaciado exitosamente'}, 
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'])
    @transaction.atomic # Añadido para seguridad
    def crear_venta_desde_carrito(self, request):
        user = request.user
        if not hasattr(user, 'cliente'):
            return Response({'detail': 'El usuario no tiene un perfil de cliente asociado.'}, status=status.HTTP_400_BAD_REQUEST)
        
        carrito = Carrito.objects.filter(cliente=user.cliente, estado='Activo').first()
        if not carrito:
            return Response({'detail': 'No hay carrito activo disponible'}, status=status.HTTP_404_NOT_FOUND)
        
        detalles_carrito = carrito.detalles.all()
        if not detalles_carrito.exists():
            return Response({'detail': 'El carrito está vacío'}, status=status.HTTP_400_BAD_REQUEST)
        
        # --- INICIO DE LÓGICA DE STOCK (Faltaba en la versión del compañero) ---
        total_calculado = 0
        productos_a_actualizar = []
        detalles_venta_a_crear = []

        for detalle_carrito in detalles_carrito:
            producto = Producto.objects.select_for_update().get(id=detalle_carrito.producto.id)
            cantidad_pedida = detalle_carrito.cantidad

            if producto.stock_actual < cantidad_pedida:
                raise ValidationError(f"Stock insuficiente para '{producto.nombre}'. Disponible: {producto.stock_actual}, Pedido: {cantidad_pedida}")

            producto.stock_actual -= cantidad_pedida
            productos_a_actualizar.append(producto)

            subtotal = detalle_carrito.subtotal
            total_calculado += subtotal
            
            detalles_venta_a_crear.append(
                DetalleVenta(
                    # 'venta' se asignará después
                    producto=producto, 
                    cantidad=cantidad_pedida, 
                    precio_unitario=detalle_carrito.precio_unitario, 
                    subtotal=subtotal
                )
            )
        # --- FIN DE LÓGICA DE STOCK ---

        # Crear la venta
        venta = Venta.objects.create(
            cliente=user.cliente,
            total=total_calculado, # CORREGIDO: 'total' y usando el total calculado
            metodo_entrada=Venta.MetodoEntrada.MOVIL, # CORREGIDO: Usando el Enum
            tipo_venta=Venta.TipoVenta.CONTADO      # CORREGIDO: Usando el Enum
        )
        
        # Asignar la venta a los detalles y guardar
        for detalle_venta in detalles_venta_a_crear:
            detalle_venta.venta = venta
        
        DetalleVenta.objects.bulk_create(detalles_venta_a_crear)
        
        # Actualizar el Stock en la BD
        Producto.objects.bulk_update(productos_a_actualizar, ['stock_actual'])
        
        # Vaciar el carrito (Eliminar Detalles y marcar Carrito como 'Convertido')
        detalles_carrito.delete()
        carrito.estado = Carrito.EstadoCarrito.CONVERTIDO
        carrito.save()
        
        # Serializar la venta
        serializer = VentaReadSerializer(venta)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def create(self, request, *args, **kwargs):
        user = request.user
        if not hasattr(user, 'cliente'):
            raise ValidationError({'detail': 'El usuario no tiene un perfil de cliente asociado.'})

        # CORREGIDO: Buscar solo carritos Activos
        carrito_existente = Carrito.objects.filter(cliente=user.cliente, estado='Activo').first()
        if carrito_existente:
            serializer = self.get_serializer(carrito_existente)
            return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # CORREGIDO: Asignar estado 'Activo'
        serializer.save(cliente=user.cliente, estado='Activo')
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

# --- ViewSet para DetalleCarrito (CU-11, Lógica Móvil) ---
class DetalleCarritoViewSet(viewsets.ModelViewSet):
    # --- FUSIONADO: Tomado de 'HEAD' (compañero) pero MODIFICADO ---
    serializer_class = DetalleCarritoSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'cliente'):
            # CORREGIDO: 'carrito__cliente'
            return DetalleCarrito.objects.filter(carrito__cliente=user.cliente).order_by('id')
        return DetalleCarrito.objects.none()
    
    def perform_create(self, serializer):
        user = self.request.user
        if not hasattr(user, 'cliente'):
            raise ValidationError({'detail': 'El usuario no tiene un perfil de cliente asociado.'})
        
        # CORREGIDO: Buscar o crear carrito 'Activo'
        carrito, created = Carrito.objects.get_or_create(
            cliente=user.cliente,
            estado='Activo'
        )
        
        producto_id = self.request.data.get('producto')
        cantidad = int(self.request.data.get('cantidad', 1))
        
        producto = get_object_or_404(Producto, id=producto_id)

        # Validar stock antes de añadir al carrito
        if producto.stock_actual < cantidad:
            raise ValidationError({'detail': f'Stock insuficiente para {producto.nombre}. Disponible: {producto.stock_actual}'})

        detalle_existente = DetalleCarrito.objects.filter(
            carrito=carrito,
            producto=producto
        ).first()
        
        if detalle_existente:
            detalle_existente.cantidad += cantidad
            
            # Validar stock total en carrito
            if producto.stock_actual < detalle_existente.cantidad:
                raise ValidationError({'detail': f'Stock insuficiente. Ya tiene {detalle_existente.cantidad - cantidad} en el carrito. Disponible: {producto.stock_actual}'})

            detalle_existente.subtotal = detalle_existente.precio_unitario * detalle_existente.cantidad
            detalle_existente.save()
            # No usamos 'raise ValidationError' para el éxito, simplemente devolvemos el objeto
            serializer.instance = detalle_existente # Asignamos la instancia al serializador
        else:
            precio_unitario = producto.precio_venta
            subtotal = precio_unitario * cantidad
            
            serializer.save(
                carrito=carrito,
                producto=producto, # Añadimos el producto
                precio_unitario=precio_unitario,
                subtotal=subtotal
            )
        
        # CORREGIDO: Eliminada la lógica de 'carrito.total'

    def partial_update(self, request, *args, **kwargs):
        detalle = self.get_object()
        nueva_cantidad = request.data.get('cantidad')
        
        if nueva_cantidad is None:
            raise ValidationError({'detail': 'La cantidad es requerida'})
        
        nueva_cantidad = int(nueva_cantidad)
        
        if nueva_cantidad <= 0:
            detalle.delete()
            # CORREGIDO: Eliminada la lógica de 'carrito.total'
            return Response({'detail': 'Producto eliminado del carrito'}, status=status.HTTP_204_NO_CONTENT)
        
        # Validar stock
        if detalle.producto.stock_actual < nueva_cantidad:
            raise ValidationError({'detail': f'Stock insuficiente. Disponible: {detalle.producto.stock_actual}'})

        detalle.cantidad = nueva_cantidad
        detalle.subtotal = detalle.precio_unitario * nueva_cantidad
        detalle.save()
        
        # CORREGIDO: Eliminada la lógica de 'carrito.total'
        
        serializer = self.get_serializer(detalle)
        return Response(serializer.data)

# --- ViewSet de Pagos (FUSIONADO) ---
stripe.api_key = settings.STRIPE_SECRET_KEY

class PagoViewSet(viewsets.ModelViewSet):
    queryset = Pago.objects.all()
    serializer_class = PagoSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    # --- FUSIONADO: 'get_serializer_class' y 'perform_create' eliminados ---

    @action(detail=False, methods=['post'], url_path='crear-payment-intent-stripe')
    def crear_payment_intent(self, request):
        # --- FUSIONADO: Combina lo mejor de ambas versiones ---
        try:
            venta_id = request.data.get('venta_id')
            if not venta_id:
                return Response({'error': 'venta_id es requerido'}, status=status.HTTP_400_BAD_REQUEST)
            
            venta = Venta.objects.get(id=venta_id)
            monto_centavos = int(float(venta.total) * 100)
            
            intent = stripe.PaymentIntent.create(
                amount=monto_centavos,
                currency='bob', # Tomado de 'HEAD' (compañero)
                metadata={'venta_id': venta.id}
            )
            
            pago = Pago.objects.create(
                venta=venta,
                monto=venta.total,
                metodo_pago='stripe',
                estado='Pendiente', # CORREGIDO: Estado del modelo
                stripe_payment_intent_id=intent.id,
                stripe_client_secret=intent.client_secret
            )
            
            return Response({
                'payment_intent_id': intent.id,
                'client_secret': intent.client_secret,
                'pago_id': pago.id,
                'monto': float(venta.total),
                'venta_id': venta.id
            })
        except Venta.DoesNotExist:
            return Response({'error': 'Venta no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='confirmar-pago-stripe')
    def confirmar_pago_stripe(self, request):
        # --- FUSIONADO: Tomado de 'HEAD' (compañero) pero CORREGIDO ---
        try:
            payment_intent_id = request.data.get('payment_intent_id')
            if not payment_intent_id:
                return Response({'error': 'payment_intent_id es requerido'}, status=status.HTTP_400_BAD_REQUEST)

            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            if intent.status != 'succeeded':
                return Response({'error': 'El pago no ha sido completado', 'status': intent.status}, status=status.HTTP_400_BAD_REQUEST)
            
            pago = Pago.objects.filter(stripe_payment_intent_id=payment_intent_id).first()
            if not pago:
                return Response({'error': 'Pago no encontrado'}, status=status.HTTP_404_NOT_FOUND)
            
            pago.estado = 'Aprobado' # CORREGIDO: 'Aprobado'
            pago.save()
            
            # (La lógica de vaciar carrito ya se hace en 'crear_venta_desde_carrito')

            return Response({
                'message': 'Pago confirmado exitosamente',
                'pago_id': pago.id,
                'venta_id': pago.venta.id,
                'estado': 'Aprobado' # CORREGIDO: 'Aprobado'
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='confirmar-pago-efectivo')
    def confirmar_pago(self, request):
        # --- FUSIONADO: Tomado de 'Incoming' (nuestra versión) ---
        """Confirmar el pago de una venta en Efectivo (para CU-10)"""
        try:
            venta_id = request.data.get('venta_id')
            if not venta_id:
                return Response({'error': 'venta_id es requerido'}, status=status.HTTP_400_BAD_REQUEST)

            venta = Venta.objects.get(id=venta_id)
            pago = Pago.objects.filter(venta=venta, estado='Pendiente').order_by('-id').first()

            if pago:
                pago.estado = 'Aprobado'
                pago.metodo_pago = 'efectivo'
                pago.save()
            else:
                pago = Pago.objects.create(
                    venta=venta,
                    monto=venta.total,
                    metodo_pago='efectivo',
                    estado='Aprobado'
                )

            return Response({
                'message': 'Pago confirmado exitosamente',
                'pago_id': pago.id,
                'venta_id': venta.id,
                'estado': 'Aprobado'
            })
        except Venta.DoesNotExist:
            return Response({'error': 'Venta no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
