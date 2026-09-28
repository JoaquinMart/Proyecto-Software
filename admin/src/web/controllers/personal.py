"""Módulo de personal de la aplicación de administración (incluye importación CSV)."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from src.core import personal as svc
from src.core.database import db
from src.core.errores import Conflicto, ErrorNegocio, NoEncontrado
from src.core.importacion import COLUMNAS, importar_personal
from src.core.sectores import listar_sectores
from src.web.handlers.auth import permiso_requerido

bp = Blueprint("personal", __name__, url_prefix="/personal")


def _obtener(persona_id):
    """Persona por id o 404."""
    try:
        return svc.obtener_persona(persona_id)
    except NoEncontrado:
        abort(404)


def _opciones():
    """Catálogos para los selectores."""
    return {"tipos": svc.tipos_personal(), "menus": svc.tipos_menu(), "sectores": listar_sectores()}


def _datos_de(persona):
    """Valores iniciales del formulario de edición."""
    return {"dni": persona.dni, "nombre": persona.nombre, "apellido": persona.apellido,
            "tipo_personal_id": str(persona.tipo_personal_id), "tipo_menu_id": str(persona.tipo_menu_id),
            "sector_id": str(persona.sector_id or ""), "activo": "1" if persona.activo else ""}


def _form(persona, datos, errores, status=200):
    """Renderiza el formulario de alta o edición."""
    return render_template("personal/form.html", persona=persona, datos=datos, errores=errores,
                           **_opciones()), status


@bp.get("/")
@permiso_requerido("personal_index")
def index():
    """Listado con búsqueda por DNI, nombre, sector, tipo y estado."""
    page = request.args.get("page", 1, type=int)
    pagina = svc.buscar_personal(request.args, page)
    return render_template("personal/index.html", pagina=pagina, filtros=request.args, **_opciones())


@bp.get("/nuevo")
@permiso_requerido("personal_new")
def nuevo():
    """Formulario de alta."""
    return _form(None, {"activo": "1"}, {})


@bp.post("/nuevo")
@permiso_requerido("personal_new")
def crear():
    """Guarda una persona nueva."""
    try:
        persona = svc.crear_persona(request.form)
    except ErrorNegocio as e:
        db.session.rollback()
        flash("Revisá los campos marcados.", "warning")
        return _form(None, request.form, e.errores, 422)
    flash(f"{persona.nombre} {persona.apellido} registrado/a.", "success")
    return redirect(url_for("personal.show", persona_id=persona.id))


@bp.get("/<int:persona_id>")
@permiso_requerido("personal_show")
def show(persona_id):
    """Ficha de la persona."""
    persona = _obtener(persona_id)
    return render_template("personal/show.html", persona=persona, tiene_historial=svc.tiene_historial(persona))


@bp.get("/<int:persona_id>/editar")
@permiso_requerido("personal_update")
def editar(persona_id):
    """Formulario de edición."""
    persona = _obtener(persona_id)
    return _form(persona, _datos_de(persona), {})


@bp.post("/<int:persona_id>/editar")
@permiso_requerido("personal_update")
def actualizar(persona_id):
    """Guarda los cambios de la persona."""
    persona = _obtener(persona_id)
    try:
        svc.actualizar_persona(persona, request.form)
    except ErrorNegocio as e:
        db.session.rollback()
        flash("Revisá los campos marcados.", "warning")
        return _form(persona, request.form, e.errores, 422)
    flash("Cambios guardados.", "success")
    return redirect(url_for("personal.show", persona_id=persona.id))


@bp.post("/<int:persona_id>/eliminar")
@permiso_requerido("personal_destroy")
def eliminar(persona_id):
    """Elimina una persona sin historial."""
    persona = _obtener(persona_id)
    try:
        svc.eliminar_persona(persona)
    except Conflicto as e:
        flash(e.mensaje, "danger")
        return redirect(url_for("personal.show", persona_id=persona_id))
    flash("Persona eliminada.", "success")
    return redirect(url_for("personal.index"))


@bp.post("/<int:persona_id>/desactivar")
@permiso_requerido("personal_update")
def desactivar(persona_id):
    """Marca la persona como inactiva (no se puede sumar a pedidos nuevos)."""
    persona = _obtener(persona_id)
    persona.activo = False
    db.session.commit()
    flash("Persona desactivada.", "success")
    return redirect(url_for("personal.show", persona_id=persona_id))


@bp.route("/importar", methods=["GET", "POST"])
@permiso_requerido("personal_import")
def importar():
    """Importación masiva desde CSV, con informe de importados y rechazados."""
    informe = None
    if request.method == "POST":
        archivo = request.files.get("archivo")
        if archivo is None or not archivo.filename:
            flash("Elegí un archivo CSV.", "warning")
        elif not archivo.filename.lower().endswith(".csv"):
            flash("El archivo debe tener extensión .csv.", "warning")
        else:
            try:
                informe = importar_personal(archivo.read())
                nivel = "success" if informe["rechazados"] == 0 else "warning"
                flash(f"Importación terminada: {informe['importados']} importados, "
                      f"{informe['rechazados']} rechazados.", nivel)
            except ErrorNegocio as e:
                db.session.rollback()
                flash(e.mensaje, "danger")
    return render_template("personal/importar.html", informe=informe, columnas=COLUMNAS)
