"""Catálogos y configuración para poblar las interfaces."""
from src.core.configuracion import obtener_config
from src.core.personal import tipos_menu, tipos_personal
from src.web.api import bp
from src.web.api import serializers as ser
from src.web.api.helpers import api_auth


@bp.get("/menu-types")
@api_auth()
def tipos_de_menu():
    """Listado de tipos de menú."""
    return {"items": [ser.catalogo(t) for t in tipos_menu()]}


@bp.get("/personnel-types")
@api_auth()
def tipos_de_personal():
    """Listado de tipos de personal."""
    return {"items": [ser.catalogo(t) for t in tipos_personal()]}


@bp.get("/configuration")
@api_auth()
def configuracion():
    """Parámetros generales: elementos por página y estado de mantenimiento."""
    config = obtener_config()
    return {"por_pagina": config.por_pagina, "mantenimiento": config.mantenimiento,
            "mensaje_mantenimiento": config.mensaje_mantenimiento}
