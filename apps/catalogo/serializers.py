from rest_framework import serializers
from .models import *

class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = [
            "id",
            "codigo_producto",
            "nombre",
            "descripcion",
            "precio_venta",
            "precio_compra",
            "fecha_vencimiento",
            "unidad_medida",
            "imagen_url",
            "estado",
            "fecha_creacion",
            "stock_actual",
            "categoria",
        ]


class InventarioProductoSerializer(serializers.ModelSerializer):
    producto = ProductoSerializer(read_only=True)
    producto_id = serializers.PrimaryKeyRelatedField(queryset=Producto.objects.all(), source='producto', write_only=True)

    class Meta:
        model = InventarioProducto
        fields = [
            "id",
            "inventario",
            "producto",
            "producto_id",
            "cantidad",
            "fecha_ingreso",
        ]


class InventarioSerializer(serializers.ModelSerializer):
    productos = serializers.SerializerMethodField()

    class Meta:
        model = Inventario
        fields = [
            "id",
            "nombre",
            "fecha_creacion",
            "productos",
        ]

    def get_productos(self, obj):
        inventario_productos = InventarioProducto.objects.filter(inventario=obj)
        return InventarioProductoSerializer(inventario_productos, many=True).data
