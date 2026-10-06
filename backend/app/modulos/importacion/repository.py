"""Persistencia: consultas de solo lectura; nunca commit.

El modulo `importacion` no escribe tablas propias: los articulos los crea `catalogo` y los vales
`movimientos`. Aqui solo se leen los datos que la vista previa necesita, en bloques para no hacer
una consulta por fila.
"""

import re
import uuid
from collections.abc import Iterable, Iterator
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modulos.almacenes.models import Almacen, TipoUbicacion, Ubicacion
from app.modulos.auditoria.models import Auditoria
from app.modulos.catalogo.models import Articulo, Categoria, Codigo, Pieza
from app.modulos.importacion.lectura import clave
from app.modulos.movimientos.models import Existencia, Movimiento, Vale

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

    def articulos_por_nombre(self, nombres: Iterable[str]) -> list[Articulo]:
        """Articulos cuyo nombre coincide (la base compara sin acentos ni mayusculas)."""
        encontrados: list[Articulo] = []
        for bloque in _en_bloques(sorted(set(nombres))):
            consulta = select(Articulo).where(Articulo.nombre.in_(bloque))
            encontrados.extend(self.session.scalars(consulta.order_by(Articulo.creado_en)))
        return encontrados

    def saldos(self, articulo_ids: Iterable[uuid.UUID]) -> dict[tuple[uuid.UUID, uuid.UUID], int]:
        """`(articulo_id, almacen_id) -> cantidad` que hay hoy en cada almacen (Existencia)."""
        ids = set(articulo_ids)
        saldos: dict[tuple[uuid.UUID, uuid.UUID], int] = {}
        for bloque in _en_bloques(sorted(ids)):
            consulta = (
                select(Existencia.articulo_id, Ubicacion.almacen_id, Existencia.cantidad)
                .join(Ubicacion, Ubicacion.id == Existencia.ubicacion_id)
                .where(Ubicacion.tipo == TipoUbicacion.ALMACEN, Existencia.articulo_id.in_(bloque))
            )
            for articulo_id, almacen_id, cantidad in self.session.execute(consulta):
                saldos[(articulo_id, almacen_id)] = int(cantidad)
        return saldos

    def ultimo_numero_con_prefijo(self, prefijo: str) -> int:
        """El consecutivo mas alto de los codigos `PREFIJO-NNNN` que ya existen (0 si no hay)."""
        patron = re.compile(rf"^{re.escape(prefijo)}-(\d+)$", re.IGNORECASE)
        mayor = 0
        consulta = select(Codigo.codigo).where(Codigo.codigo.like(f"{prefijo}-%"))
        for codigo in self.session.scalars(consulta):
            encontrado = patron.match(codigo)
            if encontrado:
                mayor = max(mayor, int(encontrado.group(1)))
        return mayor

    def bloquear_categorias(self) -> None:
        """Toma `FOR UPDATE` las categorias, en orden: serializa los lotes que crean articulos
        (consecutivo de codigos y articulos repetidos) hasta que el primero confirme."""
        self.session.execute(select(Categoria.id).order_by(Categoria.id).with_for_update())

    def fecha_de_importacion(self, huella: str) -> datetime | None:
        """La fecha de la importacion mas reciente con esa huella (I-12), o `None`."""
        return self.session.scalar(
            select(Auditoria.creado_en)
            .where(
                Auditoria.accion == "importacion.confirmar",
                Auditoria.despues["huella"].as_string() == huella,
            )
            .order_by(Auditoria.creado_en.desc())
            .limit(1)
        )
