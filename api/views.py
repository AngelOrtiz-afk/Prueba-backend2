from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from inventario.models import Producto
from ventas.models import Venta

from .serializers import ProductoSerializer, VentaSerializer
from .filters import ProductoFilter, VentaFilter


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok"}, status=status.HTTP_200_OK)


class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_class = ProductoFilter
    search_fields = ("nombre", "descripcion")
    ordering_fields = ("id", "nombre", "precio", "stock")
    ordering = ("-id",)


class VentaViewSet(viewsets.ModelViewSet):
    queryset = Venta.objects.prefetch_related("detalles__producto").all()
    serializer_class = VentaSerializer
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filterset_class = VentaFilter
    ordering_fields = ("fecha", "total")
    ordering = ("-fecha",)
