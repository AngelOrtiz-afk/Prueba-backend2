from django.db import models

from .validators import solo_letras_validator


class Producto(models.Model):
    nombre = models.CharField(max_length=100, validators=[solo_letras_validator])
    descripcion = models.TextField(blank=True)
    precio = models.PositiveIntegerField()
    stock = models.PositiveIntegerField()
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "producto"
        verbose_name_plural = "productos"
        ordering = ("nombre",)
