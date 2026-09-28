"""Sectores (solo lectura) y personal por sector."""
from flask import request

from src.core import sectores as svc
from src.core.errores import ErrorValidacion, Prohibido
from src.core.personal import buscar_personal
from src.web.api import bp
from src.web.api import serializers as ser
from src.web.api.helpers import api_auth, es_jefe, pagina_actual, paginado, usuario_api


@bp.get("/sectors")
@api_auth("sector_index")
def listar_sectores():
    """Sectores activos por defecto; ?estado=todos incluye inactivos (para consultas históricas)."""
    estado = request.args.get("estado", "activo")
    if estado not in ("activo", "todos"):
        raise ErrorValidacion({"estado": "Usá activo o todos."})
    sectores = svc.listar_sectores(solo_activos=estado == "activo")
    return {"items": [ser.sector(s) for s in sectores]}


@bp.get("/sectors/<int:sector_id>")
@api_auth("sector_show")
def obtener_sector(sector_id):
    """Datos completos del sector, aunque esté inactivo."""
    return ser.sector(svc.obtener_sector(sector_id))


@bp.get("/sectors/<int:sector_id>/personnel")
@api_auth("personal_index")
def personal_del_sector(sector_id):
    """Personal activo de un sector. Un Jefe de Servicio solo puede pedir el suyo."""
    usuario = usuario_api()
    if es_jefe(usuario) and usuario.sector_id != sector_id:
        raise Prohibido("Solo podés consultar el personal de tu sector.")
    svc.obtener_sector(sector_id)  # 404 si no existe
    filtros = {"sector_id": sector_id, "estado": "activo", "orden": "apellido"}
    return paginado(buscar_personal(filtros, pagina_actual()), ser.persona)
