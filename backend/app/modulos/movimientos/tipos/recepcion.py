"""Tipo RECEPCION (y `GET /api/traspasos/por-recibir`): PENDIENTE (otro agente).

Hoy es un stub: todo lanza `TipoNoImplementado` (501). Para implementarlo, reemplaza `TipoPendiente`
por `ManejadorTipo`, llena los ganchos y `por_recibir` (ver `README.md`, sección "Qué falta"):

- Permiso `traspasos.operar`; `vale_origen_id` es el traspaso EN_TRANSITO (se liga en `DatosVale`).
- Movimientos: EN_TRANSITO -> almacén de destino. Solo el almacén de destino recibe (X-10); lo que
  no se recibió sigue En tránsito y el traspaso queda `RECIBIDO_CON_DIFERENCIAS` (X-13).
- `al_confirmar`: cambia `vale.estado` del traspaso original (única excepción a "los vales no se
  actualizan", data-model invariante 5). `bloqueos`: el vale original (`PlanBloqueo.vales`) y las
  existencias de EN_TRANSITO y del destino.
- `por_recibir(servicio, usuario)`: traspasos EN_TRANSITO hacia el almacén de la sesión.
"""

from app.modulos.acceso.permisos import P
from app.modulos.movimientos.models import FirmaModo, TipoVale
from app.modulos.movimientos.tipos.base import TipoPendiente


class RecepcionTipo(TipoPendiente):
    tipo = TipoVale.RECEPCION
    permiso = P.TRASPASOS_OPERAR
    firma_modo = FirmaModo.SESION
    nombre_texto = "La recepción"
