"""Conversión de modelos a diccionarios JSON. Nunca incluyen contraseñas ni hashes."""
from collections import defaultdict

from src.core.models.pedidos import ESTADO_CONFIRMADO, REGULAR


def fecha_hora(valor):
    """datetime/date → texto ISO 8601 (o None)."""
    return valor.isoformat() if valor is not None else None


def catalogo(item):
    """Tipo de personal o de menú."""
    return {"id": item.id, "codigo": item.codigo, "nombre": item.nombre}


def sector_breve(sector):
    """Id y nombre de un sector (o None)."""
    return {"id": sector.id, "nombre": sector.nombre} if sector else None


def sector(s):
    """Datos completos de un sector."""
    return {"id": s.id, "nombre": s.nombre, "descripcion": s.descripcion, "activo": s.activo,
            "created_at": fecha_hora(s.created_at), "updated_at": fecha_hora(s.updated_at)}


def usuario(u):
    """Datos del usuario autenticado."""
    return {"id": u.id, "nombre": u.nombre, "apellido": u.apellido, "email": u.email,
            "rol": {"codigo": u.rol.codigo, "nombre": u.rol.nombre}, "sector": sector_breve(u.sector)}


def persona_breve(p):
    """Identificación mínima de una persona."""
    return {"id": p.id, "dni": p.dni, "nombre": p.nombre, "apellido": p.apellido}


def persona(p):
    """Ficha completa de una persona."""
    return {**persona_breve(p), "activo": p.activo, "tipo_personal": catalogo(p.tipo_personal),
            "tipo_menu": catalogo(p.tipo_menu), "sector": sector_breve(p.sector),
            "created_at": fecha_hora(p.created_at), "updated_at": fecha_hora(p.updated_at)}


def solicitud(s):
    """Solicitud nominada (persona + comida) con su autorización y entrega."""
    return {"id": s.id, "persona": persona_breve(s.persona), "comida": s.comida,
            "tipo_menu": catalogo(s.tipo_menu), "condicion": s.condicion,
            "autorizada": s.autorizada, "entregada": s.entrega_id is not None, "entrega_id": s.entrega_id}


def _totales(solicitudes):
    """{comida: {menú: cantidad}} para una lista de solicitudes."""
    totales = defaultdict(lambda: defaultdict(int))
    for s in solicitudes:
        totales[s.comida][s.tipo_menu.nombre] += 1
    return {comida: dict(menus) for comida, menus in totales.items()}


def pedido(p, detalle=False):
    """Pedido con totales pedidos y, si ya fue revisado, autorizados (siempre por separado)."""
    datos = {
        "id": p.id, "sector": sector_breve(p.sector), "fecha": p.fecha.isoformat(),
        "periodicidad": p.periodicidad, "estado": p.estado,
        "creado_por": p.creado_por.nombre_completo if p.creado_por else None,
        "created_at": fecha_hora(p.created_at), "updated_at": fecha_hora(p.updated_at),
        "revisado_por": p.revisado_por.nombre_completo if p.revisado_por else None,
        "revisado_at": fecha_hora(p.revisado_at), "motivo_rechazo": p.motivo_rechazo,
        "totales": {
            "pedidas": _totales(p.solicitudes),
            "cantidad_pedidas": len(p.solicitudes),
            "regulares": sum(1 for s in p.solicitudes if s.condicion == REGULAR),
            "excepciones": sum(1 for s in p.solicitudes if s.condicion != REGULAR),
            "autorizadas": None if p.estado == ESTADO_CONFIRMADO
            else _totales([s for s in p.solicitudes if s.autorizada]),
            "cantidad_autorizadas": None if p.estado == ESTADO_CONFIRMADO
            else sum(1 for s in p.solicitudes if s.autorizada),
        },
    }
    if detalle:
        datos["solicitudes"] = [solicitud(s) for s in p.solicitudes]
    return datos


def cupo(c):
    """Cupo de un sector para una comida."""
    return {"id": c.id, "sector": sector_breve(c.sector), "comida": c.comida, "cantidad": c.cantidad,
            "created_at": fecha_hora(c.created_at), "updated_at": fecha_hora(c.updated_at)}


def comida_autorizada(s):
    """Comida autorizada para el comedor, indicando si ya se entregó."""
    return {"solicitud_id": s.id, "persona": persona_breve(s.persona), "sector": sector_breve(s.pedido.sector),
            "fecha": s.pedido.fecha.isoformat(), "comida": s.comida, "tipo_menu": catalogo(s.tipo_menu),
            "condicion": s.condicion, "entregada": s.entrega_id is not None, "entrega_id": s.entrega_id,
            "entregada_at": fecha_hora(s.entrega.fecha_hora) if s.entrega else None}


def entrega(e):
    """Entrega con quién la registró, quién retiró y qué comidas incluyó."""
    return {
        "id": e.id, "fecha_hora": fecha_hora(e.fecha_hora),
        "registrada_por": {"id": e.usuario.id, "nombre": e.usuario.nombre, "apellido": e.usuario.apellido},
        "responsable": {"persona_id": e.responsable_persona_id, "dni": e.responsable_dni,
                        "nombre": e.responsable_nombre},
        "items": [{"solicitud_id": s.id, "persona": persona_breve(s.persona), "comida": s.comida,
                   "tipo_menu": catalogo(s.tipo_menu), "sector_id": s.pedido.sector_id,
                   "fecha": s.pedido.fecha.isoformat()} for s in e.solicitudes],
    }
