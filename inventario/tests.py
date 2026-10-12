import csv
from io import StringIO

from django.contrib.admin import site
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.http import QueryDict
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .admin import StockRangeFilter, exportar_productos_csv
from .forms import DetalleVentaForm, ProductoForm, VentaForm
from .models import Producto
from ventas.models import DetalleVenta, Venta


class ProductoAdminTest(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.productos = Producto.objects.bulk_create(
			(
				Producto(nombre="Sin stock", precio=100, stock=0),
				Producto(nombre="Stock medio", precio=200, stock=25),
				Producto(nombre="Stock alto", precio=300, stock=75),
			)
		)

	def test_stock_range_filter(self):
		model_admin = site._registry[Producto]
		request = self.client.request().wsgi_request

		for value, expected_name in (
			("0-10", "Sin stock"),
			("11-50", "Stock medio"),
			("51-plus", "Stock alto"),
		):
			params = QueryDict("stock_range=" + value)
			params._mutable = True
			filter_instance = StockRangeFilter(
				request,
				params,
				Producto,
				model_admin,
			)
			self.assertQuerySetEqual(
				filter_instance.queryset(request, Producto.objects.all()),
				[expected_name],
				transform=lambda producto: producto.nombre,
			)

	def test_exportar_productos_csv(self):
		request = self.client.request().wsgi_request
		response = exportar_productos_csv(
			site._registry[Producto],
			request,
			Producto.objects.filter(nombre__in=("Sin stock", "Stock alto")),
		)

		rows = list(csv.reader(StringIO(response.content.decode("utf-8"))))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
		self.assertIn("attachment; filename=\"productos.csv\"", response["Content-Disposition"])
		self.assertEqual(rows[0], ["ID", "Nombre", "Descripción", "Precio", "Stock", "Activo"])
		self.assertEqual([row[1] for row in rows[1:]], ["Sin stock", "Stock alto"])


class VentaTest(TestCase):
	def setUp(self):
		self.producto = Producto.objects.create(nombre="Pan", precio=1000, stock=10)
		self.venta = Venta.objects.create(cliente="Ana")

	def test_total_y_stock_al_crear_detalle(self):
		detalle = DetalleVenta.objects.create(venta=self.venta, producto=self.producto, cantidad=3)
		self.producto.refresh_from_db()
		self.venta.refresh_from_db()
		self.assertEqual(detalle.subtotal, 3000)
		self.assertEqual(self.producto.stock, 7)
		self.assertEqual(self.venta.total, 3000)

	def test_repone_stock_al_eliminar_detalle(self):
		detalle = DetalleVenta.objects.create(venta=self.venta, producto=self.producto, cantidad=3)
		detalle.delete()
		self.producto.refresh_from_db()
		self.venta.refresh_from_db()
		self.assertEqual(self.producto.stock, 10)
		self.assertEqual(self.venta.total, 0)

	def test_rechaza_stock_insuficiente(self):
		with self.assertRaises(ValidationError):
			DetalleVenta.objects.create(venta=self.venta, producto=self.producto, cantidad=11)

	def test_reporte_por_rango(self):
		Venta.objects.create(cliente="Fuera", fecha=timezone.now() - timezone.timedelta(days=5))
		user = get_user_model().objects.create_user(username="admin", password="pass", is_staff=True)
		self.client.force_login(user)
		response = self.client.get(reverse("admin:ventas_reporte"), {"desde": "2000-01-01", "hasta": "2100-01-01"})
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Ventas: 2")

	def test_crud_requiere_autenticacion(self):
		response = self.client.get(reverse("inventario:producto-list"))
		self.assertRedirects(response, "/cuentas/login/?next=/")

	def test_crud_autenticado(self):
		user = get_user_model().objects.create_user(username="user", password="pass")
		self.client.force_login(user)
		response = self.client.post(reverse("inventario:producto-create"), {
			"nombre": "Leche", "descripcion": "", "precio": 900, "stock": 5, "activo": "on",
		})
		self.assertRedirects(response, reverse("inventario:producto-list"))
		self.assertTrue(Producto.objects.filter(nombre="Leche").exists())


class DeleteCrudTest(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(username="user", password="test-password")
		self.client.force_login(self.user)

	def test_elimina_producto_sin_ventas(self):
		producto = Producto.objects.create(nombre="Producto descartable", precio=100, stock=5)

		response = self.client.post(reverse("inventario:producto-delete", args=(producto.pk,)))

		self.assertRedirects(response, reverse("inventario:producto-list"))
		self.assertFalse(Producto.objects.filter(pk=producto.pk).exists())
		self.assertTrue(any("Producto eliminado correctamente." in str(message) for message in get_messages(response.wsgi_request)))

	def test_no_elimina_producto_con_ventas(self):
		producto = Producto.objects.create(nombre="Producto vendido", precio=100, stock=5)
		venta = Venta.objects.create(cliente="Ana")
		DetalleVenta.objects.create(venta=venta, producto=producto, cantidad=1)

		response = self.client.post(reverse("inventario:producto-delete", args=(producto.pk,)))

		self.assertEqual(response.status_code, 200)
		self.assertTrue(Producto.objects.filter(pk=producto.pk).exists())
		self.assertContains(response, "¿Eliminar Producto vendido?")
		self.assertTrue(any("ventas asociadas" in str(message) for message in get_messages(response.wsgi_request)))

	def test_elimina_venta_y_repone_stock(self):
		producto = Producto.objects.create(nombre="Producto vendido", precio=100, stock=5)
		venta = Venta.objects.create(cliente="Ana")
		DetalleVenta.objects.create(venta=venta, producto=producto, cantidad=2)
		producto.refresh_from_db()
		self.assertEqual(producto.stock, 3)

		response = self.client.post(reverse("inventario:venta-delete", args=(venta.pk,)))

		self.assertRedirects(response, reverse("inventario:venta-list"))
		producto.refresh_from_db()
		self.assertEqual(producto.stock, 5)
		self.assertFalse(Venta.objects.filter(pk=venta.pk).exists())
		self.assertTrue(any("stock repuesto" in str(message) for message in get_messages(response.wsgi_request)))


class ProductoCrudTest(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(username="user", password="test-password")
		self.client.force_login(self.user)

	def test_formulario_rechaza_precio_negativo_y_no_numerico(self):
		for precio, mensaje in (("-1", "mayor o igual a 0"), ("no-numero", "número entero")):
			form = ProductoForm(data={"nombre": "Producto", "descripcion": "", "precio": precio, "stock": "1", "activo": "on"})
			self.assertFalse(form.is_valid())
			self.assertIn(mensaje, form.errors["precio"][0])

	def test_listado_muestra_estado_y_filtra_activos_inactivos(self):
		Producto.objects.create(nombre="Visible activo", precio=100, stock=1, activo=True)
		Producto.objects.create(nombre="Visible inactivo", precio=100, stock=1, activo=False)
		for index in range(11):
			Producto.objects.create(nombre=f"Otro activo {index}", precio=100, stock=1, activo=True)

		response = self.client.get(reverse("inventario:producto-list"), {"estado": "activos", "page": 2})

		self.assertContains(response, "Activo")
		self.assertNotContains(response, "Visible inactivo")
		self.assertContains(response, "text-bg-success")
		self.assertContains(response, "estado=activos")

	def test_eliminar_producto_solo_aparece_en_editar(self):
		producto = Producto.objects.create(nombre="Producto", precio=100, stock=1)

		list_response = self.client.get(reverse("inventario:producto-list"))
		detail_response = self.client.get(reverse("inventario:producto-detail", args=(producto.pk,)))
		edit_response = self.client.get(reverse("inventario:producto-update", args=(producto.pk,)))

		self.assertNotContains(list_response, reverse("inventario:producto-delete", args=(producto.pk,)))
		self.assertNotContains(detail_response, reverse("inventario:producto-delete", args=(producto.pk,)))
		self.assertContains(edit_response, "btn-outline-danger")

	def test_selector_de_venta_solo_lista_productos_activos(self):
		activo = Producto.objects.create(nombre="Activo", precio=100, stock=1, activo=True)
		inactivo = Producto.objects.create(nombre="Inactivo", precio=100, stock=1, activo=False)

		form = DetalleVentaForm()

		self.assertIn(activo, form.fields["producto"].queryset)
		self.assertNotIn(inactivo, form.fields["producto"].queryset)


class LetrasValidationTest(TestCase):
	def test_normaliza_nombre_y_cliente(self):
		producto_form = ProductoForm(data={"nombre": "  María   José ", "descripcion": "", "precio": "1", "stock": "1"})
		venta_form = VentaForm(data={"fecha": "2026-10-12T10:00", "cliente": "  Ana   López ", "observacion": ""})

		self.assertTrue(producto_form.is_valid())
		self.assertEqual(producto_form.cleaned_data["nombre"], "María José")
		self.assertTrue(venta_form.is_valid())
		self.assertEqual(venta_form.cleaned_data["cliente"], "Ana López")

	def test_rechaza_nombre_y_cliente_con_numeros(self):
		producto_form = ProductoForm(data={"nombre": "Producto 2", "descripcion": "", "precio": "1", "stock": "1"})
		venta_form = VentaForm(data={"fecha": "2026-10-12T10:00", "cliente": "Cliente 2", "observacion": ""})

		self.assertFalse(producto_form.is_valid())
		self.assertIn("Este campo solo admite letras.", producto_form.errors["nombre"])
		self.assertFalse(venta_form.is_valid())
		self.assertIn("Este campo solo admite letras.", venta_form.errors["cliente"])


class InactiveProductSaleTest(TestCase):
	def setUp(self):
		self.activo = Producto.objects.create(nombre="Activo", precio=100, stock=5)
		self.inactivo = Producto.objects.create(nombre="Inactivo", precio=100, stock=5, activo=False)
		self.venta = Venta.objects.create(cliente="Ana")

	def test_producto_inactivo_no_aparece_en_selector(self):
		form = DetalleVentaForm()

		self.assertNotIn(self.inactivo, form.fields["producto"].queryset)

		form = DetalleVentaForm(
			data={"producto": str(self.inactivo.pk), "cantidad": "1", "precio_unitario": ""}
		)
		self.assertFalse(form.is_valid())
		self.assertIn("opción válida", form.errors["producto"][0])

	def test_no_se_puede_guardar_detalle_nuevo_inactivo(self):
		detalle = DetalleVenta(venta=self.venta, producto=self.inactivo, cantidad=1)

		with self.assertRaisesMessage(ValidationError, "El producto está inactivo y no se puede vender."):
			detalle.full_clean()

	def test_detalle_historico_inactivo_puede_editarse(self):
		detalle = DetalleVenta.objects.create(venta=self.venta, producto=self.activo, cantidad=1)
		self.activo.activo = False
		self.activo.save(update_fields=("activo",))

		form = DetalleVentaForm(
			data={"producto": str(self.activo.pk), "cantidad": "1", "precio_unitario": ""},
			instance=detalle,
		)

		self.assertTrue(form.is_valid(), form.errors)
