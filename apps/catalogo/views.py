from django.shortcuts import render
from django.db import IntegrityError
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import *
from .serializers import *



class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all().order_by('id')
    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        # Manejar errores de integridad y devolver mensaje más claro
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all().order_by('id')
    serializer_class = CategoriaSerializer
    #permission_classes = [IsAuthenticated]
    
import cloudinary.uploader

class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all().order_by('id')
    serializer_class = ProductoSerializer
    #permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        try:
            imagen = request.FILES.get('imagen')
            imagen_url = None
            if imagen:
                result = cloudinary.uploader.upload(imagen)
                imagen_url = result.get('secure_url')
                request.data['imagen_url'] = imagen_url
            return super().create(request, *args, **kwargs)
        except IntegrityError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            imagen = request.FILES.get('imagen')
            if imagen:
                result = cloudinary.uploader.upload(imagen)
                imagen_url = result.get('secure_url')
                request.data['imagen_url'] = imagen_url
            return super().update(request, *args, **kwargs)
        except IntegrityError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)



class InventarioViewSet(viewsets.ModelViewSet):
    queryset = Inventario.objects.all().order_by('id')
    serializer_class = InventarioSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class InventarioProductoViewSet(viewsets.ModelViewSet):
    queryset = InventarioProducto.objects.all().order_by('id')
    serializer_class = InventarioProductoSerializer
    permission_classes = [IsAuthenticated]

