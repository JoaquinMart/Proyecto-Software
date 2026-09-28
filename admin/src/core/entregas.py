"""
Consulta de comidas autorizadas y registro de entregas en el comedor.

Una comida es entregable si su solicitud está autorizada, el pedido está autorizado
y la solicitud todavía no tiene entrega. Una persona no puede retirar dos veces la misma
comida del mismo día, aunque figure en pedidos de dos sectores (residentes).
"""
import logging
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from src.core.configuracion import por_pagina
from src.core.database import db
from src.core.errores import Conflicto, ErrorValidacion, NoEncontrado
from src.core.fechas import ahora, rango_del_dia
from src.core.models import COMIDAS, Entrega, Pedido, Persona, Solicitud
from src.core.models.pedidos import ESTADO_AUTORIZADO
from src.core.validators import comunes as v

log = logging.getLogger("alimentacion")


def _autorizadas():
    """Consulta base: solicitudes autorizadas de pedidos autorizados."""
    return (select(Solicitud).join(Solicitud.pedido).join(Solicitud.persona)
            .where(Pedido.estado == ESTADO_AUTORIZADO, Solicitud.autorizada.is_(True))
            .options(selectinload(Solicitud.persona), selectinload(Solicitud.tipo_menu),
                     selectinload(Solicitud.pedido).selectinload(Pedido.sector),
                     selectinload(Solicitud.entrega)))


def _fecha_filtro(filtros, hoy):
    """Fecha del filtro (por defecto hoy)."""
    if filtros.get("fecha"):
        fecha = v.fecha(filtros.get("fecha"))
        if fecha is None:
            raise ErrorValidacion({"fecha": "La fecha debe tener formato AAAA-MM-DD."})
        return fecha
    return hoy


def buscar_autorizadas(filtros, hoy: date, page: int = 1):
    """
    Comidas autorizadas filtradas por fecha, DNI, nombre y apellido, sector o comida.
    Exige al menos un filtro para no traer todo el sistema.
    """
    campos = ("fecha", "dni", "nombre", "sector_id", "comida")
    if not any(v.texto(filtros, c) for c in campos):
        raise ErrorValidacion({"filtros": "Indicá al menos un filtro: fecha, dni, nombre, sector_id o comida."})

    consulta = _autorizadas().where(Pedido.fecha == _fecha_filtro(filtros, hoy))
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
    sector_id = v.entero(filtros, "sector_id")
    if sector_id:
        consulta = consulta.where(Pedido.sector_id == sector_id)
    comida = v.texto(filtros, "comida").lower()
    if comida:
        if comida not in COMIDAS:
            raise ErrorValidacion({"comida": "La comida debe ser desayuno, almuerzo, merienda o cena."})
        consulta = consulta.where(Solicitud.comida == comida)

    consulta = consulta.order_by(Persona.apellido, Persona.nombre, Solicitud.comida, Solicitud.id)
    return db.paginate(consulta, page=max(page, 1), per_page=por_pagina(), error_out=False)


def autorizadas_de_persona(persona_id: int, fecha: date):
    """Comidas autorizadas de una persona en una fecha (desayuno, almuerzo, merienda, cena)."""
    if db.session.get(Persona, persona_id) is None:
        raise NoEncontrado("La persona no existe.")
    consulta = _autorizadas().where(Solicitud.persona_id == persona_id, Pedido.fecha == fecha)
    solicitudes = db.session.scalars(consulta).all()
    orden = {c: i for i, c in enumerate(COMIDAS)}
    return sorted(solicitudes, key=lambda s: orden[s.comida])


def _items(data):
    """
    Acepta dos formatos de entrada:
      {"items": [{"persona_id": 1, "comida": "almuerzo"}, ...]}      (varias comidas)
      {"comida": "almuerzo", "personas": [1, 2, 3]}                   (una comida, varias personas)
    """
    items = data.get("items")
    if items is None and data.get("personas") is not None:
        items = [{"persona_id": p, "comida": data.get("comida")} for p in data.get("personas") or []]
    if not isinstance(items, list) or not items:
        raise ErrorValidacion({"items": "Indicá al menos una persona y comida a entregar."})
    pares = []
    for item in items:
        if not isinstance(item, dict):
            raise ErrorValidacion({"items": "Formato de ítem inválido."})
        pid = item.get("persona_id")
        comida = str(item.get("comida") or "").lower()
        if not isinstance(pid, int) or isinstance(pid, bool) or comida not in COMIDAS:
            raise ErrorValidacion({"items": "Cada ítem necesita persona_id (número) y una comida válida."})
        pares.append((pid, comida))
    if len(pares) != len(set(pares)):
        raise ErrorValidacion({"items": "Hay ítems repetidos."})
    return pares


def _responsable(data):
    """Quién retira: una persona registrada (persona_id) o alguien identificado por DNI y nombre."""
    resp = data.get("responsable")
    if not isinstance(resp, dict):
        raise ErrorValidacion({"responsable": "Indicá quién retira (persona_id, o dni y nombre)."})
    if resp.get("persona_id") is not None:
        persona = db.session.get(Persona, resp.get("persona_id")) if isinstance(resp.get("persona_id"), int) else None
        if persona is None:
            raise ErrorValidacion({"responsable": "La persona responsable no existe."})
        return persona, persona.dni, f"{persona.nombre} {persona.apellido}"
    dni = v.dni(v.texto(resp, "dni"))
    nombre = v.texto(resp, "nombre")
    errores = {}
    v.validar_dni(errores, "responsable", dni)
    if not errores and (len(nombre) < 2 or len(nombre) > 110):
        errores["responsable"] = "Indicá el nombre y apellido de quien retira."
    if errores:
        raise ErrorValidacion(errores)
    return None, dni, nombre


def registrar_entrega(usuario, data, hoy: date) -> Entrega:
    """
    Registra la entrega de una o varias comidas en una misma operación.
    Fecha, hora y usuario los pone el servidor. Bloquea las filas para evitar dobles entregas.
    """
    pares = _items(data)
    responsable, resp_dni, resp_nombre = _responsable(data)

    a_entregar = []
    sin_autorizacion, ya_entregadas = [], []
    for persona_id, comida in pares:
        solicitudes = db.session.scalars(
            select(Solicitud).join(Solicitud.pedido)
            .where(Solicitud.persona_id == persona_id, Solicitud.comida == comida, Pedido.fecha == hoy,
                   Pedido.estado == ESTADO_AUTORIZADO, Solicitud.autorizada.is_(True))
            .order_by(Solicitud.id)
            .with_for_update(of=Solicitud)
        ).all()
        if not solicitudes:
            sin_autorizacion.append(f"persona {persona_id} ({comida})")
        elif any(s.entrega_id is not None for s in solicitudes):
            ya_entregadas.append(f"persona {persona_id} ({comida})")
        else:
            a_entregar.append(solicitudes[0])

    if sin_autorizacion:
        db.session.rollback()
        raise ErrorValidacion({"items": "Sin autorización vigente para hoy: " + ", ".join(sin_autorizacion) + "."})
    if ya_entregadas:
        db.session.rollback()
        raise Conflicto("Comida ya entregada: " + ", ".join(ya_entregadas) + ".")

    entrega = Entrega(
        fecha_hora=ahora(), usuario_id=usuario.id,
        responsable_persona=responsable, responsable_dni=resp_dni, responsable_nombre=resp_nombre,
    )
    db.session.add(entrega)
    for solicitud in a_entregar:
        solicitud.entrega = entrega
    db.session.commit()
    log.info("Entrega %s registrada por %s: %s comida(s), retira DNI %s",
             entrega.id, usuario.email, len(a_entregar), resp_dni)
    return entrega


def obtener_entrega(entrega_id) -> Entrega:
    """Devuelve la entrega o lanza NoEncontrado."""
    entrega = db.session.get(Entrega, entrega_id)
    if entrega is None:
        raise NoEncontrado("La entrega no existe.")
    return entrega


def listar_entregas(filtros, hoy: date, page: int = 1):
    """Entregas de una fecha (por defecto hoy), opcionalmente por sector y comida."""
    fecha = _fecha_filtro(filtros, hoy)
    inicio, fin = rango_del_dia(fecha)
    consulta = (select(Entrega).where(Entrega.fecha_hora.between(inicio, fin))
                .options(selectinload(Entrega.usuario),
                         selectinload(Entrega.solicitudes).selectinload(Solicitud.persona),
                         selectinload(Entrega.solicitudes).selectinload(Solicitud.tipo_menu),
                         selectinload(Entrega.solicitudes).selectinload(Solicitud.pedido)))
    sector_id = v.entero(filtros, "sector_id")
    comida = v.texto(filtros, "comida").lower()
    if sector_id or comida:
        sub = select(Solicitud.entrega_id).join(Solicitud.pedido).where(Solicitud.entrega_id.is_not(None))
        if sector_id:
            sub = sub.where(Pedido.sector_id == sector_id)
        if comida:
            sub = sub.where(Solicitud.comida == comida)
        consulta = consulta.where(Entrega.id.in_(sub))
    consulta = consulta.order_by(Entrega.fecha_hora.desc())
    return db.paginate(consulta, page=max(page, 1), per_page=por_pagina(), error_out=False)


def resumen_del_dia(filtros, hoy: date):
    """Totales autorizados vs. entregados por comida y tipo de menú, para una fecha."""
    from src.core.models import TipoMenu
    fecha = _fecha_filtro(filtros, hoy)
    consulta = (select(Solicitud.comida, TipoMenu.nombre,
                       func.count(Solicitud.id), func.count(Solicitud.entrega_id))
                .join(Solicitud.pedido).join(Solicitud.tipo_menu)
                .where(Pedido.fecha == fecha, Pedido.estado == ESTADO_AUTORIZADO, Solicitud.autorizada.is_(True))
                .group_by(Solicitud.comida, TipoMenu.nombre))
    sector_id = v.entero(filtros, "sector_id")
    if sector_id:
        consulta = consulta.where(Pedido.sector_id == sector_id)
    comida = v.texto(filtros, "comida").lower()
    if comida:
        consulta = consulta.where(Solicitud.comida == comida)

    detalle = [{"comida": c, "tipo_menu": m, "autorizadas": a, "entregadas": e}
               for c, m, a, e in db.session.execute(consulta)]
    orden = {c: i for i, c in enumerate(COMIDAS)}
    detalle.sort(key=lambda d: (orden[d["comida"]], d["tipo_menu"]))
    return {
        "fecha": fecha.isoformat(),
        "sector_id": sector_id,
        "autorizadas": sum(d["autorizadas"] for d in detalle),
        "entregadas": sum(d["entregadas"] for d in detalle),
        "detalle": detalle,
    }

