"""Registro de eventos y errores del backend (consola + archivo rotativo logs/app.log)."""
import logging
import os
from logging.handlers import RotatingFileHandler

FORMATO = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def init_app(app):
    """Configura el logger 'alimentacion' (eventos de negocio) y el de Flask (errores)."""
    nivel = logging.DEBUG if app.debug else logging.INFO
    formato = logging.Formatter(FORMATO)

    os.makedirs("logs", exist_ok=True)
    archivo = RotatingFileHandler("logs/app.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    archivo.setFormatter(formato)
    consola = logging.StreamHandler()
    consola.setFormatter(formato)

    for logger in (logging.getLogger("alimentacion"), app.logger):
        logger.setLevel(nivel)
        if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
            logger.addHandler(archivo)
        if logger.name == "alimentacion" and not any(type(h) is logging.StreamHandler for h in logger.handlers):
            logger.addHandler(consola)
        logger.propagate = False if logger.name == "alimentacion" else logger.propagate
