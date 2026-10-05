"""Persistencia de `trabajadores`: add, flush y consultas; nunca commit.

Las consultas de resguardo y pendientes son de SOLO LECTURA sobre tablas de otros módulos
(existencia, ubicacion, movimiento, vale, articulo, pieza). Esas tablas las escribe `movimientos`.
"""

import uuid
from collections import defaultdict

from sqlalchemy import case, exists, func, literal, or_, select
from sqlalchemy.orm import Session

from app.modulos.almacenes.models import Almacen, Ubicacion
from app.modulos.catalogo.models import Articulo, Control, Pieza
from app.modulos.movimientos.models import Existencia, Movimiento, TipoVale, Vale
from app.modulos.trabajadores.models import PeriodoContrato, Trabajador
from app.modulos.trabajadores.schemas import Situacion
from app.modulos.trabajadores.tipos import FilaLista, Pendiente


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class TrabajadorRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ----------------------------------------------------------- trabajador

    def get(self, trabajador_id: uuid.UUID, *, para_actualizar: bool = False) -> Trabajador | None:
        if para_actualizar:
            return self.session.scalar(
                select(Trabajador).where(Trabajador.id == trabajador_id).with_for_update()
            )
        return self.session.get(Trabajador, trabajador_id)

    def get_by_numero(self, numero_empleado: str) -> Trabajador | None:
        return self.session.scalar(
            select(Trabajador).where(Trabajador.numero_empleado == numero_empleado)
        )

    def get_by_curp(self, curp: str) -> Trabajador | None:
        return self.session.scalar(select(Trabajador).where(Trabajador.curp == curp))

    def add(self, trabajador: Trabajador) -> Trabajador:
        self.session.add(trabajador)
        self.session.flush()
        return trabajador

    def buscar(self, q: str, limite: int) -> list[Trabajador]:
        patron = f"%{_escapar_like(q.strip())}%"
        consulta = (
            select(Trabajador)
            .where(or_(Trabajador.nombre.like(patron), Trabajador.numero_empleado.like(patron)))
            .order_by(Trabajador.nombre)
            .limit(limite)
        )
        return list(self.session.scalars(consulta))

    # ------------------------------------------------------------- periodos

    def add_periodo(self, periodo: PeriodoContrato) -> PeriodoContrato:
        self.session.add(periodo)
        self.session.flush()
        return periodo

    def periodos(self, trabajador_id: uuid.UUID) -> list[PeriodoContrato]:
        """Del más reciente al más antiguo."""
        consulta = (
            select(PeriodoContrato)
            .where(PeriodoContrato.trabajador_id == trabajador_id)
            .order_by(PeriodoContrato.inicio.desc(), PeriodoContrato.creado_en.desc())
        )
        return list(self.session.scalars(consulta))

    def periodos_de(self, ids: list[uuid.UUID]) -> dict[uuid.UUID, list[PeriodoContrato]]:
        """Periodos de varios trabajadores, cada lista del más reciente al más antiguo."""
        if not ids:
            return {}
        consulta = (
            select(PeriodoContrato)
            .where(PeriodoContrato.trabajador_id.in_(ids))
            .order_by(PeriodoContrato.inicio.desc(), PeriodoContrato.creado_en.desc())
        )
        resultado: dict[uuid.UUID, list[PeriodoContrato]] = defaultdict(list)
        for periodo in self.session.scalars(consulta):
            resultado[periodo.trabajador_id].append(periodo)
        return resultado

    # ---------------------------------------------------------------- lista

    def _hay_pendientes(self):
        """Condición SQL: el trabajador tiene retornables en resguardo (B-03: sin consumibles)."""
        por_pieza = exists(
            select(1)
            .select_from(Ubicacion)
            .join(Pieza, Pieza.ubicacion_id == Ubicacion.id)
            .join(Articulo, Articulo.id == Pieza.articulo_id)
            .where(Ubicacion.trabajador_id == Trabajador.id, Articulo.retornable.is_(True))
            .correlate(Trabajador)
        )
        por_cantidad = exists(
            select(1)
            .select_from(Ubicacion)
            .join(Existencia, Existencia.ubicacion_id == Ubicacion.id)
            .join(Articulo, Articulo.id == Existencia.articulo_id)
            .where(
                Ubicacion.trabajador_id == Trabajador.id,
                Existencia.cantidad > 0,
                Articulo.retornable.is_(True),
                Articulo.control == Control.CANTIDAD,
            )
            .correlate(Trabajador)
        )
        return or_(por_pieza, por_cantidad)

    def _no_adeudo_emitido(self):
        """Condición SQL: hay un vale NO_ADEUDO vigente posterior al último periodo (B-09).

        Un reingreso registra un periodo nuevo y con ello el no adeudo anterior deja de contar.
        """
        ultimo_periodo = (
            select(func.max(PeriodoContrato.creado_en))
            .where(PeriodoContrato.trabajador_id == Trabajador.id)
            .scalar_subquery()
        )
        return exists(
            select(1).where(
                Vale.trabajador_id == Trabajador.id,
                Vale.tipo == TipoVale.NO_ADEUDO,
                Vale.estado != "CANCELADO",
                Vale.creado_en >= func.coalesce(ultimo_periodo, Vale.creado_en),
            )
        )

    def listar(
        self, *, q: str | None, situacion: Situacion | None, limit: int, offset: int
    ) -> tuple[list[FilaLista], int]:
        con_pendientes = self._hay_pendientes()
        no_adeudo = self._no_adeudo_emitido()
        situacion_sql = case(
            (con_pendientes, literal(Situacion.CON_PENDIENTES.value)),
            (no_adeudo, literal(Situacion.NO_ADEUDO_EMITIDO.value)),
            else_=literal(Situacion.SIN_PENDIENTES.value),
        )
        filtros = []
        if q and q.strip():
            patron = f"%{_escapar_like(q.strip())}%"
            filtros.append(
                or_(Trabajador.nombre.like(patron), Trabajador.numero_empleado.like(patron))
            )
        if situacion is not None:
            filtros.append(situacion_sql == situacion.value)

        total = self.session.scalar(select(func.count()).select_from(Trabajador).where(*filtros))
        consulta = (
            select(Trabajador, con_pendientes.label("p"), no_adeudo.label("n"))
            .where(*filtros)
            .order_by(Trabajador.nombre, Trabajador.numero_empleado)
            .limit(limit)
            .offset(offset)
        )
        filas = [
            FilaLista(trabajador=t, con_pendientes=bool(p), no_adeudo_emitido=bool(n))
            for t, p, n in self.session.execute(consulta)
        ]
        return filas, int(total or 0)

    def situacion_de(self, trabajador_id: uuid.UUID) -> Situacion:
        con_pendientes = self._hay_pendientes()
        no_adeudo = self._no_adeudo_emitido()
        fila = self.session.execute(
            select(con_pendientes.label("p"), no_adeudo.label("n")).where(
                Trabajador.id == trabajador_id
            )
        ).one()
        if fila.p:
            return Situacion.CON_PENDIENTES
        if fila.n:
            return Situacion.NO_ADEUDO_EMITIDO
        return Situacion.SIN_PENDIENTES

    # ------------------------------------------------- resguardo y pendientes

    def pendientes(self, trabajador_id: uuid.UUID) -> list[Pendiente]:
        """Retornables en resguardo: piezas con la ubicación del trabajador y artículos por
        cantidad con existencia mayor a cero. Los consumibles no cuentan (B-03)."""
        ubicacion_id = self.session.scalar(
            select(Ubicacion.id).where(Ubicacion.trabajador_id == trabajador_id)
        )
        if ubicacion_id is None:
            return []

        piezas = self.session.execute(
            select(Pieza, Articulo)
            .join(Articulo, Articulo.id == Pieza.articulo_id)
            .where(Pieza.ubicacion_id == ubicacion_id, Articulo.retornable.is_(True))
        ).all()
        cantidades = self.session.execute(
            select(Existencia.cantidad, Articulo)
            .join(Articulo, Articulo.id == Existencia.articulo_id)
            .where(
                Existencia.ubicacion_id == ubicacion_id,
                Existencia.cantidad > 0,
                Articulo.retornable.is_(True),
                Articulo.control == Control.CANTIDAD,
            )
        ).all()

        entregas_pieza = self._ultimas_entregas(
            ubicacion_id, Movimiento.pieza_id, [p.id for p, _ in piezas]
        )
        entregas_articulo = self._ultimas_entregas(
            ubicacion_id, Movimiento.articulo_id, [a.id for _, a in cantidades], solo_cantidad=True
        )

        resultado: list[Pendiente] = []
        for pieza, articulo in piezas:
            resultado.append(
                self._pendiente(articulo, pieza.codigo, 1, pieza, entregas_pieza.get(pieza.id))
            )
        for cantidad, articulo in cantidades:
            resultado.append(
                self._pendiente(
                    articulo, articulo.codigo, cantidad, None, entregas_articulo.get(articulo.id)
                )
            )
        resultado.sort(key=lambda p: (p.entregado_en is None, p.entregado_en, p.codigo))
        return resultado

    @staticmethod
    def _pendiente(articulo, codigo, cantidad, pieza, entrega) -> Pendiente:
        return Pendiente(
            articulo_id=articulo.id,
            articulo=articulo.nombre,
            control=articulo.control,
            pieza_id=pieza.id if pieza else None,
            codigo=codigo,
            numero_serie=pieza.numero_serie if pieza else None,
            cantidad=cantidad,
            entregado_en=entrega.creado_en if entrega else None,
            vale_id=entrega.vale_id if entrega else None,
            folio=entrega.folio if entrega else None,
            almacen_id=entrega.almacen_id if entrega else None,
            almacen_clave=entrega.clave if entrega else None,
            almacen=entrega.nombre if entrega else None,
        )

    def _ultimas_entregas(self, ubicacion_id, columna, ids, *, solo_cantidad: bool = False):
        """Por cada pieza o artículo, el movimiento más reciente hacia el trabajador. Se prefiere
        el de un vale de ENTREGA; un vale de cancelación que devuelve el equipo al trabajador no
        cambia quién ni cuándo se lo entregó."""
        if not ids:
            return {}
        consulta = (
            select(
                columna.label("ref"),
                Movimiento.creado_en,
                Movimiento.vale_id,
                Vale.folio,
                Vale.tipo,
                Vale.almacen_id,
                Almacen.clave,
                Almacen.nombre,
            )
            .join(Vale, Vale.id == Movimiento.vale_id)
            .join(Almacen, Almacen.id == Vale.almacen_id)
            .where(Movimiento.destino_id == ubicacion_id, columna.in_(ids))
            .order_by(Movimiento.creado_en.desc())
        )
        if solo_cantidad:
            consulta = consulta.where(Movimiento.pieza_id.is_(None))
        entregas: dict = {}
        otras: dict = {}
        for fila in self.session.execute(consulta):
            if fila.tipo == TipoVale.ENTREGA:
                entregas.setdefault(fila.ref, fila)
            else:
                otras.setdefault(fila.ref, fila)
        return {**otras, **entregas}
