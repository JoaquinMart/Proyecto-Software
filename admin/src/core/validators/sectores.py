"""Validación de los datos de un sector. Devuelve (datos_limpios, errores)."""
from sqlalchemy import func, select

from src.core.database import db
from src.core.models import Sector, Usuario
from src.core.validators import comunes as v
from src.core.validators.usuarios import ROL_JEFE


def _ids(data, campo):
    """Lee una lista de ids desde un formulario (getlist) o desde JSON (lista)."""
    if hasattr(data, "getlist"):
        valores = data.getlist(campo)
    else:
        valores = data.get(campo) or []
    if not isinstance(valores, list):
        return None
    ids = []
    for valor in valores:
        valor = str(valor).strip()
        if not valor.isdigit():
            return None
        ids.append(int(valor))
    return list(dict.fromkeys(ids))  # sin repetidos, respetando el orden


def validar_sector(data, sector: Sector | None = None):
    """Valida nombre, descripción, estado y Jefes de Servicio asignados."""
    errores = {}
    nombre = v.texto(data, "nombre")
    descripcion = (data.get("descripcion") or "").strip()
    activo = v.booleano(data, "activo")

    if not nombre:
        errores["nombre"] = "Ingresá el nombre del sector."
    elif len(nombre) < 2 or len(nombre) > 100:
        errores["nombre"] = "El nombre debe tener entre 2 y 100 caracteres."
    else:
        consulta = select(Sector.id).where(func.lower(Sector.nombre) == nombre.lower())
        if sector is not None:
            consulta = consulta.where(Sector.id != sector.id)
        if db.session.scalar(consulta):
            errores["nombre"] = "Ya existe un sector con ese nombre."

    if len(descripcion) > 500:
        errores["descripcion"] = "La descripción no puede superar los 500 caracteres."

    jefes = []
    ids = _ids(data, "jefes")
    if ids is None:
        errores["jefes"] = "La selección de Jefes de Servicio no es válida."
    else:
        for usuario_id in ids:
            usuario = db.session.get(Usuario, usuario_id)
            if usuario is None:
                errores["jefes"] = f"El usuario {usuario_id} no existe."
                break
            if usuario.rol.codigo != ROL_JEFE:
                errores["jefes"] = f"{usuario.email} no tiene rol Jefe de Servicio."
                break
            if usuario.sector_id is not None and (sector is None or usuario.sector_id != sector.id):
                errores["jefes"] = f"{usuario.email} ya está asociado a otro sector."
                break
            jefes.append(usuario)

        nuevos = [j for j in jefes if sector is None or j.sector_id != sector.id]
        if nuevos and not activo:
            errores["jefes"] = "No se pueden asignar Jefes de Servicio a un sector inactivo."

    return {"nombre": nombre, "descripcion": descripcion, "activo": activo, "jefes": jefes}, errores
