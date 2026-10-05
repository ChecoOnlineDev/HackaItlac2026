"""Contratos de entrada y salida del módulo `trabajadores`."""

import uuid
from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Situacion(StrEnum):
    """Situación de adeudo que ve RH (T-08, B-09)."""

    SIN_PENDIENTES = "SIN_PENDIENTES"
    CON_PENDIENTES = "CON_PENDIENTES"
    NO_ADEUDO_EMITIDO = "NO_ADEUDO_EMITIDO"


TEXTO_SITUACION: dict[str, str] = {
    Situacion.SIN_PENDIENTES: "Sin pendientes",
    Situacion.CON_PENDIENTES: "Con pendientes",
    Situacion.NO_ADEUDO_EMITIDO: "No adeudo emitido",
}

TEXTO_ESTADO: dict[str, str] = {
    "ACTIVO": "Activo",
    "BAJA_EN_PROCESO": "Baja en proceso",
    "INACTIVO": "Inactivo",
}


def _vacio_a_none(valor):
    if isinstance(valor, str):
        valor = valor.strip()
        return valor or None
    return valor


# ------------------------------------------------------------------ entrada


class TrabajadorCreate(BaseModel):
    """Alta (T-03). Obligatorios: nombre, número, puesto, área u obra y periodo."""

    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str = Field(min_length=1, max_length=150)
    numero_empleado: str = Field(min_length=1, max_length=30)
    puesto: str = Field(min_length=1, max_length=100)
    area_obra: str = Field(min_length=1, max_length=100)
    inicio: date
    fin: date
    referencia: str | None = Field(default=None, max_length=100)
    tallas: dict[str, str] | None = None
    curp: str | None = Field(default=None, max_length=18)
    nss: str | None = Field(default=None, max_length=11)

    @field_validator("curp", "nss", "referencia", mode="before")
    @classmethod
    def _limpiar(cls, valor):
        return _vacio_a_none(valor)

    @field_validator("curp")
    @classmethod
    def _curp(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        if len(valor) != 18 or not valor.isalnum():
            raise ValueError("La CURP lleva 18 letras y números.")
        return valor.upper()

    @field_validator("nss")
    @classmethod
    def _nss(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        if len(valor) != 11 or not valor.isdigit():
            raise ValueError("El NSS lleva 11 números.")
        return valor

    @field_validator("tallas")
    @classmethod
    def _tallas(cls, valor: dict[str, str] | None) -> dict[str, str] | None:
        if not valor:
            return None
        if len(valor) > 20 or any(len(k) > 30 or len(v) > 20 for k, v in valor.items()):
            raise ValueError("Las tallas son demasiado largas.")
        limpias = {k.strip(): v.strip() for k, v in valor.items() if k.strip() and v.strip()}
        return limpias or None


class PeriodoCreate(BaseModel):
    """Reingreso o extensión (T-02). Sin puesto o área se conservan los del periodo anterior."""

    model_config = ConfigDict(str_strip_whitespace=True)

    inicio: date
    fin: date
    puesto: str | None = Field(default=None, min_length=1, max_length=100)
    area_obra: str | None = Field(default=None, min_length=1, max_length=100)
    referencia: str | None = Field(default=None, max_length=100)

    @field_validator("referencia", mode="before")
    @classmethod
    def _limpiar(cls, valor):
        return _vacio_a_none(valor)


class CodigoCreate(BaseModel):
    """Sin `codigo`, el sistema genera uno propio para imprimir (T-05)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    codigo: str | None = Field(default=None, max_length=64)

    @field_validator("codigo", mode="before")
    @classmethod
    def _limpiar(cls, valor):
        return _vacio_a_none(valor)


class FiltrosTrabajadores(BaseModel):
    q: str | None = None
    situacion: Situacion | None = None


# ------------------------------------------------------------------- salida


class PeriodoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    puesto: str | None
    area_obra: str | None
    referencia: str | None
    inicio: date
    fin: date
    creado_en: datetime


class VigenciaOut(BaseModel):
    """T-07. Si no es vigente, `regla` es E-02 y `motivo` dice por qué."""

    vigente: bool
    motivo: str | None
    regla: str


class PendienteOut(BaseModel):
    """Un retornable en resguardo (B-02, E-17). Nunca lleva costos (RG-12)."""

    articulo_id: uuid.UUID
    articulo: str
    control: str
    pieza_id: uuid.UUID | None
    codigo: str
    numero_serie: str | None
    cantidad: int
    entregado_en: datetime | None
    vale_id: uuid.UUID | None
    folio: str | None
    almacen_id: uuid.UUID | None
    almacen_clave: str | None
    almacen: str | None
    de_periodo_anterior: bool


class ResumenPendientesOut(BaseModel):
    total: int
    de_periodos_anteriores: int
    # E-12 si hay pendientes de un periodo anterior; vacío si no.
    regla: str | None


class FichaBreveOut(BaseModel):
    """Lo que ve el almacenista al identificar al trabajador (E-17, RG-13). Sin datos reservados."""

    id: uuid.UUID
    numero_empleado: str
    nombre: str
    estado: str
    estado_texto: str
    puesto: str | None
    area_obra: str | None
    vigencia: VigenciaOut
    tiene_foto: bool
    foto_url: str | None
    resguardo: list[PendienteOut]
    pendientes: ResumenPendientesOut


class FichaOut(FichaBreveOut):
    """Ficha completa. `curp` y `nss` solo existen en la respuesta si el usuario tiene
    `trabajadores.ver_datos_personales` (RG-13): sin el permiso la clave ni aparece."""

    periodo: PeriodoOut | None
    situacion: Situacion
    situacion_texto: str
    tallas: dict[str, str] | None
    codigos: list[str]
    curp: str | None = None
    nss: str | None = None


class TrabajadorListItem(BaseModel):
    id: uuid.UUID
    numero_empleado: str
    nombre: str
    estado: str
    estado_texto: str
    puesto: str | None
    area_obra: str | None
    periodo_inicio: date | None
    periodo_fin: date | None
    vigencia: VigenciaOut
    situacion: Situacion
    situacion_texto: str
    tiene_foto: bool


class CodigoOut(BaseModel):
    codigo: str
    tipo: str
    # Verdadero si lo generó el sistema (QR propio para imprimir) y no una credencial escaneada.
    generado: bool


class FotoOut(BaseModel):
    tiene_foto: bool
    foto_url: str | None


class BajaOut(BaseModel):
    """B-01 y B-02. `puede_emitir_no_adeudo` es B-04: sin pendientes ya procede el vale."""

    id: uuid.UUID
    estado: str
    estado_texto: str
    pendientes: list[PendienteOut]
    puede_emitir_no_adeudo: bool
    reglas: list[str]
