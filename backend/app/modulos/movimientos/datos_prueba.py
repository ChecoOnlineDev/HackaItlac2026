"""Datos de prueba de `movimientos`: la mercancía entra por Kepler y se reparte por traspaso.

La mercancía nace solo con una entrada (RG-01, I-01) y esa entrada es siempre a Kepler (EK-01,
EK-02): este script no inserta saldos; confirma con el servicio del módulo un vale de ENTRADA a
Kepler y, de ahí, traspasos Kepler -> Contratistas y Contratistas -> proyecto (X-03), cada uno
recibido por el supervisor del destino. El EPP de consumo (casco, lentes, guantes, tapones,
respirador, cachucha...) queda en Kepler y Contratistas; a los almacenes de proyecto solo se les
surte herramienta (FEAT-011, sección E). Es idempotente: cada vale lleva un `id_cliente` fijo y,
si ya existe, no se repite. Solo hace `flush`; el commit lo hace `app/datos_prueba.py`.

NO carga piezas por serie (equipo de alturas, detectores...): las carga `app/datos_prueba_piezas.py`
al final del orquestador, con una entrada real y su inspección inicial.
"""

import uuid
from collections import Counter

from sqlalchemy.orm import Session

from app.modulos.acceso.repository import UsuarioRepository
from app.modulos.movimientos.models import TipoVale
from app.modulos.movimientos.schemas import ConfirmarIn, RenglonIn
from app.modulos.movimientos.service import MovimientoService

NAMESPACE = uuid.UUID("5b0e3a52-7f1c-4c58-9a6e-4a1f0f6d1a10")

# Lo que debe quedar en cada almacén: clave -> [(código, cantidad)]. Todos por cantidad.
EXISTENCIAS: dict[str, list[tuple[str, int]]] = {
    "KEP": [
        ("LENTE-CL", 200),
        ("TAPON-AU", 300),
        ("GUANTE-CAR", 120),
        ("GUANTE-DIE", 20),
        ("RESP-6200", 40),
        ("FILTRO-7093", 60),
        ("FILTRO-2097", 60),
        ("CACHUCHA", 50),
        ("CAMISOLA", 60),
        ("ZAPATO-755", 40),
        ("PETO", 40),
        ("POLAINAS", 40),
        ("FLEXOM", 30),
        ("MARRO-B", 15),
        ("CINCEL", 25),
        ("EXT-ELE", 15),
        ("DISCO-9", 100),
        ("DISCO-4M", 200),
        ("LOGO-FR", 100),
        ("LOGO-CON", 100),
    ],
    "CON": [
        ("LENTE-CL", 50),
        ("TAPON-AU", 80),
        ("GUANTE-CAR", 40),
        ("RESP-6200", 10),
        ("FILTRO-7093", 20),
        ("CACHUCHA", 15),
        ("PETO", 10),
        ("POLAINAS", 10),
        ("FLEXOM", 8),
        ("MARRO-B", 6),
        ("CINCEL", 10),
        ("EXT-ELE", 5),
        ("DISCO-9", 30),
        ("DISCO-4M", 60),
    ],
}


# Herramienta que se surte a los proyectos desde Contratistas. Nada de EPP de consumo (E.).
# Midrex queda sin surtir: es el proyecto del recorrido del guion, que arranca sin existencias.
PROYECTOS: dict[str, list[tuple[str, int]]] = {
    "HYL": [("FLEXOM", 3), ("MARRO-B", 2), ("CINCEL", 3)],
    "LAM": [("FLEXOM", 2), ("EXT-ELE", 2)],
    "MIN": [("MARRO-B", 2), ("CINCEL", 3), ("EXT-ELE", 2)],
}

# Quién envía y quién recibe en cada traspaso de la semilla (supervisores de los almacenes).
SUPERVISOR = {
    "KEP": "supervisor",
    "CON": "sup_con",
    "MID": "sup_mid",
    "HYL": "sup_hyl",
    "LAM": "sup_lam",
    "MIN": "sup_min",
}


def _sumar(*listas: list[tuple[str, int]]) -> list[tuple[str, int]]:
    total: Counter[str] = Counter()
    orden: list[str] = []
    for lista in listas:
        for codigo, n in lista:
            if codigo not in total:
                orden.append(codigo)
            total[codigo] += n
    return [(c, total[c]) for c in orden]


# Lo que entra a Kepler: lo que queda ahí más todo lo que se reparte después (EK-02).
_REPARTO_A_PROYECTOS = _sumar(*PROYECTOS.values())
CARGA_INICIAL: dict[str, list[tuple[str, int]]] = {
    "KEP": _sumar(EXISTENCIAS["KEP"], EXISTENCIAS["CON"], _REPARTO_A_PROYECTOS),
}
# Los traspasos: (origen, destino, renglones).
TRASPASOS: list[tuple[str, str, list[tuple[str, int]]]] = [
    ("KEP", "CON", _sumar(EXISTENCIAS["CON"], _REPARTO_A_PROYECTOS)),
    *(("CON", destino, renglones) for destino, renglones in PROYECTOS.items()),
]


def id_cliente_de(clave_almacen: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, f"carga-inicial/{clave_almacen}")


def id_cliente_de_traspaso(origen: str, destino: str, recepcion: bool = False) -> uuid.UUID:
    cual = "recepcion" if recepcion else "traspaso"
    return uuid.uuid5(NAMESPACE, f"reparto/{cual}/{origen}-{destino}")


def cargar(session: Session) -> None:
    usuarios = UsuarioRepository(session)
    compras = usuarios.get_by_usuario("compras")
    admin = usuarios.get_by_usuario("admin")
    if compras is None and admin is None:
        raise RuntimeError("Los datos de `acceso` deben cargarse antes que los de `movimientos`")
    servicio = MovimientoService(session)

    # 1. La entrada: siempre a Kepler, por Compras (que es de Kepler, AC-06).
    for clave, renglones in CARGA_INICIAL.items():
        id_cliente = id_cliente_de(clave)
        if servicio.repository.vale_por_id_cliente(id_cliente) is not None:
            continue
        almacen = servicio.almacenes.obtener_central()
        cuerpo = ConfirmarIn(
            tipo=TipoVale.ENTRADA,
            almacen_id=almacen.id,
            id_cliente=id_cliente,
            observacion="Carga inicial de datos de prueba",
            renglones=[RenglonIn(codigo=codigo, cantidad=n) for codigo, n in renglones],
        )
        servicio.confirmar(compras or admin, cuerpo, aislar=False, commit=False)

    # 2. El reparto por traspaso (X-03): lo envía el supervisor del origen y lo recibe el del
    # destino.
    for origen, destino, renglones in TRASPASOS:
        id_envio = id_cliente_de_traspaso(origen, destino)
        if servicio.repository.vale_por_id_cliente(id_envio) is not None:
            continue
        quien_envia = usuarios.get_by_usuario(SUPERVISOR[origen]) or admin
        quien_recibe = usuarios.get_by_usuario(SUPERVISOR[destino]) or admin
        if quien_envia is None or quien_recibe is None:
            raise RuntimeError("Faltan los supervisores de `acceso` para repartir la mercancía")
        envio, _ = servicio.confirmar(
            quien_envia,
            ConfirmarIn(
                tipo=TipoVale.TRASPASO,
                destino_almacen_id=servicio.almacenes.obtener_por_clave(destino).id,
                id_cliente=id_envio,
                observacion="Reparto de datos de prueba",
                renglones=[RenglonIn(codigo=c, cantidad=n) for c, n in renglones],
            ),
            aislar=False,
            commit=False,
        )
        servicio.confirmar(
            quien_recibe,
            ConfirmarIn(
                tipo=TipoVale.RECEPCION,
                vale_origen_id=envio.id,
                id_cliente=id_cliente_de_traspaso(origen, destino, recepcion=True),
                renglones=[RenglonIn(codigo=c, cantidad=n) for c, n in renglones],
            ),
            aislar=False,
            commit=False,
        )
    session.flush()
