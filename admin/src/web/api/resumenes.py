"""Resúmenes para control y planificación."""
from flask import request

from src.core import resumenes as svc
from src.web.api import bp
from src.web.api.helpers import api_auth, es_jefe, sector_de_jefe, usuario_api


@bp.get("/summaries/requests")
@api_auth("resumen_pedidos")
def resumen_pedidos():
    """Totales pedidos (agrupar=dia|semana|mes|sector|comida|menu). Un Jefe solo ve su sector."""
    usuario = usuario_api()
    sector = sector_de_jefe(usuario) if es_jefe(usuario) else None
    return svc.resumen_pedidos(request.args, sector)


@bp.get("/summaries/authorizations")
@api_auth("resumen_autorizaciones")
def resumen_autorizaciones():
    """Pedidas vs. autorizadas, con la diferencia."""
    return svc.resumen_autorizaciones(request.args)


@bp.get("/summaries/deliveries")
@api_auth("resumen_entregas")
def resumen_entregas():
    """Autorizadas vs. entregadas, con la diferencia."""
    return svc.resumen_entregas(request.args)
