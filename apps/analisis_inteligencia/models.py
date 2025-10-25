from django.db import models
from apps.catalogo.models import Producto,Categoria

class PrediccionVentas(models.Model):
    fecha_prediccion = models.DateField()
    periodo_inicio = models.DateField()
    periodo_fin = models.DateField()
    venta_predicha = models.IntegerField()
    confianza = models.FloatField()
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    

    def __str__(self):
        return f"{self.producto} - {self.fecha}"

    class Meta:
        db_table = 'prediccion_ventas'
        ordering = ['-fecha_prediccion']
        verbose_name = 'Predicción de Ventas'
        verbose_name_plural = 'Predicciones de Ventas'
