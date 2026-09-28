"""
Datos iniciales. Se corre con:  flask --app main seed-db

Carga roles y permisos, catálogos (tipos de personal y de menú), los sectores del
hospital, la configuración, un usuario por rol y datos de prueba (personal y cupos).
"""
import os

from src.core.database import db
from src.core.models import (Configuracion, Cupo, Permiso, Persona, Rol, Sector, TipoMenu,
                             TipoPersonal, Usuario)

ROLES = [
    ("administrador", "Administrador"),
    ("jefe_servicio", "Jefe de Servicio"),
    ("servicio_alimentacion", "Servicio de Alimentación"),
    ("sector_comedor", "Sector Comedor"),
]

# Patrón modulo_accion. admin_access habilita la aplicación de administración (Flask/Jinja)
# y api_access habilita la API que usarán las interfaces en Vue.
PERMISOS_POR_ROL = {
    "administrador": [
        "admin_access",
        "user_index", "user_new", "user_show", "user_update", "user_destroy", "user_block",
        "sector_index", "sector_new", "sector_show", "sector_update", "sector_destroy",
        "personal_index", "personal_new", "personal_show", "personal_update", "personal_destroy",
        "personal_import",
        "config_show", "config_update",
    ],
    "jefe_servicio": [
        "api_access",
        "personal_index", "personal_show", "personal_new", "personal_update", "personal_destroy",
        "pedido_index", "pedido_show", "pedido_new", "pedido_update", "pedido_destroy",
        "cupo_index", "cupo_show",
        "resumen_pedidos",
    ],
    "servicio_alimentacion": [
        "api_access",
        "sector_index", "sector_show",
        "personal_index", "personal_show", "personal_new", "personal_update", "personal_destroy",
        "autorizacion_index", "autorizacion_show", "autorizacion_update",
        "cupo_index", "cupo_show", "cupo_new", "cupo_update", "cupo_destroy",
        "comida_autorizada_index",
        "entrega_index", "entrega_show",
        "resumen_pedidos", "resumen_autorizaciones", "resumen_entregas",
    ],
    "sector_comedor": [
        "api_access",
        "sector_index", "sector_show",
        "personal_index", "personal_show",
        "cupo_index", "cupo_show",
        "comida_autorizada_index",
        "entrega_index", "entrega_show", "entrega_new",
    ],
}

TIPOS_PERSONAL = [("fijo", "Personal Fijo"), ("residente", "Residente")]
TIPOS_MENU = [("general", "General"), ("vegetariano", "Vegetariano"), ("celiaco", "Celíaco")]

# Sectores indicados en el enunciado
SECTORES = [
    "Medicos Internos", "Medicos De Guardia (Urg)", "Quirofano", "Equipo De Guardia", "Intendencia",
    "Policia", "Mantenimiento", "Electricidad", "Conmutador", "Admision De Camas", "Prep De Materiales",
    "Laboratorio De Guardia", "Economia Y Gestion", "Hemoterapia", "Secretarias De Guardia Estadistica",
    "Rayos", "Esterilizacion", "Ssp", "Mensajeria", "Ate", "Limpieza", "Cefli", "Lavadero",
    "Salud Mental", "Quirofano Cardiovascular", "Alimentacion", "Direccion", "Deposito Central",
    "Alegria Intensiva", "Estadistica", "Neurocirugia", "Hermanas", "Residentes Jefes",
    "Niño Sano 63 Y 16", "Genetica Idip",
]

# Personal de prueba: (dni, nombre, apellido, tipo, sector o None, menú)
PERSONAL_PRUEBA = [
    ("30111222", "Ana", "Pérez", "fijo", "Equipo De Guardia", "general"),
    ("31222333", "Carlos", "Díaz", "fijo", "Equipo De Guardia", "vegetariano"),
    ("32333444", "Lucía", "Fernández", "fijo", "Equipo De Guardia", "celiaco"),
    ("33444555", "Martín", "Suárez", "fijo", "Equipo De Guardia", "general"),
    ("34555666", "Sofía", "Romero", "fijo", "Laboratorio De Guardia", "general"),
    ("40111222", "Julián", "Acosta", "residente", None, "general"),
    ("41222333", "Valentina", "Benítez", "residente", None, "vegetariano"),
]


def _usuario(email, nombre, apellido, dni, password, rol, sector=None):
    """Crea un usuario activo con la contraseña hasheada."""
    usuario = Usuario(email=email, nombre=nombre, apellido=apellido, dni=dni,
                      activo=True, rol=rol, sector=sector)
    usuario.set_password(password)
    return usuario


def run():
    """Carga todos los datos iniciales. Pensado para correr sobre una base recién creada."""
    nombres = sorted({p for permisos in PERMISOS_POR_ROL.values() for p in permisos})
    permisos = {nombre: Permiso(nombre=nombre) for nombre in nombres}
    db.session.add_all(permisos.values())

    roles = {}
    for codigo, nombre in ROLES:
        rol = Rol(codigo=codigo, nombre=nombre, permisos=[permisos[p] for p in PERMISOS_POR_ROL[codigo]])
        roles[codigo] = rol
    db.session.add_all(roles.values())

    tipos = {c: TipoPersonal(codigo=c, nombre=n) for c, n in TIPOS_PERSONAL}
    menus = {c: TipoMenu(codigo=c, nombre=n) for c, n in TIPOS_MENU}
    db.session.add_all([*tipos.values(), *menus.values()])

    sectores = {n: Sector(nombre=n, descripcion="", activo=True) for n in SECTORES}
    db.session.add_all(sectores.values())

    db.session.add(Configuracion(id=1, por_pagina=25, mantenimiento=False,
                                 mensaje_mantenimiento="El sistema está en mantenimiento. Volvé a intentar más tarde."))

    guardia = sectores["Equipo De Guardia"]
    db.session.add_all([
        _usuario(os.environ.get("ADMIN_EMAIL", "admin@hospital.local").lower(), "Admin", "Sistema",
                 "10000000", os.environ.get("ADMIN_PASSWORD", "Admin1234"), roles["administrador"]),
        _usuario("jefe.guardia@hospital.local", "Laura", "Gómez", "28555111", "Jefe12345",
                 roles["jefe_servicio"], guardia),
        _usuario("alimentacion@hospital.local", "Marta", "Ruiz", "27444222", "Alim12345",
                 roles["servicio_alimentacion"]),
        _usuario("comedor@hospital.local", "Pedro", "Sosa", "29333444", "Comedor123",
                 roles["sector_comedor"]),
    ])

    for dni, nombre, apellido, tipo, sector, menu in PERSONAL_PRUEBA:
        db.session.add(Persona(dni=dni, nombre=nombre, apellido=apellido, activo=True,
                               tipo_personal=tipos[tipo], tipo_menu=menus[menu],
                               sector=sectores[sector] if sector else None))

    # Cupos de prueba para Equipo De Guardia: 3 por comida (la 4.ª persona será excepción)
    for comida in ("desayuno", "almuerzo", "merienda", "cena"):
        db.session.add(Cupo(sector=guardia, comida=comida, cantidad=3))

    db.session.commit()
