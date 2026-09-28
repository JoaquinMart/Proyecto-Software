"""Sectores o servicios del hospital."""
from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import db
from src.core.models.base import Timestamps


class Sector(Timestamps, db.Model):
    """Sector del hospital. Desactivarlo no borra su historial."""

    __tablename__ = "sectores"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)
    descripcion: Mapped[str] = mapped_column(Text, default="")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    jefes: Mapped[list["Usuario"]] = relationship(back_populates="sector")  # noqa: F821
