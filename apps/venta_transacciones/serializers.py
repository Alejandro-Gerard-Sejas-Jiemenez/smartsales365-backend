
from rest_framework import serializers
from .models import *
# Importamos el serializador de Producto para anidarlo
from apps.catalogo.serializers import ProductoSerializer 
# Importamos el MODELO de Usuario
from apps.acceso_seguridad.models import Usuario 


class _UsuarioSimpleSerializer(serializers.ModelSerializer):
    """Serializador interno solo para mostrar info del usuario en la venta."""
    class Meta:
        model = Usuario
        fields = ['id', 'nombre', 'apellido', 'correo']

# --- Serializador de Detalle (Lectura) ---
class DetalleVentaSerializer(serializers.ModelSerializer):
    # --- Tomado de 'Incoming' (anida el producto completo) ---
    producto = ProductoSerializer(read_only=True)
    
    class Meta:
        model = DetalleVenta
        fields = [
            # --- Tomado de 'Incoming' (incluye fecha_creacion) ---
            'id', 'venta', 'producto', 'cantidad', 
            'precio_unitario', 'subtotal', 
            'fecha_creacion'
        ]

# --- Serializador de Venta (Lectura) ---
class VentaReadSerializer(serializers.ModelSerializer):
    # --- Tomado de 'Incoming' (es la versión correcta) ---
    detalles = DetalleVentaSerializer(many=True, read_only=True)
    cliente = serializers.SerializerMethodField()

    class Meta:
        model = Venta
        fields = [
            'id', 
            'cliente', 
            'fecha_venta', 
            'metodo_entrada', 
            'tipo_venta', 
            'total', 
            'detalles'
        ]
    
    def get_cliente(self, obj):
        if obj.cliente and obj.cliente.usuario:
            return _UsuarioSimpleSerializer(obj.cliente.usuario).data
        return None

# --- Serializador de Venta (Escritura) ---
class VentaSerializer(serializers.ModelSerializer):
    # --- (Sin Conflicto) ---
    class Meta:
        model = Venta
        fields = [
            'id', 
            'cliente', 
            'fecha_venta', 
            'metodo_entrada', 
            'tipo_venta', 
            'total', 
        ]
        read_only_fields = ['total', 'fecha_venta']


# --- Serializadores de Carrito ---
class DetalleCarritoSerializer(serializers.ModelSerializer):
    # --- Tomado de 'Incoming' (anida el producto completo) ---
    producto = ProductoSerializer(read_only=True)
    
    class Meta:
        model = DetalleCarrito
        fields = [
            # --- Tomado de 'Incoming' (incluye fecha_agregada) ---
            'id', 'carrito', 'producto', 'cantidad', 
            'precio_unitario', 'subtotal',
            'fecha_agregada'
        ]

class CarritoSerializer(serializers.ModelSerializer):
    # --- Tomado de 'Incoming' (sincronizado con models.py) ---
    detalles = DetalleCarritoSerializer(many=True, read_only=True) 
    
    class Meta:
        model = Carrito
        fields = [
            'id', 'cliente', 'fecha_creacion', 
            'fecha_actualizacion', 
            'estado', 
            'origen', 
            'detalles'
            # 'total' se quitó (correcto)
        ]

# --- Serializador de Pago ---
class PagoSerializer(serializers.ModelSerializer):
    # --- Tomado de 'Incoming' (usa VentaReadSerializer) ---
    venta = VentaReadSerializer(read_only=True)
    venta_id = serializers.PrimaryKeyRelatedField(queryset=Venta.objects.all(), source='venta', write_only=True)
    
    class Meta:
        model = Pago
        fields = [
            'id', 'venta', 'venta_id', 'monto', 'metodo_pago', 'estado',
            'stripe_payment_intent_id', 
            'stripe_client_secret',
            'paypal_order_id', 
            'fecha_creacion', 'fecha_actualizacion', 'referencia_pago'
        ]
        read_only_fields = [
            'stripe_payment_intent_id', 
            'stripe_client_secret',
            'paypal_order_id'
        ]