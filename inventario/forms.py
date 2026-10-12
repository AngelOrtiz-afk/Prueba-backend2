from django import forms
from django.forms import inlineformset_factory

from .models import Producto
from .validators import solo_letras_validator
from ventas.models import DetalleVenta, Venta


class ProductoForm(forms.ModelForm):
    nombre = forms.CharField(
        label="Nombre",
        validators=[solo_letras_validator],
        widget=forms.TextInput(
            attrs={
                "pattern": r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]+",
                "title": "Este campo solo admite letras.",
            }
        ),
    )
    precio = forms.IntegerField(
        label="Precio",
        min_value=0,
        error_messages={"invalid": "El precio debe ser un número entero.", "min_value": "El precio debe ser mayor o igual a 0."},
        widget=forms.NumberInput(attrs={"min": "0", "step": "1"}),
    )
    stock = forms.IntegerField(
        label="Stock",
        min_value=0,
        error_messages={"invalid": "El stock debe ser un número entero.", "min_value": "El stock debe ser mayor o igual a 0."},
        widget=forms.NumberInput(attrs={"min": "0", "step": "1"}),
    )

    class Meta:
        model = Producto
        fields = ("nombre", "descripcion", "precio", "stock", "activo")
        labels = {"nombre": "Nombre", "descripcion": "Descripción", "precio": "Precio", "stock": "Stock", "activo": "Activo"}
    def clean_precio(self):
        precio = self.cleaned_data.get("precio")
        if precio is None or precio < 0:
            raise forms.ValidationError("El precio debe ser un número entero mayor o igual a 0.")
        return precio

    def clean_stock(self):
        stock = self.cleaned_data.get("stock")
        if stock is None or stock < 0:
            raise forms.ValidationError("El stock debe ser un número entero mayor o igual a 0.")
        return stock

    def clean_nombre(self):
        nombre = " ".join(self.cleaned_data.get("nombre", "").strip().split())
        if not nombre:
            raise forms.ValidationError("Este campo solo admite letras.")
        return nombre


class VentaForm(forms.ModelForm):
    cliente = forms.CharField(
        label="Cliente",
        required=False,
        validators=[solo_letras_validator],
        widget=forms.TextInput(
            attrs={
                "pattern": r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]+",
                "title": "Este campo solo admite letras.",
            }
        ),
    )

    class Meta:
        model = Venta
        fields = ("fecha", "cliente", "observacion")
        widgets = {"fecha": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fecha"].input_formats = ("%Y-%m-%dT%H:%M",)

    def clean_cliente(self):
        return " ".join(self.cleaned_data.get("cliente", "").strip().split())


class DetalleVentaForm(forms.ModelForm):
    class Meta:
        model = DetalleVenta
        fields = ("producto", "cantidad", "precio_unitario")
        widgets = {
            "cantidad": forms.NumberInput(attrs={"min": "0", "step": "1"}),
            "precio_unitario": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = Producto.objects.filter(activo=True)
        if self.instance.pk and self.instance.producto_id and not self.instance.producto.activo:
            queryset = Producto.objects.filter(pk=self.instance.producto_id) | queryset
        self.fields["producto"].queryset = queryset.distinct()

    def clean(self):
        cleaned = super().clean()
        if self.cleaned_data.get("producto") and self.cleaned_data.get("cantidad"):
            detalle = DetalleVenta(
                pk=self.instance.pk,
                venta=self.instance.venta,
                producto=cleaned["producto"],
                cantidad=cleaned["cantidad"],
                precio_unitario=cleaned.get("precio_unitario") or cleaned["producto"].precio,
            )
            detalle.full_clean(exclude=("id",))
        return cleaned


DetalleVentaFormSet = inlineformset_factory(
    Venta, DetalleVenta, form=DetalleVentaForm, extra=1, can_delete=True
)
