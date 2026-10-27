from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from inventario.models import Producto
from ventas.models import DetalleVenta, Venta


class ApiTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="api-user",
            password="test-password",
        )

    def setUp(self):
        self.client.force_authenticate(self.user)

    def test_producto_list_can_be_filtered_and_searched(self):
        Producto.objects.create(nombre="Pan", descripcion="Horneado", precio=100, stock=5)
        Producto.objects.create(nombre="Leche", descripcion="Lácteo", precio=200, stock=3, activo=False)

        response = self.client.get("/api/v1/productos/?activo=true&search=Pan")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["nombre"], "Pan")

    def test_venta_creation_reuses_stock_and_total_logic(self):
        producto = Producto.objects.create(nombre="Pan", precio=100, stock=5)

        response = self.client.post(
            "/api/v1/ventas/",
            {
                "cliente": "Ana",
                "detalles": [{"producto": producto.pk, "cantidad": 2}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        venta = Venta.objects.get(pk=response.data["id"])
        detalle = DetalleVenta.objects.get(venta=venta)
        producto.refresh_from_db()
        self.assertEqual(venta.total, 200)
        self.assertEqual(detalle.precio_unitario, 100)
        self.assertEqual(producto.stock, 3)

    def test_venta_deletion_restores_stock(self):
        producto = Producto.objects.create(nombre="Pan", precio=100, stock=5)
        venta = Venta.objects.create(cliente="Ana")
        DetalleVenta.objects.create(venta=venta, producto=producto, cantidad=2)

        response = self.client.delete(f"/api/v1/ventas/{venta.pk}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        producto.refresh_from_db()
        self.assertEqual(producto.stock, 5)

    def test_unauthenticated_access_is_rejected(self):
        self.client.logout()

        response = self.client.get("/api/v1/productos/")

        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_insufficient_stock_and_inactive_product_return_400(self):
        producto = Producto.objects.create(nombre="Pan", precio=100, stock=1)
        response = self.client.post(
            "/api/v1/ventas/",
            {"detalles": [{"producto": producto.pk, "cantidad": 2}]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Venta.objects.exists())

        producto.activo = False
        producto.save(update_fields=("activo",))
        response = self.client.post(
            "/api/v1/ventas/",
            {"detalles": [{"producto": producto.pk, "cantidad": 1}]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deleting_product_with_sales_returns_409(self):
        producto = Producto.objects.create(nombre="Pan", precio=100, stock=2)
        venta = Venta.objects.create(cliente="Ana")
        DetalleVenta.objects.create(venta=venta, producto=producto, cantidad=1)

        response = self.client.delete(f"/api/v1/productos/{producto.pk}/")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("activo=false", response.data["detail"])
