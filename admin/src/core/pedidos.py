"""
Carga de pedidos por el Jefe de Servicio.

Regla de cupo: para cada fecha y comida, las primeras N personas (N = cupo del sector)
quedan como Regulares y las siguientes como Excepción. Se calcula al cargar y se guarda
en la solicitud, así un cambio de cupo posterior no altera pedidos ya registrados.
"""
import logging
from datetime import date

from sqlalchemy import exists, select
from sqlalchemy.orm import selectinload

from src.core.configuracion import por_pagina
from src.core.cupos import cupos_de_sector
from src.core.database import db
from src.core.errores import Conflicto, ErrorValidacion, NoEncontrado, Prohibido
from src.core.models import Pedido, Persona, Solicitud
from src.core.models.pedidos import ESTADO_CONFIRMADO, ESTADOS, EXCEPCION, REGULAR
from src.core.validators import comunes as v
from src.core.validators.pedidos import validar_carga, validar_comidas

log = logging.getLogger("alimentacion")


def sector_del_jefe(jefe):
    """Sector activo del Jefe de Servicio, o error si no tiene uno."""
    if jefe.sector is None:
        raise Prohibido("Tu usuario no tiene un sector asignado.")
    if not jefe.sector.activo:
        raise Conflicto("Tu sector está inactivo y no puede registrar nuevos pedidos.")
    return jefe.sector


def _validar_personas(comidas: dict, sector_id: int) -> dict[int, Persona]:
    """Verifica que las personas existan, estén activas y pertenezcan al sector (o sean residentes)."""
    ids = {pid for personas in comidas.values() for pid in personas}
    personas = {p.id: p for p in db.session.scalars(
        select(Persona).where(Persona.id.in_(ids)).options(selectinload(Persona.tipo_personal))
    )}
    errores = []
    for pid in sorted(ids):
        persona = personas.get(pid)
        if persona is None:
            errores.append(f"La persona {pid} no existe.")
        elif not persona.activo:
            errores.append(f"{persona.nombre_completo} (DNI {persona.dni}) está inactiva.")
        elif not persona.es_residente and persona.sector_id != sector_id:
            errores.append(f"{persona.nombre_completo} (DNI {persona.dni}) no tiene asignación vigente en tu sector.")
    if errores:
        raise ErrorValidacion({"personas": " ".join(errores)})
    return personas


def _armar_solicitudes(pedido: Pedido, comidas: dict, personas: dict, cupos: dict) -> None:
    """Crea las solicitudes nominadas marcando Regular/Excepción según el cupo actual."""
    for comida, ids in comidas.items():
        cupo = cupos.get(comida, 0)
        for posicion, pid in enumerate(ids):
            pedido.solicitudes.append(Solicitud(
                persona_id=pid,
                comida=comida,
                tipo_menu_id=personas[pid].tipo_menu_id,  # copia del menú al momento de la carga
                condicion=REGULAR if posicion < cupo else EXCEPCION,
            ))


def crear_pedidos(jefe, data, hoy: date) -> list[Pedido]:
    """Crea un pedido por cada fecha del rango (diaria, semanal o mensual). Es todo o nada."""
    sector = sector_del_jefe(jefe)
    d, errores = validar_carga(data, hoy)
    if errores:
        raise ErrorValidacion(errores)
    personas = _validar_personas(d["comidas"], sector.id)

    existentes = db.session.scalars(
        select(Pedido.fecha).where(Pedido.sector_id == sector.id, Pedido.fecha.in_(d["fechas"]))
    ).all()
    if existentes:
        fechas = ", ".join(f.strftime("%d/%m/%Y") for f in sorted(existentes))
        raise Conflicto(f"Ya existe un pedido del sector para: {fechas}. Modificalo en lugar de crear otro.")

    cupos = cupos_de_sector(sector.id)
    pedidos = []
    for fecha in d["fechas"]:
        pedido = Pedido(sector=sector, fecha=fecha, periodicidad=d["periodicidad"],
                        estado=ESTADO_CONFIRMADO, creado_por=jefe)
        _armar_solicitudes(pedido, d["comidas"], personas, cupos)
        db.session.add(pedido)
        pedidos.append(pedido)
    db.session.commit()
    log.info("Pedidos creados por %s: sector %s, %s fecha(s)", jefe.email, sector.nombre, len(pedidos))
    return pedidos


def obtener_pedido(pedido_id) -> Pedido:
    """Devuelve el pedido o lanza NoEncontrado."""
    pedido = db.session.get(Pedido, pedido_id)
    if pedido is None:
        raise NoEncontrado("El pedido no existe.")
    return pedido


def pedido_del_jefe(jefe, pedido_id) -> Pedido:
    """El pedido solo es accesible para los Jefes de su sector."""
    pedido = obtener_pedido(pedido_id)
    if jefe.sector_id is None or pedido.sector_id != jefe.sector_id:
        raise Prohibido("El pedido no pertenece a tu sector.")
    return pedido


def _editable(pedido: Pedido) -> None:
    """Solo se modifica o elimina un pedido que todavía no fue revisado."""
    if pedido.estado != ESTADO_CONFIRMADO:
        raise Conflicto(f"El pedido ya fue {pedido.estado} y no se puede modificar.")


def actualizar_pedido(jefe, pedido: Pedido, data) -> Pedido:
    """Reemplaza las personas del pedido y recalcula Regular/Excepción con el cupo actual."""
    _editable(pedido)
    errores = {}
    comidas = validar_comidas(data, errores)
    if errores:
        raise ErrorValidacion(errores)
    personas = _validar_personas(comidas, pedido.sector_id)
    pedido.solicitudes.clear()
    db.session.flush()  # borra las anteriores antes de insertar (evita chocar con la restricción única)
    _armar_solicitudes(pedido, comidas, personas, cupos_de_sector(pedido.sector_id))
    pedido.modificado_por = jefe
    db.session.commit()
    log.info("Pedido %s modificado por %s", pedido.id, jefe.email)
    return pedido


def eliminar_pedido(jefe, pedido: Pedido) -> None:
    """Elimina un pedido que todavía está confirmado (sin revisar)."""
    _editable(pedido)
    pid = pedido.id
    db.session.delete(pedido)
    db.session.commit()
    log.info("Pedido %s eliminado por %s", pid, jefe.email)


def filtrar_pedidos(consulta, filtros):
    """Aplica filtros comunes: fechas, sector, comida, tipo de menú y estado."""
    desde = v.fecha(filtros.get("fecha_desde")) if filtros.get("fecha_desde") else None
    hasta = v.fecha(filtros.get("fecha_hasta")) if filtros.get("fecha_hasta") else None
    if filtros.get("fecha_desde") and desde is None or filtros.get("fecha_hasta") and hasta is None:
        raise ErrorValidacion({"fecha": "Las fechas deben tener formato AAAA-MM-DD."})
    if desde:
        consulta = consulta.where(Pedido.fecha >= desde)
    if hasta:
        consulta = consulta.where(Pedido.fecha <= hasta)

    comida = v.texto(filtros, "comida").lower()
    menu_id = v.entero(filtros, "tipo_menu_id")
    if comida or menu_id:
        condiciones = [Solicitud.pedido_id == Pedido.id]
        if comida:
            condiciones.append(Solicitud.comida == comida)
        if menu_id:
            condiciones.append(Solicitud.tipo_menu_id == menu_id)
        consulta = consulta.where(exists().where(*condiciones))

    estado = v.texto(filtros, "estado").lower()
    if estado:
        if estado not in ESTADOS:
            raise ErrorValidacion({"estado": "El estado debe ser confirmado, autorizado o rechazado."})
        consulta = consulta.where(Pedido.estado == estado)
    return consulta


def listar_pedidos(filtros, page=1, sector_id: int | None = None):
    """Listado paginado de pedidos, más recientes primero."""
    consulta = select(Pedido).options(
        selectinload(Pedido.sector), selectinload(Pedido.solicitudes).selectinload(Solicitud.tipo_menu)
    )
    if sector_id is not None:
        consulta = consulta.where(Pedido.sector_id == sector_id)
    else:
        filtro_sector = v.entero(filtros, "sector_id")
        if filtro_sector:
            consulta = consulta.where(Pedido.sector_id == filtro_sector)
    consulta = filtrar_pedidos(consulta, filtros).order_by(Pedido.fecha.desc(), Pedido.id.desc())
    return db.paginate(consulta, page=max(page, 1), per_page=por_pagina(), error_out=False)
