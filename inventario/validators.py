from django.core.validators import RegexValidator


solo_letras_validator = RegexValidator(
    regex=r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]+$",
    message="Este campo solo admite letras.",
)
