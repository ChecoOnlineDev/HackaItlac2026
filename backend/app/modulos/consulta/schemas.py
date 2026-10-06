"""Contratos de salida y filtros del módulo `consulta`.

Nada aquí lleva costos (RG-12), CURP ni NSS (RG-13).
"""

import uuid
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, PlainSerializer

from app.core.paginacion import Pagina
from app.modulos.movimientos.models import TipoVale


def _a_utc(valor: datetime) -> str:
    return valor.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")


# Las fechas de la base son UTC sin zona; se envían con la `Z` para que el navegador las
# convierta bien a la hora local (api-contracts: horas en UTC).
FechaUtc = Annotated[datetime, PlainSerializer(_a_utc, return_type=str)]

MENSAJE_SIN_RESULTADOS = "No se encontró nada con ese código o texto."
MENSAJE_SIN_REGISTROS = "No hay registros con esos filtros."
MENSAJE_BUSQUEDA_CORTA = "Escribe al menos dos caracteres para buscar."

TEXTO_TIPO_VALE: dict[str, str] = {
    "ENTRADA": "Entrada",
    "ENTREGA": "Entrega",
    "DEVOLUCION": "Devolución",
    "TRASPASO": "Traspaso",
    "RECEPCION": "Recepción",
    "NO_ADEUDO": "No adeudo",
    "CANCELACION": "Cancelación",
}

TEXTO_ESTADO_PIEZA: dict[str, str] = {
    "APTO": "Apta",
    "NO_APTO": "No apta",
    "EN_MANTENIMIENTO": "En mantenimiento",
    "EN_CALIBRACION": "En calibración",
    "BAJA": "De baja",
}

TEXTO_ESTADO_TRABAJADOR: dict[str, str] = {
    "ACTIVO": "Activo",
    "BAJA_EN_PROCESO": "Baja en proceso",
    "INACTIVO": "Inactivo",
}

TEXTO_VIRTUAL: dict[str, str] = {
    "PROVEEDOR": "Proveedor",
    "EN_TRANSITO": "En tránsito",
    "CONSUMIDO": "Consumido",
    "BAJA": "Baja",
}


class PaginaReporte[T](Pagina[T]):
    """Lista de un reporte: `{elementos, total}` y si no hubo registros, para avisarlo."""

    sin_registros: bool
    mensaje: str | None = None


# ------------------------------------------------------------------------------ escaneo


class TipoEscaneo(StrEnum):
    TRABAJADOR = "TRABAJADOR"
    ARTICULO = "ARTICULO"
    PIEZA = "PIEZA"
    VALE = "VALE"
    DESCONOCIDO = "DESCONOCIDO"


class UbicacionOut(BaseModel):
    """Dónde está algo: un almacén, un trabajador o un lugar virtual."""

    tipo: str  # ALMACEN, TRABAJADOR o VIRTUAL
    texto: str
    almacen_id: uuid.UUID | None = None
    almacen_clave: str | None = None
    trabajador_id: uuid.UUID | None = None
    numero_empleado: str | None = None
    virtual: str | None = None


class ResumenTrabajador(BaseModel):
    numero_empleado: str
    nombre: str
    estado: str
    estado_texto: str
    vigente: bool
    motivo_no_vigente: str | None
    puesto: str | None
    area_obra: str | None
    vigente_hasta: date | None
    pendientes: int


class ResumenArticulo(BaseModel):
    codigo: str
    nombre: str
    marca: str | None
    categoria: str
    control: str
    retornable: bool
    unidad: str
    activo: bool
    existencia_total: int


class ResumenPieza(BaseModel):
    codigo: str
    numero_serie: str | None
    articulo_id: uuid.UUID
    articulo: str
    estado: str
    estado_texto: str
    inspeccion_vigente_hasta: date | None
    inspeccion_vigente: bool
    ubicacion: UbicacionOut | None


class ResumenVale(BaseModel):
    folio: str
    tipo: str
    tipo_texto: str
    estado: str
    fecha: FechaUtc
    almacen_clave: str
    trabajador: str | None
    responsable: str


class ResumenDesconocido(BaseModel):
    mensaje: str = MENSAJE_SIN_RESULTADOS


class EscaneoOut(BaseModel):
    """Qué es lo que se escaneó. `id` es el de la cosa; `resumen` es breve, para la pantalla."""

    tipo: TipoEscaneo
    id: uuid.UUID | None
    resumen: ResumenTrabajador | ResumenArticulo | ResumenPieza | ResumenVale | ResumenDesconocido


# ----------------------------------------------------------------------------- búsqueda


class BusquedaArticuloItem(BaseModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    marca: str | None
    categoria: str
    control: str
    activo: bool


class BusquedaPiezaItem(BaseModel):
    id: uuid.UUID
    codigo: str
    numero_serie: str | None
    articulo_id: uuid.UUID
    articulo: str
    estado: str
    estado_texto: str
    # Quién o dónde la tiene: "Kepler (KEP)" o "Juan Pérez (EMP-1001)".
    ubicacion: str | None


class BusquedaTrabajadorItem(BaseModel):
    id: uuid.UUID
    numero_empleado: str
    nombre: str
    estado: str
    estado_texto: str


class BusquedaOut(BaseModel):
    """Coincidencias por grupo; cada grupo respeta los permisos de quien busca (C-06)."""

    q: str
    articulos: Pagina[BusquedaArticuloItem]
    piezas: Pagina[BusquedaPiezaItem]
    trabajadores: Pagina[BusquedaTrabajadorItem]
    sin_resultados: bool
    mensaje: str | None = None


# ------------------------------------------------------------------------ ficha de pieza


class ArticuloPiezaOut(BaseModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    marca: str | None
    modelo: str | None
    talla: str | None
    unidad: str
    requiere_inspeccion: bool
    vigencia_inspeccion_dias: int | None


class InspeccionOut(BaseModel):
    id: uuid.UUID
    fecha: date
    resultado: str
    resultado_texto: str
    vigente_hasta: date | None
    observacion: str | None
    usuario: str


class UsuarioOpcionOut(BaseModel):
    """Una persona que ha hecho vales, para el filtro «quién lo hizo» de la bitácora (C-11)."""

    id: uuid.UUID
    nombre: str
    usuario: str


class UsuariosOpcionesOut(BaseModel):
    elementos: list[UsuarioOpcionOut]


class TipoHistorial(StrEnum):
    MOVIMIENTO = "MOVIMIENTO"
    INSPECCION = "INSPECCION"
    CAMBIO_ESTADO = "CAMBIO_ESTADO"
    AJUSTE_VIGENCIA = "AJUSTE_VIGENCIA"


class HistorialItem(BaseModel):
    """Un hecho de la vida de la pieza. Los campos que no aplican al `tipo` van en `null`."""

    tipo: TipoHistorial
    fecha: FechaUtc  # UTC
    titulo: str
    detalle: str | None = None
    usuario: str | None = None
    # Movimiento
    vale_id: uuid.UUID | None = None
    folio: str | None = None
    tipo_vale: str | None = None
    origen: str | None = None
    destino: str | None = None
    responsable: str | None = None
    condicion: str | None = None
    # Inspección y ajuste de vigencia
    resultado: str | None = None
    vigente_hasta: date | None = None
    vigente_hasta_anterior: date | None = None
    # Cambio de estado
    estado_anterior: str | None = None
    estado_nuevo: str | None = None
    observacion: str | None = None


class PiezaFichaOut(BaseModel):
    """C-02: estado, inspección, quién la tiene e historial completo (más reciente primero)."""

    id: uuid.UUID
    codigo: str
    numero_serie: str | None
    estado: str
    estado_texto: str
    articulo: ArticuloPiezaOut
    inspeccion_vigente_hasta: date | None
    inspeccion_vigente: bool
    ultima_inspeccion: InspeccionOut | None
    ubicacion: UbicacionOut | None
    historial: list[HistorialItem]


# ---------------------------------------------------------------------------- reportes


class FormatoReporte(StrEnum):
    JSON = "json"
    CSV = "csv"


class ExistenciasFilters(BaseModel):
    almacen_id: uuid.UUID | None = None
    categoria_id: uuid.UUID | None = None
    formato: FormatoReporte = FormatoReporte.JSON


class MovimientosFilters(BaseModel):
    # Fechas locales de México; el día termina a las 23:59:59 de allá.
    desde: date | None = None
    hasta: date | None = None
    almacen_id: uuid.UUID | None = None
    tipo: TipoVale | None = None
    trabajador_id: uuid.UUID | None = None
    articulo_id: uuid.UUID | None = None
    # Quien hizo el vale (C-11).
    usuario_id: uuid.UUID | None = None
    formato: FormatoReporte = FormatoReporte.JSON


class AdeudosFilters(BaseModel):
    solo_no_vigentes: bool = False
    almacen_id: uuid.UUID | None = None
    formato: FormatoReporte = FormatoReporte.JSON


class ConsumoFilters(BaseModel):
    desde: date | None = None
    hasta: date | None = None
    almacen_id: uuid.UUID | None = None
    categoria_id: uuid.UUID | None = None
    articulo_id: uuid.UUID | None = None
    trabajador_id: uuid.UUID | None = None
    formato: FormatoReporte = FormatoReporte.JSON


class ExistenciaReporteItem(BaseModel):
    almacen_id: uuid.UUID
    almacen_clave: str
    almacen: str
    articulo_id: uuid.UUID
    codigo: str
    articulo: str
    categoria: str
    unidad: str
    activo: bool
    cantidad: int
    # No cuenta piezas No aptas, en mantenimiento ni en calibración (I-05).
    disponible: int


class MovimientoReporteItem(BaseModel):
    id: uuid.UUID
    fecha: FechaUtc  # UTC
    vale_id: uuid.UUID
    folio: str
    tipo: str
    tipo_texto: str
    articulo_id: uuid.UUID
    codigo_articulo: str
    articulo: str
    pieza: str | None
    cantidad: int
    origen: str
    destino: str
    responsable: str
    trabajador: str | None
    saldo_origen: int | None
    saldo_destino: int | None
    # Lo que anotó quien hizo el vale en ese renglón (por ejemplo el porqué de E-09).
    observacion: str | None = None


class AdeudoReporteItem(BaseModel):
    """Un pendiente de un trabajador: qué tiene, desde cuándo y de qué almacén."""

    trabajador_id: uuid.UUID
    numero_empleado: str
    trabajador: str
    estado: str
    estado_texto: str
    vigente: bool
    motivo_no_vigente: str | None
    articulo_id: uuid.UUID
    codigo: str
    articulo: str
    numero_serie: str | None
    cantidad: int
    desde: FechaUtc | None  # UTC
    folio: str | None
    almacen_clave: str | None
    almacen: str | None


class ConsumoTrabajadorItem(BaseModel):
    trabajador_id: uuid.UUID | None
    numero_empleado: str | None
    trabajador: str
    cantidad: int


class ConsumoReporteItem(BaseModel):
    """Consumo de un artículo en el periodo, con su desglose por trabajador (mayor a menor)."""

    articulo_id: uuid.UUID
    codigo: str
    articulo: str
    categoria: str
    unidad: str
    total: int
    trabajadores: list[ConsumoTrabajadorItem]
