"""Ajustes generales del sistema (una sola fila)."""
from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import db
from src.core.models.base import Timestamps


class Configuracion(Timestamps, db.Model):
    """Parámetros globales editables por el Administrador."""

    __tablename__ = "configuracion"

    id: Mapped[int] = mapped_column(primary_key=True)
    por_pagina: Mapped[int] = mapped_column(Integer, default=25)
    mantenimiento: Mapped[bool] = mapped_column(Boolean, default=False)
    mensaje_mantenimiento: Mapped[str] = mapped_column(String(255), default="")
    actualizado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
