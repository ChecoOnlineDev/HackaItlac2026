"""Datos de prueba de `movimientos`: existencias iniciales en Kepler y Contratistas.

Las existencias nacen solo con una entrada (RG-01, I-01): este script no inserta saldos, confirma
vales de ENTRADA reales con el servicio del módulo y el usuario `compras`. Es idempotente: cada
carga lleva un `id_cliente` fijo y, si ya existe, no se repite. Solo hace `flush`; el commit lo
hace `app/datos_prueba.py`.

NO carga piezas por serie (equipo de alturas, detectores...): las carga `app/datos_prueba_piezas.py`
al final del orquestador, con una entrada real y su inspección inicial.
"""

import uuid

from sqlalchemy.orm import Session

from app.modulos.acceso.repository import UsuarioRepository
from app.modulos.movimientos.models import TipoVale
from app.modulos.movimientos.schemas import ConfirmarIn, RenglonIn
from app.modulos.movimientos.service import MovimientoService

NAMESPACE = uuid.UUID("5b0e3a52-7f1c-4c58-9a6e-4a1f0f6d1a10")

# clave del almacén -> [(código del artículo, cantidad)]. Todos por cantidad.
CARGA_INICIAL: dict[str, list[tuple[str, int]]] = {
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


def id_cliente_de(clave_almacen: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, f"carga-inicial/{clave_almacen}")


def cargar(session: Session) -> None:
    usuarios = UsuarioRepository(session)
    responsable = usuarios.get_by_usuario("compras") or usuarios.get_by_usuario("admin")
    if responsable is None:
        raise RuntimeError("Los datos de `acceso` deben cargarse antes que los de `movimientos`")
    servicio = MovimientoService(session)

    for clave, renglones in CARGA_INICIAL.items():
        id_cliente = id_cliente_de(clave)
        if servicio.repository.vale_por_id_cliente(id_cliente) is not None:
            continue
        almacen = servicio.almacenes.obtener_por_clave(clave)
        cuerpo = ConfirmarIn(
            tipo=TipoVale.ENTRADA,
            almacen_id=almacen.id,
            id_cliente=id_cliente,
            observacion="Carga inicial de datos de prueba",
            renglones=[RenglonIn(codigo=codigo, cantidad=n) for codigo, n in renglones],
        )
        servicio.confirmar(responsable, cuerpo, aislar=False, commit=False)
    session.flush()
