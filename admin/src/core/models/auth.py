"""
Usuarios, roles, permisos y tokens de la API.

Esquema de autorización (usuario → rol → permisos):
  - Cada usuario tiene UN rol.
  - Cada rol tiene MUCHOS permisos (tabla intermedia rol_permiso).
  - El código nunca pregunta "¿es administrador?", sino "¿tiene el permiso user_new?".
    Cambiar lo que puede hacer un rol es tocar datos, no código.
"""
from datetime import datetime
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import db
from src.core.models.base import Timestamps

_hasher = PasswordHasher()  # Argon2id con parámetros recomendados

rol_permiso = Table(
    "rol_permiso",
    db.metadata,
    Column("rol_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permiso_id", ForeignKey("permisos.id", ondelete="CASCADE"), primary_key=True),
)


class Permiso(db.Model):
    """Acción puntual del sistema, con el patrón modulo_accion (ej: user_new)."""

    __tablename__ = "permisos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True)


class Rol(db.Model):
    """Rol del usuario. Agrupa permisos."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True)
    permisos: Mapped[list[Permiso]] = relationship(secondary=rol_permiso)


class Usuario(Timestamps, db.Model):
    """Persona que usa el sistema (no confundir con Persona, que recibe comidas)."""

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(50))
    apellido: Mapped[str] = mapped_column(String(50), index=True)
    dni: Mapped[str] = mapped_column(String(8), index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)  # False = bloqueado

    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    sector_id: Mapped[int | None] = mapped_column(ForeignKey("sectores.id"), nullable=True)

    rol: Mapped[Rol] = relationship()
    sector: Mapped[Optional["Sector"]] = relationship(back_populates="jefes")  # noqa: F821

    def set_password(self, password: str) -> None:
        """Guarda el hash Argon2 de la contraseña. El texto plano nunca se almacena."""
        self.password_hash = _hasher.hash(password)

    def check_password(self, password: str) -> bool:
        """Compara la contraseña ingresada contra el hash guardado."""
        try:
            return _hasher.verify(self.password_hash, password)
        except (VerifyMismatchError, InvalidHashError):
            return False

    def tiene_permiso(self, nombre: str) -> bool:
        """True si el rol del usuario incluye el permiso indicado."""
        return self.rol is not None and any(p.nombre == nombre for p in self.rol.permisos)

    @property
    def nombre_completo(self) -> str:
        """Apellido, Nombre."""
        return f"{self.apellido}, {self.nombre}"

    def __repr__(self):
        """Sin password_hash a propósito: nunca debe terminar en un log."""
        return f"<Usuario {self.email}>"


class ApiToken(db.Model):
    """
    Token de acceso a la API (header Authorization: Bearer <token>).
    Solo se guarda el hash SHA-256 del token: si alguien lee la tabla, no puede usarlos.
    """

    __tablename__ = "api_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    usuario: Mapped[Usuario] = relationship()
