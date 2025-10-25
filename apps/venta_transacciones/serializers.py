
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
    class Meta:
        model = Venta
        fields = [
            'id', 'fecha_venta', 'total_venta', 'detalles'
        ]

class DetalleCarritoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    class Meta:
        model = DetalleCarrito
        fields = [
            'id', 'carrito', 'producto', 'producto_nombre', 'cantidad', 'precio_unitario', 'subtotal'
        ]

class CarritoSerializer(serializers.ModelSerializer):
    detalles = DetalleCarritoSerializer(many=True, read_only=True, source='detallecarrito_set')
    class Meta:
        model = Carrito
        fields = [
            'id', 'cliente', 'fecha_creacion', 'total', 'detalles'
        ]

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