"""Servicio del módulo `almacenes`: red de almacenes, ubicaciones y lectura de existencias.

`existencia` es de `movimientos`: aquí solo se lee. Nada de este módulo escribe saldos.
"""

import uuid

from sqlalchemy.orm import Session

from app.core.paginacion import Paginacion
from app.modulos.almacenes.exceptions import AlmacenNoEncontrado, UbicacionNoEncontrada
from app.modulos.almacenes.models import Almacen, Ubicacion, UbicacionVirtual
from app.modulos.almacenes.repository import (
    AlmacenRepository,
    FiltroExistencias,
    UbicacionRepository,
)
from app.modulos.almacenes.schemas import (
    AlmacenFilters,
    AlmacenOut,
    AlmacenResumenOut,
    ExistenciaOut,
    ExistenciasOut,
)


class AlmacenService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.almacenes = AlmacenRepository(session)
        self.ubicaciones = UbicacionRepository(session)

    def obtener(self, almacen_id: uuid.UUID) -> Almacen:
        almacen = self.almacenes.get(almacen_id)
        if almacen is None:
            raise AlmacenNoEncontrado()
        return almacen

    def obtener_por_clave(self, clave: str) -> Almacen:
        almacen = self.almacenes.get_by_clave(clave)
        if almacen is None:
            raise AlmacenNoEncontrado()
        return almacen

    def ubicacion_de_almacen(self, almacen_id: uuid.UUID) -> Ubicacion:
        ubicacion = self.ubicaciones.de_almacen(almacen_id)
        if ubicacion is None:
            raise UbicacionNoEncontrada()
        return ubicacion

    def ubicacion_de_trabajador(self, trabajador_id: uuid.UUID) -> Ubicacion:
        ubicacion = self.ubicaciones.de_trabajador(trabajador_id)
        if ubicacion is None:
            raise UbicacionNoEncontrada()
        return ubicacion

    def ubicacion_virtual(self, virtual: UbicacionVirtual) -> Ubicacion:
        ubicacion = self.ubicaciones.virtual(virtual)
        if ubicacion is None:
            raise UbicacionNoEncontrada()
        return ubicacion

    def asegurar_ubicacion_de_trabajador(self, trabajador_id: uuid.UUID) -> Ubicacion:
        """Crea la ubicación de un trabajador si no existe (sin commit). Al dar de alta uno."""
        return self.ubicaciones.de_trabajador(
            trabajador_id
        ) or self.ubicaciones.crear_de_trabajador(trabajador_id)

    # ------------------------------------------------------------------ lectura

    def listar(self) -> list[AlmacenOut]:
        """Todos los almacenes con su red (quién los surte y a quién surten)."""
        almacenes = self.almacenes.listar()
        por_id = {a.id: a for a in almacenes}
        hijos: dict[uuid.UUID, list[Almacen]] = {}
        for a in almacenes:
            if a.padre_id is not None:
                hijos.setdefault(a.padre_id, []).append(a)
        return [
            AlmacenOut(
                id=a.id,
                clave=a.clave,
                nombre=a.nombre,
                tipo=a.tipo,
                estado=a.estado,
                padre_id=a.padre_id,
                padre_clave=por_id[a.padre_id].clave if a.padre_id in por_id else None,
                hijos=[AlmacenResumenOut.model_validate(h) for h in hijos.get(a.id, [])],
            )
            for a in almacenes
        ]

    def existencias(
        self, almacen_id: uuid.UUID, filtros: AlmacenFilters, pagina: Paginacion
    ) -> ExistenciasOut:
        """Existencias y disponibles por artículo de un almacén (sin costos, RG-12)."""
        almacen = self.obtener(almacen_id)
        ubicacion = self.ubicacion_de_almacen(almacen.id)
        filas, total = self.almacenes.existencias_de_almacen(
            ubicacion.id,
            FiltroExistencias(
                q=filtros.q,
                categoria_id=filtros.categoria_id,
                activo=filtros.activo,
                offset=pagina.offset,
                limit=pagina.limit,
            ),
        )
        return ExistenciasOut(
            almacen=AlmacenResumenOut.model_validate(almacen),
            elementos=[
                ExistenciaOut(
                    articulo_id=art.id,
                    codigo=art.codigo,
                    nombre=art.nombre,
                    marca=art.marca,
                    talla=art.talla,
                    unidad=art.unidad,
                    control=art.control,
                    retornable=art.retornable,
                    categoria_id=art.categoria_id,
                    categoria_nombre=categoria,
                    activo=art.activo,
                    cantidad=cantidad,
                    disponible=int(disponible or 0),
                )
                for art, categoria, cantidad, disponible in filas
            ],
            total=total,
        )

    def existencias_de_articulo(self, articulo_id: uuid.UUID) -> list[tuple[Almacen, int, int]]:
        """Dónde hay de un artículo: `(almacen, cantidad, disponible)` por almacén."""
        return [
            (almacen, cantidad, int(disponible or 0))
            for almacen, cantidad, disponible in self.almacenes.existencias_de_articulo(articulo_id)
        ]

    def poseedores_de_articulo(self, articulo_id: uuid.UUID) -> list[tuple]:
        """Quién lo tiene: `(trabajador, cantidad)` por trabajador con existencia."""
        return [(t, c) for t, c in self.almacenes.poseedores_de_articulo(articulo_id)]
