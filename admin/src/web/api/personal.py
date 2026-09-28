"""
Personal por API. Reglas de alcance del Jefe de Servicio (el backend las fuerza,
no confía en lo que mande el cliente):
  - ve el personal de su sector y los residentes;
  - crea, modifica y elimina solo Personal Fijo de su propio sector;
  - no gestiona residentes (eso es del Servicio de Alimentación).
"""
from flask import request

from src.core import personal as svc
from src.core.database import db
from src.core.errores import ErrorValidacion, Prohibido
from src.core.models import TipoPersonal
from src.core.models.catalogos import TIPO_FIJO
from src.web.api import bp
from src.web.api import serializers as ser
from src.web.api.helpers import (api_auth, cuerpo_json, es_jefe, pagina_actual, paginado,
                                 sector_de_jefe, usuario_api)


def _jefe_puede_ver(usuario, persona) -> bool:
    """Un Jefe ve personas de su sector y residentes."""
    return persona.es_residente or (usuario.sector_id is not None and persona.sector_id == usuario.sector_id)


def _jefe_puede_gestionar(usuario, persona) -> None:
    """Un Jefe solo gestiona Personal Fijo de su sector."""
    if persona.es_residente or persona.sector_id != usuario.sector_id:
        raise Prohibido("Solo podés gestionar Personal Fijo de tu sector.")


def _forzar_alcance_jefe(usuario, datos) -> dict:
    """Obliga a que el Jefe cargue Personal Fijo en su propio sector."""
    tipo_id = datos.get("tipo_personal_id")
    tipo = db.session.get(TipoPersonal, tipo_id) if isinstance(tipo_id, int) else None
    if tipo is not None and tipo.codigo != TIPO_FIJO:
        raise Prohibido("Un Jefe de Servicio solo puede gestionar Personal Fijo.")
    return {**datos, "sector_id": sector_de_jefe(usuario)}


def _datos_actuales(persona) -> dict:
    """Datos de la persona en el formato de entrada, para completar un PUT parcial."""
    return {"dni": persona.dni, "nombre": persona.nombre, "apellido": persona.apellido,
            "tipo_personal_id": persona.tipo_personal_id, "tipo_menu_id": persona.tipo_menu_id,
            "sector_id": persona.sector_id, "activo": persona.activo}


@bp.get("/personnel")
@api_auth("personal_index")
def listar_personal():
    """Búsqueda por dni, nombre, sector_id, tipo_personal_id y estado (activo por defecto)."""
    filtros = request.args
    if filtros.get("dni") and not filtros.get("dni").replace(".", "").isdigit():
        raise ErrorValidacion({"dni": "El DNI solo puede tener números."})
    if filtros.get("estado") and filtros.get("estado") not in ("activo", "inactivo", "todos"):
        raise ErrorValidacion({"estado": "Usá activo, inactivo o todos."})
    usuario = usuario_api()
    sector_jefe = sector_de_jefe(usuario) if es_jefe(usuario) else None
    pagina = svc.buscar_personal(filtros, pagina_actual(), sector_jefe_id=sector_jefe,
                                 estado_por_defecto="activo")
    return paginado(pagina, ser.persona)


@bp.get("/personnel/<int:persona_id>")
@api_auth("personal_show")
def obtener_persona(persona_id):
    """Ficha de una persona (un Jefe solo ve las de su sector y residentes)."""
    persona = svc.obtener_persona(persona_id)
    usuario = usuario_api()
    if es_jefe(usuario) and not _jefe_puede_ver(usuario, persona):
        raise Prohibido("La persona no pertenece a tu sector.")
    return ser.persona(persona)


@bp.post("/personnel")
@api_auth("personal_new")
def crear_persona():
    """Crea una persona (activa por defecto). 409 si el DNI ya existe."""
    datos = cuerpo_json()
    usuario = usuario_api()
    if es_jefe(usuario):
        datos = _forzar_alcance_jefe(usuario, datos)
    datos["activo"] = True
    persona = svc.crear_persona(datos)
    return ser.persona(persona), 201


@bp.put("/personnel/<int:persona_id>")
@api_auth("personal_update")
def actualizar_persona(persona_id):
    """Modifica una persona. Los campos que no se envían conservan su valor."""
    persona = svc.obtener_persona(persona_id)
    usuario = usuario_api()
    datos = {**_datos_actuales(persona), **cuerpo_json()}
    if es_jefe(usuario):
        _jefe_puede_gestionar(usuario, persona)
        datos = _forzar_alcance_jefe(usuario, datos)
    return ser.persona(svc.actualizar_persona(persona, datos))


@bp.delete("/personnel/<int:persona_id>")
@api_auth("personal_destroy")
def eliminar_persona(persona_id):
    """Elimina la persona o, si tiene historial, la marca como inactiva."""
    persona = svc.obtener_persona(persona_id)
    usuario = usuario_api()
    if es_jefe(usuario):
        _jefe_puede_gestionar(usuario, persona)
    resultado = svc.eliminar_o_desactivar(persona)
    return {"resultado": resultado,
            "mensaje": "Persona eliminada." if resultado == "eliminada"
            else "La persona tiene historial: se marcó como inactiva."}
