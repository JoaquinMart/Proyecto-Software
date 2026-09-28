"""Resúmenes de pedidos, autorizaciones y entregas agrupados por período, sector, comida o menú."""
from datetime import date, datetime

from sqlalchemy import Date, case, cast, func, select

from src.core.database import db
from src.core.errores import ErrorValidacion
from src.core.models import Pedido, Sector, Solicitud, TipoMenu
from src.core.models.pedidos import REGULAR
from src.core.pedidos import filtrar_pedidos
from src.core.validators import comunes as v

AGRUPAMIENTOS = {
    "dia": lambda: Pedido.fecha,
    "semana": lambda: cast(func.date_trunc("week", Pedido.fecha), Date),
    "mes": lambda: cast(func.date_trunc("month", Pedido.fecha), Date),
    "sector": lambda: Sector.nombre,
    "comida": lambda: Solicitud.comida,
    "menu": lambda: TipoMenu.nombre,
}


def resumen(filtros, sector_forzado: int | None = None) -> dict:
    """
    Totales por grupo: pedidas, regulares, excepciones, autorizadas y entregadas.
    Filtros: fecha_desde, fecha_hasta, sector_id, comida, tipo_menu_id, agrupar.
    """
    agrupar = v.texto(filtros, "agrupar").lower() or "dia"
    if agrupar not in AGRUPAMIENTOS:
        raise ErrorValidacion({"agrupar": "Usá dia, semana, mes, sector, comida o menu."})
    grupo = AGRUPAMIENTOS[agrupar]().label("grupo")

    consulta = (select(
        grupo,
        func.count(Solicitud.id).label("pedidas"),
        func.count(case((Solicitud.condicion == REGULAR, 1))).label("regulares"),
        func.count(case((Solicitud.autorizada.is_(True), 1))).label("autorizadas"),
        func.count(Solicitud.entrega_id).label("entregadas"),
    ).select_from(Solicitud).join(Solicitud.pedido).join(Pedido.sector).join(Solicitud.tipo_menu))

    sector_id = sector_forzado or v.entero(filtros, "sector_id")
    if sector_id:
        consulta = consulta.where(Pedido.sector_id == sector_id)
    comida = v.texto(filtros, "comida").lower()
    menu_id = v.entero(filtros, "tipo_menu_id")
    if comida:
        consulta = consulta.where(Solicitud.comida == comida)
    if menu_id:
        consulta = consulta.where(Solicitud.tipo_menu_id == menu_id)
    # Reutiliza el filtro de fechas y estado de pedidos (sin comida/menú, ya aplicados arriba)
    consulta = filtrar_pedidos(consulta, {k: filtros.get(k) for k in ("fecha_desde", "fecha_hasta", "estado")})
    consulta = consulta.group_by(grupo).order_by(grupo)

    filas = []
    for fila in db.session.execute(consulta):
        valor = fila.grupo
        filas.append({
            "grupo": valor.isoformat() if isinstance(valor, (date, datetime)) else valor,
            "pedidas": fila.pedidas,
            "regulares": fila.regulares,
            "excepciones": fila.pedidas - fila.regulares,
            "autorizadas": fila.autorizadas,
            "entregadas": fila.entregadas,
        })
    return {"agrupar": agrupar, "filas": filas}


def resumen_pedidos(filtros, sector_forzado=None) -> dict:
    """Totales de comidas pedidas (con regulares y excepciones)."""
    datos = resumen(filtros, sector_forzado)
    campos = ("grupo", "pedidas", "regulares", "excepciones")
    datos["filas"] = [{k: f[k] for k in campos} for f in datos["filas"]]
    return datos


def resumen_autorizaciones(filtros) -> dict:
    """Pedidas vs. autorizadas, con la diferencia."""
    datos = resumen(filtros)
    datos["filas"] = [{"grupo": f["grupo"], "pedidas": f["pedidas"], "autorizadas": f["autorizadas"],
                       "diferencia": f["pedidas"] - f["autorizadas"]} for f in datos["filas"]]
    return datos


def resumen_entregas(filtros) -> dict:
    """Autorizadas vs. entregadas, con la diferencia."""
    datos = resumen(filtros)
    datos["filas"] = [{"grupo": f["grupo"], "autorizadas": f["autorizadas"], "entregadas": f["entregadas"],
                       "diferencia": f["autorizadas"] - f["entregadas"]} for f in datos["filas"]]
    return datos
