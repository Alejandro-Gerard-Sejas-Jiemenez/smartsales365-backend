from django.db import models
from apps.catalogo.models import Producto, Cliente
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal

class Venta(models.Model):
    # --- Versión Fusionada (Tomada de 'Incoming' 933fcff...) ---
    class MetodoEntrada(models.TextChoices):
        WEB = 'Web', 'Web'
        MOVIL = 'Móvil', 'Móvil'
        TELEFONO = 'Teléfono', 'Teléfono'
        MOSTRADOR = 'Mostrador', 'Mostrador'
    
    class TipoVenta(models.TextChoices):
        CONTADO = 'Contado', 'Contado'
    
    cliente = models.ForeignKey(Cliente, on_delete=models.RESTRICT, null=True)
    fecha_venta = models.DateTimeField(default=timezone.now)
    
    metodo_entrada = models.CharField(max_length=50, choices=MetodoEntrada.choices, default=MetodoEntrada.MOVIL)
    tipo_venta = models.CharField(max_length=50, choices=TipoVenta.choices, default=TipoVenta.CONTADO)
    
    total = models.DecimalField(
        max_digits=12, decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        default=0.00
    )
    # --- Fin de la Versión Fusionada ---

    class Meta:
        ordering = ['-fecha_venta']
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'

    def __str__(self):
        # --- Versión Fusionada (Tomada de 'Incoming' 933fcff...) ---
        return f"Venta {self.id} - {self.cliente.usuario.correo} - Total: {self.total}"
    
    # --- Versión Fusionada (Tomada de 'HEAD' para compatibilidad) ---
    @property
    def total_venta(self):
        return self.total


class DetalleVenta(models.Model):
    """
    Detalle de los productos en una Venta.
    """
    venta = models.ForeignKey(Venta, related_name='detalles', on_delete=models.CASCADE)
    
    producto = models.ForeignKey(Producto, on_delete=models.RESTRICT)
    
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    # --- Versión Fusionada (Tomada de 'Incoming' 933fcff...) ---
    # (max_digits=12 es mejor, y default=timezone.now es más seguro para migraciones)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2) 
    fecha_creacion = models.DateTimeField(default=timezone.now)
    # --- Fin de la Versión Fusionada ---
    
    class Meta:
        ordering = ['id']
        verbose_name = 'Detalle de Venta'
        verbose_name_plural = 'Detalles de Ventas'

    def __str__(self):
        return f"Venta {self.venta.id} - Producto {self.producto.nombre}"

class Carrito(models.Model):
    # --- Sin Conflicto ---
    class EstadoCarrito(models.TextChoices):
        ACTIVO = 'Activo', 'Activo'
        ABANDONADO = 'Abandonado', 'Abandonado'
        CONVERTIDO = 'Convertido', 'Convertido' 

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='carrito')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    estado = models.CharField(max_length=20, choices=EstadoCarrito.choices, default=EstadoCarrito.ACTIVO)
    origen = models.CharField(max_length=50, default='FlutterApp') 
    
    class Meta:
        ordering = ['-fecha_actualizacion']
        verbose_name = 'Carrito'
        verbose_name_plural = 'Carritos'

    def __str__(self):
        # --- Versión Fusionada (Tomada de 'Incoming' 933fcff...) ---
        # (Es más descriptiva)
        return f"Carrito {self.id} de {self.cliente.usuario.correo} ({self.estado})"

class DetalleCarrito(models.Model):
    # --- Sin Conflicto ---
    """
    Productos dentro de un Carrito.
    """
    carrito = models.ForeignKey(Carrito, related_name='detalles', on_delete=models.CASCADE)
    
    producto = models.ForeignKey(Producto, on_delete=models.RESTRICT)
    
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    fecha_agregada = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-fecha_agregada']
        verbose_name = 'Detalle de Carrito'
        verbose_name_plural = 'Detalles de Carritos'

    def __str__(self):
        return f"Carrito {self.carrito.id} - Producto {self.producto.nombre}"

class Pago(models.Model):
    # --- Sin Conflicto ---
    """
    Gestión de Pagos (Stripe y PayPal).
    """
    ESTADOS_PAGO = [
        ('Pendiente', 'Pendiente'),
        ('Procesando', 'Procesando'),
        ('Aprobado', 'Aprobado'),
        ('Rechazado', 'Rechazado'),
        ('Reembolsado', 'Reembolsado'),
        ('Cancelado', 'Cancelado'),
    ]
    
    METODOS_PAGO = [
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('efectivo', 'Efectivo'),
    ]
    
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='pagos', null=True)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    metodo_pago = models.CharField(max_length=20, choices=METODOS_PAGO)
    estado = models.CharField(max_length=20, choices=ESTADOS_PAGO, default='Pendiente')
    
    stripe_payment_intent_id = models.CharField(max_length=200, null=True, blank=True)
    stripe_client_secret = models.CharField(max_length=300, null=True, blank=True)
    paypal_order_id = models.CharField(max_length=200, null=True, blank=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    referencia_pago = models.CharField(max_length=100, null=True, blank=True)
    
    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
    
    def __str__(self):
        return f'Pago #{self.id} (Venta #{self.venta.id}) - Bs{self.monto} ({self.estado})'
