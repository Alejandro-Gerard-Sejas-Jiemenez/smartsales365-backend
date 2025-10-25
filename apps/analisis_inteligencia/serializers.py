from rest_framework import serializers
from .models import *

class PrediccionVentasSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrediccionVentas
        fields = '__all__'