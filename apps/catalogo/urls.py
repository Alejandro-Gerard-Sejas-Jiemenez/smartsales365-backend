from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *


router = DefaultRouter()
router.register('productos', ProductoViewSet, basename='productos')
router.register('inventarios', InventarioViewSet, basename='inventarios')
router.register('inventario-productos', InventarioProductoViewSet, basename='inventario-productos')

urlpatterns = [
    path('', include(router.urls)),
]