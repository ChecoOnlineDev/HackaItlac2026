"""Tablero de inicio (FEAT-008): tarjetas y ranking de lo más usado. SOLO LEE; nunca hace `commit`.

Reglas: TB-01 (alcance por almacén, AC-06), TB-02 (qué cuenta como usado) y TB-03 (fechas de
México). El permiso `tablero.ver` lo exige el router; el alcance lo decide aquí el servidor.
"""

import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.tiempo import ahora_utc, hoy_mx
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.acceso.service import AccesoService
from app.modulos.almacenes.exceptions import AlmacenNoEncontrado
from app.modulos.almacenes.models import Almacen
from app.modulos.catalogo.exceptions import CategoriaNoEncontrada
from app.modulos.consulta.exceptions import RangoFechasDemasiadoLargo
from app.modulos.consulta.repository_tablero import TableroRepository
from app.modulos.consulta.schemas_tablero import (
    DIAS_MAXIMOS_RANGO,
    NOMBRE_SIN_ALMACEN,
    NOMBRE_TODOS,
    AlcanceOut,
    AlmacenRefOut,
    BarraAlmacenOut,
    BarraConsumoOut,
    CategoriaRefOut,
    ConsumoTableroFilters,
    ConsumoTableroOut,
    ExistenciasTarjeta,
    OtrosOut,
    ResumenTableroOut,
)
from app.modulos.consulta.service import rango_utc

# Días de anticipación de «inspecciones por vencer»: el mismo plazo de E-11.
DIAS_INSPECCION_POR_VENCER = 7


@dataclass(frozen=True)
class AlcanceTablero:
    """Qué ve el tablero. `almacen` es `None` si son todos (o si el usuario no tiene almacén)."""

    almacen: Almacen | None
    es_todos: bool
    vacio: bool
    puede_elegir: bool

    @property
    def almacen_id(self) -> uuid.UUID | None:
        return self.almacen.id if self.almacen else None


class TableroService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.tablero = TableroRepository(session)
        self.acceso = AccesoService(session)

    # ===================================================================== alcance (TB-01)

    def _alcance(self, usuario: Usuario, almacen_id: uuid.UUID | None) -> AlcanceTablero:
        """Con `almacenes.todos`: todos o el almacén pedido (404 si no existe; uno cerrado sí se
        puede ver). Sin él: solo el asignado y `almacen_id` se ignora; sin asignado, vacío."""
        if self.acceso.puede_operar_todos_los_almacenes(usuario):
            if almacen_id is None:
                return AlcanceTablero(None, es_todos=True, vacio=False, puede_elegir=True)
            almacen = self.tablero.almacen(almacen_id)
            if almacen is None:
                raise AlmacenNoEncontrado()
            return AlcanceTablero(almacen, es_todos=False, vacio=False, puede_elegir=True)
        almacen = self.tablero.almacen(usuario.almacen_id) if usuario.almacen_id else None
        if almacen is None:
            return AlcanceTablero(None, es_todos=False, vacio=True, puede_elegir=False)
        return AlcanceTablero(almacen, es_todos=False, vacio=False, puede_elegir=False)

    @staticmethod
    def _alcance_out(alcance: AlcanceTablero) -> AlcanceOut:
        if alcance.es_todos:
            nombre = NOMBRE_TODOS
        else:
            nombre = alcance.almacen.nombre if alcance.almacen else NOMBRE_SIN_ALMACEN
        return AlcanceOut(
            almacen_id=alcance.almacen_id,
            nombre=nombre,
            es_todos=alcance.es_todos,
            puede_elegir=alcance.puede_elegir,
        )

    # ========================================================================== resumen

    def resumen(self, usuario: Usuario, almacen_id: uuid.UUID | None) -> ResumenTableroOut:
        """Las tarjetas de FEAT-008 4.2.2 dentro del alcance del usuario (TB-01)."""
        alcance = self._alcance(usuario, almacen_id)
        generado = ahora_utc()
        ve_resguardo = P.RESGUARDO_VER in self.acceso.permisos_de(usuario)
        if alcance.vacio:
            return ResumenTableroOut(
                alcance=self._alcance_out(alcance),
                existencias=ExistenciasTarjeta(unidades=0, articulos=0),
                resguardo_equipo_importante=0,
                sin_existencia=0,
                traspasos_en_transito=0,
                entregas_hoy=0,
                solicitudes_compra_abiertas=0,
                inspecciones_por_vencer=0,
                piezas_serie_pendiente=0,
                alto_valor_fuera=0 if ve_resguardo else None,
                generado_en=generado,
            )
        x = alcance.almacen_id
        hoy = hoy_mx()
        inicio, fin = rango_utc(hoy, hoy)  # TB-03: «hoy» es el día de México
        unidades, articulos = self.tablero.existencias(x)
        return ResumenTableroOut(
            alcance=self._alcance_out(alcance),
            existencias=ExistenciasTarjeta(unidades=unidades, articulos=articulos),
            resguardo_equipo_importante=self.tablero.resguardo_equipo_importante(x),
            sin_existencia=self.tablero.sin_existencia(x),
            traspasos_en_transito=self.tablero.traspasos_en_transito(x),
            entregas_hoy=self.tablero.entregas(x, inicio, fin),
            solicitudes_compra_abiertas=self.tablero.solicitudes_abiertas(x),
            inspecciones_por_vencer=self.tablero.inspecciones_por_vencer(
                x, hoy, hoy + timedelta(days=DIAS_INSPECCION_POR_VENCER)
            ),
            piezas_serie_pendiente=self.tablero.piezas_serie_pendiente(x),
            alto_valor_fuera=self.tablero.alto_valor_fuera(x) if ve_resguardo else None,
            generado_en=generado,
        )

    # ========================================================================== consumo

    def consumo(self, usuario: Usuario, filtros: ConsumoTableroFilters) -> ConsumoTableroOut:
        """El ranking de lo más usado (TB-02), agrupado aquí: por artículo y, si se pide y el
        alcance es «todos», por almacén. Lo que no cabe en `limite` va junto en `otros`."""
        hasta = filtros.hasta or hoy_mx()
        desde = filtros.desde or hasta.replace(day=1)  # por omisión, del día 1 del mes a `hasta`
        inicio, fin = rango_utc(desde, hasta)  # TB-03; rechaza el rango invertido
        if (hasta - desde).days > DIAS_MAXIMOS_RANGO:
            raise RangoFechasDemasiadoLargo()
        assert inicio is not None and fin is not None

        alcance = self._alcance(usuario, filtros.almacen_id)
        categoria = None
        if filtros.categoria_id is not None:
            categoria = self.tablero.categoria(filtros.categoria_id)
            if categoria is None:
                raise CategoriaNoEncontrada()
        separar = filtros.separar_por_almacen and alcance.es_todos

        filas = (
            []
            if alcance.vacio
            else self.tablero.consumo(
                desde=inicio,
                hasta_excluyente=fin,
                almacen_id=alcance.almacen_id,
                categoria_id=filtros.categoria_id,
            )
        )
        articulos = self._agrupar(filas)
        ranking = sorted(articulos.values(), key=lambda a: (-a["total"], a["articulo"].casefold()))
        ranking = [a for a in ranking if a["total"] != 0]
        barras = [self._barra(a, separar) for a in ranking[: filtros.limite]]
        resto = ranking[filtros.limite :]
        otros = OtrosOut(total=sum(a["total"] for a in resto), articulos=len(resto))
        return ConsumoTableroOut(
            desde=desde,
            hasta=hasta,
            almacen=AlmacenRefOut(
                id=alcance.almacen.id, clave=alcance.almacen.clave, nombre=alcance.almacen.nombre
            )
            if alcance.almacen
            else None,
            categoria=CategoriaRefOut(id=categoria.id, nombre=categoria.nombre)
            if categoria
            else None,
            limite=filtros.limite,
            separar_por_almacen=separar,
            barras=barras,
            otros=otros,
            total_general=sum(b.total for b in barras) + otros.total,
            sin_registros=not ranking,
        )

    @staticmethod
    def _agrupar(filas: list) -> dict[uuid.UUID, dict]:
        """Suma las filas `(artículo, almacén)` por artículo."""
        articulos: dict[uuid.UUID, dict] = {}
        for f in filas:
            a = articulos.setdefault(
                f.articulo_id,
                {
                    "articulo_id": f.articulo_id,
                    "articulo": f.articulo,
                    "unidad": f.unidad,
                    "categoria_id": f.categoria_id,
                    "categoria": f.categoria,
                    "total": 0,
                    "almacenes": {},
                },
            )
            cantidad = int(f.cantidad)
            a["total"] += cantidad
            nombre, total = a["almacenes"].get(f.almacen_id, (f.almacen, 0))
            a["almacenes"][f.almacen_id] = (nombre, total + cantidad)
        return articulos

    @staticmethod
    def _barra(a: dict, separar: bool) -> BarraConsumoOut:
        por_almacen: list[BarraAlmacenOut] = []
        if separar:
            partes = [
                BarraAlmacenOut(almacen_id=almacen_id, almacen=nombre, total=total)
                for almacen_id, (nombre, total) in a["almacenes"].items()
                if total != 0
            ]
            por_almacen = sorted(partes, key=lambda p: (-p.total, p.almacen.casefold()))
        return BarraConsumoOut(
            articulo_id=a["articulo_id"],
            articulo=a["articulo"],
            categoria=CategoriaRefOut(id=a["categoria_id"], nombre=a["categoria"]),
            unidad=a["unidad"],
            total=a["total"],
            por_almacen=por_almacen,
        )
