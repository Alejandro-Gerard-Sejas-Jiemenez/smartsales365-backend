
from apps.acceso_seguridad.models import Usuario
from django.db import models
from django.utils import timezone

class Cliente(models.Model):

    ciudad = models.CharField(max_length=120)
    codigo_postal = models.CharField(max_length=20)
    preferencia_compra = models.CharField(max_length=100, blank=True)#creo que lo voy a eliminar ese atributo 
    total_compras = models.PositiveIntegerField(default=0)#aqui se almacenara las compras totales realizadas por el cliente
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    
    class Meta:
        ordering = ['id']
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

    def __str__(self):
        return self.usuario.correo

class Categoria(models.Model):
    nombre = models.CharField(max_length=150)
    estado = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['id']
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
    def __str__(self):
        return self.nombre
    
    
class Producto(models.Model):

    codigo_producto = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2)
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2)
    unidad_medida = models.CharField(max_length=50)#creo que lo eliminar ese atributo 
    imagen_url = models.URLField(max_length=200, blank=True)
    estado = models.BooleanField(default=True)
    stock_actual = models.PositiveIntegerField(default=0)
    ano_garantia = models.PositiveIntegerField(default=0)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='productos')
    
    class Meta:
        ordering = ['id']
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'

    def __str__(self):
        return f"{self.nombre} - {self.codigo_producto}"

# Clase Inventario con relación muchos a muchos usando modelo intermedio
class Inventario(models.Model):
    nombre = models.CharField(max_length=100)
    productos = models.ManyToManyField(Producto, through='InventarioProducto', related_name='inventarios', help_text='INV-PROD-234')
    class Meta:
        ordering = ['id']
        verbose_name = 'Inventario'
        verbose_name_plural = 'Inventarios'

    def __str__(self):
        return self.nombre

# Modelo intermedio para Inventario y Producto
class InventarioProducto(models.Model):
    inventario = models.ForeignKey(Inventario, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=0)
    fecha_ingreso = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('inventario', 'producto')
        verbose_name = 'Inventario Producto'
        verbose_name_plural = 'Inventario Productos'

    def __str__(self):
        return f"{self.inventario.nombre} - {self.producto.nombre} ({self.cantidad})"

