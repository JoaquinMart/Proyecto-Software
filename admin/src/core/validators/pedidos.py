"""Validación de la carga de pedidos y de autorizaciones. Devuelven (datos_limpios, errores)."""
import calendar
from datetime import date, timedelta

from src.core.models import COMIDAS
from src.core.models.pedidos import PERIODICIDADES
from src.core.validators import comunes as v

MAX_DIAS = 31


def validar_comidas(data, errores):
    """Valida el detalle por comida: {"almuerzo": [person_id, ...], ...}."""
    comidas = data.get("comidas")
    detalle = {}
    if not isinstance(comidas, dict) or not comidas:
        errores["comidas"] = "Indicá al menos una comida con sus personas."
        return detalle
    for comida, personas in comidas.items():
        if comida not in COMIDAS:
            errores["comidas"] = f"'{comida}' no es una comida válida."
            return {}
        if not isinstance(personas, list) or not all(isinstance(p, int) and not isinstance(p, bool) for p in personas):
            errores["comidas"] = f"La lista de personas de {comida} debe tener ids numéricos."
            return {}
        if len(personas) != len(set(personas)):
            errores["comidas"] = f"Hay personas repetidas en {comida}."
            return {}
        if personas:
            detalle[comida] = personas
    if not detalle:
        errores["comidas"] = "Indicá al menos una persona en alguna comida."
    return detalle


def validar_carga(data, hoy: date):
    """
    Valida una carga nueva:
      periodicidad: diaria | semanal | mensual
      fecha_desde (o fecha): AAAA-MM-DD, no anterior a hoy
      fecha_hasta: opcional. Por defecto: igual (diaria), +6 días (semanal) o fin de mes (mensual).
      comidas: {"desayuno": [ids], "almuerzo": [ids], ...}
    """
    errores = {}
    periodicidad = v.texto(data, "periodicidad").lower() or "diaria"
    if periodicidad not in PERIODICIDADES:
        errores["periodicidad"] = "La periodicidad debe ser diaria, semanal o mensual."

    desde = v.fecha(data.get("fecha_desde") or data.get("fecha"))
    hasta = v.fecha(data.get("fecha_hasta")) if data.get("fecha_hasta") else None
    if desde is None:
        errores["fecha_desde"] = "Indicá la fecha en formato AAAA-MM-DD."
    elif desde < hoy:
        errores["fecha_desde"] = "No se pueden cargar pedidos para fechas pasadas."
    elif data.get("fecha_hasta") and hasta is None:
        errores["fecha_hasta"] = "La fecha final no es válida."

    if desde is not None and "periodicidad" not in errores and "fecha_hasta" not in errores:
        if hasta is None:
            if periodicidad == "semanal":
                hasta = desde + timedelta(days=6)
            elif periodicidad == "mensual":
                hasta = desde.replace(day=calendar.monthrange(desde.year, desde.month)[1])
            else:
                hasta = desde
        if hasta < desde:
            errores["fecha_hasta"] = "La fecha final no puede ser anterior a la inicial."
        elif (hasta - desde).days + 1 > MAX_DIAS:
            errores["fecha_hasta"] = f"El rango no puede superar los {MAX_DIAS} días."

    comidas = validar_comidas(data, errores)

    fechas = []
    if not errores:
        fechas = [desde + timedelta(days=i) for i in range((hasta - desde).days + 1)]
    return {"periodicidad": periodicidad, "fechas": fechas, "comidas": comidas}, errores


def validar_autorizacion(data):
    """
    Valida la autorización nominada. Acepta:
      {"solicitudes": [{"id": 12, "autorizada": true}, ...]}   (individual)
      {"autorizar_todas": true}                                  (masiva)
    Las solicitudes no mencionadas quedan como no autorizadas.
    """
    errores = {}
    if v.booleano(data, "autorizar_todas"):
        return {"todas": True, "decisiones": {}}, errores

    items = data.get("solicitudes")
    decisiones = {}
    if not isinstance(items, list) or not items:
        errores["solicitudes"] = "Enviá la lista de solicitudes con su decisión, o autorizar_todas: true."
        return {"todas": False, "decisiones": {}}, errores
    for item in items:
        if (not isinstance(item, dict) or not isinstance(item.get("id"), int)
                or not isinstance(item.get("autorizada"), bool)):
            errores["solicitudes"] = "Cada solicitud debe tener id (número) y autorizada (true/false)."
            break
        decisiones[item["id"]] = item["autorizada"]
    return {"todas": False, "decisiones": decisiones}, errores
