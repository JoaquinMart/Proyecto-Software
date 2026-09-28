"""Reglas de negocio de sectores."""
import logging

from sqlalchemy import delete, exists, func, select
from sqlalchemy.orm import selectinload

from src.core.configuracion import por_pagina
from src.core.database import db
from src.core.errores import Conflicto, ErrorValidacion, NoEncontrado
from src.core.models import Cupo, Pedido, Persona, Sector, Usuario
from src.core.validators import comunes as v
from src.core.validators.sectores import validar_sector

log = logging.getLogger("alimentacion")

ORDENES = {"nombre": lambda: [Sector.nombre], "creacion": lambda: [Sector.created_at]}


def listar_sectores(solo_activos=False):
    """Todos los sectores ordenados por nombre (para selectores y la API)."""
    consulta = select(Sector).order_by(Sector.nombre)
    if solo_activos:
        consulta = consulta.where(Sector.activo.is_(True))
    return db.session.scalars(consulta).all()


def obtener_sector(sector_id) -> Sector:
    """Devuelve el sector o lanza NoEncontrado."""
    sector = db.session.get(Sector, sector_id)
    if sector is None:
        raise NoEncontrado("El sector no existe.")
    return sector


def _usuarios_activos(sector: Sector) -> int:
    """Cantidad de usuarios activos asociados al sector."""
    return db.session.scalar(
        select(func.count(Usuario.id)).where(Usuario.sector_id == sector.id, Usuario.activo.is_(True))
    )


def _asignar_jefes(sector: Sector, jefes) -> None:
    """Deja asignados exactamente los Jefes indicados (los que se quitan quedan sin sector)."""
    for jefe in list(sector.jefes):
        if jefe not in jefes:
            jefe.sector = None
    for jefe in jefes:
        jefe.sector = sector


def crear_sector(data) -> Sector:
    """Crea un sector con sus Jefes de Servicio."""
    d, errores = validar_sector(data)
    if errores:
        raise ErrorValidacion(errores)
    sector = Sector(nombre=d["nombre"], descripcion=d["descripcion"], activo=d["activo"])
    db.session.add(sector)
    _asignar_jefes(sector, d["jefes"])
    db.session.commit()
    log.info("Sector creado: %s", sector.nombre)
    return sector


def actualizar_sector(sector: Sector, data) -> Sector:
    """Actualiza un sector. No se puede desactivar si tiene usuarios activos."""
    d, errores = validar_sector(data, sector)
    if errores:
        raise ErrorValidacion(errores)
    if sector.activo and not d["activo"]:
        activos = [j for j in d["jefes"] if j.activo]
        if activos:
            raise ErrorValidacion(
                {"activo": f"No se puede desactivar: tiene {len(activos)} usuario(s) activo(s) asociado(s)."}
            )
    sector.nombre = d["nombre"]
    sector.descripcion = d["descripcion"]
    sector.activo = d["activo"]
    _asignar_jefes(sector, d["jefes"])
    db.session.commit()
    log.info("Sector actualizado: %s (activo=%s)", sector.nombre, sector.activo)
    return sector


def desactivar_sector(sector: Sector) -> None:
    """Regla: no se puede desactivar un sector con usuarios activos. El historial se conserva."""
    activos = _usuarios_activos(sector)
    if activos:
        raise Conflicto(f"No se puede desactivar el sector: tiene {activos} usuario(s) activo(s) asociado(s).")
    sector.activo = False
    db.session.commit()
    log.info("Sector desactivado: %s", sector.nombre)


def tiene_asociados(sector: Sector) -> bool:
    """True si el sector tiene personal, usuarios o pedidos."""
    sid = sector.id
    return bool(db.session.scalar(select(
        exists().where(Persona.sector_id == sid)
        | exists().where(Usuario.sector_id == sid)
        | exists().where(Pedido.sector_id == sid)
    )))


def eliminar_sector(sector: Sector) -> None:
    """Elimina un sector sin personal, usuarios ni pedidos. Si tiene, hay que desactivarlo."""
    if tiene_asociados(sector):
        raise Conflicto("El sector tiene personal, usuarios o pedidos asociados. Desactivalo en lugar de eliminarlo.")
    db.session.execute(delete(Cupo).where(Cupo.sector_id == sector.id))
    nombre = sector.nombre
    db.session.delete(sector)
    db.session.commit()
    log.info("Sector eliminado: %s", nombre)


def buscar_sectores(filtros, page: int = 1):
    """Búsqueda por nombre, estado y Jefe asignado, con orden y paginación."""
    consulta = select(Sector).options(selectinload(Sector.jefes))

    nombre = v.texto(filtros, "nombre")
    if nombre:
        consulta = consulta.where(Sector.nombre.ilike(v.like(nombre), escape="\\"))

    estado = filtros.get("estado")
    if estado in ("activo", "inactivo"):
        consulta = consulta.where(Sector.activo.is_(estado == "activo"))

    jefe_id = v.entero(filtros, "jefe_id")
    if jefe_id:
        consulta = consulta.where(exists().where(Usuario.sector_id == Sector.id, Usuario.id == jefe_id))

    columnas = ORDENES.get(filtros.get("orden"), ORDENES["nombre"])()
    descendente = filtros.get("dir", "asc") == "desc"
    consulta = consulta.order_by(*[c.desc() if descendente else c.asc() for c in columnas], Sector.id)

    return db.paginate(consulta, page=max(page, 1), per_page=por_pagina(), error_out=False)


def contar_personal(sector: Sector) -> int:
    """Cantidad de personas asignadas al sector."""
    return db.session.scalar(select(func.count(Persona.id)).where(Persona.sector_id == sector.id))
