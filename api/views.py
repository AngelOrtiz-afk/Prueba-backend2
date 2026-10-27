from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets

from inventario.models import Producto
from ventas.models import Venta

from .serializers import ProductoSerializer, VentaSerializer


class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_fields = ("activo",)
    search_fields = ("nombre", "descripcion")
    ordering_fields = ("nombre", "precio", "stock")
    ordering = ("nombre",)


class VentaViewSet(viewsets.ModelViewSet):
    queryset = Venta.objects.prefetch_related("detalles__producto").all()
    serializer_class = VentaSerializer
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filterset_fields = {
        "fecha": ("date", "date__gte", "date__lte"),
    }
    ordering_fields = ("fecha", "total")
    ordering = ("-fecha",)
