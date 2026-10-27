from django.db import transaction
from rest_framework import serializers

from inventario.models import Producto
from ventas.models import DetalleVenta, Venta


class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = ("id", "nombre", "descripcion", "precio", "stock", "activo")


class DetalleVentaSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleVenta
        fields = ("id", "producto", "cantidad", "precio_unitario", "subtotal")
        read_only_fields = ("id", "subtotal")


class VentaSerializer(serializers.ModelSerializer):
    detalles = DetalleVentaSerializer(many=True)

    class Meta:
        model = Venta
        fields = ("id", "fecha", "cliente", "observacion", "total", "detalles")
        read_only_fields = ("id", "total")

    def validate_detalles(self, value):
        if not value:
            raise serializers.ValidationError("La venta debe incluir al menos un detalle.")
        return value

    @staticmethod
    def _create_details(venta, details):
        for detail in details:
            DetalleVenta.objects.create(venta=venta, **detail)

    @transaction.atomic
    def create(self, validated_data):
        details = validated_data.pop("detalles")
        venta = Venta.objects.create(**validated_data)
        self._create_details(venta, details)
        return venta

    @transaction.atomic
    def update(self, instance, validated_data):
        details = validated_data.pop("detalles", None)
        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)
        instance.save(update_fields=tuple(validated_data) or None)

        if details is not None:
            instance.detalles.all().delete()
            self._create_details(instance, details)
        return instance
