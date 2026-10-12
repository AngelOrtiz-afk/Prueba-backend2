from django.urls import path

from . import views

app_name = "inventario"

urlpatterns = [
    path("", views.ProductoListView.as_view(), name="producto-list"),
    path("productos/nuevo/", views.ProductoCreateView.as_view(), name="producto-create"),
    path("productos/<int:pk>/", views.ProductoDetailView.as_view(), name="producto-detail"),
    path("productos/<int:pk>/editar/", views.ProductoUpdateView.as_view(), name="producto-update"),
    path("productos/<int:pk>/eliminar/", views.ProductoDeleteView.as_view(), name="producto-delete"),
    path("ventas/", views.VentaListView.as_view(), name="venta-list"),
    path("ventas/nueva/", views.VentaCreateView.as_view(), name="venta-create"),
    path("ventas/<int:pk>/", views.VentaDetailView.as_view(), name="venta-detail"),
    path("ventas/<int:pk>/editar/", views.VentaUpdateView.as_view(), name="venta-update"),
    path("ventas/<int:pk>/eliminar/", views.VentaDeleteView.as_view(), name="venta-delete"),
]
