"""Persistencia del módulo `catalogo`: add, flush y consultas; nunca commit.

Las consultas de `movimiento` y `trabajador` son de SOLO LECTURA: esas tablas son de otros módulos.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import delete, exists, func, select, update
from sqlalchemy.orm import Session

from app.core.tiempo import hoy_mx
from app.modulos.catalogo.models import (
    Articulo,
    Categoria,
    Codigo,
    Control,
    Dotacion,
    EstadoPieza,
    Pieza,
    Puesto,
    TipoCodigo,
)
from app.modulos.movimientos.models import Movimiento
from app.modulos.trabajadores.models import EstadoTrabajador, PeriodoContrato, Trabajador


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@dataclass(frozen=True)
class FiltroArticulos:
    q: str | None = None
    categoria_id: uuid.UUID | None = None
    activo: bool | None = None
    # FEAT-012: solo artículos activos que no tienen costo capturado.
    sin_costo: bool = False
    offset: int = 0
    limit: int = 50


class CategoriaRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, categoria_id: uuid.UUID) -> Categoria | None:
        return self.session.get(Categoria, categoria_id)

    def get_by_nombre(self, nombre: str) -> Categoria | None:
        return self.session.scalar(select(Categoria).where(Categoria.nombre == nombre))

    def bloquear(self, categoria_id: uuid.UUID) -> None:
        """`FOR UPDATE` de la categoría: serializa la generación de códigos `PREFIJO-NNNN`."""
        self.session.execute(
            select(Categoria.id).where(Categoria.id == categoria_id).with_for_update()
        )

    def listar(
        self, *, activo: bool | None, offset: int, limit: int
    ) -> tuple[list[Categoria], int]:
        condiciones = [] if activo is None else [Categoria.activo == activo]
        total = self.session.scalar(select(func.count()).select_from(Categoria).where(*condiciones))
        filas = self.session.scalars(
            select(Categoria)
            .where(*condiciones)
            .order_by(Categoria.nombre)
            .offset(offset)
            .limit(limit)
        )
        return list(filas), int(total or 0)

    def add(self, categoria: Categoria) -> Categoria:
        self.session.add(categoria)
        self.session.flush()
        return categoria


class ArticuloRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, articulo_id: uuid.UUID) -> Articulo | None:
        return self.session.get(Articulo, articulo_id)

    def get_by_codigo(self, codigo: str) -> Articulo | None:
        return self.session.scalar(select(Articulo).where(Articulo.codigo == codigo))

    def get_by_nombre(self, nombre: str) -> Articulo | None:
        """El artículo con ese nombre (la base compara sin acentos ni mayúsculas), si hay."""
        return self.session.scalar(select(Articulo).where(Articulo.nombre == nombre).limit(1))

    def listar(self, filtro: FiltroArticulos) -> tuple[list[tuple[Articulo, str]], int]:
        """`(articulo, nombre de su categoría)` ordenados por nombre, y el total sin paginar."""
        condiciones = []
        if filtro.q and filtro.q.strip():
            patron = f"%{_escapar_like(filtro.q.strip())}%"
            condiciones.append(
                Articulo.nombre.ilike(patron, escape="\\")
                | Articulo.codigo.ilike(patron, escape="\\")
                | Articulo.marca.ilike(patron, escape="\\")
                | Articulo.modelo.ilike(patron, escape="\\")
            )
        if filtro.categoria_id is not None:
            condiciones.append(Articulo.categoria_id == filtro.categoria_id)
        if filtro.activo is not None:
            condiciones.append(Articulo.activo == filtro.activo)
        if filtro.sin_costo:
            condiciones.append(Articulo.activo.is_(True))
            condiciones.append(Articulo.costo_unitario.is_(None))

        total = self.session.scalar(select(func.count()).select_from(Articulo).where(*condiciones))
        filas = self.session.execute(
            select(Articulo, Categoria.nombre)
            .join(Categoria, Categoria.id == Articulo.categoria_id)
            .where(*condiciones)
            .order_by(Articulo.nombre, Articulo.codigo)
            .offset(filtro.offset)
            .limit(filtro.limit)
        ).all()
        return [(a, n) for a, n in filas], int(total or 0)

    def add(self, articulo: Articulo) -> Articulo:
        self.session.add(articulo)
        self.session.flush()
        return articulo

    def eliminar(self, articulo: Articulo) -> None:
        """Borra el artículo y su código (solo si no tiene movimientos; lo verifica el service)."""
        self.session.execute(
            delete(Codigo).where(Codigo.tipo == TipoCodigo.ARTICULO, Codigo.ref_id == articulo.id)
        )
        self.session.delete(articulo)
        self.session.flush()

    def tiene_movimientos(self, articulo_id: uuid.UUID) -> bool:
        """Solo lectura: `movimiento` es del módulo `movimientos`."""
        return bool(
            self.session.scalar(select(exists().where(Movimiento.articulo_id == articulo_id)))
        )

    def tiene_piezas(self, articulo_id: uuid.UUID) -> bool:
        return bool(self.session.scalar(select(exists().where(Pieza.articulo_id == articulo_id))))

    def get_varios(self, ids: list[uuid.UUID]) -> dict[uuid.UUID, Articulo]:
        if not ids:
            return {}
        filas = self.session.scalars(select(Articulo).where(Articulo.id.in_(ids)))
        return {a.id: a for a in filas}

    def en_dotacion(self, articulo_id: uuid.UUID) -> bool:
        return bool(
            self.session.scalar(select(exists().where(Dotacion.articulo_id == articulo_id)))
        )

    def dotacion_maxima(self, articulo_id: uuid.UUID) -> int | None:
        """La mayor cantidad recomendada de este artículo en cualquier puesto (D-04)."""
        return self.session.scalar(
            select(func.max(Dotacion.cantidad)).where(Dotacion.articulo_id == articulo_id)
        )


class PiezaRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, pieza_id: uuid.UUID) -> Pieza | None:
        return self.session.get(Pieza, pieza_id)

    def bloquear(self, pieza_id: uuid.UUID) -> Pieza | None:
        """La pieza con bloqueo de escritura hasta cerrar la transacción."""
        return self.session.scalar(
            select(Pieza)
            .where(Pieza.id == pieza_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def get_by_serie(self, articulo_id: uuid.UUID, numero_serie: str) -> Pieza | None:
        return self.session.scalar(
            select(Pieza).where(
                Pieza.articulo_id == articulo_id, Pieza.numero_serie == numero_serie
            )
        )

    def add(self, pieza: Pieza) -> Pieza:
        self.session.add(pieza)
        self.session.flush()
        return pieza

    def quitar_inspeccion_vigente(self, articulo_id: uuid.UUID) -> int:
        """Deja sin inspección vigente a todas las piezas del artículo (CF-09)."""
        resultado = self.session.execute(
            update(Pieza)
            .where(Pieza.articulo_id == articulo_id, Pieza.inspeccion_vigente_hasta.is_not(None))
            .values(inspeccion_vigente_hasta=None)
        )
        return resultado.rowcount or 0


class EtiquetaRepository:
    """Lecturas para las hojas de QR (US-ETQ-001). Devuelve `(codigo, texto)`."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def piezas(self) -> list[tuple[str, str]]:
        """Una por pieza que no está de baja: nombre del artículo, talla y serie."""
        filas = self.session.execute(
            select(Pieza.codigo, Articulo.nombre, Articulo.talla, Pieza.numero_serie)
            .join(Articulo, Articulo.id == Pieza.articulo_id)
            .where(Pieza.estado != EstadoPieza.BAJA)
            .order_by(Articulo.nombre, Pieza.codigo)
        ).all()
        resultado = []
        for codigo, nombre, talla, serie in filas:
            partes = [nombre]
            if talla:
                partes.append(f"talla {talla}")
            if serie:
                partes.append(f"serie {serie}")
            resultado.append((codigo, " · ".join(partes)))
        return resultado

    def estantes(self) -> list[tuple[str, str]]:
        """Una por artículo activo por cantidad (I-07): su código de producto y su nombre."""
        filas = self.session.execute(
            select(Articulo.codigo, Articulo.nombre)
            .where(Articulo.control == Control.CANTIDAD, Articulo.activo.is_(True))
            .order_by(Articulo.nombre, Articulo.codigo)
        ).all()
        return [(c, n) for c, n in filas]

    def credenciales(self) -> list[tuple[str, str, str, str | None]]:
        """Solo lectura de `trabajador`: `(codigo, nombre, numero_empleado, puesto)` de los
        trabajadores que no están inactivos. Nunca CURP ni NSS (RG-13)."""
        filas = self.session.execute(
            select(Codigo.codigo, Trabajador.id, Trabajador.nombre, Trabajador.numero_empleado)
            .join(Trabajador, Trabajador.id == Codigo.ref_id)
            .where(
                Codigo.tipo == TipoCodigo.TRABAJADOR,
                Trabajador.estado != EstadoTrabajador.INACTIVO,
            )
            .order_by(Trabajador.nombre, Codigo.codigo)
        ).all()
        # El puesto es el del periodo vigente hoy (mismo criterio que la vigencia E-02); si no hay
        # uno vigente, el del más reciente (los periodos llegan del más nuevo al más viejo).
        puestos: dict[uuid.UUID, str | None] = {}
        if filas:
            hoy = hoy_mx()
            periodos = self.session.execute(
                select(
                    PeriodoContrato.trabajador_id,
                    PeriodoContrato.puesto,
                    PeriodoContrato.inicio,
                    PeriodoContrato.fin,
                )
                .where(PeriodoContrato.trabajador_id.in_([f[1] for f in filas]))
                .order_by(PeriodoContrato.inicio.desc(), PeriodoContrato.creado_en.desc())
            ).all()
            recientes: dict[uuid.UUID, str | None] = {}
            for trabajador_id, puesto, inicio, fin in periodos:
                recientes.setdefault(trabajador_id, puesto)
                if inicio <= hoy <= fin:
                    puestos.setdefault(trabajador_id, puesto)
            for trabajador_id, puesto in recientes.items():
                puestos.setdefault(trabajador_id, puesto)
        return [(c, n, e, puestos.get(tid)) for c, tid, n, e in filas]


class PuestoRepository:
    """Puestos y su dotación (D-01). Nunca hace commit."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, puesto_id: uuid.UUID) -> Puesto | None:
        return self.session.get(Puesto, puesto_id)

    def get_by_nombre(self, nombre: str) -> Puesto | None:
        """La colación de la base ignora mayúsculas y acentos."""
        return self.session.scalar(select(Puesto).where(Puesto.nombre == nombre.strip()))

    def listar(
        self, *, activo: bool | None, offset: int, limit: int
    ) -> tuple[list[tuple[Puesto, int]], int]:
        """`(puesto, total de artículos de su dotación)` por nombre, y el total sin paginar."""
        condiciones = [] if activo is None else [Puesto.activo == activo]
        total = self.session.scalar(select(func.count()).select_from(Puesto).where(*condiciones))
        cuenta = (
            select(func.count(Dotacion.id))
            .where(Dotacion.puesto_id == Puesto.id)
            .correlate(Puesto)
            .scalar_subquery()
        )
        filas = self.session.execute(
            select(Puesto, cuenta)
            .where(*condiciones)
            .order_by(Puesto.nombre)
            .offset(offset)
            .limit(limit)
        ).all()
        return [(p, int(n or 0)) for p, n in filas], int(total or 0)

    def total_articulos(self, puesto_id: uuid.UUID) -> int:
        return int(
            self.session.scalar(
                select(func.count(Dotacion.id)).where(Dotacion.puesto_id == puesto_id)
            )
            or 0
        )

    def add(self, puesto: Puesto) -> Puesto:
        self.session.add(puesto)
        self.session.flush()
        return puesto

    def renglones(self, puesto_id: uuid.UUID) -> list[tuple[Dotacion, Articulo]]:
        """La dotación del puesto con sus artículos, por nombre de artículo."""
        filas = self.session.execute(
            select(Dotacion, Articulo)
            .join(Articulo, Articulo.id == Dotacion.articulo_id)
            .where(Dotacion.puesto_id == puesto_id)
            .order_by(Articulo.nombre, Articulo.codigo)
        ).all()
        return [(d, a) for d, a in filas]

    def reemplazar_renglones(self, puesto_id: uuid.UUID, nuevos: dict[uuid.UUID, int]) -> None:
        """Deja la dotación exactamente como `nuevos` (`articulo_id -> cantidad`)."""
        actuales = {
            d.articulo_id: d
            for d in self.session.scalars(select(Dotacion).where(Dotacion.puesto_id == puesto_id))
        }
        for articulo_id, fila in actuales.items():
            if articulo_id not in nuevos:
                self.session.delete(fila)
            elif fila.cantidad != nuevos[articulo_id]:
                fila.cantidad = nuevos[articulo_id]
        for articulo_id, cantidad in nuevos.items():
            if articulo_id not in actuales:
                self.session.add(
                    Dotacion(puesto_id=puesto_id, articulo_id=articulo_id, cantidad=cantidad)
                )
        self.session.flush()
