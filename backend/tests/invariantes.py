"""Verificador de invariantes de datos (data-model.md, «Invariantes»), reutilizable.

    from tests.invariantes import verificar_invariantes, tomar_huella

    huella = tomar_huella(session)          # opcional: foto de vales, movimientos e inspecciones
    ... operar por la API ...
    verificar_invariantes(session, huella)  # AssertionError con TODAS las violaciones

Revisa la base completa de la prueba (línea base de datos de prueba más lo que la prueba operó).
Solo lee. No usa la API: consulta las tablas para no depender de lo que se quiere comprobar.

Qué comprueba (el número es el de la invariante en data-model.md):

  1     `existencia.cantidad` = entradas menos salidas de esa ubicación y artículo, según
        `movimiento`; el saldo guardado en cada movimiento coincide con repetirlos en orden; y en
        artículos por pieza la existencia es el número de piezas que hay ahí.
  2     Ninguna existencia negativa; PROVEEDOR no lleva existencia.
  3     Artículos por pieza: `pieza_id` y cantidad 1; por cantidad: `pieza_id` vacío.
  4     `pieza.ubicacion_id` es el destino de su último movimiento.
  5     `movimiento` y `vale` no cambian (solo `vale.estado`), contra la huella; el estado es
        coherente (CANCELADO solo con su vale de cancelación; traspaso EN_TRANSITO,
        RECIBIDO_CON_DIFERENCIAS o RECIBIDO según lo pendiente); todo movimiento nace con la
        fecha de su vale.
  6     Un valor de `codigo` aparece una sola vez (sin distinguir mayúsculas) y todo código de
        artículo, pieza y vale está registrado y apunta a lo que dice.
  8     Un trabajador no tiene vale NO_ADEUDO vigente con retornables en resguardo (al emitirlo
        y, si no hubo entregas después, hoy).
  9     Un vale que no es de no adeudo deja movimientos (no hay vales vacíos).
  10    `inspeccion`, `ajuste_vigencia` y `evento_pieza` solo se insertan, contra la huella.
  RG-06 Folios consecutivos sin huecos por (almacén, tipo), sin repetirse, con el contador
        `serie_folio` al día y la forma `CLAVE-PREFIJO-000123`.
"""

import re
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modulos.almacenes.models import Almacen, Ubicacion, UbicacionVirtual
from app.modulos.catalogo.models import Articulo, Codigo, Pieza
from app.modulos.inspecciones.models import AjusteVigencia, EventoPieza, Inspeccion
from app.modulos.movimientos.models import (
    PREFIJO_FOLIO,
    Existencia,
    Movimiento,
    SerieFolio,
    TipoVale,
    Vale,
)
from app.modulos.trabajadores.models import Trabajador

_TABLAS_INMUTABLES = {
    "vales": Vale.__table__,
    "movimientos": Movimiento.__table__,
    "inspecciones": Inspeccion.__table__,
    "ajustes_vigencia": AjusteVigencia.__table__,
    "eventos_pieza": EventoPieza.__table__,
}
# Del vale solo `estado` puede cambiar (invariante 5).
_COLUMNAS_QUE_PUEDEN_CAMBIAR = {"vales": {"estado"}}


@dataclass
class Huella:
    """Foto de las tablas que solo se insertan, para comparar después."""

    tablas: dict[str, dict[Any, dict[str, Any]]] = field(default_factory=dict)


def tomar_huella(session: Session) -> Huella:
    """Foto de vales, movimientos, inspecciones, ajustes y eventos de pieza (invariantes 5 y 10)."""
    session.flush()
    huella = Huella()
    for nombre, tabla in _TABLAS_INMUTABLES.items():
        filas = session.execute(select(tabla)).mappings().all()
        huella.tablas[nombre] = {fila["id"]: dict(fila) for fila in filas}
    return huella


# ------------------------------------------------------------------------ utilidades


def _ubicaciones(session: Session) -> dict[uuid.UUID, Ubicacion]:
    return {u.id: u for u in session.scalars(select(Ubicacion))}


def _nombre(ub: Ubicacion | None, almacenes: dict[uuid.UUID, str]) -> str:
    if ub is None:
        return "?"
    if ub.almacen_id:
        return f"almacén {almacenes.get(ub.almacen_id, '?')}"
    if ub.trabajador_id:
        return f"trabajador {ub.trabajador_id}"
    return f"ubicación {ub.virtual}"


def _movimientos_en_orden(session: Session) -> list[Any]:
    """Todos los movimientos, del primero al último (fecha del vale, luego renglón)."""
    return list(
        session.execute(
            select(Movimiento.__table__).order_by(
                Movimiento.creado_en, Movimiento.renglon, Movimiento.id
            )
        ).mappings()
    )


# ------------------------------------------------------------------ cada invariante


def _existencias_y_saldos(session: Session) -> list[str]:
    """Invariantes 1 y 2, el saldo guardado en cada movimiento y la cuenta de piezas."""
    errores: list[str] = []
    ubs = _ubicaciones(session)
    almacenes = {a.id: a.clave for a in session.scalars(select(Almacen))}
    proveedor = next((i for i, u in ubs.items() if u.virtual == UbicacionVirtual.PROVEEDOR), None)

    esperado: dict[tuple, int] = defaultdict(int)
    corriente: dict[tuple, int] = defaultdict(int)
    for m in _movimientos_en_orden(session):
        for ubicacion, signo, campo in (
            (m["origen_id"], -1, "saldo_origen"),
            (m["destino_id"], +1, "saldo_destino"),
        ):
            if ubicacion == proveedor:
                if m[campo] is not None:
                    errores.append(
                        f"[2] movimiento {m['id']}: PROVEEDOR no lleva existencia pero guardó "
                        f"{campo}={m[campo]}"
                    )
                continue
            llave = (ubicacion, m["articulo_id"])
            esperado[llave] += signo * m["cantidad"]
            corriente[llave] += signo * m["cantidad"]
            if m[campo] != corriente[llave]:
                errores.append(
                    f"[1] movimiento {m['id']} (renglón {m['renglon']}): {campo}={m[campo]} y "
                    f"repetido en orden da {corriente[llave]} en "
                    f"{_nombre(ubs.get(ubicacion), almacenes)}"
                )

    guardado: dict[tuple, int] = {}
    for fila in session.scalars(select(Existencia)):
        llave = (fila.ubicacion_id, fila.articulo_id)
        guardado[llave] = fila.cantidad
        if fila.cantidad < 0:
            errores.append(
                f"[2] existencia negativa ({fila.cantidad}) en "
                f"{_nombre(ubs.get(fila.ubicacion_id), almacenes)}, artículo {fila.articulo_id}"
            )
        if fila.ubicacion_id == proveedor:
            errores.append(f"[2] PROVEEDOR lleva existencia del artículo {fila.articulo_id}")
    for llave in set(esperado) | set(guardado):
        if llave[0] == proveedor:
            continue
        if guardado.get(llave, 0) != esperado.get(llave, 0):
            errores.append(
                f"[1] {_nombre(ubs.get(llave[0]), almacenes)}, artículo {llave[1]}: "
                f"existencia={guardado.get(llave, 0)}, movimientos suman {esperado.get(llave, 0)}"
            )

    # Una pieza ocupa 1 en la existencia de su ubicación (RG-05): cuenta de piezas por lugar.
    por_pieza = {a.id for a in session.scalars(select(Articulo)) if a.control == "PIEZA"}
    piezas_ahi: dict[tuple, int] = defaultdict(int)
    for ubicacion_id, articulo_id in session.execute(
        select(Pieza.ubicacion_id, Pieza.articulo_id).where(Pieza.ubicacion_id.is_not(None))
    ):
        if ubicacion_id != proveedor:
            piezas_ahi[(ubicacion_id, articulo_id)] += 1
    for llave in set(piezas_ahi) | {k for k in guardado if k[1] in por_pieza}:
        if guardado.get(llave, 0) != piezas_ahi.get(llave, 0):
            errores.append(
                f"[1] {_nombre(ubs.get(llave[0]), almacenes)}, artículo por pieza {llave[1]}: "
                f"existencia={guardado.get(llave, 0)} pero hay {piezas_ahi.get(llave, 0)} piezas"
            )
    return errores


def _piezas_y_cantidades(session: Session) -> list[str]:
    """Invariante 3: pieza_id solo en artículos por pieza, y con cantidad 1."""
    errores: list[str] = []
    control = {a.id: a.control for a in session.scalars(select(Articulo))}
    for m in session.execute(select(Movimiento.__table__)).mappings():
        es_pieza = control.get(m["articulo_id"]) == "PIEZA"
        if es_pieza and (m["pieza_id"] is None or m["cantidad"] != 1):
            errores.append(
                f"[3] movimiento {m['id']}: artículo por pieza sin pieza_id o con cantidad "
                f"{m['cantidad']}"
            )
        if not es_pieza and m["pieza_id"] is not None:
            errores.append(f"[3] movimiento {m['id']}: artículo por cantidad con pieza_id")
    return errores


def _ubicacion_de_las_piezas(session: Session) -> list[str]:
    """Invariante 4: la pieza está donde terminó su último movimiento."""
    errores: list[str] = []
    ultimo: dict[uuid.UUID, uuid.UUID] = {}
    for m in _movimientos_en_orden(session):
        if m["pieza_id"] is not None:
            ultimo[m["pieza_id"]] = m["destino_id"]
    for pieza in session.scalars(select(Pieza)):
        if pieza.id in ultimo and pieza.ubicacion_id != ultimo[pieza.id]:
            errores.append(
                f"[4] pieza {pieza.codigo}: ubicacion_id={pieza.ubicacion_id}, su último "
                f"movimiento terminó en {ultimo[pieza.id]}"
            )
        if pieza.id not in ultimo and pieza.ubicacion_id is not None:
            errores.append(f"[4] pieza {pieza.codigo} tiene ubicación y ningún movimiento")
    return errores


def _inmutables(session: Session, huella: Huella | None) -> list[str]:
    """Invariantes 5 y 10 contra la huella, y la coherencia del estado de los vales."""
    errores: list[str] = []
    if huella is not None:
        for nombre, tabla in _TABLAS_INMUTABLES.items():
            actuales = {f["id"]: dict(f) for f in session.execute(select(tabla)).mappings().all()}
            libres = _COLUMNAS_QUE_PUEDEN_CAMBIAR.get(nombre, set())
            for id_, antes in huella.tablas[nombre].items():
                ahora = actuales.get(id_)
                if ahora is None:
                    errores.append(f"[5/10] {nombre} {id_}: se borró")
                    continue
                cambiadas = sorted(c for c in antes if antes[c] != ahora[c] and c not in libres)
                if cambiadas:
                    errores.append(f"[5/10] {nombre} {id_}: cambió {cambiadas}")

    vales = {v.id: v for v in session.scalars(select(Vale))}
    cancelados_por: dict[uuid.UUID, int] = defaultdict(int)
    for v in vales.values():
        if v.tipo == TipoVale.CANCELACION and v.vale_origen_id:
            cancelados_por[v.vale_origen_id] += 1
    enviado: dict[uuid.UUID, int] = defaultdict(int)
    recibido: dict[uuid.UUID, int] = defaultdict(int)
    fecha_de_vale = {v.id: v.creado_en for v in vales.values()}
    for m in session.execute(select(Movimiento.__table__)).mappings():
        vale = vales[m["vale_id"]]
        if m["creado_en"] != fecha_de_vale[m["vale_id"]]:
            errores.append(f"[5] movimiento {m['id']}: su fecha no es la de su vale {vale.folio}")
        if vale.tipo == TipoVale.TRASPASO:
            enviado[vale.id] += m["cantidad"]
        elif vale.tipo == TipoVale.RECEPCION and vale.vale_origen_id:
            recibido[vale.vale_origen_id] += m["cantidad"]

    for v in vales.values():
        if v.estado == "CANCELADO":
            if cancelados_por[v.id] != 1:
                errores.append(
                    f"[5] vale {v.folio} está CANCELADO y tiene {cancelados_por[v.id]} vales de "
                    "cancelación"
                )
            continue
        if cancelados_por[v.id]:
            errores.append(f"[5] vale {v.folio} tiene su cancelación pero no está CANCELADO")
        if v.tipo == TipoVale.TRASPASO:
            pendiente = enviado[v.id] - recibido[v.id]
            if recibido[v.id] == 0:
                correcto = "EN_TRANSITO"
            elif pendiente > 0:
                correcto = "RECIBIDO_CON_DIFERENCIAS"
            else:
                correcto = "RECIBIDO"
            if pendiente < 0:
                errores.append(f"[5] traspaso {v.folio} recibió más de lo enviado")
            elif v.estado != correcto:
                errores.append(
                    f"[5] traspaso {v.folio}: estado {v.estado}, por lo recibido debería ser "
                    f"{correcto}"
                )
        elif v.estado != "EMITIDO":
            errores.append(f"[5] vale {v.folio} ({v.tipo}) tiene estado {v.estado}")
    return errores


def _codigos(session: Session) -> list[str]:
    """Invariante 6: un código identifica una sola cosa y todo lo escaneable está registrado."""
    errores: list[str] = []
    filas = list(session.scalars(select(Codigo)))
    registro: dict[str, tuple[str, uuid.UUID]] = {}
    for fila in filas:
        clave = fila.codigo.casefold()
        if clave in registro:
            errores.append(f"[6] el código {fila.codigo!r} aparece más de una vez")
        registro[clave] = (fila.tipo, fila.ref_id)

    def exigir(valor: str | None, tipo: str, ref_id: uuid.UUID, de_quien: str) -> None:
        if not valor:
            return
        encontrado = registro.get(valor.casefold())
        if encontrado is None:
            errores.append(f"[6] {de_quien}: el código {valor!r} no está registrado")
        elif encontrado != (tipo, ref_id):
            errores.append(
                f"[6] {de_quien}: el código {valor!r} está registrado como {encontrado}, "
                f"no como {(tipo, ref_id)}"
            )

    for a in session.scalars(select(Articulo)):
        exigir(a.codigo, "ARTICULO", a.id, f"artículo {a.codigo}")
    for p in session.scalars(select(Pieza)):
        exigir(p.codigo, "PIEZA", p.id, f"pieza {p.codigo}")
    for v in session.scalars(select(Vale)):
        exigir(v.token, "VALE", v.id, f"vale {v.folio} (token)")
        exigir(v.folio, "VALE", v.id, f"vale {v.folio} (folio)")
    existentes = {t.id for t in session.scalars(select(Trabajador))}
    for fila in filas:
        if fila.tipo == "TRABAJADOR" and fila.ref_id not in existentes:
            errores.append(
                f"[6] la credencial {fila.codigo!r} apunta a un trabajador que no existe"
            )
    return errores


def _no_adeudo(session: Session) -> list[str]:
    """Invariante 8: con retornables en resguardo no hay vale de no adeudo vigente."""
    errores: list[str] = []
    retornable = {a.id: a.retornable for a in session.scalars(select(Articulo))}
    ub_trabajador = {
        u.id: u.trabajador_id for u in session.scalars(select(Ubicacion)) if u.trabajador_id
    }
    por_trabajador: dict[uuid.UUID, list[Any]] = defaultdict(list)
    for m in _movimientos_en_orden(session):
        for lado, signo in (("origen_id", -1), ("destino_id", +1)):
            trabajador = ub_trabajador.get(m[lado])
            if trabajador is not None and retornable.get(m["articulo_id"]):
                por_trabajador[trabajador].append((m["creado_en"], m["articulo_id"], signo, m))

    vales = list(session.scalars(select(Vale).order_by(Vale.creado_en)))
    for v in vales:
        if v.tipo != TipoVale.NO_ADEUDO or v.trabajador_id is None:
            continue
        saldo: dict[uuid.UUID, int] = defaultdict(int)
        for fecha, articulo_id, signo, m in por_trabajador[v.trabajador_id]:
            if fecha <= v.creado_en:
                saldo[articulo_id] += signo * m["cantidad"]
        con_resguardo = {a: n for a, n in saldo.items() if n != 0}
        if con_resguardo:
            errores.append(
                f"[8] vale {v.folio}: el trabajador {v.trabajador_id} tenía retornables en "
                f"resguardo al emitirlo: {con_resguardo}"
            )
    # Hoy: el último no adeudo sigue vigente si no hubo entregas al trabajador después de él.
    ultimo_nad: dict[uuid.UUID, Vale] = {}
    for v in vales:
        if v.tipo == TipoVale.NO_ADEUDO and v.trabajador_id:
            ultimo_nad[v.trabajador_id] = v
    for trabajador, nad in ultimo_nad.items():
        hubo_entrega = any(
            v.tipo == TipoVale.ENTREGA
            and v.trabajador_id == trabajador
            and v.creado_en > nad.creado_en
            for v in vales
        )
        if hubo_entrega:
            continue
        saldo = defaultdict(int)
        for _fecha, articulo_id, signo, m in por_trabajador[trabajador]:
            saldo[articulo_id] += signo * m["cantidad"]
        if any(n != 0 for n in saldo.values()):
            errores.append(
                f"[8] trabajador {trabajador}: tiene el no adeudo {nad.folio} vigente y "
                "retornables en resguardo"
            )
    return errores


def _vales_vacios(session: Session) -> list[str]:
    """Invariante 9: un vale confirmado deja movimientos (salvo el de no adeudo, sin renglones)."""
    errores: list[str] = []
    con_movimientos = set(session.scalars(select(Movimiento.vale_id).distinct()))
    for v in session.scalars(select(Vale)):
        if v.tipo == TipoVale.NO_ADEUDO:
            if v.id in con_movimientos:
                errores.append(f"[9] el vale de no adeudo {v.folio} tiene movimientos")
        elif v.id not in con_movimientos:
            errores.append(f"[9] el vale {v.folio} ({v.tipo}) no tiene movimientos")
    return errores


_FOLIO = re.compile(r"^(?P<clave>[A-Z0-9]+)-(?P<prefijo>[A-Z]{3})-(?P<n>\d{6})$")


def _folios(session: Session) -> list[str]:
    """RG-06: consecutivo por (almacén, tipo) del vale, sin huecos ni repeticiones."""
    errores: list[str] = []
    claves = {a.id: a.clave for a in session.scalars(select(Almacen))}
    numeros: dict[tuple, list[int]] = defaultdict(list)
    for v in session.scalars(select(Vale)):
        coincide = _FOLIO.match(v.folio)
        if coincide is None:
            errores.append(f"[RG-06] el folio {v.folio!r} no tiene la forma CLAVE-TIPO-000123")
            continue
        if coincide["clave"] != claves.get(v.almacen_id):
            errores.append(
                f"[RG-06] el folio {v.folio} no es de su almacén {claves.get(v.almacen_id)}"
            )
        if coincide["prefijo"] != PREFIJO_FOLIO[TipoVale(v.tipo)]:
            errores.append(f"[RG-06] el folio {v.folio} no corresponde al tipo {v.tipo}")
        numeros[(v.almacen_id, v.tipo)].append(int(coincide["n"]))
    series = {(s.almacen_id, s.tipo): s.ultimo for s in session.scalars(select(SerieFolio))}
    for llave, lista in numeros.items():
        nombre = f"{claves.get(llave[0])}-{PREFIJO_FOLIO[TipoVale(llave[1])]}"
        if sorted(lista) != list(range(1, len(lista) + 1)):
            errores.append(f"[RG-06] folios {nombre} con huecos o repetidos: {sorted(lista)}")
        if series.get(llave) != max(lista):
            errores.append(
                f"[RG-06] serie_folio {nombre}: ultimo={series.get(llave)}, el folio mayor es "
                f"{max(lista)}"
            )
    for llave, ultimo in series.items():
        if llave not in numeros and ultimo != 0:
            errores.append(f"[RG-06] serie_folio {llave}: ultimo={ultimo} y no hay vales")
    return errores


# Cuántos vales hay: útil para que una prueba compruebe que no escribió nada.
def contar(session: Session) -> dict[str, int]:
    return {
        "vales": session.scalar(select(func.count()).select_from(Vale)) or 0,
        "movimientos": session.scalar(select(func.count()).select_from(Movimiento)) or 0,
    }


def violaciones(session: Session, huella: Huella | None = None) -> list[str]:
    """Todas las violaciones encontradas (lista vacía si todo cuadra)."""
    session.flush()
    session.expire_all()
    return [
        *_existencias_y_saldos(session),
        *_piezas_y_cantidades(session),
        *_ubicacion_de_las_piezas(session),
        *_inmutables(session, huella),
        *_codigos(session),
        *_no_adeudo(session),
        *_vales_vacios(session),
        *_folios(session),
    ]


def verificar_invariantes(session: Session, huella: Huella | None = None) -> None:
    """Falla con la lista completa de invariantes rotas; no hace nada si todo cuadra."""
    errores = violaciones(session, huella)
    assert not errores, "Invariantes rotas:\n- " + "\n- ".join(errores)
