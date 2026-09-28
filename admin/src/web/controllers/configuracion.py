"""Ajustes del sistema (solo Administrador)."""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from src.core.configuracion import actualizar_config, obtener_config
from src.core.database import db
from src.core.errores import ErrorValidacion
from src.web.handlers.auth import permiso_requerido, usuario_actual

bp = Blueprint("configuracion", __name__, url_prefix="/configuracion")


@bp.get("/")
@permiso_requerido("config_show")
def index():
    """Formulario de ajustes."""
    config = obtener_config()
    datos = {"por_pagina": config.por_pagina, "mantenimiento": "1" if config.mantenimiento else "",
             "mensaje_mantenimiento": config.mensaje_mantenimiento}
    return render_template("configuracion/form.html", datos=datos, errores={}, config=config)


@bp.post("/")
@permiso_requerido("config_update")
def actualizar():
    """Guarda los ajustes."""
    try:
        actualizar_config(request.form, usuario_actual())
    except ErrorValidacion as e:
        db.session.rollback()
        flash("Revisá los campos marcados.", "warning")
        return render_template("configuracion/form.html", datos=request.form, errores=e.errores,
                               config=obtener_config()), 422
    flash("Ajustes guardados.", "success")
    return redirect(url_for("configuracion.index"))
