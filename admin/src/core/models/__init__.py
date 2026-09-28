"""Modelos de la aplicación. Importarlos acá los registra en la metadata de SQLAlchemy."""
from src.core.models.auth import ApiToken, Permiso, Rol, Usuario, rol_permiso
from src.core.models.catalogos import TipoMenu, TipoPersonal
from src.core.models.configuracion import Configuracion
from src.core.models.pedidos import COMIDAS, Cupo, Entrega, Pedido, Solicitud
from src.core.models.personal import Persona
from src.core.models.sectores import Sector

__all__ = [
    "ApiToken", "Permiso", "Rol", "Usuario", "rol_permiso", "TipoMenu", "TipoPersonal",
    "Configuracion", "COMIDAS", "Cupo", "Entrega", "Pedido", "Solicitud", "Persona", "Sector",
]
