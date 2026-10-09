"""Contratos de entrada y salida del módulo `movimientos` (Create, Out, ListItem, Filters).

Ningún contrato de este módulo lleva costos: ni el cuerpo los acepta (`extra="forbid"`) ni la
respuesta de un vale los muestra (F-12, RG-12).
"""

import math
import uuid
from datetime import UTC, date, datetime
from typing import Annotated, Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    computed_field,
    field_validator,
    model_validator,
)

from app.modulos.inspecciones.models import ResultadoInspeccion
from app.modulos.movimientos.models import Condicion, EstadoVale, FirmaModo, Nivel, TipoVale
from app.modulos.trabajadores.schemas import FichaBreveOut


def _a_utc(valor: datetime) -> str:
    return valor.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")


# Las fechas de la base son UTC sin zona; se envían con la `Z` (api-contracts: horas en UTC).
FechaUtc = Annotated[datetime, PlainSerializer(_a_utc, return_type=str)]

CANTIDAD_MAXIMA = 1_000_000
# Fotos de daño (`data:` URL en base64): cada una y todas las de un vale (H8). El cuerpo completo
# del vale tiene además su propio tope por ruta (`LIMITE_CUERPO_VALE`, 12 MB).
FOTO_CARACTERES_MAXIMO = 4_000_000  # ~3 MB de imagen
FOTOS_VALE_CARACTERES_MAXIMO = 10 * 1024 * 1024  # ~7.5 MB de imagen


def _vacio_a_none(valor: Any) -> Any:
    if isinstance(valor, str):
        valor = valor.strip()
        return valor or None
    return valor


# ------------------------------------------------------------------------------ entrada


class _Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class InspeccionInicialIn(_Estricto):
    """Inspección inicial de una pieza que entra (I-03). Sin `fecha`, es la de hoy."""

    fecha: date | None = None
    resultado: ResultadoInspeccion
    observacion: str | None = Field(default=None, max_length=1000)

    _limpiar = field_validator("observacion", mode="before")(_vacio_a_none)


class PiezaEntradaIn(_Estricto):
    """La pieza que entra en un renglón de ENTRADA de un artículo por pieza (I-02)."""

    codigo: str = Field(min_length=1, max_length=64)
    numero_serie: str | None = Field(default=None, max_length=80)
    inspeccion: InspeccionInicialIn | None = None

    _limpiar = field_validator("numero_serie", mode="before")(_vacio_a_none)


class RenglonIn(_Estricto):
    codigo: str = Field(min_length=1, max_length=64)
    cantidad: int = Field(default=1, ge=1, le=CANTIDAD_MAXIMA)
    condicion: Condicion | None = None
    observacion: str | None = Field(default=None, max_length=1000)
    pieza: PiezaEntradaIn | None = None
    # Solo DEVOLUCION con condición DANADO (V-05): foto del daño como `data:image/...;base64,...`.
    foto: str | None = Field(default=None, max_length=FOTO_CARACTERES_MAXIMO)

    _limpiar = field_validator("observacion", "foto", mode="before")(_vacio_a_none)


class ValeIn(_Estricto):
    """Cuerpo común de `evaluar` y de `confirmar` para todos los tipos de vale.

    `almacen_id` solo lo indica quien tiene `almacenes.todos`; el resto opera su almacén
    asignado (si lo manda y ya no es el suyo, 409 `ALMACEN_CAMBIO`, AC-13).
    """

    tipo: TipoVale
    almacen_id: uuid.UUID | None = None
    trabajador_id: uuid.UUID | None = None
    proyecto_id: uuid.UUID | None = None
    destino_almacen_id: uuid.UUID | None = None
    vale_origen_id: uuid.UUID | None = None
    autorizacion_id: uuid.UUID | None = None
    renglones: list[RenglonIn] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def _fotos_del_vale_con_tope(self) -> Self:
        if self.proyecto_id is not None and self.tipo != TipoVale.ENTREGA:
            raise ValueError("El proyecto solo se indica en una entrega (PR-14).")
        total = sum(len(r.foto) for r in self.renglones if r.foto)
        if total > FOTOS_VALE_CARACTERES_MAXIMO:
            raise ValueError("Las fotos del vale pesan demasiado. Reduce su tamaño o quita alguna.")
        return self


# Trazo de la firma (F-02): hasta este número de puntos `{x, y, t}` en total.
TRAZO_PUNTOS_MAXIMO = 20_000
TRAZO_PUNTOS_MINIMO = 10  # al confirmar una entrega (lo exige el tipo ENTREGA)


def _punto_valido(punto: Any) -> bool:
    """Un punto `{x, y, t}` con tres números finitos (no booleanos)."""
    if not isinstance(punto, dict):
        return False
    for clave in ("x", "y", "t"):
        valor = punto.get(clave)
        if isinstance(valor, bool) or not isinstance(valor, int | float):
            return False
        if isinstance(valor, float) and not math.isfinite(valor):
            return False
    return True


def contar_puntos_del_trazo(trazo: list[Any]) -> int:
    """Puntos en total de un trazo: lista de puntos o lista de trazos (listas de puntos)."""
    return sum(len(e) if isinstance(e, list) else 1 for e in trazo)


class FirmaIn(_Estricto):
    modo: FirmaModo
    imagen: str | None = Field(default=None, max_length=4_000_000)
    # La interfaz manda una lista de trazos (cada uno, una lista de puntos `{x, y, t}`); también
    # se acepta una lista plana de puntos. El mínimo de puntos lo exige la confirmación.
    trazo: list[Any] = Field(default_factory=list)

    @field_validator("trazo")
    @classmethod
    def _trazo_con_forma(cls, trazo: list[Any]) -> list[Any]:
        if contar_puntos_del_trazo(trazo) > TRAZO_PUNTOS_MAXIMO:
            raise ValueError(f"El trazo de la firma pasa de {TRAZO_PUNTOS_MAXIMO} puntos.")
        for elemento in trazo:
            puntos = elemento if isinstance(elemento, list) else [elemento]
            if not all(_punto_valido(p) for p in puntos):
                raise ValueError("Cada punto del trazo debe traer x, y y t numéricos.")
        return trazo


class EvaluarIn(ValeIn):
    """El cuerpo de `evaluar` es el mismo que el de confirmar: acepta los campos de la
    confirmación (`id_cliente`, `observacion`, `firma`) para que la interfaz mande un solo
    cuerpo, pero los ignora (evaluar nunca escribe)."""

    id_cliente: uuid.UUID | None = None
    observacion: str | None = Field(default=None, max_length=1000)
    firma: FirmaIn | None = None


class ConfirmarIn(ValeIn):
    """Lo que agrega la confirmación (api-contracts, Vales)."""

    id_cliente: uuid.UUID
    observacion: str | None = Field(default=None, max_length=1000)
    firma: FirmaIn | None = None
    reserva_papel_id: uuid.UUID | None = None

    _limpiar = field_validator("observacion", mode="before")(_vacio_a_none)


class NoAdeudoIn(_Estricto):
    """`POST /api/trabajadores/{id}/no-adeudo` (B-04). Lo interpreta el tipo NO_ADEUDO."""

    id_cliente: uuid.UUID
    almacen_id: uuid.UUID | None = None
    observacion: str | None = Field(default=None, max_length=1000)


class CancelacionIn(_Estricto):
    """`POST /api/vales/{id}/cancelacion` (K-01 a K-05). Lo interpreta el tipo CANCELACION."""

    motivo: str = Field(min_length=1, max_length=1000)
    id_cliente: uuid.UUID
    rehacer: bool = False


# ------------------------------------------------------------------------ salida: evaluar


class MotivoOut(BaseModel):
    regla: str
    nivel: Nivel
    mensaje: str
    codigo: str | None = None
    # Solo en un motivo naranja del vale (X-17): una autorización lo cubre, y si ya lo cubre.
    autorizable: bool = False
    autorizado: bool = False


class ArticuloEvaluadoOut(BaseModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    marca: str | None
    modelo: str | None
    talla: str | None
    unidad: str
    control: str
    retornable: bool
    activo: bool
    motivo_uso_especial: str | None


class PiezaEvaluadaOut(BaseModel):
    """`id` va vacío en una pieza que todavía no existe (renglón de ENTRADA)."""

    id: uuid.UUID | None
    codigo: str
    numero_serie: str | None
    estado: str | None
    inspeccion_vigente_hasta: date | None
    pendiente_inspeccion: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def serie_pendiente(self) -> bool:
        """Derivado de `numero_serie` nulo (E-29, I-02)."""
        return not self.numero_serie


class TitularOut(BaseModel):
    """Dónde está una pieza que no está en este almacén (E-03)."""

    tipo: str | None
    id: uuid.UUID | None
    nombre: str
    descripcion: str
    numero_empleado: str | None = None


class RenglonEvaluadoOut(BaseModel):
    es_epp: bool = False
    requiere_aprobacion: bool = False
    aprobacion: (
        Literal["APROBADO", "RECHAZADO", "NO_INCLUIDO", "CANTIDAD_MAYOR", "PENDIENTE"] | None
    ) = None
    motivo_rechazo: str | None = None
    renglon: int
    codigo: str
    articulo: ArticuloEvaluadoOut | None
    pieza: PiezaEvaluadaOut | None
    titular: TitularOut | None
    cantidad: int
    disponible: int | None
    nivel: Nivel
    motivos: list[MotivoOut]
    pide_observacion: bool
    autorizable: bool
    requiere_confirmacion: bool
    # Un naranja que la autorización indicada ya cubre.
    autorizado: bool = False


class AlmacenResumenOut(BaseModel):
    id: uuid.UUID
    clave: str
    nombre: str


class RutaEvaluacionOut(BaseModel):
    """Solo en un TRASPASO (X-03, X-16 a X-18): la clase de ruta y quién la autoriza, tal como
    la evaluó el servidor. `autorizadores_disponibles` (sin contar a quien envía) solo viene con
    `autoriza = SUPERVISOR_ORIGEN` (X-17)."""

    clase: Literal["HABITUAL", "LATERAL", "NO_HABITUAL", "MISMO"]
    autoriza: Literal["NADIE", "ENVIO_PROPIO", "SUPERVISOR_ORIGEN", "ADMINISTRADOR"]
    autorizadores_disponibles: int | None = None


class ProyectoResumenOut(BaseModel):
    id: uuid.UUID
    clave: str
    nombre: str


class EvaluacionOut(BaseModel):
    requiere_aprobacion_despacho: bool = False
    despacho: dict[str, str] = Field(default_factory=lambda: {"modo": "NO_APLICA"})
    nivel: Nivel
    puede_confirmar: bool
    # Verdadero si algún renglón pide una observación (E-09): al confirmar hace falta una, en el
    # renglón (`renglones[].observacion`) o en el vale (`observacion`); sin ella, 422 con E-09.
    pide_observacion: bool = False
    # Motivos que valen para todo el vale (por ejemplo E-12) y no para un renglón.
    motivos: list[MotivoOut]
    almacen: AlmacenResumenOut
    trabajador: FichaBreveOut | None = None
    proyecto: ProyectoResumenOut | None = None
    proyectos_del_trabajador: list[ProyectoResumenOut] = Field(default_factory=list)
    pide_proyecto: bool = False
    # Si el cuerpo trae `autorizacion_id` y no sirve para este vale, por qué (A-03).
    autorizacion_error: str | None = None
    # Solo en un TRASPASO.
    ruta: RutaEvaluacionOut | None = None
    renglones: list[RenglonEvaluadoOut]


# ----------------------------------------------------------------------- salida: confirmar


class RenglonConfirmadoOut(BaseModel):
    renglon: int
    codigo: str
    articulo: str
    cantidad: int
    nivel: Nivel
    reglas: list[str]


class ValeConfirmadoOut(BaseModel):
    """201 al confirmar (o 200 si el `id_cliente` ya existía): `{id, folio, token, creado_en,
    renglones}`."""

    id: uuid.UUID
    folio: str
    token: str
    creado_en: FechaUtc
    renglones: list[RenglonConfirmadoOut]


class ReservaPapelOut(BaseModel):
    id: uuid.UUID
    folio: str
    token: str
    vence_en: FechaUtc
    ticket: dict[str, Any]
    evaluacion: EvaluacionOut


# ------------------------------------------------------------------------- salida: consulta


class PersonaOut(BaseModel):
    id: uuid.UUID
    nombre: str


class TrabajadorValeOut(BaseModel):
    id: uuid.UUID
    numero_empleado: str
    nombre: str
    puesto: str | None
    area_obra: str | None


class UbicacionOut(BaseModel):
    tipo: str
    nombre: str
    clave: str | None = None


class RenglonValeOut(BaseModel):
    """Un renglón del vale. Descripción con marca, código o serie, cantidad y condición (E-24).
    Nunca trae costos."""

    renglon: int
    articulo_id: uuid.UUID
    articulo: str
    marca: str | None
    modelo: str | None
    talla: str | None
    codigo_articulo: str
    pieza_id: uuid.UUID | None
    codigo_pieza: str | None
    numero_serie: str | None
    cantidad: int
    condicion: str | None
    nivel: Nivel
    reglas: list[str]
    observacion: str | None
    origen: UbicacionOut
    destino: UbicacionOut
    saldo_origen: int | None
    saldo_destino: int | None


class ValidoOut(BaseModel):
    """ "Validó" (A-04): quién pidió, quién autorizó, cuándo, por qué medio y el motivo."""

    # Nulo en el envío propio de un traslado lateral (X-16): no hubo solicitud.
    autorizacion_id: uuid.UUID | None
    solicito: PersonaOut | None
    autorizo: PersonaOut
    # PIN, REMOTA o ENVIO_PROPIO.
    medio: str
    resuelta_en: FechaUtc
    motivo: str


class CancelacionVistaOut(BaseModel):
    """En un vale CANCELADO: su cancelación (K-02): folio, motivo, quién y cuándo."""

    id: uuid.UUID
    folio: str
    motivo: str | None
    responsable: PersonaOut
    creado_en: FechaUtc


class ValeDetalleOut(BaseModel):
    proyecto: ProyectoResumenOut | None = None
    id: uuid.UUID
    folio: str
    token: str
    tipo: TipoVale
    estado: EstadoVale
    almacen: AlmacenResumenOut
    destino_almacen: AlmacenResumenOut | None
    trabajador: TrabajadorValeOut | None
    responsable: PersonaOut
    observacion: str | None
    firma_modo: FirmaModo | None
    tiene_firma: bool
    valido: ValidoOut | None
    vale_origen_id: uuid.UUID | None
    vale_origen_folio: str | None
    # Solo en un vale CANCELADO: el vale que lo canceló, con el motivo.
    cancelacion: CancelacionVistaOut | None = None
    dispositivo: str | None
    creado_en: FechaUtc
    renglones: list[RenglonValeOut]
    lote: dict[str, Any] | None = None
    resumen: dict[str, Any] | None = None
    relacionados: list[dict[str, Any]] = Field(default_factory=list)
    capturado_sin_conexion: bool = False
    capturado_en: FechaUtc | None = None


class ValeListItem(BaseModel):
    id: uuid.UUID
    folio: str
    tipo: TipoVale
    estado: EstadoVale
    almacen: AlmacenResumenOut
    trabajador: PersonaOut | None
    numero_empleado: str | None
    responsable: PersonaOut
    renglones: int
    creado_en: FechaUtc


class ValeFilters(BaseModel):
    tipo: TipoVale | None = None
    almacen_id: uuid.UUID | None = None
    desde: date | None = None
    hasta: date | None = None
    trabajador_id: uuid.UUID | None = None
    usuario_id: uuid.UUID | None = None
