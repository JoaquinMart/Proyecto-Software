"""Conexión a PostgreSQL mediante SQLAlchemy (Flask-SQLAlchemy)."""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Clase base de todos los modelos."""


db = SQLAlchemy(model_class=Base)


def init_app(app):
    """Vincula la base de datos con la aplicación Flask."""
    db.init_app(app)


def reset():
    """Borra y vuelve a crear todas las tablas. Solo para desarrollo."""
    from src.core import models  # noqa: F401  (registra los modelos en la metadata)

    db.drop_all()
    db.create_all()
