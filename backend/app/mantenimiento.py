"""Mantenimiento por línea de comandos: verificar consistencia y reconstruir existencias.

    uv run python -m app.mantenimiento verificar
    uv run python -m app.mantenimiento reconstruir-existencias --simular
    uv run python -m app.mantenimiento reconstruir-existencias --aplicar
    uv run python -m app.mantenimiento sembrar-almacenes

`verificar` es de SOLO LECTURA. Compara la base real con las invariantes de
`docs/architecture/data-model.md` y sale con código 0 si todo cuadra, o con 1 listando las
diferencias en español:

  1. existencia = suma de movimientos por (ubicación, artículo)       (invariante 1)
  2. ninguna existencia es negativa                                    (invariante 2)
  3. pieza con `pieza_id` y artículo por cantidad sin él               (invariante 3)
  4. `pieza.ubicacion_id` = destino de su último movimiento            (invariante 4)
  5. vales: un vale cancelado tiene su cancelación y viceversa         (invariante 5)
  6. un código aparece una sola vez y apunta a algo que existe         (invariante 6)
  7. trabajador inactivo: sin retornables y con su no adeudo vigente   (invariante 8)
  8. folios consecutivos y sin huecos por (almacén, tipo), igual al contador `serie_folio` (RG-06)

`reconstruir-existencias` calcula lo que las existencias DEBERÍAN valer desde la bitácora
(`movimiento`). Con `--simular` solo muestra las diferencias y no escribe.

`--aplicar` es la ÚNICA operación que escribe `existencia` fuera del motor de `movimientos`
(AGENTS.md: "solo el módulo `movimientos` escribe..."). Se justifica como recuperación ante un
daño ya ocurrido (por ejemplo, alguien editó la base a mano o se restauró una copia parcial):
la bitácora es la verdad y las existencias son su suma guardada (ADR-001). Por eso:

  - solo existe por línea de comandos; no hay endpoint ni pantalla;
  - exige escribir una frase de confirmación y no corre sin terminal interactiva;
  - nunca toca `movimiento` ni `vale`, ni la ubicación de las piezas;
  - se niega a escribir si la bitácora arrojaría una existencia negativa (primero hay que
    resolver esa diferencia);
  - deja un renglón en `auditoria` (`mantenimiento.reconstruir_existencias`) con lo que cambió,
    en la misma transacción.

`sembrar-almacenes` (FEAT-008, 4.1.5) crea la red inicial del reto (Kepler, Contratistas, Midrex,
HYL, Laminador y Minas) SOLO si no existe ningún almacén, con sus ubicaciones, las ubicaciones
virtuales que falten y su renglón de auditoría (`almacen.crear`), todo en una transacción. Si ya
hay alguno, no hace nada y lo dice: es seguro de repetir.

Este módulo está aislado: no importa servicios de otros módulos, solo sus modelos.
"""

import argparse
import sys
import uuid
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.modelos_registro  # noqa: F401
from app.db import get_sessionmaker
from app.modulos.almacenes.models import (
    Almacen,
    TipoAlmacen,
    TipoUbicacion,
    Ubicacion,
    UbicacionVirtual,
)
from app.modulos.auditoria.models import Auditoria
from app.modulos.catalogo.models import Articulo, Codigo, Control, Pieza, TipoCodigo
from app.modulos.movimientos.models import (
    PREFIJO_FOLIO,
    EstadoVale,
    Existencia,
    Movimiento,
    SerieFolio,
    TipoVale,
    Vale,
)
from app.modulos.trabajadores.models import EstadoTrabajador, Trabajador

FRASE_CONFIRMACION = "REESCRIBIR EXISTENCIAS"
MAXIMO_POR_REGLA = 25  # renglones que se imprimen por tipo de diferencia (el resto se cuenta)


@dataclass(frozen=True)
class Diferencia:
    """Una diferencia encontrada. `invariante` es el número de data-model.md (o `RG-06`)."""

    invariante: str
    detalle: str


# ------------------------------------------------------------------ etiquetas legibles


class _Etiquetas:
    """Nombres que entiende una persona: clave del almacén, número de empleado, código."""

    def __init__(self, session: Session) -> None:
        self.ubicacion: dict[uuid.UUID, str] = {}
        self.proveedor: uuid.UUID | None = None
        almacenes = dict(session.execute(select(Almacen.id, Almacen.clave)).all())
        trabajadores = dict(
            session.execute(select(Trabajador.id, Trabajador.numero_empleado)).all()
        )
        for u in session.execute(select(Ubicacion)).scalars():
            if u.almacen_id:
                self.ubicacion[u.id] = f"almacén {almacenes.get(u.almacen_id, '?')}"
            elif u.trabajador_id:
                self.ubicacion[u.id] = f"trabajador {trabajadores.get(u.trabajador_id, '?')}"
            else:
                self.ubicacion[u.id] = f"ubicación {u.virtual}"
                if u.virtual == UbicacionVirtual.PROVEEDOR:
                    self.proveedor = u.id
        self.articulo = dict(session.execute(select(Articulo.id, Articulo.codigo)).all())

    def lugar(self, ubicacion_id: uuid.UUID | None) -> str:
        if ubicacion_id is None:
            return "ningún lugar"
        return self.ubicacion.get(ubicacion_id, f"ubicación desconocida {ubicacion_id}")

    def cosa(self, articulo_id: uuid.UUID) -> str:
        return f"artículo {self.articulo.get(articulo_id, articulo_id)}"


# ---------------------------------------------------------------- cálculo desde la bitácora


def existencias_esperadas(
    session: Session, proveedor_id: uuid.UUID | None
) -> dict[tuple[uuid.UUID, uuid.UUID], int]:
    """Suma de movimientos por (ubicación, artículo): entradas menos salidas. PROVEEDOR no lleva
    existencia (data-model.md), así que se omite."""
    total: dict[tuple[uuid.UUID, uuid.UUID], int] = defaultdict(int)
    entradas = session.execute(
        select(
            Movimiento.destino_id, Movimiento.articulo_id, func.sum(Movimiento.cantidad)
        ).group_by(Movimiento.destino_id, Movimiento.articulo_id)
    ).all()
    for ubicacion_id, articulo_id, cantidad in entradas:
        total[(ubicacion_id, articulo_id)] += int(cantidad)
    salidas = session.execute(
        select(
            Movimiento.origen_id, Movimiento.articulo_id, func.sum(Movimiento.cantidad)
        ).group_by(Movimiento.origen_id, Movimiento.articulo_id)
    ).all()
    for ubicacion_id, articulo_id, cantidad in salidas:
        total[(ubicacion_id, articulo_id)] -= int(cantidad)
    if proveedor_id is not None:
        for clave in [k for k in total if k[0] == proveedor_id]:
            del total[clave]
    return dict(total)


def _existencias_guardadas(session: Session) -> dict[tuple[uuid.UUID, uuid.UUID], int]:
    filas = session.execute(
        select(Existencia.ubicacion_id, Existencia.articulo_id, Existencia.cantidad)
    ).all()
    return {(u, a): int(c) for u, a, c in filas}


# ------------------------------------------------------------------------- verificaciones


def _verificar_existencias(session: Session, et: _Etiquetas) -> list[Diferencia]:
    esperadas = existencias_esperadas(session, et.proveedor)
    guardadas = _existencias_guardadas(session)
    salida: list[Diferencia] = []
    for clave in sorted(esperadas.keys() | guardadas.keys(), key=lambda k: (str(k[0]), str(k[1]))):
        debe = esperadas.get(clave, 0)
        hay = guardadas.get(clave, 0)
        lugar, cosa = et.lugar(clave[0]), et.cosa(clave[1])
        if debe < 0:
            salida.append(
                Diferencia(
                    "2",
                    f"La bitácora deja {debe} (negativo) de {cosa} en {lugar}: salió más de lo "
                    "que entró.",
                )
            )
        if hay < 0:
            salida.append(Diferencia("2", f"Existencia negativa ({hay}) de {cosa} en {lugar}."))
        if debe != hay:
            salida.append(
                Diferencia(
                    "1",
                    f"{cosa} en {lugar}: la existencia guardada es {hay} pero los movimientos "
                    f"suman {debe}.",
                )
            )
    return salida


def _verificar_piezas(session: Session, et: _Etiquetas) -> list[Diferencia]:
    salida: list[Diferencia] = []
    # Invariante 3: pieza_id solo en artículos por pieza, y siempre en ellos.
    sin_pieza = session.execute(
        select(Vale.folio, Movimiento.renglon, Articulo.codigo)
        .join(Vale, Vale.id == Movimiento.vale_id)
        .join(Articulo, Articulo.id == Movimiento.articulo_id)
        .where(Articulo.control == Control.PIEZA, Movimiento.pieza_id.is_(None))
    ).all()
    for folio, renglon, codigo in sin_pieza:
        salida.append(
            Diferencia(
                "3",
                f"Vale {folio}, renglón {renglon}: el artículo {codigo} es por pieza pero el "
                "movimiento no dice cuál pieza.",
            )
        )
    con_pieza = session.execute(
        select(Vale.folio, Movimiento.renglon, Articulo.codigo)
        .join(Vale, Vale.id == Movimiento.vale_id)
        .join(Articulo, Articulo.id == Movimiento.articulo_id)
        .where(Articulo.control == Control.CANTIDAD, Movimiento.pieza_id.is_not(None))
    ).all()
    for folio, renglon, codigo in con_pieza:
        salida.append(
            Diferencia(
                "3",
                f"Vale {folio}, renglón {renglon}: el artículo {codigo} es por cantidad pero el "
                "movimiento nombra una pieza.",
            )
        )

    # Invariante 4: la pieza está en el destino de su último movimiento.
    ultimo: dict[uuid.UUID, uuid.UUID] = {}
    movs = session.execute(
        select(Movimiento.pieza_id, Movimiento.destino_id)
        .where(Movimiento.pieza_id.is_not(None))
        .order_by(Movimiento.creado_en, Movimiento.renglon)
    ).all()
    for pieza_id, destino_id in movs:
        ultimo[pieza_id] = destino_id
    for pieza in session.execute(select(Pieza)).scalars():
        debe = ultimo.get(pieza.id)
        if pieza.ubicacion_id != debe:
            salida.append(
                Diferencia(
                    "4",
                    f"Pieza {pieza.codigo}: está en {et.lugar(pieza.ubicacion_id)} pero su "
                    f"último movimiento la dejó en {et.lugar(debe)}.",
                )
            )
    return salida


def _verificar_vales_cancelados(session: Session) -> list[Diferencia]:
    salida: list[Diferencia] = []
    vales = session.execute(
        select(Vale.id, Vale.folio, Vale.tipo, Vale.estado, Vale.vale_origen_id)
    )
    por_id = {v.id: v for v in vales}
    canceladores: dict[uuid.UUID, list[str]] = defaultdict(list)
    for v in por_id.values():
        if v.tipo == TipoVale.CANCELACION:
            if v.vale_origen_id is None or v.vale_origen_id not in por_id:
                salida.append(
                    Diferencia("5", f"La cancelación {v.folio} no apunta a un vale que exista.")
                )
                continue
            canceladores[v.vale_origen_id].append(v.folio)
    for v in por_id.values():
        n = len(canceladores.get(v.id, []))
        if v.estado == EstadoVale.CANCELADO and n == 0:
            salida.append(
                Diferencia("5", f"El vale {v.folio} está cancelado sin vale de cancelación.")
            )
        elif v.estado != EstadoVale.CANCELADO and n > 0:
            folios = ", ".join(canceladores[v.id])
            salida.append(
                Diferencia(
                    "5",
                    f"El vale {v.folio} tiene la cancelación {folios} pero no figura cancelado.",
                )
            )
        elif n > 1:
            salida.append(
                Diferencia(
                    "5",
                    f"El vale {v.folio} tiene {n} cancelaciones ({', '.join(canceladores[v.id])}); "
                    "solo puede tener una.",
                )
            )
    return salida


def _verificar_codigos(session: Session) -> list[Diferencia]:
    """Invariante 6. La llave primaria ya impide repetir un código; aquí se revisa que cada código
    apunte a algo que existe, que lo que existe tenga su código y que no haya dos códigos con
    el mismo texto salvo por mayúsculas (la colación los trataría como uno)."""
    salida: list[Diferencia] = []
    existentes = {
        TipoCodigo.ARTICULO: dict(session.execute(select(Articulo.id, Articulo.codigo)).all()),
        TipoCodigo.PIEZA: dict(session.execute(select(Pieza.id, Pieza.codigo)).all()),
        TipoCodigo.VALE: dict(session.execute(select(Vale.id, Vale.folio)).all()),
        TipoCodigo.TRABAJADOR: dict(
            session.execute(select(Trabajador.id, Trabajador.numero_empleado)).all()
        ),
    }
    codigos = session.execute(select(Codigo.codigo, Codigo.tipo, Codigo.ref_id)).all()
    vistos: dict[str, str] = {}
    registrados: dict[str, set[uuid.UUID]] = defaultdict(set)
    for codigo, tipo, ref_id in codigos:
        clave = codigo.casefold()
        if clave in vistos and vistos[clave] != codigo:
            salida.append(
                Diferencia("6", f"Los códigos «{vistos[clave]}» y «{codigo}» son el mismo.")
            )
        vistos[clave] = codigo
        registrados[tipo].add(ref_id)
        if ref_id not in existentes.get(tipo, {}):
            salida.append(
                Diferencia("6", f"El código «{codigo}» ({tipo}) apunta a algo que ya no existe.")
            )
    for tipo in (TipoCodigo.ARTICULO, TipoCodigo.PIEZA, TipoCodigo.VALE):
        for ref_id, texto in existentes[tipo].items():
            if ref_id not in registrados[tipo]:
                salida.append(
                    Diferencia("6", f"{tipo.capitalize()} {texto}: no tiene su código registrado.")
                )
    return salida


def _retornables_en_posesion(session: Session, ubicacion_id: uuid.UUID, hasta=None) -> int:
    """Retornables que la ubicación (un trabajador) recibió menos los que devolvió."""

    def suma(columna) -> int:
        q = (
            select(func.coalesce(func.sum(Movimiento.cantidad), 0))
            .join(Articulo, Articulo.id == Movimiento.articulo_id)
            .where(columna == ubicacion_id, Articulo.retornable.is_(True))
        )
        if hasta is not None:
            q = q.where(Movimiento.creado_en <= hasta)
        return int(session.execute(q).scalar_one())

    return suma(Movimiento.destino_id) - suma(Movimiento.origen_id)


def _verificar_no_adeudo(session: Session) -> list[Diferencia]:
    """Invariante 8 y B-08: un trabajador Inactivo no tiene retornables en resguardo y tiene un
    vale de no adeudo vigente (no cancelado); un no adeudo vigente no se emitió con equipo
    pendiente."""
    salida: list[Diferencia] = []
    vigentes: dict[uuid.UUID, list] = defaultdict(list)
    for vale in session.execute(
        select(Vale).where(Vale.tipo == TipoVale.NO_ADEUDO, Vale.estado != EstadoVale.CANCELADO)
    ).scalars():
        vigentes[vale.trabajador_id].append(vale)

    ubicaciones = dict(
        session.execute(
            select(Ubicacion.trabajador_id, Ubicacion.id).where(
                Ubicacion.trabajador_id.is_not(None)
            )
        ).all()
    )
    for t in session.execute(select(Trabajador)).scalars():
        ubicacion_id = ubicaciones.get(t.id)
        if ubicacion_id is None:
            continue
        if t.estado == EstadoTrabajador.INACTIVO:
            if not vigentes.get(t.id):
                salida.append(
                    Diferencia(
                        "8",
                        f"El trabajador {t.numero_empleado} está Inactivo y no tiene vale de "
                        "no adeudo vigente.",
                    )
                )
            n = _retornables_en_posesion(session, ubicacion_id)
            if n > 0:
                salida.append(
                    Diferencia(
                        "8",
                        f"El trabajador {t.numero_empleado} está Inactivo pero tiene {n} "
                        "pieza(s) retornable(s) en resguardo.",
                    )
                )
        for vale in vigentes.get(t.id, []):
            n = _retornables_en_posesion(session, ubicacion_id, hasta=vale.creado_en)
            if n > 0:
                salida.append(
                    Diferencia(
                        "8",
                        f"El vale de no adeudo {vale.folio} se emitió con {n} retornable(s) "
                        f"todavía en resguardo del trabajador {t.numero_empleado}.",
                    )
                )
    return salida


def _verificar_folios(session: Session) -> list[Diferencia]:
    salida: list[Diferencia] = []
    claves = dict(session.execute(select(Almacen.id, Almacen.clave)).all())
    numeros: dict[tuple[uuid.UUID, str], list[int]] = defaultdict(list)
    for v in session.execute(select(Vale.id, Vale.folio, Vale.almacen_id, Vale.tipo)).all():
        clave = claves.get(v.almacen_id, "?")
        prefijo = PREFIJO_FOLIO.get(TipoVale(v.tipo), "?")
        partes = v.folio.split("-")
        esperado = f"{clave}-{prefijo}-"
        if len(partes) != 3 or not v.folio.startswith(esperado) or not partes[2].isdigit():
            salida.append(
                Diferencia("RG-06", f"El folio {v.folio} no tiene la forma {esperado}000000.")
            )
            continue
        numeros[(v.almacen_id, v.tipo)].append(int(partes[2]))
    contadores = {
        (s.almacen_id, s.tipo): s.ultimo for s in session.execute(select(SerieFolio)).scalars()
    }
    for llave in sorted(numeros.keys() | contadores.keys(), key=lambda k: (str(k[0]), k[1])):
        lista = sorted(numeros.get(llave, []))
        nombre = f"{claves.get(llave[0], '?')}-{PREFIJO_FOLIO.get(TipoVale(llave[1]), '?')}"
        if len(lista) != len(set(lista)):
            salida.append(Diferencia("RG-06", f"Hay folios repetidos en la serie {nombre}."))
        faltan = sorted(set(range(1, (lista[-1] if lista else 0) + 1)) - set(lista))
        if faltan:
            muestra = ", ".join(str(n) for n in faltan[:10])
            salida.append(
                Diferencia("RG-06", f"A la serie {nombre} le faltan los consecutivos: {muestra}.")
            )
        ultimo_real = lista[-1] if lista else 0
        if contadores.get(llave, 0) != ultimo_real:
            salida.append(
                Diferencia(
                    "RG-06",
                    f"El contador de la serie {nombre} marca {contadores.get(llave, 0)} pero el "
                    f"último vale es el {ultimo_real}.",
                )
            )
    return salida


def verificar(session: Session) -> list[Diferencia]:
    """Corre todas las comprobaciones (solo lectura) y devuelve las diferencias encontradas."""
    et = _Etiquetas(session)
    diferencias: list[Diferencia] = []
    diferencias += _verificar_existencias(session, et)
    diferencias += _verificar_piezas(session, et)
    diferencias += _verificar_vales_cancelados(session)
    diferencias += _verificar_codigos(session)
    diferencias += _verificar_no_adeudo(session)
    diferencias += _verificar_folios(session)
    return diferencias


# ----------------------------------------------------------------------- reconstrucción


@dataclass(frozen=True)
class CambioExistencia:
    ubicacion_id: uuid.UUID
    articulo_id: uuid.UUID
    antes: int
    despues: int


def calcular_reconstruccion(session: Session) -> list[CambioExistencia]:
    """Lo que habría que cambiar para que `existencia` sea la suma de la bitácora. No escribe."""
    et = _Etiquetas(session)
    esperadas = existencias_esperadas(session, et.proveedor)
    guardadas = _existencias_guardadas(session)
    cambios = []
    for clave in sorted(esperadas.keys() | guardadas.keys(), key=lambda k: (str(k[0]), str(k[1]))):
        debe, hay = esperadas.get(clave, 0), guardadas.get(clave, 0)
        if debe != hay:
            cambios.append(CambioExistencia(clave[0], clave[1], hay, debe))
    return cambios


def aplicar_reconstruccion(session: Session, cambios: list[CambioExistencia]) -> int:
    """Escribe los cambios y deja su renglón de auditoría. Hace `flush`, no `commit`.

    Se niega si algún valor calculado es negativo (la bitácora misma está mal)."""
    negativos = [c for c in cambios if c.despues < 0]
    if negativos:
        raise ValueError(
            f"{len(negativos)} existencia(s) saldrían negativas: la bitácora tiene un problema "
            "que debe revisarse antes de reconstruir."
        )
    for c in cambios:
        fila = session.get(Existencia, (c.ubicacion_id, c.articulo_id))
        if fila is None:
            session.add(
                Existencia(
                    ubicacion_id=c.ubicacion_id, articulo_id=c.articulo_id, cantidad=c.despues
                )
            )
        else:
            fila.cantidad = c.despues
    session.add(
        Auditoria(
            usuario_id=None,
            accion="mantenimiento.reconstruir_existencias",
            entidad="existencia",
            entidad_id=None,
            antes=None,
            despues={
                "cambios": [
                    {
                        "ubicacion_id": str(c.ubicacion_id),
                        "articulo_id": str(c.articulo_id),
                        "antes": c.antes,
                        "despues": c.despues,
                    }
                    for c in cambios
                ]
            },
        )
    )
    session.flush()
    return len(cambios)


# ------------------------------------------------------------------------ línea de comandos


def _imprimir_diferencias(diferencias: Sequence[Diferencia], salida: Callable[[str], None]) -> None:
    por_regla: dict[str, list[Diferencia]] = defaultdict(list)
    for d in diferencias:
        por_regla[d.invariante].append(d)
    for regla in sorted(por_regla):
        lista = por_regla[regla]
        salida(f"\n[{_nombre_regla(regla)}] {len(lista)} diferencia(s)")
        for d in lista[:MAXIMO_POR_REGLA]:
            salida(f"  - {d.detalle}")
        if len(lista) > MAXIMO_POR_REGLA:
            salida(f"  ... y {len(lista) - MAXIMO_POR_REGLA} más.")


def _nombre_regla(regla: str) -> str:
    return "Folios (RG-06)" if regla == "RG-06" else f"Invariante {regla}"


# (clave, nombre, tipo, clave del padre). Kepler surte a Contratistas; Contratistas, a las áreas.
RED_INICIAL = (
    ("KEP", "Kepler", TipoAlmacen.CENTRAL, None),
    ("CON", "Contratistas", TipoAlmacen.SUBALMACEN, "KEP"),
    ("MID", "Midrex", TipoAlmacen.PROYECTO, "CON"),
    ("HYL", "HYL", TipoAlmacen.PROYECTO, "CON"),
    ("LAM", "Laminador", TipoAlmacen.PROYECTO, "CON"),
    ("MIN", "Minas", TipoAlmacen.PROYECTO, "CON"),
)


def sembrar_almacenes(session: Session) -> list[str]:
    """Crea la red inicial si no hay ningún almacén y devuelve las claves creadas; con alguno ya
    existente no escribe nada y devuelve `[]`. Hace `flush`, no `commit`."""
    if session.scalar(select(func.count()).select_from(Almacen)):
        return []
    creados: dict[str, Almacen] = {}
    for clave, nombre, tipo, clave_padre in RED_INICIAL:
        padre = creados[clave_padre] if clave_padre else None
        almacen = Almacen(
            clave=clave, nombre=nombre, tipo=tipo, padre_id=padre.id if padre else None
        )
        session.add(almacen)
        session.flush()
        session.add(Ubicacion(tipo=TipoUbicacion.ALMACEN, almacen_id=almacen.id))
        session.add(
            Auditoria(
                usuario_id=None,
                accion="almacen.crear",
                entidad="almacen",
                entidad_id=str(almacen.id),
                antes=None,
                despues={
                    "codigo": clave,
                    "nombre": nombre,
                    "tipo": str(tipo),
                    "padre_id": str(padre.id) if padre else None,
                    "origen": "mantenimiento.sembrar-almacenes",
                },
            )
        )
        creados[clave] = almacen
    # Las ubicaciones virtuales (proveedor, en tránsito, consumido y baja) también hacen falta.
    existentes = set(
        session.scalars(select(Ubicacion.virtual).where(Ubicacion.virtual.is_not(None)))
    )
    for virtual in UbicacionVirtual:
        if virtual.value not in existentes:
            session.add(Ubicacion(tipo=TipoUbicacion.VIRTUAL, virtual=virtual.value))
    session.flush()
    return list(creados)


def _comando_sembrar(session: Session, salida: Callable[[str], None]) -> int:
    creados = sembrar_almacenes(session)
    if not creados:
        salida("Ya hay almacenes: no se creó nada.")
        return 0
    session.commit()
    salida(f"Listo: se crearon {len(creados)} almacenes ({', '.join(creados)}).")
    return 0


def _comando_verificar(session: Session, salida: Callable[[str], None]) -> int:
    diferencias = verificar(session)
    if not diferencias:
        salida("Todo cuadra: no se encontraron diferencias.")
        return 0
    salida(f"Se encontraron {len(diferencias)} diferencia(s).")
    _imprimir_diferencias(diferencias, salida)
    return 1


def _comando_reconstruir(
    session: Session,
    *,
    aplicar: bool,
    salida: Callable[[str], None],
    pedir: Callable[[str], str],
    interactivo: bool,
) -> int:
    cambios = calcular_reconstruccion(session)
    et = _Etiquetas(session)
    if not cambios:
        salida("Las existencias ya son iguales a la suma de la bitácora. No hay nada que cambiar.")
        return 0
    salida(f"{len(cambios)} existencia(s) difieren de la suma de la bitácora:")
    for c in cambios[:MAXIMO_POR_REGLA]:
        salida(
            f"  - {et.cosa(c.articulo_id)} en {et.lugar(c.ubicacion_id)}: "
            f"guardada {c.antes}, debería ser {c.despues}."
        )
    if len(cambios) > MAXIMO_POR_REGLA:
        salida(f"  ... y {len(cambios) - MAXIMO_POR_REGLA} más.")
    if not aplicar:
        salida("\nSimulación: no se escribió nada. Para corregirlas use --aplicar.")
        return 1
    if any(c.despues < 0 for c in cambios):
        salida("\nNo se aplica: la bitácora arrojaría existencias negativas. Revise primero.")
        return 2
    if not interactivo:
        salida("\nNo se aplica: se necesita una terminal interactiva para confirmar.")
        return 2
    salida(
        "\nEsto reescribe la tabla de existencias a partir de la bitácora y queda en la auditoría."
        "\nHaga un respaldo antes (scripts/respaldo.sh)."
    )
    try:
        respuesta = pedir(f"Para continuar escriba «{FRASE_CONFIRMACION}»: ").strip()
    except EOFError:  # sin terminal que responda
        respuesta = ""
    if respuesta != FRASE_CONFIRMACION:
        salida("Confirmación incorrecta: no se escribió nada.")
        return 2
    n = aplicar_reconstruccion(session, cambios)
    session.commit()
    salida(f"Listo: se corrigieron {n} existencia(s). Vuelva a correr «verificar».")
    return 0


def main(
    argv: Sequence[str] | None = None,
    *,
    session: Session | None = None,
    salida: Callable[[str], None] = print,
    pedir: Callable[[str], str] = input,
    interactivo: bool | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.mantenimiento",
        description="Verificación de consistencia y mantenimiento de la base de datos.",
    )
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("verificar", help="Compara la base con sus invariantes (solo lectura).")
    rec = sub.add_parser(
        "reconstruir-existencias", help="Recalcula las existencias desde la bitácora."
    )
    sub.add_parser(
        "sembrar-almacenes",
        help="Crea Kepler, Contratistas, Midrex, HYL, Laminador y Minas si no hay ningún almacén.",
    )
    grupo = rec.add_mutually_exclusive_group(required=True)
    grupo.add_argument(
        "--simular", action="store_true", help="Muestra las diferencias; no escribe."
    )
    grupo.add_argument("--aplicar", action="store_true", help="Escribe, con confirmación.")
    args = parser.parse_args(argv)

    if interactivo is None:
        interactivo = sys.stdin.isatty()

    def correr(s: Session) -> int:
        if args.comando == "verificar":
            return _comando_verificar(s, salida)
        if args.comando == "sembrar-almacenes":
            return _comando_sembrar(s, salida)
        return _comando_reconstruir(
            s, aplicar=args.aplicar, salida=salida, pedir=pedir, interactivo=interactivo
        )

    if session is not None:
        return correr(session)
    with get_sessionmaker()() as s:
        try:
            return correr(s)
        except Exception:
            s.rollback()
            raise


if __name__ == "__main__":
    sys.exit(main())
