from django.db import transaction
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from inventario.models import Producto

from .models import Venta


@receiver(pre_delete, sender=Venta)
def reponer_stock_al_eliminar_venta(sender, instance, **kwargs):
    with transaction.atomic():
        for detalle in instance.detalles.all().only("producto_id", "cantidad"):
            producto = Producto.objects.select_for_update().get(pk=detalle.producto_id)
            producto.stock += detalle.cantidad
            producto.save(update_fields=("stock",))
