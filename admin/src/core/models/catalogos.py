"""Catálogos predefinidos: tipos de personal y tipos de menú (tablas independientes)."""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import db

TIPO_RESIDENTE = "residente"
TIPO_FIJO = "fijo"


class TipoPersonal(db.Model):
    """Residente o Personal Fijo."""

    __tablename__ = "tipos_personal"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True)


class TipoMenu(db.Model):
    """General, Vegetariano o Celíaco."""

    __tablename__ = "tipos_menu"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True)
