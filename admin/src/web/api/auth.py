"""Autenticación de la API: login, logout y datos del usuario (token Bearer)."""
import logging

from sqlalchemy import func, select

from src.core.database import db
from src.core.models import Usuario
from src.core.tokens import crear_token, revocar_token
from src.web.api import bp, respuesta_error
from src.web.api import serializers as ser
from src.web.api.helpers import PERMISO_API, api_auth, cuerpo_json, token_de_request, usuario_api

log = logging.getLogger("alimentacion")


@bp.post("/auth/login")
def login():
    """Recibe {email, password} y devuelve un token Bearer con su vencimiento."""
    datos = cuerpo_json()
    email = str(datos.get("email") or "").strip().lower()
    password = str(datos.get("password") or "")
    if not email or not password:
        return respuesta_error(400, "Indicá email y password.")

    usuario = db.session.scalar(select(Usuario).where(func.lower(Usuario.email) == email))
    if usuario is None or not usuario.check_password(password):
        log.warning("API login fallido para %s", email)
        return respuesta_error(401, "Correo o contraseña incorrectos.")
    if not usuario.activo:
        return respuesta_error(403, "La cuenta está bloqueada.")
    if not usuario.tiene_permiso(PERMISO_API):
        return respuesta_error(403, "Tu rol no tiene acceso a las interfaces operativas.")

    token, vence = crear_token(usuario)
    log.info("API login: %s", usuario.email)
    return {"token": token, "token_type": "Bearer", "expires_at": ser.fecha_hora(vence),
            "usuario": ser.usuario(usuario)}


@bp.post("/auth/logout")
@api_auth()
def logout():
    """Revoca el token usado en la request."""
    revocar_token(token_de_request())
    log.info("API logout: %s", usuario_api().email)
    return {"mensaje": "Sesión cerrada."}


@bp.get("/auth/me")
@api_auth()
def me():
    """Datos del usuario autenticado: id, nombre, apellido, email, rol y sector."""
    return ser.usuario(usuario_api())
