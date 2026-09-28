"""Comidas autorizadas y entregas (Sector Comedor y Servicio de Alimentación)."""
from flask import request

from src.core import entregas as svc
from src.core.errores import ErrorValidacion
from src.core.fechas import hoy
from src.core.validators import comunes as v
from src.web.api import bp
from src.web.api import serializers as ser
from src.web.api.helpers import api_auth, cuerpo_json, pagina_actual, paginado, usuario_api


@bp.get("/authorized-meals")
@api_auth("comida_autorizada_index")
def comidas_autorizadas():
    """Autorizadas por fecha (hoy por defecto), dni, nombre, sector_id o comida. Exige al menos un filtro."""
    pagina = svc.buscar_autorizadas(request.args, hoy(), pagina_actual())
    datos = paginado(pagina, ser.comida_autorizada)
    datos["resumen"] = svc.resumen_del_dia(request.args, hoy())
    return datos


@bp.get("/authorized-meals/<int:persona_id>")
@api_auth("comida_autorizada_index")
def comidas_de_persona(persona_id):
    """Comidas autorizadas de una persona en una fecha (hoy por defecto), indicando si ya se entregaron."""
    fecha = hoy()
    if request.args.get("fecha"):
        fecha = v.fecha(request.args.get("fecha"))
        if fecha is None:
            raise ErrorValidacion({"fecha": "La fecha debe tener formato AAAA-MM-DD."})
    solicitudes = svc.autorizadas_de_persona(persona_id, fecha)
    return {"persona_id": persona_id, "fecha": fecha.isoformat(),
            "items": [ser.comida_autorizada(s) for s in solicitudes]}


@bp.get("/deliveries")
@api_auth("entrega_index")
def listar_entregas():
    """Entregas de una fecha (hoy por defecto), con filtros sector_id y comida."""
    return paginado(svc.listar_entregas(request.args, hoy(), pagina_actual()), ser.entrega)


@bp.get("/deliveries/summary")
@api_auth("entrega_index")
def resumen_del_dia():
    """Totales autorizados vs. entregados del día, por comida y tipo de menú."""
    return svc.resumen_del_dia(request.args, hoy())


@bp.post("/deliveries")
@api_auth("entrega_new")
def registrar_entrega():
    """
    Registra el retiro de una o varias comidas. Fecha, hora y usuario los completa el servidor.
    {"items": [{"persona_id": 1, "comida": "almuerzo"}], "responsable": {"persona_id": 1}}
    """
    entrega = svc.registrar_entrega(usuario_api(), cuerpo_json(), hoy())
    return ser.entrega(entrega), 201


@bp.get("/deliveries/<int:entrega_id>")
@api_auth("entrega_show")
def obtener_entrega(entrega_id):
    """Detalle de una entrega."""
    return ser.entrega(svc.obtener_entrega(entrega_id))
