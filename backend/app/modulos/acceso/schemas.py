"""Contratos de entrada y salida del módulo `acceso`."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer


def _a_utc(valor: datetime) -> str:
    return valor.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")


# Las fechas de la base son UTC sin zona; se envían con la `Z` (api-contracts: horas en UTC).
FechaUtc = Annotated[datetime, PlainSerializer(_a_utc, return_type=str)]


class LoginIn(BaseModel):
    usuario: str = Field(min_length=1, max_length=60)
    contrasena: str = Field(min_length=1, max_length=200)


class UsuarioSesionOut(BaseModel):
    id: uuid.UUID
    nombre: str
    usuario: str


class RolSesionOut(BaseModel):
    id: uuid.UUID
    nombre: str


class AlmacenSesionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clave: str
    nombre: str


class SesionOut(BaseModel):
    """Lo que la interfaz necesita para armar menús y botones (el servidor es el control)."""

    usuario: UsuarioSesionOut
    rol: RolSesionOut
    almacen: AlmacenSesionOut | None
    permisos: list[str]


class DispositivoOut(BaseModel):
    """Una sesión abierta del usuario en un dispositivo. Sin huellas ni dirección IP."""

    id: uuid.UUID
    inicio: FechaUtc
    ultimo_uso: FechaUtc
    # Hasta cuándo sirve sin volver a usarla (la ventana renovable, sin pasar del tope).
    vence_en: FechaUtc
    agente: str | None
    actual: bool


class DispositivosOut(BaseModel):
    dispositivos: list[DispositivoOut]


class CerradasOut(BaseModel):
    cerradas: int


# ------------------------------------------------- usuarios, personal y roles (FEAT-006)


class RolOut(BaseModel):
    """Un rol, para poblar selectores. Los permisos del rol son de la matriz de FEAT-006."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    descripcion: str | None
    activo: bool
    protegido: bool


class PersonalOut(BaseModel):
    """Quien opera un almacén. Nunca trae contraseñas ni PIN."""

    id: uuid.UUID
    nombre: str
    usuario: str
    rol: RolSesionOut
    almacen: AlmacenSesionOut | None
    activo: bool


class UsuarioOut(PersonalOut):
    tiene_pin: bool
    creado_en: datetime


class AsignarAlmacenIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # `null` deja al usuario sin almacén.
    almacen_id: uuid.UUID | None


class UsuarioCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=150)
    usuario: str = Field(min_length=3, max_length=60, pattern=r"^[A-Za-z0-9._-]+$")
    contrasena: str = Field(min_length=8, max_length=200)
    rol_id: uuid.UUID
    almacen_id: uuid.UUID | None = None
    pin: str | None = Field(default=None, pattern=r"^\d{4,8}$")


class UsuarioUpdate(BaseModel):
    """Lista cerrada de campos editables: no admite contraseñas ni hashes."""

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    rol_id: uuid.UUID | None = None
    activo: bool | None = None
    almacen_id: uuid.UUID | None = None


class RestablecerContrasenaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contrasena: str = Field(min_length=8, max_length=200)
    pin: str | None = Field(default=None, pattern=r"^\d{4,8}$")


# ------------------------------------------------------- roles y permisos (FEAT-006, AC-08 a AC-11)


class PermisoOut(BaseModel):
    clave: str
    descripcion: str
    modulo: str
    es_de_informacion: bool
    mvp: bool
    llega_con: str
    # Permisos de ver que este necesita: activarlo los activa y quitarlos lo quita.
    requiere: list[str]


class RolResumenOut(RolOut):
    # Roles con los que nació el sistema: no se eliminan ni cambian de nombre.
    inicial: bool
    total_usuarios: int
    total_permisos: int


class RolDetalleOut(RolResumenOut):
    permisos: list[str]


class RolCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=80)
    descripcion: str | None = Field(default=None, max_length=500)
    permisos: list[str] = Field(default_factory=list, max_length=200)


class RolUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    descripcion: str | None = Field(default=None, max_length=500)
    activo: bool | None = None


class RolPermisosIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    permisos: list[str] = Field(max_length=200)
