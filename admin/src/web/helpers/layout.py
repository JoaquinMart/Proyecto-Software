"""Datos comunes que necesita layout.html en TODAS las vistas de administración."""
from flask import current_app, request

from src.core.configuracion import obtener_config
from src.web.handlers.auth import usuario_actual

# Cada ítem se muestra solo si su blueprint existe Y el usuario tiene el permiso.
MENU = [
    {"label": "Usuarios",             "endpoint": "usuarios.index",      "blueprint": "usuarios",      "permiso": "user_index",     "icon": "users"},
    {"label": "Sectores y servicios", "endpoint": "sectores.index",      "blueprint": "sectores",      "permiso": "sector_index",   "icon": "building"},
    {"label": "Personal",             "endpoint": "personal.index",      "blueprint": "personal",      "permiso": "personal_index", "icon": "id"},
    {"label": "Ajustes del sistema",  "endpoint": "configuracion.index", "blueprint": "configuracion", "permiso": "config_show",    "icon": "sliders"},
]


def endpoint_existe(nombre):
    """True si hay una vista registrada con ese endpoint."""
    return nombre in current_app.view_functions


def init_app(app):
    """Registra el context processor del layout."""
    @app.context_processor
    def inject_layout():
        """Menú visible, sección activa, usuario y estado de mantenimiento."""
        usuario = usuario_actual()
        visibles = [m for m in MENU if endpoint_existe(m["endpoint"])
                    and usuario is not None and usuario.tiene_permiso(m["permiso"])]
        mantenimiento = False
        if usuario is not None and request.blueprint != "api":
            mantenimiento = obtener_config().mantenimiento
        return {
            "menu_items": visibles,
            "blueprint_activo": request.blueprint,
            "usuario_actual": usuario,
            "endpoint_existe": endpoint_existe,
            "sitio_en_mantenimiento": mantenimiento,
        }
