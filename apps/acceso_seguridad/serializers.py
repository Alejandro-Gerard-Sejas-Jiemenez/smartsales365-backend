from rest_framework import serializers
from .models import Usuario, Bitacora, Aviso 

class UsuarioReadSerializer(serializers.ModelSerializer):

    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)

    class Meta:
        model = Usuario
        fields = ['id', 'correo', 'nombre', 'apellido', 'telefono', 'is_active', 'last_login', 'cliente_nombre']

class UsuarioWriteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Usuario
        fields = ['id', 'correo', 'password', 'nombre', 'apellido', 'telefono', 'is_active']

    def to_internal_value(self, data):
        if self.instance and 'password' not in data:
            self.fields['password'].required = False
        return super().to_internal_value(data)

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = Usuario.objects.create_user(password=password, **validated_data)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class RegistroSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=4)

    class Meta:
        model = Usuario
        fields = ['id', 'correo', 'password', 'nombre', 'apellido']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = Usuario(**validated_data)
        user.set_password(password)
        user.is_active = True
        user.save()
        return user

class PerfilSerializer(serializers.ModelSerializer):
    usuario_info = serializers.SerializerMethodField() 
    class Meta:
        model = Usuario
        fields = ['id', 'correo', 'nombre', 'apellido',  'usuario_info']

    def get_usuario_info(self, obj):
        if obj.usuario:
            return {
                'id': obj.usuario.id,
                'nombre': obj.usuario.nombre,
                'apellidos': obj.usuario.apellidos
            }
        return None

class RecuperarPasswordSerializer(serializers.Serializer):
    correo = serializers.EmailField()

class CambiarPasswordSerializer(serializers.Serializer):
    password_actual = serializers.CharField()
    password_nueva = serializers.CharField(min_length=4)


class LoginSerializer(serializers.Serializer):
    correo = serializers.EmailField()
    password = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

class BitacoraSerializer(serializers.ModelSerializer):
    usuario_correo = serializers.CharField(source='usuario.correo', read_only=True)

    class Meta:
        model = Bitacora
        fields = ['id', 'usuario', 'usuario_correo', 'accion', 'descripcion', 'ip', 'fecha']
        read_only_fields = ['fecha']

class SolicitarRecuperacionSerializer(serializers.Serializer):
    correo = serializers.EmailField()

class ConfirmarRecuperacionSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=100)
    nueva_password = serializers.CharField(min_length=6, max_length=128)
    confirmar_password = serializers.CharField(max_length=128)
    
    def validate(self, attrs):
        if attrs['nueva_password'] != attrs['confirmar_password']:
            raise serializers.ValidationError("Las contraseñas no coinciden")
        return attrs

class AvisoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Aviso
        fields = ['id', 'asunto', 'mensaje', 'fecha_push', 'hora_push', 'urgente', 'estado']