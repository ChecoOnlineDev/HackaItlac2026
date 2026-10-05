"""Persistencia: consultas de solo lectura; nunca commit.

El modulo `importacion` no escribe tablas propias: los articulos los crea `catalogo` y los vales
`movimientos`. Aqui solo se leen los datos que la vista previa necesita, en bloques para no hacer
una consulta por fila.
"""

import uuid
from collections.abc import Iterable, Iterator

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modulos.almacenes.models import Almacen
from app.modulos.catalogo.models import Articulo, Categoria, Codigo, Pieza
from app.modulos.importacion.lectura import clave
from app.modulos.movimientos.models import Movimiento, Vale

BLOQUE = 500


def _en_bloques(valores: Iterable, tamano: int = BLOQUE) -> Iterator[list]:
    bloque: list = []
    for v in valores:
        bloque.append(v)
        if len(bloque) >= tamano:
            yield bloque
            bloque = []
    if bloque:
        yield bloque


class ImportacionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def categorias(self) -> list[Categoria]:
        return list(self.session.scalars(select(Categoria).order_by(Categoria.nombre)))

    def almacenes(self) -> list[Almacen]:
        return list(self.session.scalars(select(Almacen).order_by(Almacen.clave)))

    def codigos(self, codigos: Iterable[str]) -> dict[str, Codigo]:
        """Los codigos que ya identifican algo, por su `clave` (sin acentos ni mayusculas: la base
        compara asi)."""
        encontrados: dict[str, Codigo] = {}
        for bloque in _en_bloques(sorted(set(codigos))):
            for fila in self.session.scalars(select(Codigo).where(Codigo.codigo.in_(bloque))):
                encontrados[clave(fila.codigo)] = fila
        return encontrados

    def articulos(self, ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, Articulo]:
        encontrados: dict[uuid.UUID, Articulo] = {}
        for bloque in _en_bloques(sorted(set(ids))):
            for fila in self.session.scalars(select(Articulo).where(Articulo.id.in_(bloque))):
                encontrados[fila.id] = fila
        return encontrados

    def series_en_uso(
        self, articulo_ids: Iterable[uuid.UUID], series: Iterable[str]
    ) -> set[tuple[uuid.UUID, str]]:
        """Pares `(articulo_id, clave(serie))` que ya existen entre las piezas."""
        ids = set(articulo_ids)
        if not ids:
            return set()
        usadas: set[tuple[uuid.UUID, str]] = set()
        for bloque in _en_bloques(sorted(set(series))):
            consulta = select(Pieza.articulo_id, Pieza.numero_serie).where(
                Pieza.numero_serie.in_(bloque), Pieza.articulo_id.in_(ids)
            )
            for articulo_id, serie in self.session.execute(consulta):
                usadas.add((articulo_id, clave(serie)))
        return usadas

    def vales_por_id_cliente(self, ids: Iterable[uuid.UUID]) -> list[Vale]:
        ids = list(ids)
        if not ids:
            return []
        return list(self.session.scalars(select(Vale).where(Vale.id_cliente.in_(ids))))

    def resumen_de_vales(
        self, vale_ids: Iterable[uuid.UUID]
    ) -> dict[uuid.UUID, tuple[int, int, int]]:
        """`vale_id -> (renglones, piezas, unidades)` de los movimientos de cada vale."""
        ids = list(vale_ids)
        if not ids:
            return {}
        consulta = (
            select(
                Movimiento.vale_id,
                func.count(Movimiento.id),
                func.count(Movimiento.pieza_id),
                func.coalesce(func.sum(Movimiento.cantidad), 0),
            )
            .where(Movimiento.vale_id.in_(ids))
            .group_by(Movimiento.vale_id)
        )
        return {v: (int(r), int(p), int(u)) for v, r, p, u in self.session.execute(consulta)}
