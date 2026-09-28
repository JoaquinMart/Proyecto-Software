"""Ajustes del sistema: elementos por página y modo mantenimiento."""
import logging

from src.core.database import db
from src.core.errores import ErrorValidacion
from src.core.models import Configuracion
from src.core.validators.configuracion import validar_configuracion

log = logging.getLogger("alimentacion")


def obtener_config() -> Configuracion:
    """Devuelve la fila de configuración, creándola con valores por defecto si no existe."""
    config = db.session.get(Configuracion, 1)
    if config is None:
        config = Configuracion(id=1, por_pagina=25, mantenimiento=False, mensaje_mantenimiento="")
        db.session.add(config)
        db.session.commit()
    return config


def por_pagina() -> int:
    """Cantidad de elementos por página que deben respetar todos los listados."""
    return obtener_config().por_pagina


def actualizar_config(data, usuario) -> Configuracion:
    """Valida y guarda los ajustes. Registra quién los cambió."""
    datos, errores = validar_configuracion(data)
    if errores:
        raise ErrorValidacion(errores)
    config = obtener_config()
    config.por_pagina = datos["por_pagina"]
    config.mantenimiento = datos["mantenimiento"]
    config.mensaje_mantenimiento = datos["mensaje_mantenimiento"]
    config.actualizado_por_id = usuario.id
    db.session.commit()
    log.info("Configuración actualizada por %s (mantenimiento=%s)", usuario.email, config.mantenimiento)
    return config
