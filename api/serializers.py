from django.core.exceptions import ValidationError as DjangoValidationError
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

    def validate(self, attrs):
        for detail in attrs.get("detalles", []):
            producto = detail["producto"]
            if not producto.activo:
                raise serializers.ValidationError(
                    {"detalles": f"El producto {producto.pk} está inactivo y no se puede vender."}
                )
        return attrs

    @staticmethod
    def _create_details(venta, details):
        for detail in details:
            DetalleVenta.objects.create(venta=venta, **detail)

    @transaction.atomic
    def create(self, validated_data):
        details = validated_data.pop("detalles")
        venta = Venta.objects.create(**validated_data)
        try:
            self._create_details(venta, details)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            ) from exc
        return venta

    @transaction.atomic
    def update(self, instance, validated_data):
        details = validated_data.pop("detalles", None)
        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)
        instance.save(update_fields=tuple(validated_data) or None)

        if details is not None:
            # Sending detalles replaces the complete list; delete() restores old stock first.
            instance.detalles.all().delete()
            try:
                self._create_details(instance, details)
            except DjangoValidationError as exc:
                raise serializers.ValidationError(
                    exc.message_dict if hasattr(exc, "message_dict") else exc.messages
                ) from exc
        return instance
