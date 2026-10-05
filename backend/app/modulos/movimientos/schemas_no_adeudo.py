"""Respuesta de `POST /api/trabajadores/{id}/no-adeudo` (B-04, B-08). Sin costos (F-12)."""

import uuid

from pydantic import BaseModel, Field

from app.modulos.movimientos.schemas import ValeConfirmadoOut


class TrabajadorNoAdeudoOut(BaseModel):
    """Cómo queda el trabajador al emitirse el vale: Inactivo hasta el reingreso (B-08)."""

    id: uuid.UUID
    numero_empleado: str
    nombre: str
    estado: str
    estado_texto: str


class NoAdeudoOut(ValeConfirmadoOut):
    """El vale de no adeudo (`{id, folio, token, creado_en, renglones: []}`) y el trabajador.
    `repetido` no se envía: solo decide 201 o 200 en el router (mismo `id_cliente`)."""

    trabajador: TrabajadorNoAdeudoOut
    repetido: bool = Field(default=False, exclude=True)
