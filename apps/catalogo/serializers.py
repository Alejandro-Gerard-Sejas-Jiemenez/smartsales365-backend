from rest_framework import serializers
from .models import *
from apps.acceso_seguridad.models import Usuario


class ClienteSerializer(serializers.ModelSerializer):
    usuario = serializers.PrimaryKeyRelatedField(queryset=Usuario.objects.all())

    class Meta:
        model = Cliente
        fields = [
            "id",
            "ciudad",
            "codigo_postal",
            "preferencia_compra",
            "total_compras",
            "usuario",
        ]

    def create(self, validated_data):
        # usuario ya viene en validated_data por source='usuario'
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = [
            "id",
            "nombre",
            "estado",
        ]
        
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
            "unidad_medida",
            "imagen_url",
            "estado",
            "stock_actual",
            "ano_garantia",
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
        ]


class InventarioSerializer(serializers.ModelSerializer):
    productos = serializers.SerializerMethodField()

    class Meta:
        model = Inventario
        fields = [
            "id",
            "nombre",
            "productos",
        ]

    def get_productos(self, obj) -> list:
        inventario_productos = InventarioProducto.objects.filter(inventario=obj)
        return InventarioProductoSerializer(inventario_productos, many=True).data
