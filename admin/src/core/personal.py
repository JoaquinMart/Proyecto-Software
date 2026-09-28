"""Reglas de negocio del personal del hospital."""
import logging

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import selectinload

from src.core.configuracion import por_pagina
from src.core.database import db
from src.core.errores import Conflicto, ErrorValidacion, NoEncontrado
from src.core.models import Persona, Solicitud, TipoMenu, TipoPersonal
from src.core.models.catalogos import TIPO_RESIDENTE
from src.core.validators import comunes as v
from src.core.validators.personal import MSG_DNI_DUPLICADO, validar_persona

log = logging.getLogger("alimentacion")

ORDENES = {
    "apellido": lambda: [Persona.apellido, Persona.nombre],
    "dni": lambda: [Persona.dni],
    "creacion": lambda: [Persona.created_at],
}


def tipos_personal():
    """Catálogo de tipos de personal."""
    return db.session.scalars(select(TipoPersonal).order_by(TipoPersonal.id)).all()


def tipos_menu():
    """Catálogo de tipos de menú."""
    return db.session.scalars(select(TipoMenu).order_by(TipoMenu.id)).all()


def obtener_persona(persona_id) -> Persona:
    """Devuelve la persona o lanza NoEncontrado."""
    persona = db.session.get(Persona, persona_id)
    if persona is None:
        raise NoEncontrado("La persona no existe.")
    return persona


def _error_validacion(errores):
    """Convierte los errores del validador en la excepción adecuada (409 si solo es DNI duplicado)."""
    if errores == {"dni": MSG_DNI_DUPLICADO}:
        raise Conflicto(MSG_DNI_DUPLICADO, errores)
    raise ErrorValidacion(errores)


def crear_persona(data, commit=True) -> Persona:
    """Crea una persona validada. Queda activa por defecto."""
    d, errores = validar_persona(data)
    if errores:
        _error_validacion(errores)
    persona = Persona(
        dni=d["dni"], nombre=d["nombre"], apellido=d["apellido"], activo=d["activo"],
        tipo_personal=d["tipo_personal"], tipo_menu=d["tipo_menu"], sector=d["sector"],
    )
    db.session.add(persona)
    if commit:
        db.session.commit()
        log.info("Persona creada: DNI %s", persona.dni)
    return persona


def actualizar_persona(persona: Persona, data) -> Persona:
    """
    Actualiza una persona. Si pasa a Residente, pierde el sector (lo hace el validador).
    Los pedidos históricos no cambian: la solicitud guarda su propio menú y el sector está en el pedido.
    """
    d, errores = validar_persona(data, persona)
    if errores:
        _error_validacion(errores)
    persona.dni = d["dni"]
    persona.nombre = d["nombre"]
    persona.apellido = d["apellido"]
    persona.activo = d["activo"]
    persona.tipo_personal = d["tipo_personal"]
    persona.tipo_menu = d["tipo_menu"]
    persona.sector = d["sector"]
    db.session.commit()
    log.info("Persona actualizada: DNI %s", persona.dni)
    return persona


def tiene_historial(persona: Persona) -> bool:
    """True si la persona figura en algún pedido (y por lo tanto en autorizaciones o entregas)."""
    return bool(db.session.scalar(select(exists().where(Solicitud.persona_id == persona.id))))


def eliminar_persona(persona: Persona) -> None:
    """Elimina una persona sin historial. Si tiene pedidos o entregas, hay que desactivarla."""
    if tiene_historial(persona):
        raise Conflicto("La persona tiene pedidos o entregas registrados. Desactivala en lugar de eliminarla.")
    dni = persona.dni
    db.session.delete(persona)
    db.session.commit()
    log.info("Persona eliminada: DNI %s", dni)


def eliminar_o_desactivar(persona: Persona) -> str:
    """Para la API: elimina si no tiene historial; si lo tiene, la marca inactiva."""
    if tiene_historial(persona):
        persona.activo = False
        db.session.commit()
        log.info("Persona desactivada: DNI %s", persona.dni)
        return "desactivada"
    eliminar_persona(persona)
    return "eliminada"


def buscar_personal(filtros, page: int = 1, sector_jefe_id: int | None = None, estado_por_defecto="todos"):
    """
    Búsqueda por DNI, nombre o apellido, sector, tipo y estado.
    sector_jefe_id: si se indica (Jefe de Servicio), se fuerza a su sector + residentes,
    sin importar el sector que pida el cliente.
    """
    consulta = (select(Persona).join(Persona.tipo_personal)
                .options(selectinload(Persona.sector), selectinload(Persona.tipo_menu),
                         selectinload(Persona.tipo_personal)))

    dni = v.dni(v.texto(filtros, "dni"))
    if dni:
        consulta = consulta.where(Persona.dni.like(v.like(dni), escape="\\"))

    nombre = v.texto(filtros, "nombre")
    if nombre:
        patron = v.like(nombre)
        consulta = consulta.where(or_(
            func.concat(Persona.nombre, " ", Persona.apellido).ilike(patron, escape="\\"),
            func.concat(Persona.apellido, " ", Persona.nombre).ilike(patron, escape="\\"),
        ))

    tipo_id = v.entero(filtros, "tipo_personal_id")
    if tipo_id:
        consulta = consulta.where(Persona.tipo_personal_id == tipo_id)

    if sector_jefe_id is not None:
        consulta = consulta.where(or_(Persona.sector_id == sector_jefe_id, TipoPersonal.codigo == TIPO_RESIDENTE))
    else:
        sector_id = v.entero(filtros, "sector_id")
        if sector_id:
            consulta = consulta.where(Persona.sector_id == sector_id)

    estado = filtros.get("estado") or estado_por_defecto
    if estado in ("activo", "inactivo"):
        consulta = consulta.where(Persona.activo.is_(estado == "activo"))

    columnas = ORDENES.get(filtros.get("orden"), ORDENES["apellido"])()
    descendente = filtros.get("dir", "asc") == "desc"
    consulta = consulta.order_by(*[c.desc() if descendente else c.asc() for c in columnas], Persona.id)

    return db.paginate(consulta, page=max(page, 1), per_page=por_pagina(), error_out=False)
