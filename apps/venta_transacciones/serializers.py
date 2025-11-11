
from rest_framework import serializers
from .models import *

class DetalleVentaSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    class Meta:
        model = DetalleVenta
        fields = [
            'id', 'venta', 'producto', 'producto_nombre', 'cantidad', 'precio_unitario', 'subtotal'
        ]

class VentaSerializer(serializers.ModelSerializer):
    detalles = DetalleVentaSerializer(many=True, read_only=True)
    total_venta = serializers.DecimalField(source='total', max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Venta
        fields = [
            'id', 'cliente', 'fecha_venta', 'total', 'total_venta', 'metodo_entrada', 'tipo_venta', 'detalles'
        ]
        read_only_fields = ['fecha_venta']

class DetalleCarritoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_imagen = serializers.CharField(source='producto.imagen_url', read_only=True)
    producto_info = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = DetalleCarrito
        fields = [
            'id', 'carrito', 'producto', 'producto_nombre', 'producto_imagen', 
            'producto_info', 'cantidad', 'precio_unitario', 'subtotal'
        ]
        read_only_fields = ['carrito', 'precio_unitario', 'subtotal']  # Se calculan automáticamente
    
    def get_producto_info(self, obj):
        """Devuelve información completa del producto"""
        from apps.catalogo.serializers import ProductoSerializer
        return ProductoSerializer(obj.producto).data

class CarritoSerializer(serializers.ModelSerializer):
    detalles = DetalleCarritoSerializer(many=True, read_only=True, source='detallecarrito_set')
    cliente_nombre = serializers.CharField(source='cliente.usuario.nombre', read_only=True)
    cliente_correo = serializers.CharField(source='cliente.usuario.correo', read_only=True)
    
    class Meta:
        model = Carrito
        fields = [
            'id', 'cliente', 'cliente_nombre', 'cliente_correo', 'fecha_creacion', 'total', 'detalles'
        ]
        read_only_fields = ['cliente', 'fecha_creacion', 'total']  # El cliente se asigna automáticamente

class PagoSerializer(serializers.ModelSerializer):
    venta = VentaSerializer(read_only=True)
    venta_id = serializers.PrimaryKeyRelatedField(queryset=Venta.objects.all(), source='venta', write_only=True)
    class Meta:
        model = Pago
        fields = [
            'id', 'venta', 'venta_id', 'monto', 'metodo_pago', 'estado',
            'stripe_payment_intent_id', 'stripe_client_secret',
            'fecha_creacion', 'fecha_actualizacion', 'referencia_pago', 'notas'
        ]
        read_only_fields = ['stripe_payment_intent_id', 'stripe_client_secret']

class PagoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pago
        fields = ['venta', 'monto', 'metodo_pago']