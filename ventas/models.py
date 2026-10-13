from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from inventario.models import Producto
from inventario.validators import solo_letras_validator

class Venta(models.Model):
    fecha = models.DateTimeField(default=timezone.now)
    cliente = models.CharField(max_length=150, blank=True, validators=[solo_letras_validator])
    observacion = models.TextField(blank=True)
    total = models.PositiveIntegerField(default=0, editable=False)

    def recalcular_total(self):
        self.total = sum(detalle.subtotal for detalle in self.detalles.all())
        self.save(update_fields=("total",))
        return self.total

    def __str__(self):
        return f"Venta #{self.pk}"

    class Meta:
        verbose_name = "venta"
        verbose_name_plural = "ventas"
        ordering = ("-fecha",)


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey("inventario.Producto", on_delete=models.PROTECT, related_name="detalles_venta")
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.PositiveIntegerField(null=True, blank=True)

    @property
    def subtotal(self):
        return self.cantidad * (self.precio_unitario or 0)

    def clean(self):
        if self.cantidad < 1:
            raise ValidationError({"cantidad": "La cantidad debe ser al menos 1."})
        if self.producto_id and not self.producto.activo:
            anterior = self.__class__.objects.filter(pk=self.pk).only("producto_id").first() if self.pk else None
            if not anterior or anterior.producto_id != self.producto_id:
                raise ValidationError("El producto está inactivo y no se puede vender.")
        if self.producto_id:
            stock_disponible = Producto.objects.only("stock").get(pk=self.producto_id).stock
            anterior = self.__class__.objects.filter(pk=self.pk).only("producto_id", "cantidad").first() if self.pk else None
            if anterior and anterior.producto_id == self.producto_id:
                stock_disponible += anterior.cantidad
            if self.cantidad > stock_disponible:
                raise ValidationError({"cantidad": "La cantidad supera el stock disponible."})

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.precio_unitario is None:
                self.precio_unitario = self.producto.precio
            anterior = self.__class__.objects.select_for_update().get(pk=self.pk) if self.pk else None
            if anterior and anterior.producto_id != self.producto_id:
                producto_anterior = Producto.objects.select_for_update().get(pk=anterior.producto_id)
                producto_anterior.stock += anterior.cantidad
                producto_anterior.save(update_fields=("stock",))

            producto = Producto.objects.select_for_update().get(pk=self.producto_id)
            if not producto.activo and (not anterior or anterior.producto_id != self.producto_id):
                raise ValidationError("El producto está inactivo y no se puede vender.")
            if anterior and anterior.producto_id == self.producto_id:
                diferencia = self.cantidad - anterior.cantidad
            else:
                diferencia = self.cantidad
            if diferencia > producto.stock:
                raise ValidationError("La cantidad supera el stock disponible.")
            producto.stock -= diferencia
            producto.save(update_fields=("stock",))
            super().save(*args, **kwargs)
            self.venta.recalcular_total()

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            detalle = self.__class__.objects.select_for_update().get(pk=self.pk)
            producto = Producto.objects.select_for_update().get(pk=detalle.producto_id)
            producto.stock += detalle.cantidad
            producto.save(update_fields=("stock",))
            venta = detalle.venta
            result = super().delete(*args, **kwargs)
            venta.recalcular_total()
            return result

    class Meta:
        verbose_name = "detalle de venta"
        verbose_name_plural = "detalles de venta"
        ordering = ("id",)
