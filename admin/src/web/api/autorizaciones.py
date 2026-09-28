"""Autorización de pedidos (Servicio de Alimentación)."""
from flask import request

from src.core.autorizaciones import autorizar_pedido, rechazar_pedido
from src.core.pedidos import listar_pedidos, obtener_pedido
from src.web.api import bp
from src.web.api import serializers as ser
from src.web.api.helpers import api_auth, cuerpo_json, pagina_actual, paginado, usuario_api


@bp.get("/authorizations")
@api_auth("autorizacion_index")
def listar():
    """Pedidos de todos los sectores (filtros: fecha_desde, fecha_hasta, sector_id, comida, tipo_menu_id, estado).
    Solo aparecen fechas con pedidos registrados. Estado confirmado = pendiente de autorización."""
    return paginado(listar_pedidos(request.args, pagina_actual()), ser.pedido)


@bp.get("/authorizations/<int:pedido_id>")
@api_auth("autorizacion_show")
def detalle(pedido_id):
    """Detalle por comida y tipo de menú, con pedidas y autorizadas por separado y las personas."""
    return ser.pedido(obtener_pedido(pedido_id), detalle=True)


@bp.put("/authorizations/<int:pedido_id>")
@api_auth("autorizacion_update")
def autorizar(pedido_id):
    """Autorización nominada: {"solicitudes": [{"id": 1, "autorizada": true}, ...]} o {"autorizar_todas": true}."""
    pedido = autorizar_pedido(usuario_api(), obtener_pedido(pedido_id), cuerpo_json())
    return ser.pedido(pedido, detalle=True)


@bp.post("/authorizations/<int:pedido_id>/reject")
@api_auth("autorizacion_update")
def rechazar(pedido_id):
    """Rechaza el pedido completo. Cuerpo opcional: {"motivo": "..."}."""
    datos = request.get_json(silent=True) or {}
    motivo = datos.get("motivo") if isinstance(datos, dict) else None
    pedido = rechazar_pedido(usuario_api(), obtener_pedido(pedido_id), motivo)
    return ser.pedido(pedido, detalle=True)
