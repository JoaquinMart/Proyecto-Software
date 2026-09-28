"""
Reglas de negocio de usuarios. Los controllers solo llaman a estas funciones;
las validaciones de datos están en src/core/validators/usuarios.py.
"""
import logging

from sqlalchemy import delete, exists, func, or_, select
from sqlalchemy.orm import selectinload

from src.core.configuracion import por_pagina
from src.core.database import db
from src.core.errores import Conflicto, ErrorValidacion
from src.core.models import ApiToken, Entrega, Pedido, Solicitud, Usuario
from src.core.validators import comunes as v
from src.core.validators.usuarios import ROL_ADMIN, ROL_JEFE, validar_usuario

log = logging.getLogger("alimentacion")

__all__ = ["ROL_ADMIN", "ROL_JEFE"]

ORDENES = {
    "creacion": lambda: [Usuario.created_at],
    "apellido": lambda: [Usuario.apellido, Usuario.nombre],
    "email": lambda: [Usuario.email],
}


def crear_usuario(data) -> Usuario:
    """Crea un usuario validado, con la contraseña hasheada."""
    d, errores = validar_usuario(data)
    if errores:
        raise ErrorValidacion(errores)
    usuario = Usuario(
        email=d["email"], nombre=d["nombre"], apellido=d["apellido"], dni=d["dni"],
        activo=d["activo"], rol=d["rol"], sector=d["sector"],
    )
    usuario.set_password(d["password"])
    db.session.add(usuario)
    db.session.commit()
    log.info("Usuario creado: %s (rol %s)", usuario.email, usuario.rol.codigo)
    return usuario


def actualizar_usuario(usuario: Usuario, data, actor: Usuario) -> Usuario:
    """Actualiza un usuario. Contraseña vacía = se conserva la actual."""
    d, errores = validar_usuario(data, usuario)
    if not errores and usuario.id == actor.id and d["rol"].codigo != ROL_ADMIN:
        errores["rol_id"] = "No podés quitarte tu propio rol de Administrador."
    if errores:
        raise ErrorValidacion(errores)

    usuario.email = d["email"]
    usuario.nombre = d["nombre"]
    usuario.apellido = d["apellido"]
    usuario.dni = d["dni"]
    usuario.activo = d["activo"]
    usuario.rol = d["rol"]
    usuario.sector = d["sector"]
    if d["password"]:
        usuario.set_password(d["password"])
    db.session.commit()
    log.info("Usuario actualizado: %s por %s", usuario.email, actor.email)
    return usuario


def tiene_operaciones(usuario: Usuario) -> bool:
    """True si el usuario creó, modificó o revisó pedidos, autorizó solicitudes o registró entregas."""
    uid = usuario.id
    return bool(db.session.scalar(select(
        exists().where(or_(Pedido.creado_por_id == uid, Pedido.modificado_por_id == uid,
                           Pedido.revisado_por_id == uid))
        | exists().where(Solicitud.autorizada_por_id == uid)
        | exists().where(Entrega.usuario_id == uid)
    )))


def eliminar_usuario(usuario: Usuario, actor: Usuario) -> None:
    """Elimina un usuario sin operaciones. Si tiene historial, hay que bloquearlo."""
    if usuario.id == actor.id:
        raise Conflicto("No podés eliminar tu propio usuario.")
    if tiene_operaciones(usuario):
        raise Conflicto("El usuario tiene operaciones registradas y no se puede eliminar. Bloquealo en su lugar.")
    db.session.execute(delete(ApiToken).where(ApiToken.usuario_id == usuario.id))
    email = usuario.email
    db.session.delete(usuario)
    db.session.commit()
    log.info("Usuario eliminado: %s por %s", email, actor.email)


def bloquear_usuario(usuario: Usuario) -> None:
    """Bloquea un usuario (no puede iniciar sesión). Los administradores no se bloquean."""
    if usuario.rol.codigo == ROL_ADMIN:
        raise Conflicto("Los usuarios administradores no se pueden bloquear.")
    usuario.activo = False
    db.session.commit()
    log.info("Usuario bloqueado: %s", usuario.email)


def desbloquear_usuario(usuario: Usuario) -> None:
    """Vuelve a habilitar el acceso de un usuario."""
    usuario.activo = True
    db.session.commit()
    log.info("Usuario desbloqueado: %s", usuario.email)


def listar_jefes():
    """Usuarios con rol Jefe de Servicio, para los selectores."""
    from src.core.models import Rol
    return db.session.scalars(
        select(Usuario).join(Usuario.rol).where(Rol.codigo == ROL_JEFE).order_by(Usuario.apellido, Usuario.nombre)
    ).all()


def buscar_usuarios(filtros, page: int = 1):
    """Filtros combinables + orden + paginación en el servidor."""
    consulta = select(Usuario).options(selectinload(Usuario.rol), selectinload(Usuario.sector))

    email = v.texto(filtros, "email")
    if email:
        consulta = consulta.where(Usuario.email.ilike(v.like(email.lower()), escape="\\"))

    nombre = v.texto(filtros, "nombre")
    if nombre:
        patron = v.like(nombre)
        consulta = consulta.where(or_(
            func.concat(Usuario.nombre, " ", Usuario.apellido).ilike(patron, escape="\\"),
            func.concat(Usuario.apellido, " ", Usuario.nombre).ilike(patron, escape="\\"),
        ))

    dni = v.dni(v.texto(filtros, "dni"))
    if dni:
        consulta = consulta.where(Usuario.dni.like(v.like(dni), escape="\\"))

    activo = filtros.get("activo")
    if activo in ("si", "no"):
        consulta = consulta.where(Usuario.activo.is_(activo == "si"))

    rol_id = v.entero(filtros, "rol_id")
    if rol_id:
        consulta = consulta.where(Usuario.rol_id == rol_id)

    sector_id = v.entero(filtros, "sector_id")
    if sector_id:
        consulta = consulta.where(Usuario.sector_id == sector_id)

    columnas = ORDENES.get(filtros.get("orden"), ORDENES["creacion"])()
    descendente = filtros.get("dir", "desc") != "asc"
    consulta = consulta.order_by(*[c.desc() if descendente else c.asc() for c in columnas], Usuario.id)

    return db.paginate(consulta, page=max(page, 1), per_page=por_pagina(), error_out=False)
