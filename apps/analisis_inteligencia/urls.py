from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register('predicciones-ventas', PrediccionVentasViewSet, basename='predicciones-ventas')
urlpatterns = [
    path('', include(router.urls)),
]