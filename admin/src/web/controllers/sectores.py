"""Módulo de sectores de la aplicación de administración."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from src.core import sectores as svc
from src.core.database import db
from src.core.errores import Conflicto, ErrorValidacion, NoEncontrado
from src.core.usuarios import listar_jefes
from src.web.handlers.auth import permiso_requerido

bp = Blueprint("sectores", __name__, url_prefix="/sectores")


def _obtener(sector_id):
    """Sector por id o 404."""
    try:
        return svc.obtener_sector(sector_id)
    except NoEncontrado:
        abort(404)


def _datos_de(sector):
    """Valores iniciales del formulario de edición."""
    return {"nombre": sector.nombre, "descripcion": sector.descripcion,
            "activo": "1" if sector.activo else "", "jefes": [str(j.id) for j in sector.jefes]}


def _form(sector, datos, errores, status=200):
    """Renderiza el formulario de alta o edición."""
    seleccionados = datos.getlist("jefes") if hasattr(datos, "getlist") else datos.get("jefes", [])
    return render_template("sectores/form.html", sector=sector, datos=datos, errores=errores,
                           jefes=listar_jefes(), seleccionados=seleccionados), status


@bp.get("/")
@permiso_requerido("sector_index")
def index():
    """Listado con búsqueda por nombre, estado y Jefe, orden y paginación."""
    page = request.args.get("page", 1, type=int)
    pagina = svc.buscar_sectores(request.args, page)
    return render_template("sectores/index.html", pagina=pagina, filtros=request.args, jefes=listar_jefes())


@bp.get("/nuevo")
@permiso_requerido("sector_new")
def nuevo():
    """Formulario de alta."""
    return _form(None, {"activo": "1"}, {})


@bp.post("/nuevo")
@permiso_requerido("sector_new")
def crear():
    """Guarda un sector nuevo."""
    try:
        sector = svc.crear_sector(request.form)
    except ErrorValidacion as e:
        db.session.rollback()
        flash("Revisá los campos marcados.", "warning")
        return _form(None, request.form, e.errores, 422)
    flash(f"Sector {sector.nombre} creado.", "success")
    return redirect(url_for("sectores.show", sector_id=sector.id))


@bp.get("/<int:sector_id>")
@permiso_requerido("sector_show")
def show(sector_id):
    """Detalle del sector con sus Jefes de Servicio."""
    sector = _obtener(sector_id)
    return render_template("sectores/show.html", sector=sector, cantidad_personal=svc.contar_personal(sector))


@bp.get("/<int:sector_id>/editar")
@permiso_requerido("sector_update")
def editar(sector_id):
    """Formulario de edición."""
    sector = _obtener(sector_id)
    return _form(sector, _datos_de(sector), {})


@bp.post("/<int:sector_id>/editar")
@permiso_requerido("sector_update")
def actualizar(sector_id):
    """Guarda los cambios del sector."""
    sector = _obtener(sector_id)
    try:
        svc.actualizar_sector(sector, request.form)
    except ErrorValidacion as e:
        db.session.rollback()
        flash("Revisá los campos marcados.", "warning")
        return _form(sector, request.form, e.errores, 422)
    flash("Cambios guardados.", "success")
    return redirect(url_for("sectores.show", sector_id=sector.id))


@bp.post("/<int:sector_id>/desactivar")
@permiso_requerido("sector_update")
def desactivar(sector_id):
    """Desactiva el sector si no tiene usuarios activos."""
    sector = _obtener(sector_id)
    try:
        svc.desactivar_sector(sector)
        flash(f"Sector {sector.nombre} desactivado.", "success")
    except Conflicto as e:
        flash(e.mensaje, "danger")
    return redirect(url_for("sectores.show", sector_id=sector_id))


@bp.post("/<int:sector_id>/eliminar")
@permiso_requerido("sector_destroy")
def eliminar(sector_id):
    """Elimina un sector sin personal, usuarios ni pedidos."""
    sector = _obtener(sector_id)
    nombre = sector.nombre
    try:
        svc.eliminar_sector(sector)
    except Conflicto as e:
        flash(e.mensaje, "danger")
        return redirect(url_for("sectores.show", sector_id=sector_id))
    flash(f"Sector {nombre} eliminado.", "success")
    return redirect(url_for("sectores.index"))
