from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone

class UsuarioManager(BaseUserManager):
    def create_user(self, correo, password=None, **extra):
        if not correo:
            raise ValueError('El correo es obligatorio')
        correo = self.normalize_email(correo)
        user = self.model(correo=correo, **extra)
        if password:
            user.set_password(password)  # hash
        else:
            user.set_unusable_password()
        user.save()
        return user

    def create_superuser(self, correo, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        extra.setdefault('is_active', True)
        if extra.get('is_staff') is not True:
            raise ValueError('Superusuario requiere is_staff=True')
        if extra.get('is_superuser') is not True:
            raise ValueError('Superusuario requiere is_superuser=True')
        return self.create_user(correo, password, **extra)


class Usuario(AbstractBaseUser, PermissionsMixin):
    correo = models.EmailField(unique=True)
    nombre = models.CharField(max_length=100, blank=True)
    apellido = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)

    is_active = models.BooleanField(default=True)      
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    actualizado = models.DateTimeField(auto_now=True)
    
    # Campos para control de intentos fallidos
    intentos_fallidos = models.IntegerField(default=0)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)
    
    # Campos para recuperación de contraseña
    token_recuperacion = models.CharField(max_length=100, null=True, blank=True)
    token_expira = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'correo'
    REQUIRED_FIELDS = []  
    objects = UsuarioManager()

    def __str__(self):
        return self.correo

    class Meta:
        db_table = 'usuario'
        ordering = ['correo']
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def esta_bloqueado(self):
        """Verifica si el usuario está bloqueado por intentos fallidos"""
        if self.bloqueado_hasta and timezone.now() < self.bloqueado_hasta:
            return True
        return False
    
    def incrementar_intentos_fallidos(self):
        """Incrementa los intentos fallidos y bloquea si llega a 3"""
        self.intentos_fallidos += 1
        if self.intentos_fallidos >= 3:
            # Bloquear por 30 minutos
            self.bloqueado_hasta = timezone.now() + timezone.timedelta(minutes=30)
        self.save()
    
    def resetear_intentos_fallidos(self):
        """Resetea los intentos fallidos al login exitoso"""
        self.intentos_fallidos = 0
        self.bloqueado_hasta = None
        self.save()

class Bitacora(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    accion = models.CharField(max_length=100)  # 'LOGIN', 'LOGOUT', 'CREAR_USUARIO', etc.
    descripcion = models.TextField(blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bitacora'
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.usuario.correo} - {self.accion} - {self.fecha}"
    
class Aviso(models.Model):#va a notificaciones
    ESTADO_CHOICES = (
        ('PENDIENTE', 'Pendiente'),
        ('ENVIADO', 'Enviado'),
        ('FALLIDO', 'Fallido'),
    )
    
    asunto = models.CharField(max_length=200)
    mensaje = models.TextField()
    fecha_push = models.DateField(null=True, blank=True)
    hora_push = models.TimeField(null=True, blank=True)
    urgente = models.BooleanField(default=False) 
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, blank=True)

    def __str__(self):
        return self.asunto

    class Meta:
        db_table = 'aviso'
        verbose_name = 'Aviso'
        verbose_name_plural = 'Avisos'
        ordering = ['-fecha_push']