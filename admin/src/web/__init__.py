"""Creación y configuración de la aplicación Flask."""
import click
from flask import Flask, render_template, request
from flask_session import Session
from werkzeug.exceptions import HTTPException

from src.core import database, seeds
from src.web import logs
from src.web.api import bp as api_bp
from src.web.api import respuesta_error
from src.web.config import config
from src.web.controllers.auth import bp as auth_bp
from src.web.controllers.configuracion import bp as configuracion_bp
from src.web.controllers.personal import bp as personal_bp
from src.web.controllers.sectores import bp as sectores_bp
from src.web.controllers.usuarios import bp as usuarios_bp
from src.web.handlers import auth, csrf
from src.web.helpers import layout

sesiones = Session()

MENSAJES_API = {
    400: "Solicitud inválida.",
    401: "Autenticación requerida.",
    403: "No tenés permiso para esta operación.",
    404: "El recurso no existe.",
    405: "Método no permitido para esta ruta.",
    413: "El cuerpo de la solicitud es demasiado grande.",
    415: "Tipo de contenido no soportado.",
}

ERRORES = {
    400: ("Solicitud inválida", "El formulario venció o no es válido. Volvé atrás, recargá la página e intentá de nuevo."),
    403: ("Sin permiso", "Tu usuario no tiene permiso para acceder a esta sección."),
    404: ("Página no encontrada", "La dirección no existe o el registro fue eliminado."),
    405: ("Método no permitido", "La acción no está disponible desde esta dirección."),
    413: ("Archivo demasiado grande", "El archivo supera el tamaño máximo permitido."),
}


def create_app(env="development", static_folder="../../static"):
    """Arma la aplicación: configuración, extensiones, blueprints, errores y comandos."""
    app = Flask(__name__, static_folder=static_folder)
    app.config.from_object(config[env])

    logs.init_app(app)
    database.init_app(app)
    sesiones.init_app(app)
    csrf.init_app(app)      # primero: valida el token de los formularios POST
    auth.init_app(app)      # después: exige sesión en la aplicación de administración
    layout.init_app(app)

    for blueprint in (auth_bp, usuarios_bp, sectores_bp, personal_bp, configuracion_bp, api_bp):
        app.register_blueprint(blueprint)

    @app.get("/")
    def home():
        """Página de inicio de la administración."""
        return render_template("home.html")

    @app.errorhandler(HTTPException)
    def error_http(error):
        """Errores HTTP: JSON para la API, página HTML para la administración."""
        if request.path.startswith("/api/"):
            return respuesta_error(error.code, MENSAJES_API.get(error.code, error.name))
        titulo, mensaje = ERRORES.get(error.code, (error.name, error.description))
        return render_template("error.html", codigo=error.code, titulo=titulo, mensaje=mensaje), error.code

    @app.errorhandler(Exception)
    def error_inesperado(error):
        """Cualquier error no previsto: se registra en el log y se responde 500."""
        database.db.session.rollback()
        if app.debug and not request.path.startswith("/api/"):
            raise error  # en desarrollo se ve el depurador de Flask con el detalle
        app.logger.exception("Error no controlado en %s %s", request.method, request.path)
        if request.path.startswith("/api/"):
            return respuesta_error(500, "Error interno del servidor.")
        return render_template("error.html", codigo=500, titulo="Error del servidor",
                               mensaje="Ocurrió un error inesperado. Ya quedó registrado."), 500

    @app.cli.command("reset-db")
    def reset_db():
        """Borra y recrea todas las tablas."""
        database.reset()
        click.echo("Base de datos recreada.")

    @app.cli.command("seed-db")
    def seed_db():
        """Carga roles, permisos, catálogos, sectores, usuarios y datos de prueba."""
        seeds.run()
        click.echo("Datos iniciales cargados.")

    return app
