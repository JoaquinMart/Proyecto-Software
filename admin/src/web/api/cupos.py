"""Cupos por sector y comida. Los gestiona Servicio de Alimentación; el Jefe solo consulta los suyos."""
from flask import request

from src.core import cupos as svc
from src.core.errores import Prohibido
from src.core.validators import comunes as v
from src.web.api import bp
from src.web.api import serializers as ser
from src.web.api.helpers import (api_auth, cuerpo_json, es_jefe, pagina_actual, paginado,
                                 sector_de_jefe, usuario_api)


@bp.get("/quotas")
@api_auth("cupo_index")
def listar_cupos():
    """Cupos filtrados por sector_id y comida, ordenados por sector."""
    usuario = usuario_api()
    sector_forzado = None
    if es_jefe(usuario):
        sector_forzado = sector_de_jefe(usuario)
        pedido = v.entero(request.args, "sector_id")
        if pedido and pedido != sector_forzado:
            raise Prohibido("Solo podés consultar los cupos de tu sector.")
    return paginado(svc.buscar_cupos(request.args, pagina_actual(), sector_forzado), ser.cupo)


@bp.post("/quotas")
@api_auth("cupo_new")
def crear_cupo():
    """Crea un cupo {sector_id, comida, cantidad}."""
    return ser.cupo(svc.crear_cupo(cuerpo_json())), 201


@bp.get("/quotas/<int:cupo_id>")
@api_auth("cupo_show")
def obtener_cupo(cupo_id):
    """Datos del cupo (un Jefe solo los de su sector)."""
    cupo = svc.obtener_cupo(cupo_id)
    usuario = usuario_api()
    if es_jefe(usuario) and cupo.sector_id != usuario.sector_id:
        raise Prohibido("El cupo no pertenece a tu sector.")
    return ser.cupo(cupo)


@bp.put("/quotas/<int:cupo_id>")
@api_auth("cupo_update")
def actualizar_cupo(cupo_id):
    """Modifica el cupo. Solo afecta pedidos que se registren después del cambio."""
    cupo = svc.obtener_cupo(cupo_id)
    datos = {"sector_id": cupo.sector_id, "comida": cupo.comida, "cantidad": cupo.cantidad, **cuerpo_json()}
    return ser.cupo(svc.actualizar_cupo(cupo, datos))


@bp.delete("/quotas/<int:cupo_id>")
@api_auth("cupo_destroy")
def eliminar_cupo(cupo_id):
    """Elimina el cupo. Responde 204."""
    svc.eliminar_cupo(svc.obtener_cupo(cupo_id))
    return "", 204
