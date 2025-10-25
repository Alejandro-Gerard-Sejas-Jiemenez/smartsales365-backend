from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import PrediccionVentas
from .serializers import *

class PrediccionVentasViewSet(viewsets.ModelViewSet):
    queryset = PrediccionVentas.objects.all().order_by('id')
    serializer_class = PrediccionVentasSerializer
    permission_classes = [IsAuthenticated]
    
