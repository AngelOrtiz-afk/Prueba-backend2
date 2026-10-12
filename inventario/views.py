import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import DetalleVentaFormSet, ProductoForm, VentaForm
from .models import Producto
from ventas.models import Venta

logger = logging.getLogger("ventas")


class ProductoListView(LoginRequiredMixin, ListView):
    model = Producto
    template_name = "inventario/producto_list.html"
    context_object_name = "productos"
    paginate_by = 10

    def get_queryset(self):
        query = self.request.GET.get("q", "").strip()
        estado = self.request.GET.get("estado", "todos")
        queryset = super().get_queryset()
        if query:
            queryset = queryset.filter(Q(nombre__icontains=query) | Q(descripcion__icontains=query))
        if estado == "activos":
            queryset = queryset.filter(activo=True)
        elif estado == "inactivos":
            queryset = queryset.filter(activo=False)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.copy()
        query.pop("page", None)
        context["pagination_query"] = query.urlencode()
        return context


class ProductoCreateView(LoginRequiredMixin, CreateView):
    model = Producto
    form_class = ProductoForm
    template_name = "inventario/form.html"
    success_url = reverse_lazy("inventario:producto-list")

    def form_valid(self, form):
        messages.success(self.request, "Producto creado correctamente.")
        return super().form_valid(form)


class ProductoUpdateView(ProductoCreateView, UpdateView):
    def form_valid(self, form):
        messages.success(self.request, "Producto actualizado correctamente.")
        return super(ProductoCreateView, self).form_valid(form)


class ProductoDetailView(LoginRequiredMixin, DetailView):
    model = Producto
    template_name = "inventario/producto_detail.html"
    context_object_name = "producto"


class ProductoDeleteView(LoginRequiredMixin, DeleteView):
    model = Producto
    template_name = "inventario/confirm_delete.html"
    success_url = reverse_lazy("inventario:producto-list")
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cancel_url"] = reverse_lazy("inventario:producto-update", kwargs={"pk": self.object.pk})
        return context

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Producto eliminado correctamente.")
            return response
        except ProtectedError:
            messages.error(
                self.request,
                "No se puede eliminar porque tiene ventas asociadas. "
                "Puedes desactivarlo modificando el campo activo.",
            )
            return self.get(self.request, self.object.pk)


class VentaListView(LoginRequiredMixin, ListView):
    model = Venta
    template_name = "inventario/venta_list.html"
    context_object_name = "ventas"
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        desde = self.request.GET.get("desde")
        hasta = self.request.GET.get("hasta")
        if desde:
            queryset = queryset.filter(fecha__date__gte=desde)
        if hasta:
            queryset = queryset.filter(fecha__date__lte=hasta)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.copy()
        query.pop("page", None)
        context["pagination_query"] = query.urlencode()
        return context


class VentaDetailView(LoginRequiredMixin, DetailView):
    model = Venta
    template_name = "inventario/venta_detail.html"
    context_object_name = "venta"


class VentaCreateView(LoginRequiredMixin, CreateView):
    model = Venta
    form_class = VentaForm
    template_name = "inventario/venta_form.html"
    success_url = reverse_lazy("inventario:venta-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["formset"] = kwargs.get("formset", DetalleVentaFormSet(self.request.POST or None, instance=self.object))
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]
        if not formset.is_valid():
            return self.render_to_response(self.get_context_data(form=form, formset=formset))
        try:
            with transaction.atomic():
                self.object = form.save()
                formset.instance = self.object
                formset.save()
        except Exception as exc:
            logger.exception("Error al crear venta")
            form.add_error(None, str(exc))
            return self.render_to_response(self.get_context_data(form=form, formset=formset))
        logger.info("Venta %s creada", self.object.pk)
        messages.success(self.request, "Venta creada correctamente.")
        return super().form_valid(form)


class VentaUpdateView(VentaCreateView, UpdateView):
    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]
        if not formset.is_valid():
            return self.render_to_response(self.get_context_data(form=form, formset=formset))
        try:
            with transaction.atomic():
                self.object = form.save()
                formset.instance = self.object
                formset.save()
        except Exception as exc:
            logger.exception("Error al actualizar venta")
            form.add_error(None, str(exc))
            return self.render_to_response(self.get_context_data(form=form, formset=formset))
        messages.success(self.request, "Venta actualizada correctamente.")
        return super(VentaCreateView, self).form_valid(form)


class VentaDeleteView(LoginRequiredMixin, DeleteView):
    model = Venta
    template_name = "inventario/confirm_delete.html"
    success_url = reverse_lazy("inventario:venta-list")
    cancel_url = success_url

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cancel_url"] = self.cancel_url
        return context

    def form_valid(self, form):
        venta_pk = self.object.pk
        with transaction.atomic():
            for detalle in list(self.object.detalles.all()):
                detalle.delete()
            response = super().form_valid(form)
        logger.info("Venta %s anulada", venta_pk)
        messages.success(self.request, "Venta anulada y stock repuesto.")
        return response
