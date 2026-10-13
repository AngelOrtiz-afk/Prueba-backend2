from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def miles(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return value
    return f"{number:,}".replace(",", ".")


@register.filter
def clp(value):
    return f"${miles(value)}"


@register.filter
def add_class(field, css_class):
    if not hasattr(field, "as_widget"):
        return field
    return field.as_widget(attrs={"class": css_class})


@register.filter
def field_errors(field):
    if not getattr(field, "errors", None):
        return ""
    errors = "".join(
        f'<div class="invalid-feedback d-block">{conditional_escape(error)}</div>'
        for error in field.errors
    )
    return mark_safe(errors)
