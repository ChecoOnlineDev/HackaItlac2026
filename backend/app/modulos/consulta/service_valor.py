"""Valor del inventario (FEAT-012, VI-01 a VI-07). SOLO LEE; nunca hace `commit`.

El permiso `reportes.valor_inventario` lo exige el router; el alcance (AC-06) se decide aquí con la
misma lógica del tablero. Un artículo sin costo no suma (VI-04). Nunca sale el costo de un artículo.
"""

import uuid
from collections import defaultdict
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.tiempo import ahora_utc
from app.modulos.acceso.models import Usuario
from app.modulos.consulta.repository_valor import ValorRepository
from app.modulos.consulta.schemas_tablero import (
    AlcanceValorOut,
    ValorAlmacenOut,
    ValorCategoriaOut,
    ValorInventarioOut,
)
from app.modulos.consulta.service_tablero import TableroService

MAXIMO_CATEGORIAS = 6
CERO = Decimal("0.00")


def _texto(valor: Decimal) -> str:
    return f"{valor:.2f}"


def _valor(fila) -> Decimal:
    return Decimal(fila.costo) * int(fila.cantidad) if fila.costo is not None else CERO


class ValorInventarioService:
    def __init__(self, session: Session) -> None:
        self.valores = ValorRepository(session)
        self.tablero = TableroService(session)

    def valor(self, usuario: Usuario, almacen_id: uuid.UUID | None) -> ValorInventarioOut:
        alcance = self.tablero._alcance(usuario, almacen_id)
        nombre = alcance.almacen.nombre if alcance.almacen else None
        alcance_out = AlcanceValorOut(
            todos=alcance.es_todos,
            almacen_id=alcance.almacen.id if alcance.almacen else None,
            almacen_nombre=nombre or ("Almacenes asignados" if alcance.asignados else None),
        )
        if alcance.vacio:
            return ValorInventarioOut(
                alcance=alcance_out,
                total=_texto(CERO),
                en_almacen=_texto(CERO),
                en_resguardo=_texto(CERO),
                en_transito=None,
                articulos_sin_costo=0,
                unidades_sin_costo=0,
                por_categoria=[],
                por_almacen=[],
                generado_en=ahora_utc(),
            )
        x = alcance.almacen_id
        filas_almacen = self.valores.en_almacen(x)
        filas_resguardo = self.valores.en_resguardo(x)
        # El tránsito no se atribuye a un almacén: solo se da en el alcance «todos».
        filas_transito = self.valores.en_transito() if alcance.es_todos else None

        en_almacen = sum((_valor(f) for f in filas_almacen), CERO)
        en_resguardo = sum((_valor(f) for f in filas_resguardo), CERO)
        en_transito = (
            sum((_valor(f) for f in filas_transito), CERO) if filas_transito is not None else None
        )
        todas = [*filas_almacen, *filas_resguardo, *(filas_transito or [])]

        sin_costo = [f for f in todas if f.costo is None]
        por_categoria: dict[str, Decimal] = defaultdict(lambda: CERO)
        unidades_categoria: dict[str, int] = defaultdict(int)
        for f in todas:
            por_categoria[f.categoria] += _valor(f)
            unidades_categoria[f.categoria] += int(f.cantidad)

        return ValorInventarioOut(
            alcance=alcance_out,
            total=_texto(en_almacen + en_resguardo + (en_transito or CERO)),
            en_almacen=_texto(en_almacen),
            en_resguardo=_texto(en_resguardo),
            en_transito=_texto(en_transito) if en_transito is not None else None,
            articulos_sin_costo=len({f.articulo_id for f in sin_costo}),
            unidades_sin_costo=sum(int(f.cantidad) for f in sin_costo),
            por_categoria=self._categorias(por_categoria, unidades_categoria),
            por_almacen=self._almacenes(filas_almacen, filas_resguardo, alcance.asignados)
            if alcance.es_todos or alcance.asignados
            else [],
            generado_en=ahora_utc(),
            unidades_en_almacen=sum(int(f.cantidad) for f in filas_almacen),
            unidades_en_resguardo=sum(int(f.cantidad) for f in filas_resguardo),
            unidades_total=sum(int(f.cantidad) for f in todas),
        )

    @staticmethod
    def _categorias(
        valores: dict[str, Decimal], unidades: dict[str, int]
    ) -> list[ValorCategoriaOut]:
        orden = sorted(valores.items(), key=lambda kv: (-kv[1], kv[0].casefold()))
        if len(orden) > MAXIMO_CATEGORIAS:
            resto = sum((v for _, v in orden[MAXIMO_CATEGORIAS:]), CERO)
            unidades["Otras"] = sum(unidades[c] for c, _ in orden[MAXIMO_CATEGORIAS:])
            orden = [*orden[:MAXIMO_CATEGORIAS], ("Otras", resto)]
        return [
            ValorCategoriaOut(categoria=c, valor=_texto(v), unidades=unidades[c]) for c, v in orden
        ]

    def _almacenes(
        self, filas_almacen: list, filas_resguardo: list, asignados=None
    ) -> list[ValorAlmacenOut]:
        en_almacen: dict[uuid.UUID, Decimal] = defaultdict(lambda: CERO)
        en_resguardo: dict[uuid.UUID, Decimal] = defaultdict(lambda: CERO)
        unidades_almacen: dict[uuid.UUID, int] = defaultdict(int)
        unidades_resguardo: dict[uuid.UUID, int] = defaultdict(int)
        for f in filas_almacen:
            en_almacen[f.almacen_id] += _valor(f)
            unidades_almacen[f.almacen_id] += int(f.cantidad)
        for f in filas_resguardo:
            if f.almacen_id is not None:
                en_resguardo[f.almacen_id] += _valor(f)
                unidades_resguardo[f.almacen_id] += int(f.cantidad)
        return [
            ValorAlmacenOut(
                almacen_id=a.id,
                nombre=a.nombre,
                en_almacen=_texto(en_almacen[a.id]),
                en_resguardo=_texto(en_resguardo[a.id]),
                total=_texto(en_almacen[a.id] + en_resguardo[a.id]),
                unidades_en_almacen=unidades_almacen[a.id],
                unidades_en_resguardo=unidades_resguardo[a.id],
                unidades_total=unidades_almacen[a.id] + unidades_resguardo[a.id],
            )
            for a in self.valores.almacenes()
            if asignados is None or a.id in asignados
        ]
