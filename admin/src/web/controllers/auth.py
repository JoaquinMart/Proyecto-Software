"""Login, logout y perfil de la aplicación de administración."""
import logging

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from sqlalchemy import func, select

from src.core.database import db
from src.core.models import Usuario
from src.web.handlers.auth import PERMISO_ADMIN, usuario_actual

bp = Blueprint("auth", __name__)
log = logging.getLogger("alimentacion")


def _destino_seguro(url):
    """Solo se permite volver a rutas internas (evita redirecciones a otros sitios)."""
    if url and url.startswith("/") and not url.startswith("//"):
        return url
    return url_for("home")


@bp.get("/login")
def login():
    """Formulario de inicio de sesión."""
    if usuario_actual() is not None:
        return redirect(url_for("home"))
    return render_template("auth/login.html", email="")


@bp.post("/login")
def login_post():
    """Valida las credenciales contra la base y crea la sesión."""
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    usuario = db.session.scalar(select(Usuario).where(func.lower(Usuario.email) == email)) if email else None

    # Mismo mensaje si no existe el correo o si la contraseña está mal.
    if usuario is None or not usuario.check_password(password):
        log.warning("Login fallido para %s desde %s", email or "(vacío)", request.remote_addr)
        flash("Correo o contraseña incorrectos.", "danger")
        return render_template("auth/login.html", email=email), 401

    if not usuario.activo:
        log.warning("Login de usuario bloqueado: %s", email)
        flash("Tu cuenta está bloqueada. Contactá a un administrador.", "danger")
        return render_template("auth/login.html", email=email), 403

    if not usuario.tiene_permiso(PERMISO_ADMIN):
        flash("Tu usuario no tiene acceso a la aplicación de administración.", "danger")
        return render_template("auth/login.html", email=email), 403

    session.clear()  # sesión nueva al loguearse (evita fijación de sesión)
    session["user_id"] = usuario.id
    session.permanent = True  # aplica PERMANENT_SESSION_LIFETIME
    log.info("Login: %s", usuario.email)
    flash(f"Hola, {usuario.nombre}.", "success")
    return redirect(_destino_seguro(request.args.get("next")))


@bp.post("/logout")
def logout():
    """Cierra la sesión."""
    usuario = usuario_actual()
    if usuario is not None:
        log.info("Logout: %s", usuario.email)
    session.clear()
    flash("Cerraste la sesión.", "info")
    return redirect(url_for("auth.login"))


@bp.get("/perfil")
def perfil():
    """Datos del usuario logueado."""
    return render_template("auth/perfil.html", usuario=usuario_actual())
