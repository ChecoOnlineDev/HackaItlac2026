"""Contratos de proyectos; situaciones calculadas con fecha mexicana."""

import re
import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProyectoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    clave: str = Field(min_length=2, max_length=20)
    nombre: str = Field(min_length=1, max_length=100)
    almacen_id: uuid.UUID
    inicio: date
    fin_estimado: date

    @field_validator("clave")
    @classmethod
    def normalizar_clave(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.fullmatch(r"[A-Z0-9-]{2,20}", v):
            raise ValueError("Usa de 2 a 20 letras sin acentos, números o guion.")
        return v

    @field_validator("nombre")
    @classmethod
    def limpiar_nombre(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Escribe el nombre.")
        return v.strip()


class ProyectoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    clave: str | None = Field(default=None, min_length=2, max_length=20)
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    almacen_id: uuid.UUID | None = None
    inicio: date | None = None
    fin_estimado: date | None = None

    @field_validator("clave")
    @classmethod
    def clave_valida(cls, v: str | None) -> str | None:
        return ProyectoCreate.normalizar_clave(v) if v is not None else v

    @field_validator("nombre")
    @classmethod
    def nombre_valido(cls, v: str | None) -> str | None:
        return ProyectoCreate.limpiar_nombre(v) if v is not None else v


class CierreIn(BaseModel):
    motivo: str = Field(min_length=1, max_length=500)

    @field_validator("motivo")
    @classmethod
    def motivo_valido(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Escribe el motivo del cierre.")
        return v.strip()


class ReaperturaIn(BaseModel):
    fin_estimado: date | None = None
    motivo: str | None = Field(default=None, max_length=500)


class AlmacenRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    clave: str
    nombre: str


class ProyectoOut(BaseModel):
    id: uuid.UUID
    clave: str
    nombre: str
    almacen: AlmacenRef
    inicio: date
    fin_estimado: date
    estado: str
    situacion: str
    asignable: bool
    trabajadores_asignados: int
    aviso: str | None = None
    cerrado_en: datetime | None
    motivo_cierre: str | None
    creado_en: datetime


class CierreOut(ProyectoOut):
    asignaciones_terminadas: int
    trabajadores_sin_proyecto: int


class AsignacionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    proyecto_id: uuid.UUID
    principal: bool | None = None
    inicio: date | None = None
    reemplaza_asignacion_id: uuid.UUID | None = None


class AsignacionOut(BaseModel):
    id: uuid.UUID
    asignacion_id: uuid.UUID
    proyecto: ProyectoOut
    principal: bool
    inicio: date
    fin: date | None
    creado_en: datetime
    terminada_en: datetime | None


class TerminoOut(BaseModel):
    asignaciones: list[AsignacionOut]
    queda_sin_proyecto: bool


Situacion = Literal["VIGENTE", "POR_INICIAR", "FIN_VENCIDO", "CERRADO"]
