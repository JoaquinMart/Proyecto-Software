"""Cupos por sector y comida (administrados por Servicio de Alimentación vía API)."""
import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.core.configuracion import por_pagina
from src.core.database import db
from src.core.errores import Conflicto, ErrorValidacion, NoEncontrado
from src.core.models import Cupo, Sector
from src.core.validators import comunes as v
from src.core.validators.cupos import validar_cupo

log = logging.getLogger("alimentacion")


def cupos_de_sector(sector_id: int) -> dict[str, int]:
    """{comida: cantidad} con los cupos vigentes de un sector."""
    filas = db.session.execute(select(Cupo.comida, Cupo.cantidad).where(Cupo.sector_id == sector_id))
    return {comida: cantidad for comida, cantidad in filas}


def obtener_cupo(cupo_id) -> Cupo:
    """Devuelve el cupo o lanza NoEncontrado."""
    cupo = db.session.get(Cupo, cupo_id)
    if cupo is None:
        raise NoEncontrado("El cupo no existe.")
    return cupo


def _duplicado(sector_id, comida, excluir_id=None) -> bool:
    """True si ya hay un cupo para ese sector y comida."""
    consulta = select(Cupo.id).where(Cupo.sector_id == sector_id, Cupo.comida == comida)
    if excluir_id:
        consulta = consulta.where(Cupo.id != excluir_id)
    return db.session.scalar(consulta) is not None


def crear_cupo(data) -> Cupo:
    """Crea un cupo. No puede haber dos para el mismo sector y comida."""
    d, errores = validar_cupo(data)
    if errores:
        raise ErrorValidacion(errores)
    if _duplicado(d["sector"].id, d["comida"]):
        raise Conflicto("Ya existe un cupo para ese sector y comida.")
    cupo = Cupo(sector=d["sector"], comida=d["comida"], cantidad=d["cantidad"])
    db.session.add(cupo)
    db.session.commit()
    log.info("Cupo creado: %s / %s = %s", cupo.sector.nombre, cupo.comida, cupo.cantidad)
    return cupo


def actualizar_cupo(cupo: Cupo, data) -> Cupo:
    """
    Modifica un cupo. Solo afecta pedidos futuros: la condición Regular/Excepción
    ya guardada en cada solicitud no se recalcula.
    """
    d, errores = validar_cupo(data, cupo)
    if errores:
        raise ErrorValidacion(errores)
    if _duplicado(d["sector"].id, d["comida"], excluir_id=cupo.id):
        raise Conflicto("Ya existe un cupo para ese sector y comida.")
    cupo.sector = d["sector"]
    cupo.comida = d["comida"]
    cupo.cantidad = d["cantidad"]
    db.session.commit()
    log.info("Cupo actualizado: %s / %s = %s", cupo.sector.nombre, cupo.comida, cupo.cantidad)
    return cupo


def eliminar_cupo(cupo: Cupo) -> None:
    """Elimina un cupo (sin cupo, todas las solicitudes nuevas de esa comida son excepción)."""
    db.session.delete(cupo)
    db.session.commit()


def buscar_cupos(filtros, page: int = 1, sector_forzado: int | None = None):
    """Listado por sector y comida, ordenado por sector."""
    consulta = select(Cupo).join(Cupo.sector).options(selectinload(Cupo.sector))
    sector_id = sector_forzado or v.entero(filtros, "sector_id")
    if sector_id:
        consulta = consulta.where(Cupo.sector_id == sector_id)
    comida = v.texto(filtros, "comida").lower()
    if comida:
        consulta = consulta.where(Cupo.comida == comida)
    descendente = filtros.get("dir", "asc") == "desc"
    consulta = consulta.order_by(Sector.nombre.desc() if descendente else Sector.nombre.asc(), Cupo.comida)
    return db.paginate(consulta, page=max(page, 1), per_page=por_pagina(), error_out=False)
