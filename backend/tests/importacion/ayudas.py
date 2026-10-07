"""Ayudas de las pruebas de `importacion`: arman tablas y cuentan lo que hay en la base."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modulos.auditoria.models import Auditoria
from app.modulos.catalogo.models import Articulo, Categoria, Codigo, Pieza
from app.modulos.movimientos.models import Existencia, Movimiento, SerieFolio, Vale

IMPORTACION = "/api/importacion"
VISTA_PREVIA = "/api/importacion/vista-previa"
ARCHIVO = "/api/importacion/archivo"

# El orden de las columnas de las tablas de prueba.
COLUMNAS = {
    "codigo": 0,
    "nombre": 1,
    "marca": 2,
    "categoria": 3,
    "cantidad": 4,
    "almacen": 5,
    "serie": 6,
    "costo": 7,
    "codigo_pieza": 8,
    "unidad": 9,
}

MANUAL = "Herramienta manual"  # por cantidad
ELECTRICA = "Herramienta eléctrica"  # por pieza
ALTURAS = "Equipo de alturas"  # por pieza, pide inspección


def unico(prefijo: str) -> str:
    return f"{prefijo}-{uuid.uuid4().hex[:8].upper()}"


def fila(
    codigo: str,
    nombre: str = "Artículo de prueba",
    marca: str = "Marca",
    categoria: str = MANUAL,
    cantidad: str | int = "",
    almacen: str = "KEP",
    serie: str = "",
    costo: str | int | float = "",
    codigo_pieza: str = "",
    unidad: str = "",
) -> list:
    return [
        codigo,
        nombre,
        marca,
        categoria,
        cantidad,
        almacen,
        serie,
        costo,
        codigo_pieza,
        unidad,
    ]


def cuerpo(filas: list[list], **extra) -> dict:
    return {"filas": filas, "columnas": COLUMNAS, **extra}


def confirmacion(filas: list[list], **extra) -> dict:
    return cuerpo(filas, id_lote=str(uuid.uuid4()), **extra)


def categoria_id(session: Session, nombre: str) -> str:
    return str(session.scalar(select(Categoria.id).where(Categoria.nombre == nombre)))


def conteos(session: Session) -> dict[str, int]:
    """Cuanto hay de cada cosa que la importacion puede escribir."""
    tablas = {
        "articulos": Articulo,
        "piezas": Pieza,
        "codigos": Codigo,
        "vales": Vale,
        "movimientos": Movimiento,
        "existencias": Existencia,
        "auditoria": Auditoria,
    }
    salida = {n: session.scalar(select(func.count()).select_from(m)) for n, m in tablas.items()}
    salida["suma_existencias"] = session.scalar(select(func.sum(Existencia.cantidad))) or 0
    salida["folios"] = session.scalar(select(func.sum(SerieFolio.ultimo))) or 0
    return salida


def articulo(session: Session, codigo: str) -> Articulo | None:
    return session.scalar(select(Articulo).where(Articulo.codigo == codigo))


def numero_de_folio(folio: str) -> int:
    return int(folio.rsplit("-", 1)[1])
