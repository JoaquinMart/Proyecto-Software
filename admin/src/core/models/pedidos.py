"""
Pedidos, solicitudes nominadas, cupos y entregas.

Modelo adoptado:
  - Pedido: un sector para una fecha (único por sector + fecha). Tiene estado.
  - Solicitud: una persona + una comida dentro de un pedido. Es la unidad nominada:
      guarda el tipo de menú y la condición Regular/Excepción AL MOMENTO de la carga
      (cambios posteriores en la ficha o en el cupo no la alteran),
      la autorización (autorizada None/True/False) y la entrega (entrega_id).
  - Lo pedido, lo autorizado y lo entregado quedan diferenciados en columnas distintas
    de la misma solicitud, y los totales se calculan contando solicitudes.
"""
from datetime import date, datetime

from sqlalchemy import (Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer,
                        String, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import db
from src.core.models.auth import Usuario
from src.core.models.base import Timestamps
from src.core.models.catalogos import TipoMenu
from src.core.models.personal import Persona
from src.core.models.sectores import Sector

COMIDAS = ("desayuno", "almuerzo", "merienda", "cena")
ESTADO_CONFIRMADO = "confirmado"
ESTADO_AUTORIZADO = "autorizado"
ESTADO_RECHAZADO = "rechazado"
ESTADOS = (ESTADO_CONFIRMADO, ESTADO_AUTORIZADO, ESTADO_RECHAZADO)
REGULAR = "regular"
EXCEPCION = "excepcion"
PERIODICIDADES = ("diaria", "semanal", "mensual")

_COMIDAS_SQL = ", ".join(f"'{c}'" for c in COMIDAS)


class Cupo(Timestamps, db.Model):
    """Cantidad máxima de solicitudes regulares por sector y comida."""

    __tablename__ = "cupos"
    __table_args__ = (
        UniqueConstraint("sector_id", "comida", name="uq_cupo_sector_comida"),
        CheckConstraint(f"comida IN ({_COMIDAS_SQL})", name="ck_cupo_comida"),
        CheckConstraint("cantidad > 0", name="ck_cupo_cantidad"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sector_id: Mapped[int] = mapped_column(ForeignKey("sectores.id"))
    comida: Mapped[str] = mapped_column(String(10))
    cantidad: Mapped[int] = mapped_column(Integer)

    sector: Mapped[Sector] = relationship()


class Pedido(Timestamps, db.Model):
    """Pedido de un sector para una fecha."""

    __tablename__ = "pedidos"
    __table_args__ = (
        UniqueConstraint("sector_id", "fecha", name="uq_pedido_sector_fecha"),
        CheckConstraint("estado IN ('confirmado', 'autorizado', 'rechazado')", name="ck_pedido_estado"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sector_id: Mapped[int] = mapped_column(ForeignKey("sectores.id"))
    fecha: Mapped[date] = mapped_column(Date, index=True)
    periodicidad: Mapped[str] = mapped_column(String(10))
    estado: Mapped[str] = mapped_column(String(12), default=ESTADO_CONFIRMADO, index=True)

    creado_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    modificado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    revisado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    revisado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_rechazo: Mapped[str | None] = mapped_column(String(255), nullable=True)

    sector: Mapped[Sector] = relationship()
    creado_por: Mapped[Usuario] = relationship(foreign_keys=[creado_por_id])
    modificado_por: Mapped[Usuario | None] = relationship(foreign_keys=[modificado_por_id])
    revisado_por: Mapped[Usuario | None] = relationship(foreign_keys=[revisado_por_id])
    solicitudes: Mapped[list["Solicitud"]] = relationship(
        back_populates="pedido", cascade="all, delete-orphan", order_by="Solicitud.id"
    )


class Entrega(db.Model):
    """Retiro de una o varias comidas en una misma operación del comedor."""

    __tablename__ = "entregas"

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))  # quién entregó
    responsable_persona_id: Mapped[int | None] = mapped_column(ForeignKey("personal.id"), nullable=True)
    responsable_dni: Mapped[str] = mapped_column(String(8))              # quién retiró
    responsable_nombre: Mapped[str] = mapped_column(String(110))

    usuario: Mapped[Usuario] = relationship()
    responsable_persona: Mapped[Persona | None] = relationship()
    solicitudes: Mapped[list["Solicitud"]] = relationship(back_populates="entrega")


class Solicitud(db.Model):
    """Una comida para una persona dentro de un pedido (unidad nominada)."""

    __tablename__ = "solicitudes"
    __table_args__ = (
        UniqueConstraint("pedido_id", "persona_id", "comida", name="uq_solicitud_persona_comida"),
        CheckConstraint(f"comida IN ({_COMIDAS_SQL})", name="ck_solicitud_comida"),
        CheckConstraint("condicion IN ('regular', 'excepcion')", name="ck_solicitud_condicion"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id", ondelete="CASCADE"), index=True)
    persona_id: Mapped[int] = mapped_column(ForeignKey("personal.id"), index=True)
    comida: Mapped[str] = mapped_column(String(10))
    tipo_menu_id: Mapped[int] = mapped_column(ForeignKey("tipos_menu.id"))  # copia al cargar
    condicion: Mapped[str] = mapped_column(String(10))                     # regular | excepcion

    # Autorización: None = pendiente, True = autorizada, False = no autorizada
    autorizada: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    autorizada_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    autorizada_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Entrega: NULL = todavía no se entregó
    entrega_id: Mapped[int | None] = mapped_column(ForeignKey("entregas.id"), nullable=True, index=True)

    pedido: Mapped[Pedido] = relationship(back_populates="solicitudes")
    persona: Mapped[Persona] = relationship()
    tipo_menu: Mapped[TipoMenu] = relationship()
    autorizada_por: Mapped[Usuario | None] = relationship()
    entrega: Mapped[Entrega | None] = relationship(back_populates="solicitudes")
