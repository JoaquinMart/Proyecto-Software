"""Autenticación por token, lectura del cuerpo JSON y paginación para la API."""
from functools import wraps

from flask import g, request

from src.core.errores import ErrorValidacion, Prohibido
from src.core.tokens import usuario_de_token
from src.core.validators.usuarios import ROL_JEFE
from src.web.api import respuesta_error

PERMISO_API = "api_access"


def token_de_request() -> str | None:
    """Extrae el token del header 'Authorization: Bearer <token>'."""
    encabezado = request.headers.get("Authorization", "")
    tipo, _, token = encabezado.partition(" ")
    if tipo.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def api_auth(*permisos):
    """
    Decorador de endpoints protegidos.
    1) Sin token o token inválido/vencido → 401 (antes de cualquier otra regla).
    2) Sin acceso a la API o sin alguno de los permisos → 403.
    """
    def decorador(vista):
        """Envuelve la vista con el control de acceso."""
        @wraps(vista)
        def envoltura(*args, **kwargs):
            """Verifica credenciales y permisos antes de ejecutar la vista."""
            usuario = usuario_de_token(token_de_request())
            if usuario is None:
                return respuesta_error(401, "Token ausente, inválido o vencido.")
            if not usuario.tiene_permiso(PERMISO_API) or not all(usuario.tiene_permiso(p) for p in permisos):
                return respuesta_error(403, "Tu rol no tiene permiso para esta operación.")
            g.api_usuario = usuario
            return vista(*args, **kwargs)
        return envoltura
    return decorador


def usuario_api():
    """Usuario autenticado en el request actual de la API."""
    return g.api_usuario


def es_jefe(usuario) -> bool:
    """True si el usuario tiene rol Jefe de Servicio."""
    return usuario.rol.codigo == ROL_JEFE


def sector_de_jefe(usuario) -> int:
    """Id del sector del Jefe de Servicio, o 403 si no tiene uno asignado."""
    if usuario.sector_id is None:
        raise Prohibido("Tu usuario no tiene un sector asignado.")
    return usuario.sector_id


def cuerpo_json() -> dict:
    """Cuerpo de la request como diccionario, o 400 si no es un objeto JSON."""
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        raise ErrorValidacion({"body": "Se esperaba un objeto JSON en el cuerpo de la solicitud."})
    return datos


def pagina_actual() -> int:
    """Número de página pedido (?page=), por defecto 1."""
    return max(request.args.get("page", 1, type=int) or 1, 1)


def paginado(pagina, serializar) -> dict:
    """Serializa un resultado paginado de Flask-SQLAlchemy."""
    return {
        "items": [serializar(item) for item in pagina.items],
        "pagina": pagina.page,
        "por_pagina": pagina.per_page,
        "total": pagina.total,
        "paginas": pagina.pages,
    }
