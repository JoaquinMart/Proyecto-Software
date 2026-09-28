"""
Importación masiva de personal desde CSV.

Formato (primera fila = encabezados, separador coma o punto y coma, UTF-8):
    dni,nombre,apellido,tipo_personal,sector,menu
    30111222,Ana,Pérez,Personal Fijo,Laboratorio De Guardia,General
    40111333,Juan,López,Residente,,Vegetariano

- tipo_personal y menu: nombre o código del catálogo (sin distinguir mayúsculas ni tildes).
- sector: nombre exacto del sector (se ignora para Residentes).
Cada fila se valida con las mismas reglas que el alta manual. Las filas válidas se importan
y las inválidas se informan con su motivo; una fila con error no frena al resto.
"""
import csv
import io
import logging
import unicodedata

from sqlalchemy import select

from src.core.database import db
from src.core.errores import ErrorNegocio
from src.core.models import Sector, TipoMenu, TipoPersonal
from src.core.personal import crear_persona

log = logging.getLogger("alimentacion")

COLUMNAS = ["dni", "nombre", "apellido", "tipo_personal", "sector", "menu"]
MAX_FILAS = 5000
MAX_BYTES = 2 * 1024 * 1024


def _clave(texto: str) -> str:
    """Normaliza para comparar: minúsculas, sin tildes, sin espacios extra."""
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.lower().split())


def _decodificar(contenido: bytes) -> str:
    """Decodifica UTF-8 (con o sin BOM) y, si falla, Latin-1 (típico de Excel en Windows)."""
    try:
        return contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        return contenido.decode("latin-1")


def importar_personal(contenido: bytes) -> dict:
    """
    Procesa el CSV y devuelve el informe:
    {"procesados": n, "importados": n, "rechazados": n, "errores": [{"fila": n, "dni": "...", "motivo": "..."}]}
    """
    if len(contenido) > MAX_BYTES:
        raise ErrorNegocio("El archivo supera los 2 MB.")
    texto = _decodificar(contenido)
    if not texto.strip():
        raise ErrorNegocio("El archivo está vacío.")

    try:
        dialecto = csv.Sniffer().sniff(texto.splitlines()[0], delimiters=",;")
    except csv.Error:
        dialecto = csv.excel
    lector = csv.DictReader(io.StringIO(texto), dialect=dialecto)
    encabezados = [_clave(c) for c in (lector.fieldnames or [])]
    faltantes = [c for c in COLUMNAS if c not in encabezados]
    if faltantes:
        raise ErrorNegocio(f"Faltan columnas en el encabezado: {', '.join(faltantes)}. "
                           f"Se esperan: {', '.join(COLUMNAS)}.")

    tipos = {}
    for t in db.session.scalars(select(TipoPersonal)):
        tipos[_clave(t.nombre)] = t.id
        tipos[_clave(t.codigo)] = t.id
    menus = {}
    for m in db.session.scalars(select(TipoMenu)):
        menus[_clave(m.nombre)] = m.id
        menus[_clave(m.codigo)] = m.id
    sectores = {_clave(s.nombre): s.id for s in db.session.scalars(select(Sector))}

    informe = {"procesados": 0, "importados": 0, "rechazados": 0, "errores": []}
    dnis_en_archivo = set()

    for numero, fila in enumerate(lector, start=2):  # la fila 1 es el encabezado
        if informe["procesados"] >= MAX_FILAS:
            raise ErrorNegocio(f"El archivo supera las {MAX_FILAS} filas.")
        fila = {_clave(k): (val or "").strip() for k, val in fila.items() if k is not None}
        if not any(fila.values()):
            continue  # fila vacía
        informe["procesados"] += 1
        dni = fila.get("dni", "").replace(".", "")

        motivo = None
        if dni and dni in dnis_en_archivo:
            motivo = "DNI repetido dentro del archivo."
        elif fila.get("tipo_personal") and _clave(fila["tipo_personal"]) not in tipos:
            motivo = f"Tipo de personal inexistente: '{fila['tipo_personal']}'."
        elif fila.get("menu") and _clave(fila["menu"]) not in menus:
            motivo = f"Tipo de menú inexistente: '{fila['menu']}'."
        elif fila.get("sector") and _clave(fila["sector"]) not in sectores:
            motivo = f"Sector inexistente: '{fila['sector']}'."

        if motivo is None:
            data = {
                "dni": dni, "nombre": fila.get("nombre"), "apellido": fila.get("apellido"),
                "tipo_personal_id": tipos.get(_clave(fila.get("tipo_personal", ""))),
                "tipo_menu_id": menus.get(_clave(fila.get("menu", ""))),
                "sector_id": sectores.get(_clave(fila.get("sector", ""))),
                "activo": True,
            }
            try:
                with db.session.begin_nested():  # si falla, se deshace solo esta fila
                    crear_persona(data, commit=False)
            except ErrorNegocio as e:
                motivo = " ".join(e.errores.values()) if e.errores else e.mensaje

        if motivo:
            informe["rechazados"] += 1
            informe["errores"].append({"fila": numero, "dni": dni, "motivo": motivo})
        else:
            informe["importados"] += 1
            dnis_en_archivo.add(dni)

    db.session.commit()
    log.info("Importación CSV: %s procesados, %s importados, %s rechazados",
             informe["procesados"], informe["importados"], informe["rechazados"])
    return informe
