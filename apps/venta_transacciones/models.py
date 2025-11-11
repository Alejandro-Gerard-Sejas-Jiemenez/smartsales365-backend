from django.db import models
from apps.catalogo.models import Producto,Cliente

class Venta(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, null=True, blank=True)
    fecha_venta = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_entrada = models.CharField(max_length=50, null=True, blank=True)
    tipo_venta = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        ordering = ['id']
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'

    def __str__(self):
        return f"Venta {self.id} - Total: {self.total}"
    
    # Propiedad de compatibilidad para código existente
    @property
    def total_venta(self):
        return self.total


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['id']
        verbose_name = 'Detalle de Venta'
        verbose_name_plural = 'Detalles de Ventas'

    def __str__(self):
        return f"Detalle {self.id} - Venta {self.venta.id} - Producto {self.producto.nombre}"

class Carrito(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ['id']
        verbose_name = 'Carrito'
        verbose_name_plural = 'Carritos'

    def __str__(self):
        return f"Carrito {self.id} - Cliente {self.cliente.usuario.correo}"

class DetalleCarrito(models.Model):
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['id']
        verbose_name = 'Detalle de Carrito'
        verbose_name_plural = 'Detalles de Carritos'

    def __str__(self):
        return f"Detalle {self.id} - Carrito {self.carrito.id} - Producto {self.producto.nombre}"
class Pago(models.Model):
    ESTADOS_PAGO = [
        ('pendiente', 'Pendiente'),
        ('procesando', 'Procesando'),
        ('completado', 'Completado'),
        ('fallido', 'Fallido'),
        ('cancelado', 'Cancelado'),
        ('reembolsado', 'Reembolsado'),
    ]
    
    METODOS_PAGO = [
        ('stripe', 'Stripe'),
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
    ]
    
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, null=True, blank=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.CharField(max_length=20, choices=METODOS_PAGO, default='stripe')
    estado = models.CharField(max_length=20, choices=ESTADOS_PAGO, default='pendiente')
    
    # Campos específicos de Stripe
    stripe_payment_intent_id = models.CharField(max_length=200, null=True, blank=True)
    stripe_client_secret = models.CharField(max_length=300, null=True, blank=True)
    
    # Timestamps y datos adicionales
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    referencia_pago = models.CharField(max_length=100, null=True, blank=True)
    notas = models.TextField(null=True, blank=True)
    
    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
    
    def __str__(self):
        return f'Pago #{self.id} - Factura #{self.factura.id} - Bs{self.monto}'
