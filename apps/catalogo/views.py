from rest_framework import viewsets, permissions, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from apps.acceso_seguridad.models import Usuario
from apps.acceso_seguridad.permissions import IsAdminRole 
from .models import *
from .serializers import (
    ClienteReadSerializer, 
    ClienteWriteSerializer, 
    CategoriaSerializer, 
    ProductoSerializer, 
    InventarioSerializer,
    InventarioProductoSerializer
)


class ClienteViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminRole]
    queryset = Usuario.objects.filter(rol='CLIENTE').select_related('cliente').order_by('nombre')
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'apellido', 'correo', 'cliente__ciudad']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ClienteWriteSerializer
        return ClienteReadSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        self.perform_create(serializer) 
        
        serializer.instance.refresh_from_db()

        read_serializer = ClienteReadSerializer(serializer.instance)
        
        headers = self.get_success_headers(read_serializer.data)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        serializer.instance.refresh_from_db()

        read_serializer = ClienteReadSerializer(instance)
        
        return Response(read_serializer.data)


    @action(detail=True, methods=['post'], url_path='toggle-estado')
    def toggle_estado(self, request, pk=None):
        try:
            usuario = self.get_object() 
            if usuario.rol != 'CLIENTE':
               return Response({"detail": "Este usuario no es un cliente."}, status=status.HTTP_400_BAD_REQUEST)
            
            usuario.is_active = not usuario.is_active
            usuario.save()
            
            serializer = ClienteReadSerializer(usuario) 
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"detail": f"Error al cambiar el estado: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

# --- ViewSets para los otros modelos de Catálogo ---
class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all().order_by('id')
    serializer_class = CategoriaSerializer
    permission_classes = [IsAdminRole]
    
class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all().order_by('id')
    serializer_class = ProductoSerializer
    permission_classes = [IsAdminRole]
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'codigo_producto', 'categoria__nombre']

class InventarioViewSet(viewsets.ModelViewSet):
    queryset = Inventario.objects.all().order_by('id')
    serializer_class = InventarioSerializer
    permission_classes = [IsAdminRole]

class InventarioProductoViewSet(viewsets.ModelViewSet):
    queryset = InventarioProducto.objects.all().order_by('id')
    serializer_class = InventarioProductoSerializer
    permission_classes = [IsAdminRole]

