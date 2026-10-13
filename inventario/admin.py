import csv
from datetime import datetime, time
from django.contrib import admin
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone

from .forms import DetalleVentaBaseFormSet, DetalleVentaForm
from .models import Producto
from ventas.models import DetalleVenta, Venta


def formato_miles(value):
    return f"{value:,}".replace(",", ".")

# Register your models here.


class StockRangeFilter(admin.SimpleListFilter):
    title = "rango de stock"
    parameter_name = "stock_range"

    def lookups(self, request, model_admin):
        return (
            ("0-10", "0 a 10 unidades"),
            ("11-50", "11 a 50 unidades"),
            ("51-plus", "51 unidades o más"),
        )

    def queryset(self, request, queryset):
        if self.value() == "0-10":
            return queryset.filter(stock__range=(0, 10))
        if self.value() == "11-50":
            return queryset.filter(stock__range=(11, 50))
        if self.value() == "51-plus":
            return queryset.filter(stock__gte=51)
        return queryset


@admin.action(description="Exportar productos seleccionados a CSV")
def exportar_productos_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="productos.csv"'

    writer = csv.writer(response)
    writer.writerow(("ID", "Nombre", "Descripción", "Precio", "Stock", "Activo"))
    for producto in queryset.order_by("id"):
        writer.writerow(
            (
                producto.id,
                producto.nombre,
                producto.descripcion,
                producto.precio,
                producto.stock,
                "Sí" if producto.activo else "No",
            )
        )

    return response


class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "precio_formateado", "stock_formateado", "activo")
    search_fields = ("nombre",)
    list_filter = ("activo", StockRangeFilter)
    actions = (exportar_productos_csv,)
    ordering = ("nombre", "stock")
    search_fields = ("nombre", "descripcion")

    @admin.display(ordering="precio", description="Precio")
    def precio_formateado(self, obj):
        return f"${formato_miles(obj.precio)}"

    @admin.display(ordering="stock", description="Stock")
    def stock_formateado(self, obj):
        return formato_miles(obj.stock)

    def get_search_results(self, request, queryset, search_term):
        queryset, may_have_duplicates = super().get_search_results(request, queryset, search_term)
        if request.GET.get("model_name") == "detalleventa":
            queryset = queryset.filter(activo=True)
        return queryset, may_have_duplicates

admin.site.register(model_or_iterable=Producto, admin_class=ProductoAdmin)


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    form = DetalleVentaForm
    formset = DetalleVentaBaseFormSet
    min_num = 1
    validate_min = True
    extra = 1
    autocomplete_fields = ("producto",)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "producto":
            kwargs["queryset"] = Producto.objects.filter(activo=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.action(description="Exportar ventas seleccionadas a CSV")
def exportar_ventas_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="ventas.csv"'
    writer = csv.writer(response)
    writer.writerow(("ID", "Fecha", "Cliente", "Total"))
    for venta in queryset.order_by("fecha"):
        writer.writerow((venta.id, timezone.localtime(venta.fecha), venta.cliente, venta.total))
    return response


class VentaAdmin(admin.ModelAdmin):
    inlines = (DetalleVentaInline,)
    readonly_fields = ("total",)
    list_display = ("id", "fecha", "cliente", "total_formateado")
    list_filter = (("fecha", admin.DateFieldListFilter),)
    date_hierarchy = "fecha"
    search_fields = ("cliente", "id")
    actions = (exportar_ventas_csv,)
    change_list_template = "admin/ventas/venta/change_list.html"

    @admin.display(ordering="total", description="Total")
    def total_formateado(self, obj):
        return f"${formato_miles(obj.total)}"

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.recalcular_total()

    def get_urls(self):
        return [
            path("reporte/", self.admin_site.admin_view(self.reporte), name="ventas_reporte"),
        ] + super().get_urls()

    def reporte(self, request):
        desde = request.GET.get("desde", "")
        hasta = request.GET.get("hasta", "")
        ventas = Venta.objects.all()
        if desde:
            ventas = ventas.filter(fecha__date__gte=desde)
        if hasta:
            ventas = ventas.filter(fecha__date__lte=hasta)
        context = {
            **self.admin_site.each_context(request),
            "title": "Reporte de ventas",
            "ventas": ventas,
            "desde": desde,
            "hasta": hasta,
            "cantidad": ventas.count(),
            "total": sum(venta.total for venta in ventas),
        }
        if request.GET.get("exportar"):
            response = HttpResponse(content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = 'attachment; filename="reporte-ventas.csv"'
            writer = csv.writer(response)
            writer.writerow(("ID", "Fecha", "Cliente", "Total"))
            for venta in ventas:
                writer.writerow((venta.id, venta.fecha, venta.cliente, venta.total))
            return response
        return TemplateResponse(request, "admin/ventas/reporte.html", context)


admin.site.register(Venta, VentaAdmin)
admin.site.site_header = "La Tiendita - Administración"
admin.site.site_title = "La Tiendita"
admin.site.index_title = "Panel de control"