"""Contratos de entrada y salida del módulo `acceso`."""

import uuid

from pydantic import BaseModel, ConfigDict, Field


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
