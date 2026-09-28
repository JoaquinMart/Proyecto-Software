"""
Autenticación y autorización de la aplicación de administración, hechas a mano (sin flask-login).

- usuario_actual(): lee session["user_id"] y trae el usuario de la base.
- requerir_login(): before_request global. Toda la aplicación de administración exige sesión,
  salvo el login y los archivos estáticos. La API tiene su propia autenticación por token.
- @permiso_requerido("user_new"): protege cada vista según el permiso.
"""
from functools import wraps

from flask import abort, g, redirect, request, session, url_for

from src.core.database import db
from src.core.models import Usuario

RUTAS_PUBLICAS = {"auth.login", "auth.login_post", "static"}
PERMISO_ADMIN = "admin_access"


def usuario_actual():
    """Usuario logueado en la aplicación de administración, o None."""
    if "usuario" not in g:
        usuario = None
        user_id = session.get("user_id")
        if user_id:
            usuario = db.session.get(Usuario, user_id)
            # Si lo bloquearon, lo borraron o le quitaron el acceso con la sesión abierta, se corta ahí.
            if usuario is None or not usuario.activo or not usuario.tiene_permiso(PERMISO_ADMIN):
                session.clear()
                usuario = None
        g.usuario = usuario
    return g.usuario


def requerir_login():
    """Redirige al login cualquier request de la aplicación de administración sin sesión."""
    if request.endpoint is None or request.endpoint in RUTAS_PUBLICAS or request.path.startswith("/api/"):
        return None
    if usuario_actual() is None:
        siguiente = request.full_path.rstrip("?") if request.method == "GET" else None
        return redirect(url_for("auth.login", next=siguiente))
    return None


def permiso_requerido(*permisos):
    """Decorador: exige que el usuario logueado tenga todos los permisos indicados (si no, 403)."""
    def decorador(vista):
        """Envuelve la vista con el control de acceso."""
        @wraps(vista)
        def envoltura(*args, **kwargs):
            """Verifica credenciales y permisos antes de ejecutar la vista."""
            usuario = usuario_actual()
            if usuario is None:
                return redirect(url_for("auth.login"))
            if not all(usuario.tiene_permiso(p) for p in permisos):
                abort(403)
            return vista(*args, **kwargs)
        return envoltura
    return decorador


def tiene_permiso(nombre):
    """Para las plantillas: {% if tiene_permiso('user_new') %}...{% endif %}"""
    usuario = usuario_actual()
    return usuario is not None and usuario.tiene_permiso(nombre)


def init_app(app):
    """Registra el control de sesión y el helper de permisos para Jinja."""
    app.before_request(requerir_login)
    app.jinja_env.globals["tiene_permiso"] = tiene_permiso
