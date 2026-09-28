"""Validación de los datos de una persona del personal. Devuelve (datos_limpios, errores)."""
from sqlalchemy import select

from src.core.database import db
from src.core.models import Persona, Sector, TipoMenu, TipoPersonal
from src.core.models.catalogos import TIPO_RESIDENTE
from src.core.validators import comunes as v

MSG_DNI_DUPLICADO = "Ya existe una persona con ese DNI."


def validar_persona(data, persona: Persona | None = None):
    """
    Valida DNI, nombre, apellido, tipo de personal, sector y tipo de menú.
    Regla de sector: obligatorio para Personal Fijo; los Residentes no tienen sector.
    """
    errores = {}
    dni = v.dni(v.texto(data, "dni"))
    nombre = v.texto(data, "nombre")
    apellido = v.texto(data, "apellido")
    activo = v.booleano(data, "activo", por_defecto=persona is None or persona.activo)

    v.validar_dni(errores, "dni", dni)
    if "dni" not in errores:
        consulta = select(Persona.id).where(Persona.dni == dni)
        if persona is not None:
            consulta = consulta.where(Persona.id != persona.id)
        if db.session.scalar(consulta):
            errores["dni"] = MSG_DNI_DUPLICADO

    v.validar_nombre(errores, "nombre", nombre, "el nombre")
    v.validar_nombre(errores, "apellido", apellido, "el apellido")

    tipo_id = v.entero(data, "tipo_personal_id")
    tipo = db.session.get(TipoPersonal, tipo_id) if tipo_id else None
    if tipo is None:
        errores["tipo_personal_id"] = "Elegí un tipo de personal válido."

    menu_id = v.entero(data, "tipo_menu_id")
    menu = db.session.get(TipoMenu, menu_id) if menu_id else None
    if menu is None:
        errores["tipo_menu_id"] = "Elegí un tipo de menú válido."

    sector = None
    if tipo is not None and tipo.codigo != TIPO_RESIDENTE:
        sector_id = v.entero(data, "sector_id")
        sector = db.session.get(Sector, sector_id) if sector_id else None
        if sector is None:
            errores["sector_id"] = "Elegí el sector de la persona."
        elif not sector.activo and (persona is None or persona.sector_id != sector.id):
            errores["sector_id"] = "No se puede asignar un sector inactivo."

    datos = {
        "dni": dni, "nombre": nombre, "apellido": apellido, "activo": activo,
        "tipo_personal": tipo, "tipo_menu": menu, "sector": sector,
    }
    return datos, errores
