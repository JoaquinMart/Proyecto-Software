"""Validación de cupos. Devuelve (datos_limpios, errores)."""
from src.core.database import db
from src.core.models import COMIDAS, Sector
from src.core.validators import comunes as v

MAX_CUPO = 10000


def validar_cupo(data, cupo=None):
    """Valida sector (existente y activo), comida y cantidad mayor que cero."""
    errores = {}
    sector_id = v.entero(data, "sector_id")
    sector = db.session.get(Sector, sector_id) if sector_id else None
    if sector is None:
        errores["sector_id"] = "El sector no existe."
    elif not sector.activo and (cupo is None or cupo.sector_id != sector.id):
        errores["sector_id"] = "No se puede crear un cupo para un sector inactivo."

    comida = v.texto(data, "comida").lower()
    if comida not in COMIDAS:
        errores["comida"] = "La comida debe ser desayuno, almuerzo, merienda o cena."

    cantidad = v.entero(data, "cantidad")
    if cantidad is None:
        errores["cantidad"] = "La cantidad debe ser un número mayor que cero."
    elif cantidad > MAX_CUPO:
        errores["cantidad"] = f"La cantidad no puede superar {MAX_CUPO}."

    return {"sector": sector, "comida": comida, "cantidad": cantidad}, errores
