import django_filters

from inventario.models import Producto
from ventas.models import Venta


class ProductoFilter(django_filters.FilterSet):
    precio_min = django_filters.NumberFilter(field_name="precio", lookup_expr="gte")
    precio_max = django_filters.NumberFilter(field_name="precio", lookup_expr="lte")
    stock_min = django_filters.NumberFilter(field_name="stock", lookup_expr="gte")
    stock_max = django_filters.NumberFilter(field_name="stock", lookup_expr="lte")

    class Meta:
        model = Producto
        fields = ("activo", "precio_min", "precio_max", "stock_min", "stock_max")


class VentaFilter(django_filters.FilterSet):
    fecha_desde = django_filters.DateFilter(field_name="fecha", lookup_expr="date__gte")
    fecha_hasta = django_filters.DateFilter(field_name="fecha", lookup_expr="date__lte")
    cliente = django_filters.CharFilter(field_name="cliente", lookup_expr="icontains")

    class Meta:
        model = Venta
        fields = ("fecha_desde", "fecha_hasta", "cliente")
