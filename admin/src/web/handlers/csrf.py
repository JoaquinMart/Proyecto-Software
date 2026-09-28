"""
Protección CSRF mínima: cada formulario POST lleva un token guardado en la sesión.
Evita que otro sitio envíe formularios (ej: eliminar un usuario) en nombre del admin logueado.

En las plantillas:
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
"""
import secrets

from flask import abort, request, session

METODOS_PROTEGIDOS = {"POST", "PUT", "PATCH", "DELETE"}


def generar_token():
    """Devuelve (y crea si hace falta) el token CSRF de la sesión."""
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(32)
    return session["_csrf"]


def validar_token():
    """Rechaza con 400 los formularios POST sin token o con un token distinto al de la sesión."""
    if request.method not in METODOS_PROTEGIDOS:
        return
    if request.path.startswith("/api/"):  # la API usa tokens Bearer, no cookies
        return
    if request.url_rule is None:  # ruta o método inexistente: que responda 404/405
        return
    enviado = request.form.get("csrf_token", "")
    esperado = session.get("_csrf", "")
    if not enviado or not esperado or not secrets.compare_digest(enviado, esperado):
        abort(400)


def init_app(app):
    """Registra la validación y el helper csrf_token() para Jinja."""
    app.before_request(validar_token)
    app.jinja_env.globals["csrf_token"] = generar_token
