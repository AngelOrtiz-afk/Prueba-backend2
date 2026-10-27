from rest_framework.routers import DefaultRouter

from .views import ProductoViewSet, VentaViewSet

router = DefaultRouter()
router.register("productos", ProductoViewSet, basename="producto")
router.register("ventas", VentaViewSet, basename="venta")

urlpatterns = router.urls
