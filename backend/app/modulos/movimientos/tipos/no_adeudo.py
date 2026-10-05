"""Tipo NO_ADEUDO (y `POST /api/trabajadores/{id}/no-adeudo`): PENDIENTE (otro agente).

Hoy es un stub: todo lanza `TipoNoImplementado` (501). Para implementarlo, reemplaza `TipoPendiente`
por `ManejadorTipo`, llena los ganchos y `emitir_no_adeudo` (ver `README.md`, sección "Qué falta"):

- Permiso `no_adeudo.emitir`. Vale SIN movimientos (`construir_movimientos` devuelve `[]`; el motor
  acepta vales sin movimientos solo para este tipo).
- Con pendientes responde 409 `CON_PENDIENTES` (B-04, invariante 8): usa
  `TrabajadorService.pendientes_de`.
- `al_confirmar`: `TrabajadorService.marcar_inactivo` (B-08). `bloqueos`: el trabajador.
"""

from app.modulos.acceso.permisos import P
from app.modulos.movimientos.models import FirmaModo, TipoVale
from app.modulos.movimientos.tipos.base import TipoPendiente


class NoAdeudoTipo(TipoPendiente):
    tipo = TipoVale.NO_ADEUDO
    permiso = P.NO_ADEUDO_EMITIR
    firma_modo = FirmaModo.SESION
    admite_sin_renglones = True
    nombre_texto = "El vale de no adeudo"
