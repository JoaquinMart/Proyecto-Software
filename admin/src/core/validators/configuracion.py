"""Validación de los ajustes del sistema. Devuelve (datos_limpios, errores)."""
from src.core.validators import comunes as v

MAX_POR_PAGINA = 25


def validar_configuracion(data):
    """Valida elementos por página (1 a 25), modo mantenimiento y su mensaje."""
    errores = {}
    por_pagina = v.entero(data, "por_pagina")
    mantenimiento = v.booleano(data, "mantenimiento")
    mensaje = (data.get("mensaje_mantenimiento") or "").strip()

    if por_pagina is None or por_pagina > MAX_POR_PAGINA:
        errores["por_pagina"] = f"Ingresá un número entre 1 y {MAX_POR_PAGINA}."
    if mantenimiento and not mensaje:
        errores["mensaje_mantenimiento"] = "Escribí el mensaje que verán los usuarios durante el mantenimiento."
    if len(mensaje) > 255:
        errores["mensaje_mantenimiento"] = "El mensaje no puede superar los 255 caracteres."

    return {"por_pagina": por_pagina, "mantenimiento": mantenimiento, "mensaje_mantenimiento": mensaje}, errores
