from django.core.management.base import BaseCommand
from django.db import transaction

from inventario.models import Producto
from ventas.models import DetalleVenta, Venta


class Command(BaseCommand):
    help = "Carga productos y ventas de demostración de forma idempotente."

    @transaction.atomic
    def handle(self, *args, **options):
        productos = []
        for index in range(1, 11):
            producto, _ = Producto.objects.get_or_create(
                nombre=f"Producto demo {index}",
                defaults={"descripcion": "Producto de demostración", "precio": index * 1000, "stock": 50},
            )
            productos.append(producto)
        for index in range(1, 6):
            venta, created = Venta.objects.get_or_create(cliente=f"Cliente demo {index}")
            if created:
                DetalleVenta.objects.create(venta=venta, producto=productos[index - 1], cantidad=index)
        self.stdout.write(self.style.SUCCESS("Datos demo cargados correctamente."))
