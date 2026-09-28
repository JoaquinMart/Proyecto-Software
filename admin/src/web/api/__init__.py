"""
API JSON para las interfaces operativas (Jefe de Servicio, Servicio de Alimentación, Sector Comedor).

Todas las rutas cuelgan de /api. Autenticación por token Bearer (ver api/helpers.py).
Los errores siempre se devuelven como:
    {"error": {"codigo": 400, "mensaje": "...", "detalles": {"campo": "mensaje"}}}
La documentación de cada endpoint está en docs/API.md.
"""
import logging

from flask import Blueprint

from src.core.configuracion import obtener_config
from src.core.database import db
from src.core.errores import ErrorNegocio

bp = Blueprint("api", __name__, url_prefix="/api")
log = logging.getLogger("alimentacion")


def respuesta_error(codigo: int, mensaje: str, detalles: dict | None = None):
    """Arma la respuesta de error estándar de la API."""
    cuerpo = {"error": {"codigo": codigo, "mensaje": mensaje}}
    if detalles:
        cuerpo["error"]["detalles"] = detalles
    return cuerpo, codigo


@bp.before_request
def controlar_mantenimiento():
    """Si el sitio está en mantenimiento, la API responde 503 (salvo la consulta de configuración)."""
    from flask import request
    if request.endpoint == "api.configuracion":
        return None
    config = obtener_config()
    if config.mantenimiento:
        return respuesta_error(503, config.mensaje_mantenimiento or "Sitio en mantenimiento.")
    return None


@bp.errorhandler(ErrorNegocio)
def manejar_error_negocio(error: ErrorNegocio):
    """Convierte las excepciones de negocio en respuestas JSON con su código HTTP."""
    db.session.rollback()
    return respuesta_error(error.status, error.mensaje, error.errores)


# Importar los módulos registra sus rutas en el blueprint.
from src.web.api import (auth, autorizaciones, catalogos, cupos, entregas, pedidos,  # noqa: E402,F401
                         personal, resumenes, sectores)
