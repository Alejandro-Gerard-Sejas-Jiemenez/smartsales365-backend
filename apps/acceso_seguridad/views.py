from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .utils import enviar_email_brevo
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
import random
import string
import secrets

from .models import Usuario, Bitacora, Aviso
from .serializers import (
    UsuarioReadSerializer,
    UsuarioWriteSerializer,
    RegistroSerializer,
    PerfilSerializer,
    CambiarPasswordSerializer,
    BitacoraSerializer,
    LoginSerializer,
    LogoutSerializer,
    SolicitarRecuperacionSerializer,
    ConfirmarRecuperacionSerializer,
    RecuperarPasswordSerializer,
    AvisoSerializer
)


# LOGIN usando correo + password => devuelve access / refresh y usuario
class LoginJWTView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        correo = request.data.get("correo")
        password = request.data.get("password")

        # Verificar si existe el usuario
        try:
            usuario = Usuario.objects.get(correo=correo)

            # Verificar si está bloqueado
            if usuario.esta_bloqueado():
                tiempo_restante = (
                    usuario.bloqueado_hasta - timezone.now()
                ).seconds // 60
                return Response(
                    {
                        "detail": "Usuario bloqueado por múltiples intentos fallidos",
                        "bloqueado": True,
                        "minutos_restantes": tiempo_restante,
                    },
                    status=status.HTTP_423_LOCKED,
                )

        except Usuario.DoesNotExist:
            return Response(
                {"detail": "Credenciales inválidas"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Autenticar
        user = authenticate(request, correo=correo, password=password)
        if not user:
            # Incrementar intentos fallidos
            usuario.incrementar_intentos_fallidos()
            registrar_bitacora(
                usuario,
                "LOGIN_FALLIDO",
                f'Intento de login fallido desde {request.META.get("REMOTE_ADDR", "IP desconocida")}',
                request,
            )

            if usuario.intentos_fallidos >= 3:
                return Response(
                    {
                        "detail": "Usuario bloqueado por múltiples intentos fallidos. Solicita recuperación de contraseña.",
                        "bloqueado": True,
                        "debe_recuperar": True,
                    },
                    status=status.HTTP_423_LOCKED,
                )

            return Response(
                {
                    "detail": "Credenciales inválidas",
                    "intentos_restantes": 3 - usuario.intentos_fallidos,
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {"detail": "Usuario inactivo"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Login exitoso - resetear intentos fallidos
        user.resetear_intentos_fallidos()
        registrar_bitacora(
            user,
            "LOGIN",
            f'Login exitoso desde {request.META.get("REMOTE_ADDR", "IP desconocida")}',
            request,
        )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "usuario": UsuarioReadSerializer(user).data,
            }
        )


# PERFIL (requiere Bearer token)
class PerfilView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PerfilSerializer

    def get(self, request):
        ser = PerfilSerializer(request.user)
        user = request.user
        registrar_bitacora(
            user,
            "PERFIL",
            f'Acceso a perfil desde {request.META.get("REMOTE_ADDR", "IP desconocida")}',
            request,
        )
        return Response(ser.data)

# USUARIOS CRUD
class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = (
        Usuario.objects.all()
        .order_by("id")
    )

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return UsuarioWriteSerializer
        return UsuarioReadSerializer

    @action(detail=True, methods=["post"])
    def cambiar_password(self, request, pk=None):
        usuario = self.get_object()
        serializer = CambiarPasswordSerializer(data=request.data)

        if serializer.is_valid():
            # Verificar password actual
            if not usuario.check_password(serializer.validated_data["password_actual"]):
                return Response({"detail": "Contraseña actual incorrecta"}, status=400)

            # Cambiar password
            usuario.set_password(serializer.validated_data["password_nueva"])
            usuario.save()
            return Response({"detail": "Contraseña actualizada correctamente"})

        return Response(serializer.errors, status=400)


class LogoutJWTView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LogoutSerializer

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "Falta refresh"}, status=400)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()  # requiere app blacklist
        except Exception:
            return Response({"detail": "Refresh inválido"}, status=400)
        return Response({"detail": "OK"})


class RegistroView(APIView):
    permission_classes = [AllowAny]
    serializer_class = RegistroSerializer

    def post(self, request):
        ser = RegistroSerializer(data=request.data)
        if ser.is_valid():
            user = ser.save()
            registrar_bitacora(
                user,
                "REGISTRO",
                f'Registro exitoso desde {request.META.get("REMOTE_ADDR", "IP desconocida")}',
                request,
            )
            return Response(
                {"id": user.id, "correo": user.correo}, status=status.HTTP_201_CREATED
            )
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


# Recuperar contraseña - Simple sin email
class RecuperarPasswordView(APIView):
    permission_classes = [AllowAny]
    serializer_class = RecuperarPasswordSerializer

    def post(self, request):
        serializer = RecuperarPasswordSerializer(data=request.data)
        if serializer.is_valid():
            correo = serializer.validated_data["correo"]
            try:
                usuario = Usuario.objects.get(correo=correo, is_active=True)

                # Generar password temporal simple
                temp_password = "".join(
                    random.choices(string.ascii_letters + string.digits, k=8)
                )
                usuario.set_password(temp_password)
                usuario.save()
                registrar_bitacora(
                    usuario,
                    "RECUPERAR_PASSWORD",
                    f'Contraseña recuperada desde {request.META.get("REMOTE_ADDR", "IP desconocida")}',
                    request,
                )
                # Aquí podrías enviar email (opcional)
                # Por ahora solo retorna la password temporal (para proyecto universitario)
                return Response(
                    {
                        "detail": "Password temporal generada",
                        "temp_password": temp_password,  # En producción NO hagas esto
                    }
                )

            except Usuario.DoesNotExist:
                # No revelar si el usuario existe o no
                return Response(
                    {"detail": "Si el correo existe, se enviará la nueva contraseña"}
                )

        return Response(serializer.errors, status=400)


# Solicitar recuperación de contraseña - Envía email con token
class SolicitarRecuperacionView(APIView):
    permission_classes = [AllowAny]
    serializer_class = SolicitarRecuperacionSerializer

    def post(self, request):
        serializer = SolicitarRecuperacionSerializer(data=request.data)
        if serializer.is_valid():
            correo = serializer.validated_data["correo"]
            try:
                usuario = Usuario.objects.get(correo=correo, is_active=True)

                # Generar token seguro
                token = secrets.token_urlsafe(32)
                usuario.token_recuperacion = token
                usuario.token_expira = timezone.now() + timezone.timedelta(hours=1)
                usuario.save()

                # Enviar email con Brevo
                try:
                    enviar_email_brevo(
                        to_email=correo,
                        subject="Recuperación de Contraseña - Smart Condominium",
                        html_content=f"""
                        <p>Hola {usuario.nombre},</p>
                        <p>Has solicitado recuperar tu contraseña. Usa el siguiente token para crear una nueva contraseña:</p>
                        <p><b>{token}</b></p>
                        <p>Este token expira en 1 hora.</p>
                        <p>Si no solicitaste este cambio, ignora este email.</p>
                        <br>
                        <p>Saludos,<br>Equipo Smart Condominium</p>
                        """,
                    )

                    registrar_bitacora(
                        usuario,
                        "SOLICITAR_RECUPERACION",
                        f'Token de recuperación enviado desde {request.META.get("REMOTE_ADDR", "IP desconocida")}',
                        request,
                    )

                    return Response(
                        {
                            "detail": "Se ha enviado un token de recuperación a tu email",
                            "email_enviado": True,
                        }
                    )

                except Exception as e:
                    return Response(
                        {
                            "detail": "Error al enviar email con Brevo",
                            "error": str(e),
                            "token_temporal": token,  # Solo para desarrollo
                        }
                    )

            except Usuario.DoesNotExist:
                pass

        return Response(
            {"detail": "Si el correo existe, se enviará el token de recuperación"}
        )


# Confirmar recuperación con token
class ConfirmarRecuperacionView(APIView):
    permission_classes = [AllowAny]
    serializer_class = ConfirmarRecuperacionSerializer

    def post(self, request):
        serializer = ConfirmarRecuperacionSerializer(data=request.data)
        if serializer.is_valid():
            token = serializer.validated_data["token"]
            nueva_password = serializer.validated_data["nueva_password"]

            try:
                usuario = Usuario.objects.get(
                    token_recuperacion=token,
                    token_expira__gt=timezone.now(),
                    is_active=True,
                )

                # Cambiar contraseña
                usuario.set_password(nueva_password)
                usuario.token_recuperacion = None
                usuario.token_expira = None
                # Desbloquear usuario y resetear intentos
                usuario.resetear_intentos_fallidos()
                usuario.save()

                registrar_bitacora(
                    usuario,
                    "RECUPERACION_EXITOSA",
                    f'Contraseña recuperada exitosamente desde {request.META.get("REMOTE_ADDR", "IP desconocida")}',
                    request,
                )

                return Response(
                    {"detail": "Contraseña actualizada correctamente", "exito": True}
                )

            except Usuario.DoesNotExist:
                return Response(
                    {"detail": "Token inválido o expirado"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BitacoraViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Bitacora.objects.all().select_related("usuario").order_by("-fecha")
    serializer_class = BitacoraSerializer
    permission_classes = [IsAuthenticated]


# Función helper para registrar en bitácora
def registrar_bitacora(usuario, accion, descripcion="", request=None):
    ip = None
    if request:
        ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR"))
    Bitacora.objects.create(
        usuario=usuario, accion=accion, descripcion=descripcion, ip=ip
    )

class AvisoViewSet(viewsets.ModelViewSet):
    queryset = Aviso.objects.all().order_by('-fecha_push')
    serializer_class = AvisoSerializer