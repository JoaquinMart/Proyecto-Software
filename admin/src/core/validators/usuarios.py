"""Validación de los datos de un usuario. Devuelve (datos_limpios, errores)."""
from sqlalchemy import func, select

from src.core.database import db
from src.core.models import Rol, Sector, Usuario
from src.core.validators import comunes as v

ROL_ADMIN = "administrador"
ROL_JEFE = "jefe_servicio"
MIN_PASSWORD = 8


def validar_usuario(data, usuario: Usuario | None = None):
    """
    Valida el formulario de alta (usuario=None) o edición de un usuario.
    Devuelve (datos, errores); si errores no está vacío, los datos no deben usarse.
    """
    errores = {}
    es_alta = usuario is None

    email = v.texto(data, "email").lower()
    nombre = v.texto(data, "nombre")
    apellido = v.texto(data, "apellido")
    dni = v.dni(v.texto(data, "dni"))
    password = data.get("password") or ""
    confirmacion = data.get("password_confirmacion") or ""

    if not email:
        errores["email"] = "Ingresá el correo electrónico."
    elif len(email) > 120 or not v.EMAIL_RE.match(email):
        errores["email"] = "El correo no tiene un formato válido."
    else:
        consulta = select(Usuario.id).where(func.lower(Usuario.email) == email)
        if not es_alta:
            consulta = consulta.where(Usuario.id != usuario.id)
        if db.session.scalar(consulta):
            errores["email"] = "Ya existe un usuario con ese correo."

    v.validar_nombre(errores, "nombre", nombre, "el nombre")
    v.validar_nombre(errores, "apellido", apellido, "el apellido")
    v.validar_dni(errores, "dni", dni)

    if es_alta and not password:
        errores["password"] = "Ingresá una contraseña."
    elif password:
        if len(password) < MIN_PASSWORD:
            errores["password"] = f"La contraseña debe tener al menos {MIN_PASSWORD} caracteres."
        elif len(password) > 128:
            errores["password"] = "La contraseña no puede superar los 128 caracteres."
        elif password != confirmacion:
            errores["password_confirmacion"] = "Las contraseñas no coinciden."

    rol_id = v.entero(data, "rol_id")
    rol = db.session.get(Rol, rol_id) if rol_id else None
    if rol is None:
        errores["rol_id"] = "Elegí un rol."

    # Sector solo para Jefe de Servicio. Para otro rol queda en None: eso también cubre
    # "si se modifica el rol de un Jefe, se elimina su asociación con el sector".
    sector = None
    if rol is not None and rol.codigo == ROL_JEFE:
        sector_id = v.entero(data, "sector_id")
        sector = db.session.get(Sector, sector_id) if sector_id else None
        if sector is None:
            errores["sector_id"] = "Elegí el sector del Jefe de Servicio."
        elif not sector.activo and (es_alta or usuario.sector_id != sector.id):
            errores["sector_id"] = "No se puede asignar un sector inactivo."

    activo = v.booleano(data, "activo")
    if rol is not None and rol.codigo == ROL_ADMIN:
        activo = True  # los administradores no se pueden bloquear

    datos = {
        "email": email, "nombre": nombre, "apellido": apellido, "dni": dni,
        "password": password, "rol": rol, "sector": sector, "activo": activo,
    }
    return datos, errores
