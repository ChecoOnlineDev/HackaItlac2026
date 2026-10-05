"""Piezas de prueba (equipo de alturas y herramientas por serie), cargadas con vales reales.

Es un módulo neutral porque depende de tres módulos a la vez: `catalogo` (artículos), `movimientos`
(la ENTRADA que da de alta cada pieza) e `inspecciones` (la inspección inicial, I-03). Lo invoca
`app/datos_prueba.py` al final, cuando ya existen los usuarios, el catálogo y las existencias.

Qué carga, todo en Kepler (KEP), con UN vale de ENTRADA real (usuario `compras`):

    ALT-001  Arnés Kevlar          SN-ARN-K-0001  APTA, inspeccionada hoy (vigente 180 días)
    ALT-002  Arnés Kevlar          SN-ARN-K-0002  APTA, inspeccionada hoy
    ALT-003  Arnés Kevlar          SN-ARN-K-0003  NO APTA (costura dañada)
    ALT-004  Arnés Poliéster       SN-ARN-P-0001  APTA, inspeccionada hoy
    ALT-005  Arnés Poliéster       SN-ARN-P-0002  VENCIDA: inspeccionada hace 200 días
    ALT-006  Bandola               SN-BAN-0001    APTA
    ALT-007  Gancho doble de vida  SN-GAN-0001    APTA
    ALT-008  Retráctil 3 mts       SN-RET-0001    APTA
    HER-001  Minipulidor           SN-MIN-0001    APTA (sin inspección: el artículo no la pide)
    HER-002  Minipulidor           SN-MIN-0002    APTA
    HER-003  Detector de gases     SN-DET-0001    APTA
    HER-004  Detector de gases     SN-DET-0002    APTA
    HER-005  Radio de comunicación SN-RAD-0001    APTA

Cómo queda VENCIDA una pieza sin tocar la base a mano: la inspección inicial de la ENTRADA admite
`fecha` (I-03, no futura) y el servicio de inspecciones calcula `vigente_hasta = fecha + vigencia`
(180 días en alturas). La ALT-005 entra con `fecha = hoy - 200 días`, así que su vigencia terminó
hace 20 días, como ocurriría de verdad con el paso del tiempo. Es la misma ruta que usa la
interfaz: nada se inserta con SQL.

Es idempotente y repetible: cada pieza se identifica por su código; solo se da entrada a las que
faltan, en un vale cuyo `id_cliente` es determinista por esas piezas. Las fechas de las
inspecciones se calculan al cargar; una pieza APTA ya cargada no se reinspecciona, así que su
vigencia corre desde el día de la primera carga. Solo hace `flush`; el commit lo hace
`app/datos_prueba.py`.

El artículo RADIO (Radio de comunicación, categoría «Equipo de alto valor») no está en el PDF
página 7; se crea aquí para tener el tercer tipo de herramienta por serie de las demostraciones.
"""

import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tiempo import hoy_mx
from app.modulos.acceso.repository import UsuarioRepository
from app.modulos.catalogo.models import Articulo, Categoria, Pieza
from app.modulos.catalogo.schemas import ArticuloCreate
from app.modulos.catalogo.service import CatalogoService
from app.modulos.inspecciones.models import ResultadoInspeccion
from app.modulos.movimientos.models import TipoVale
from app.modulos.movimientos.schemas import (
    ConfirmarIn,
    InspeccionInicialIn,
    PiezaEntradaIn,
    RenglonIn,
)
from app.modulos.movimientos.service import MovimientoService

NAMESPACE = uuid.UUID("5b0e3a52-7f1c-4c58-9a6e-4a1f0f6d1a20")
ALMACEN = "KEP"
# Días que hace que se inspeccionó la pieza VENCIDA: más que la vigencia de alturas (180).
DIAS_DE_LA_INSPECCION_VENCIDA = 200

ARTICULO_RADIO = ("RADIO", "Radio de comunicación", "Equipo de alto valor")


@dataclass(frozen=True)
class PiezaPrueba:
    codigo: str
    articulo: str  # código del artículo
    serie: str
    # None: sin inspección inicial (el artículo no la pide).
    resultado: ResultadoInspeccion | None = ResultadoInspeccion.APTO
    hace_dias: int = 0
    observacion: str | None = None


PIEZAS: tuple[PiezaPrueba, ...] = (
    PiezaPrueba("ALT-001", "ARN-KEV", "SN-ARN-K-0001"),
    PiezaPrueba("ALT-002", "ARN-KEV", "SN-ARN-K-0002"),
    PiezaPrueba(
        "ALT-003",
        "ARN-KEV",
        "SN-ARN-K-0003",
        ResultadoInspeccion.NO_APTO,
        observacion="Costura dañada en la cinta del pecho (dato de prueba).",
    ),
    PiezaPrueba("ALT-004", "ARN-POL", "SN-ARN-P-0001"),
    PiezaPrueba("ALT-005", "ARN-POL", "SN-ARN-P-0002", hace_dias=DIAS_DE_LA_INSPECCION_VENCIDA),
    PiezaPrueba("ALT-006", "BANDOLA", "SN-BAN-0001"),
    PiezaPrueba("ALT-007", "GAN-DOB", "SN-GAN-0001"),
    PiezaPrueba("ALT-008", "RET-3M", "SN-RET-0001"),
    PiezaPrueba("HER-001", "MINIPUL", "SN-MIN-0001", resultado=None),
    PiezaPrueba("HER-002", "MINIPUL", "SN-MIN-0002", resultado=None),
    PiezaPrueba("HER-003", "DET-GAS", "SN-DET-0001", resultado=None),
    PiezaPrueba("HER-004", "DET-GAS", "SN-DET-0002", resultado=None),
    PiezaPrueba("HER-005", "RADIO", "SN-RAD-0001", resultado=None),
)

CODIGOS = tuple(p.codigo for p in PIEZAS)


def id_cliente_de(codigos: list[str]) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, "piezas/" + ",".join(sorted(codigos)))


def _asegurar_articulo_radio(session: Session, actor_id: uuid.UUID) -> None:
    codigo, nombre, categoria_nombre = ARTICULO_RADIO
    if session.scalar(select(Articulo.id).where(Articulo.codigo == codigo)) is not None:
        return
    categoria = session.scalar(select(Categoria).where(Categoria.nombre == categoria_nombre))
    if categoria is None:
        raise RuntimeError("Las categorías de `catalogo` deben cargarse antes que las piezas")
    CatalogoService(session).crear_articulo(
        ArticuloCreate(codigo=codigo, nombre=nombre, categoria_id=categoria.id), actor_id
    )
    session.flush()


def _renglon(pieza: PiezaPrueba, hoy) -> RenglonIn:
    inspeccion = None
    if pieza.resultado is not None:
        inspeccion = InspeccionInicialIn(
            fecha=hoy - timedelta(days=pieza.hace_dias),
            resultado=pieza.resultado,
            observacion=pieza.observacion,
        )
    return RenglonIn(
        codigo=pieza.articulo,
        cantidad=1,
        pieza=PiezaEntradaIn(codigo=pieza.codigo, numero_serie=pieza.serie, inspeccion=inspeccion),
    )


def cargar(session: Session) -> None:
    usuarios = UsuarioRepository(session)
    responsable = usuarios.get_by_usuario("compras") or usuarios.get_by_usuario("admin")
    if responsable is None:
        raise RuntimeError("Los datos de `acceso` deben cargarse antes que las piezas")
    _asegurar_articulo_radio(session, responsable.id)

    existentes = set(session.scalars(select(Pieza.codigo).where(Pieza.codigo.in_(CODIGOS))))
    faltantes = [p for p in PIEZAS if p.codigo not in existentes]
    if not faltantes:
        return

    servicio = MovimientoService(session)
    id_cliente = id_cliente_de([p.codigo for p in faltantes])
    if servicio.repository.vale_por_id_cliente(id_cliente) is not None:
        return
    hoy = hoy_mx()
    almacen = servicio.almacenes.obtener_por_clave(ALMACEN)
    cuerpo = ConfirmarIn(
        tipo=TipoVale.ENTRADA,
        almacen_id=almacen.id,
        id_cliente=id_cliente,
        observacion="Piezas de prueba: equipo de alturas y herramientas por serie",
        renglones=[_renglon(p, hoy) for p in faltantes],
    )
    servicio.confirmar(responsable, cuerpo, aislar=False, commit=False)
    session.flush()
