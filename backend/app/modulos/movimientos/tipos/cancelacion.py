"""Tipo CANCELACION (y `POST /api/vales/{id}/cancelacion`): PENDIENTE (otro agente).

Hoy es un stub: todo lanza `TipoNoImplementado` (501). Para implementarlo, reemplaza `TipoPendiente`
por `ManejadorTipo`, llena los ganchos y `cancelar` (ver `README.md`, sección "Qué falta"):

- Permiso `vales.cancelar` (los propios) o `vales.cancelar_todos` (los de cualquiera, K-01).
- Movimientos inversos de los del vale original (K-02), en un vale propio con su folio y
  `vale_origen_id`. No procede (409 `NO_CANCELABLE`) si lo que movió ya se movió o las existencias
  ya no alcanzan (K-03), ni para una RECEPCION o un NO_ADEUDO (K-04).
- `al_confirmar`: `vale.estado` del original pasa a `CANCELADO`. `bloqueos`: el vale original
  (`PlanBloqueo.vales`), las existencias y las piezas de sus movimientos.
- `cancelar(servicio, usuario, vale_id, datos)`: arma el cuerpo y llama
  `servicio.confirmar(...)`; con `rehacer` devuelve además el borrador (K-05).
"""

from app.modulos.acceso.permisos import P
from app.modulos.movimientos.models import FirmaModo, TipoVale
from app.modulos.movimientos.tipos.base import TipoPendiente


class CancelacionTipo(TipoPendiente):
    tipo = TipoVale.CANCELACION
    permiso = P.VALES_CANCELAR
    firma_modo = FirmaModo.SESION
    nombre_texto = "La cancelación"
