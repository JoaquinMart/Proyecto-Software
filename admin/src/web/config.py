"""Configuración de la aplicación por entorno. Los secretos se leen del archivo .env."""
import os
from datetime import timedelta

from cachelib.file import FileSystemCache


class Config:
    """Configuración común."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "cambiar-esta-clave-en-el-.env")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/alimentacion"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 3 * 1024 * 1024  # tope de subida (CSV de personal)
    JSON_SORT_KEYS = False

    # --- Flask-Session: la sesión se guarda en el servidor, la cookie solo lleva el id ---
    SESSION_TYPE = "cachelib"
    SESSION_CACHELIB = FileSystemCache(cache_dir="flask_session", threshold=500)
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)  # expiración de la cookie

    # --- Cookie de sesión segura ---
    SESSION_COOKIE_NAME = "alimentacion_admin"
    SESSION_COOKIE_HTTPONLY = True     # JavaScript no puede leerla
    SESSION_COOKIE_SAMESITE = "Lax"    # no se envía en requests de otros sitios
    SESSION_COOKIE_SECURE = False      # en producción va True (solo HTTPS)


class DevelopmentConfig(Config):
    """Desarrollo local."""

    DEBUG = True


class ProductionConfig(Config):
    """Servidor de la cátedra (HTTPS)."""

    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    """Tests."""

    TESTING = True


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "test": TestingConfig,
}
