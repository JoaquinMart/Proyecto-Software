"""
Tokens de acceso para la API (Bearer). Se implementan a mano:
- Al hacer login se genera un token aleatorio y se guarda solo su hash SHA-256.
- Cada request trae el token en el header Authorization y se busca su hash.
- Vencen a las TOKEN_HORAS horas y el logout los revoca.
"""
import hashlib
import secrets
from datetime import timedelta

from sqlalchemy import select

from src.core.database import db
from src.core.fechas import ahora
from src.core.models import ApiToken

TOKEN_HORAS = 8


def _hash(token: str) -> str:
    """Hash SHA-256 del token en hexadecimal."""
    return hashlib.sha256(token.encode()).hexdigest()


def crear_token(usuario) -> tuple[str, "datetime"]:  # noqa: F821
    """Genera un token nuevo para el usuario. Devuelve (token, vencimiento)."""
    token = secrets.token_urlsafe(32)
    momento = ahora()
    registro = ApiToken(token_hash=_hash(token), usuario_id=usuario.id,
                        created_at=momento, expires_at=momento + timedelta(hours=TOKEN_HORAS))
    db.session.add(registro)
    db.session.commit()
    return token, registro.expires_at


def usuario_de_token(token: str):
    """Devuelve el usuario si el token es válido, no venció, no fue revocado y el usuario está activo."""
    if not token:
        return None
    registro = db.session.scalar(select(ApiToken).where(ApiToken.token_hash == _hash(token)))
    if registro is None or registro.revoked_at is not None or registro.expires_at <= ahora():
        return None
    if not registro.usuario.activo:
        return None
    return registro.usuario


def revocar_token(token: str) -> None:
    """Invalida el token (logout)."""
    registro = db.session.scalar(select(ApiToken).where(ApiToken.token_hash == _hash(token)))
    if registro is not None and registro.revoked_at is None:
        registro.revoked_at = ahora()
        db.session.commit()
