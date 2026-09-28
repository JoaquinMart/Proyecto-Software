"""Personal del hospital: las personas para las que se piden y entregan comidas."""
from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import db
from src.core.models.base import Timestamps
from src.core.models.catalogos import TIPO_RESIDENTE, TipoMenu, TipoPersonal
from src.core.models.sectores import Sector


class Persona(Timestamps, db.Model):
    """
    Persona que puede incluirse en pedidos. No necesariamente tiene usuario en el sistema.
    Los residentes no tienen sector: pueden sumarse a pedidos de cualquier sector.
    """

    __tablename__ = "personal"

    id: Mapped[int] = mapped_column(primary_key=True)
    dni: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(50))
    apellido: Mapped[str] = mapped_column(String(50), index=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    tipo_personal_id: Mapped[int] = mapped_column(ForeignKey("tipos_personal.id"))
    tipo_menu_id: Mapped[int] = mapped_column(ForeignKey("tipos_menu.id"))
    sector_id: Mapped[int | None] = mapped_column(ForeignKey("sectores.id"), nullable=True)

    tipo_personal: Mapped[TipoPersonal] = relationship()
    tipo_menu: Mapped[TipoMenu] = relationship()
    sector: Mapped[Sector | None] = relationship()

    @property
    def es_residente(self) -> bool:
        """True si la persona es de tipo Residente."""
        return self.tipo_personal is not None and self.tipo_personal.codigo == TIPO_RESIDENTE

    @property
    def nombre_completo(self) -> str:
        """Apellido, Nombre."""
        return f"{self.apellido}, {self.nombre}"
