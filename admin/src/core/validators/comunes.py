"""Funciones de validación reutilizadas por todos los módulos."""
import re
from datetime import date

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
NOMBRE_RE = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' \-]{2,50}$")
DNI_RE = re.compile(r"^\d{7,8}$")

MSG_NOMBRE = "Usá entre 2 y 50 letras. Se permiten espacios, apóstrofo y guion."
MSG_DNI = "El DNI debe tener 7 u 8 números, sin puntos."


def texto(data, campo) -> str:
    """Devuelve el campo como texto, sin espacios sobrantes."""
    valor = data.get(campo) if hasattr(data, "get") else None
    if valor is None:
        return ""
    return " ".join(str(valor).split())


def entero(data, campo) -> int | None:
    """Devuelve el campo como entero positivo, o None si no es válido."""
    valor = data.get(campo) if hasattr(data, "get") else None
    if isinstance(valor, bool):
        return None
    if isinstance(valor, int):
        return valor if valor > 0 else None
    valor = str(valor or "").strip()
    return int(valor) if valor.isdigit() and int(valor) > 0 else None


def booleano(data, campo, por_defecto=False) -> bool:
    """Interpreta checkboxes de formulario ('1', 'on') y booleanos JSON."""
    valor = data.get(campo) if hasattr(data, "get") else None
    if valor is None or valor == "":
        return por_defecto
    if isinstance(valor, bool):
        return valor
    return str(valor).strip().lower() in ("1", "on", "true", "si", "sí")


def dni(valor: str) -> str:
    """Normaliza un DNI quitando puntos y espacios."""
    return str(valor or "").replace(".", "").replace(" ", "").strip()


def validar_nombre(errores, campo, valor, etiqueta):
    """Valida nombre o apellido y agrega el error si corresponde."""
    if not valor:
        errores[campo] = f"Ingresá {etiqueta}."
    elif not NOMBRE_RE.match(valor):
        errores[campo] = MSG_NOMBRE


def validar_dni(errores, campo, valor):
    """Valida el formato del DNI y agrega el error si corresponde."""
    if not valor:
        errores[campo] = "Ingresá el DNI."
    elif not DNI_RE.match(valor):
        errores[campo] = MSG_DNI


def fecha(valor) -> date | None:
    """Convierte 'AAAA-MM-DD' en date, o None si no es válida."""
    try:
        return date.fromisoformat(str(valor).strip())
    except (TypeError, ValueError):
        return None


def like(valor: str) -> str:
    """Arma un patrón LIKE escapando comodines tipeados por el usuario."""
    valor = valor.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{valor}%"
