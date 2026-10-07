"""Persistencia del módulo `almacenes`. Solo `add`, `flush` y consultas; nunca commit."""

import uuid
from dataclasses import dataclass

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, aliased

from app.modulos.acceso.models import Usuario
from app.modulos.almacenes.models import (
    Almacen,
    TipoAlmacen,
    TipoUbicacion,
    Ubicacion,
    UbicacionVirtual,
)
from app.modulos.catalogo.models import Articulo, Categoria, Control, EstadoPieza, Pieza
from app.modulos.movimientos.models import (
    EstadoVale,
    Existencia,
    Movimiento,
    SerieFolio,
    TipoVale,
    Vale,
)
from app.modulos.solicitudes_compra.models import (
    EstadoSolicitud,
    SerieSolicitudCompra,
    SolicitudCompra,
)
from app.modulos.trabajadores.models import Trabajador

# Un traspaso con algo todavía En tránsito: enviado y no recibido, o recibido con diferencias.
ESTADOS_TRASPASO_EN_TRANSITO = (EstadoVale.EN_TRANSITO, EstadoVale.RECIBIDO_CON_DIFERENCIAS)
ESTADOS_SOLICITUD_ABIERTA = (EstadoSolicitud.PENDIENTE, EstadoSolicitud.EN_COMPRA)


@dataclass(frozen=True)
class FiltroExistencias:
    q: str | None = None
    categoria_id: uuid.UUID | None = None
    activo: bool | None = None
    offset: int = 0
    limit: int = 50


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class AlmacenRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, almacen_id: uuid.UUID) -> Almacen | None:
        return self.session.get(Almacen, almacen_id)

    def get_by_clave(self, clave: str) -> Almacen | None:
        return self.session.scalar(select(Almacen).where(Almacen.clave == clave))

    def listar(self) -> list[Almacen]:
        return list(self.session.scalars(select(Almacen).order_by(Almacen.clave)))

    def get_for_update(self, almacen_id: uuid.UUID) -> Almacen | None:
        """El almacén con su fila bloqueada: dos cambios del mismo almacén se turnan."""
        return self.session.scalar(
            select(Almacen)
            .where(Almacen.id == almacen_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def get_by_nombre(self, nombre: str) -> Almacen | None:
        return self.session.scalar(select(Almacen).where(Almacen.nombre == nombre))

    def hay_central(self) -> bool:
        consulta = (
            select(func.count()).select_from(Almacen).where(Almacen.tipo == TipoAlmacen.CENTRAL)
        )
        return (self.session.scalar(consulta) or 0) > 0

    def add(self, almacen: Almacen) -> Almacen:
        self.session.add(almacen)
        self.session.flush()
        return almacen

    def hijos(self, padre_id: uuid.UUID) -> list[Almacen]:
        consulta = select(Almacen).where(Almacen.padre_id == padre_id).order_by(Almacen.clave)
        return list(self.session.scalars(consulta))

    # ------------------------------------------- resumen y bloqueos de cierre (solo lectura)
    # Las tablas de otros módulos (existencia, vale, solicitud_compra, usuario) solo se leen.
    # Cada consulta acepta un `almacen_id` para uno solo o `None` para todos.

    def bloquear_existencias_de(self, almacen_id: uuid.UUID) -> None:
        """Espera a que terminen los vales que están moviendo existencias de ese almacén."""
        self.session.execute(
            select(Existencia.articulo_id)
            .join(Ubicacion, Ubicacion.id == Existencia.ubicacion_id)
            .where(Ubicacion.almacen_id == almacen_id)
            .with_for_update()
        ).all()

    def existencias_por_almacen(
        self, almacen_id: uuid.UUID | None = None
    ) -> dict[uuid.UUID, tuple[int, int]]:
        """`{almacen_id: (unidades, artículos con cantidad mayor a cero)}`."""
        consulta = (
            select(
                Ubicacion.almacen_id,
                func.coalesce(func.sum(Existencia.cantidad), 0),
                func.count(),
            )
            .join(Existencia, Existencia.ubicacion_id == Ubicacion.id)
            .where(Ubicacion.almacen_id.is_not(None), Existencia.cantidad > 0)
            .group_by(Ubicacion.almacen_id)
        )
        if almacen_id is not None:
            consulta = consulta.where(Ubicacion.almacen_id == almacen_id)
        return {a: (int(u), int(n)) for a, u, n in self.session.execute(consulta).all()}

    def articulos_con_existencia(
        self, almacen_id: uuid.UUID, limite: int
    ) -> list[tuple[Articulo, int]]:
        consulta = (
            select(Articulo, Existencia.cantidad)
            .join(Existencia, Existencia.articulo_id == Articulo.id)
            .join(Ubicacion, Ubicacion.id == Existencia.ubicacion_id)
            .where(Ubicacion.almacen_id == almacen_id, Existencia.cantidad > 0)
            .order_by(Existencia.cantidad.desc(), Articulo.codigo)
            .limit(limite)
        )
        return [(a, int(c)) for a, c in self.session.execute(consulta).all()]

    def usuarios_activos_por_almacen(
        self, almacen_id: uuid.UUID | None = None
    ) -> dict[uuid.UUID, int]:
        consulta = (
            select(Usuario.almacen_id, func.count())
            .where(Usuario.almacen_id.is_not(None), Usuario.activo.is_(True))
            .group_by(Usuario.almacen_id)
        )
        if almacen_id is not None:
            consulta = consulta.where(Usuario.almacen_id == almacen_id)
        return {a: int(n) for a, n in self.session.execute(consulta).all()}

    def usuarios_activos(self, almacen_id: uuid.UUID, limite: int) -> list[Usuario]:
        return list(
            self.session.scalars(
                select(Usuario)
                .where(Usuario.almacen_id == almacen_id, Usuario.activo.is_(True))
                .order_by(Usuario.nombre)
                .limit(limite)
            )
        )

    def traspasos_en_transito_por_almacen(
        self, almacen_id: uuid.UUID | None = None
    ) -> dict[uuid.UUID, int]:
        """Traspasos desde o hacia cada almacén con algo todavía En tránsito."""
        consulta = select(Vale.id, Vale.almacen_id, Vale.destino_almacen_id).where(
            Vale.tipo == TipoVale.TRASPASO, Vale.estado.in_(ESTADOS_TRASPASO_EN_TRANSITO)
        )
        cuenta: dict[uuid.UUID, int] = {}
        for _, origen, destino in self.session.execute(consulta).all():
            for a in {origen, destino}:
                if a is not None and (almacen_id is None or a == almacen_id):
                    cuenta[a] = cuenta.get(a, 0) + 1
        return cuenta

    def traspasos_en_transito(self, almacen_id: uuid.UUID, limite: int) -> list[tuple]:
        """`(vale, origen, destino)` de los traspasos En tránsito desde o hacia el almacén."""
        origen = aliased(Almacen)
        destino = aliased(Almacen)
        consulta = (
            select(Vale, origen, destino)
            .join(origen, origen.id == Vale.almacen_id)
            .join(destino, destino.id == Vale.destino_almacen_id)
            .where(
                Vale.tipo == TipoVale.TRASPASO,
                Vale.estado.in_(ESTADOS_TRASPASO_EN_TRANSITO),
                (Vale.almacen_id == almacen_id) | (Vale.destino_almacen_id == almacen_id),
            )
            .order_by(Vale.creado_en.desc())
            .limit(limite)
        )
        return list(self.session.execute(consulta).all())

    def solicitudes_abiertas_por_almacen(
        self, almacen_id: uuid.UUID | None = None
    ) -> dict[uuid.UUID, int]:
        consulta = (
            select(SolicitudCompra.almacen_id, func.count())
            .where(SolicitudCompra.estado.in_(ESTADOS_SOLICITUD_ABIERTA))
            .group_by(SolicitudCompra.almacen_id)
        )
        if almacen_id is not None:
            consulta = consulta.where(SolicitudCompra.almacen_id == almacen_id)
        return {a: int(n) for a, n in self.session.execute(consulta).all()}

    def piezas_en_resguardo_por_almacen(
        self, almacen_id: uuid.UUID | None = None
    ) -> dict[uuid.UUID, int]:
        """Piezas de artículos por pieza que tiene un trabajador, por el almacén del vale de
        la entrega que las puso en sus manos (el último movimiento hacia su ubicación)."""
        de_entrega = (
            select(Vale.almacen_id)
            .join(Movimiento, Movimiento.vale_id == Vale.id)
            .where(
                Movimiento.pieza_id == Pieza.id,
                Movimiento.destino_id == Pieza.ubicacion_id,
            )
            .order_by(Movimiento.creado_en.desc(), Movimiento.id.desc())
            .limit(1)
            .correlate(Pieza)
            .scalar_subquery()
        )
        base = (
            select(de_entrega.label("almacen_id"))
            .select_from(Pieza)
            .join(Ubicacion, Ubicacion.id == Pieza.ubicacion_id)
            .where(Ubicacion.tipo == TipoUbicacion.TRABAJADOR)
            .subquery()
        )
        consulta = (
            select(base.c.almacen_id, func.count())
            .where(base.c.almacen_id.is_not(None))
            .group_by(base.c.almacen_id)
        )
        if almacen_id is not None:
            consulta = consulta.where(base.c.almacen_id == almacen_id)
        return {a: int(n) for a, n in self.session.execute(consulta).all()}

    def con_folios(self, almacen_id: uuid.UUID | None = None) -> set[uuid.UUID]:
        """Almacenes que ya emitieron algún folio de vale o de solicitud (AL-05)."""
        ids: set[uuid.UUID] = set()
        for columna in (SerieFolio.almacen_id, SerieSolicitudCompra.almacen_id, Vale.almacen_id):
            consulta = select(columna).distinct()
            if almacen_id is not None:
                consulta = consulta.where(columna == almacen_id)
            ids.update(self.session.scalars(consulta))
        return ids

    # ------------------------------------------------- existencias (solo lectura)
    # La tabla `existencia` es de `movimientos`: aquí solo se lee.

    @staticmethod
    def _disponible():
        """Existencia que se puede entregar. En artículos por pieza solo cuentan las piezas Aptas
        que están en esa ubicación; en los de cantidad, la existencia completa (I-05)."""
        aptas = (
            select(func.count(Pieza.id))
            .where(
                Pieza.ubicacion_id == Existencia.ubicacion_id,
                Pieza.articulo_id == Existencia.articulo_id,
                Pieza.estado == EstadoPieza.APTO,
            )
            .correlate(Existencia)
            .scalar_subquery()
        )
        return case((Articulo.control == Control.PIEZA, aptas), else_=Existencia.cantidad)

    def existencias_de_almacen(
        self, ubicacion_id: uuid.UUID, filtro: FiltroExistencias
    ) -> tuple[list, int]:
        """Artículos con existencia en esa ubicación: `(filas, total)`, ordenados por nombre."""
        condiciones = [Existencia.ubicacion_id == ubicacion_id, Existencia.cantidad > 0]
        if filtro.q:
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

        base = (
            select(Articulo, Categoria.nombre, Existencia.cantidad, self._disponible())
            .join(Existencia, Existencia.articulo_id == Articulo.id)
            .join(Categoria, Categoria.id == Articulo.categoria_id)
            .where(*condiciones)
        )
        total = self.session.scalar(
            select(func.count())
            .select_from(Articulo)
            .join(Existencia, Existencia.articulo_id == Articulo.id)
            .where(*condiciones)
        )
        filas = self.session.execute(
            base.order_by(Articulo.nombre, Articulo.codigo)
            .offset(filtro.offset)
            .limit(filtro.limit)
        ).all()
        return list(filas), int(total or 0)

    def existencias_de_articulo(self, articulo_id: uuid.UUID) -> list:
        """Dónde hay de un artículo: `(Almacen, cantidad, disponible)` por almacén."""
        consulta = (
            select(Almacen, Existencia.cantidad, self._disponible())
            .join(Ubicacion, Ubicacion.almacen_id == Almacen.id)
            .join(Existencia, Existencia.ubicacion_id == Ubicacion.id)
            .join(Articulo, Articulo.id == Existencia.articulo_id)
            .where(Existencia.articulo_id == articulo_id, Existencia.cantidad > 0)
            .order_by(Almacen.clave)
        )
        return list(self.session.execute(consulta).all())

    def poseedores_de_articulo(self, articulo_id: uuid.UUID) -> list:
        """Quién lo tiene: `(Trabajador, cantidad)` por trabajador con existencia."""
        consulta = (
            select(Trabajador, Existencia.cantidad)
            .join(Ubicacion, Ubicacion.trabajador_id == Trabajador.id)
            .join(Existencia, Existencia.ubicacion_id == Ubicacion.id)
            .where(Existencia.articulo_id == articulo_id, Existencia.cantidad > 0)
            .order_by(Trabajador.nombre)
        )
        return list(self.session.execute(consulta).all())


class UbicacionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, ubicacion_id: uuid.UUID) -> Ubicacion | None:
        return self.session.get(Ubicacion, ubicacion_id)

    def de_almacen(self, almacen_id: uuid.UUID) -> Ubicacion | None:
        return self.session.scalar(select(Ubicacion).where(Ubicacion.almacen_id == almacen_id))

    def de_trabajador(self, trabajador_id: uuid.UUID) -> Ubicacion | None:
        return self.session.scalar(
            select(Ubicacion).where(Ubicacion.trabajador_id == trabajador_id)
        )

    def virtual(self, virtual: UbicacionVirtual) -> Ubicacion | None:
        return self.session.scalar(select(Ubicacion).where(Ubicacion.virtual == virtual.value))

    def add(self, ubicacion: Ubicacion) -> Ubicacion:
        self.session.add(ubicacion)
        self.session.flush()
        return ubicacion

    def crear_de_almacen(self, almacen_id: uuid.UUID) -> Ubicacion:
        return self.add(Ubicacion(tipo=TipoUbicacion.ALMACEN, almacen_id=almacen_id))

    def crear_de_trabajador(self, trabajador_id: uuid.UUID) -> Ubicacion:
        return self.add(Ubicacion(tipo=TipoUbicacion.TRABAJADOR, trabajador_id=trabajador_id))

    def crear_virtual(self, virtual: UbicacionVirtual) -> Ubicacion:
        return self.add(Ubicacion(tipo=TipoUbicacion.VIRTUAL, virtual=virtual.value))
