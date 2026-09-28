"""Módulo de usuarios de la aplicación de administración."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy import select

from src.core import usuarios as svc
from src.core.database import db
from src.core.errores import Conflicto, ErrorValidacion
from src.core.models import Rol, Usuario
from src.core.sectores import listar_sectores
from src.core.validators.usuarios import ROL_ADMIN, ROL_JEFE
from src.web.handlers.auth import permiso_requerido, usuario_actual

bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")


def _opciones():
    """Roles y sectores para los selectores."""
    return {
        "roles": db.session.scalars(select(Rol).order_by(Rol.id)).all(),
        "sectores": listar_sectores(),
        "ROL_JEFE": ROL_JEFE,
        "ROL_ADMIN": ROL_ADMIN,
    }


def _obtener(usuario_id):
    """Usuario por id o 404."""
    usuario = db.session.get(Usuario, usuario_id)
    if usuario is None:
        abort(404)
    return usuario


def _datos_de(usuario):
    """Valores iniciales del formulario de edición. La contraseña nunca se precarga."""
    return {
        "email": usuario.email, "nombre": usuario.nombre, "apellido": usuario.apellido,
        "dni": usuario.dni, "rol_id": str(usuario.rol_id),
        "sector_id": str(usuario.sector_id or ""), "activo": "1" if usuario.activo else "",
    }


# ------------------------------------------------------------------ listado
@bp.get("/")
@permiso_requerido("user_index")
def index():
    """Listado con filtros, orden y paginación."""
    page = request.args.get("page", 1, type=int)
    pagina = svc.buscar_usuarios(request.args, page)
    return render_template("usuarios/index.html", pagina=pagina, filtros=request.args, **_opciones())


# --------------------------------------------------------------------- alta
@bp.get("/nuevo")
@permiso_requerido("user_new")
def nuevo():
    """Formulario de alta."""
    return render_template("usuarios/form.html", usuario=None, datos={"activo": "1"}, errores={}, **_opciones())


@bp.post("/nuevo")
@permiso_requerido("user_new")
def crear():
    """Guarda un usuario nuevo."""
    try:
        usuario = svc.crear_usuario(request.form)
    except ErrorValidacion as e:
        flash("Revisá los campos marcados.", "warning")
        return render_template(
            "usuarios/form.html", usuario=None, datos=request.form, errores=e.errores, **_opciones()
        ), 422
    flash(f"Usuario {usuario.email} creado.", "success")
    return redirect(url_for("usuarios.show", usuario_id=usuario.id))


# ------------------------------------------------------------------ detalle
@bp.get("/<int:usuario_id>")
@permiso_requerido("user_show")
def show(usuario_id):
    """Detalle de un usuario."""
    return render_template("usuarios/show.html", usuario=_obtener(usuario_id), ROL_ADMIN=ROL_ADMIN)


# ------------------------------------------------------------------- edición
@bp.get("/<int:usuario_id>/editar")
@permiso_requerido("user_update")
def editar(usuario_id):
    """Formulario de edición."""
    usuario = _obtener(usuario_id)
    return render_template(
        "usuarios/form.html", usuario=usuario, datos=_datos_de(usuario), errores={}, **_opciones()
    )


@bp.post("/<int:usuario_id>/editar")
@permiso_requerido("user_update")
def actualizar(usuario_id):
    """Guarda los cambios."""
    usuario = _obtener(usuario_id)
    try:
        svc.actualizar_usuario(usuario, request.form, actor=usuario_actual())
    except ErrorValidacion as e:
        db.session.rollback()
        flash("Revisá los campos marcados.", "warning")
        return render_template(
            "usuarios/form.html", usuario=usuario, datos=request.form, errores=e.errores, **_opciones()
        ), 422
    flash("Cambios guardados.", "success")
    return redirect(url_for("usuarios.show", usuario_id=usuario.id))


# --------------------------------------------------------------------- baja
@bp.post("/<int:usuario_id>/eliminar")
@permiso_requerido("user_destroy")
def eliminar(usuario_id):
    """Elimina un usuario sin operaciones."""
    usuario = _obtener(usuario_id)
    email = usuario.email
    try:
        svc.eliminar_usuario(usuario, actor=usuario_actual())
    except Conflicto as e:
        flash(str(e), "danger")
        return redirect(url_for("usuarios.show", usuario_id=usuario_id))
    flash(f"Usuario {email} eliminado.", "success")
    return redirect(url_for("usuarios.index"))


# ------------------------------------------------------------------ bloqueo
@bp.post("/<int:usuario_id>/bloquear")
@permiso_requerido("user_block")
def bloquear(usuario_id):
    """Bloquea un usuario."""
    usuario = _obtener(usuario_id)
    try:
        svc.bloquear_usuario(usuario)
        flash(f"{usuario.email} bloqueado. Ya no puede iniciar sesión.", "success")
    except Conflicto as e:
        flash(str(e), "danger")
    return redirect(url_for("usuarios.show", usuario_id=usuario_id))


@bp.post("/<int:usuario_id>/desbloquear")
@permiso_requerido("user_block")
def desbloquear(usuario_id):
    """Desbloquea un usuario."""
    usuario = _obtener(usuario_id)
    svc.desbloquear_usuario(usuario)
    flash(f"{usuario.email} desbloqueado.", "success")
    return redirect(url_for("usuarios.show", usuario_id=usuario_id))
