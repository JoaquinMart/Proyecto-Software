"""Pedidos de comidas (Jefe de Servicio). El sector siempre sale del usuario autenticado."""
from flask import request

from src.core import pedidos as svc
from src.core.fechas import hoy
from src.web.api import bp
from src.web.api import serializers as ser
from src.web.api.helpers import api_auth, cuerpo_json, pagina_actual, paginado, sector_de_jefe, usuario_api


@bp.get("/requests")
@api_auth("pedido_index")
def listar_pedidos():
    """Pedidos del sector del Jefe (filtros: fecha_desde, fecha_hasta, comida, tipo_menu_id, estado)."""
    sector_id = sector_de_jefe(usuario_api())
    pagina = svc.listar_pedidos(request.args, pagina_actual(), sector_id=sector_id)
    return paginado(pagina, ser.pedido)


@bp.post("/requests")
@api_auth("pedido_new")
def crear_pedido():
    """Carga diaria, semanal o mensual. Crea un pedido por fecha y marca Regular/Excepción según el cupo."""
    pedidos = svc.crear_pedidos(usuario_api(), cuerpo_json(), hoy())
    return {"pedidos": [ser.pedido(p, detalle=True) for p in pedidos]}, 201


@bp.get("/requests/<int:pedido_id>")
@api_auth("pedido_show")
def obtener_pedido(pedido_id):
    """Detalle completo del pedido (solo del propio sector)."""
    return ser.pedido(svc.pedido_del_jefe(usuario_api(), pedido_id), detalle=True)


@bp.put("/requests/<int:pedido_id>")
@api_auth("pedido_update")
def actualizar_pedido(pedido_id):
    """Reemplaza las personas por comida. Solo si el pedido sigue confirmado."""
    usuario = usuario_api()
    pedido = svc.pedido_del_jefe(usuario, pedido_id)
    return ser.pedido(svc.actualizar_pedido(usuario, pedido, cuerpo_json()), detalle=True)


@bp.delete("/requests/<int:pedido_id>")
@api_auth("pedido_destroy")
def eliminar_pedido(pedido_id):
    """Elimina un pedido todavía confirmado. Responde 204 sin cuerpo."""
    usuario = usuario_api()
    svc.eliminar_pedido(usuario, svc.pedido_del_jefe(usuario, pedido_id))
    return "", 204
