"""Tipo TRASPASO (salida): PENDIENTE (lo implementa otro agente sobre el motor ya hecho).

Hoy es un stub: todo lanza `TipoNoImplementado` (501). Para implementarlo, reemplaza `TipoPendiente`
por `ManejadorTipo` y llena los ganchos (ver `README.md` del módulo, sección "Qué falta"):

- Permiso `traspasos.operar`; `destino_almacen_id` obligatorio y distinto del origen.
- Movimientos: almacén de origen -> EN_TRANSITO (X-01). El vale queda en estado `EN_TRANSITO`
  (`DatosVale.estado`) y lleva `destino_almacen_id`; firma de sesión (F-09).
- Reglas: X-01 a X-07 y X-09 (un artículo inactivo sí se traslada; una pieza No apta conserva su
  estado). Ruta no habitual: aviso amarillo (X-03).
- `bloqueos`: existencias (almacén de origen, EN_TRANSITO) y piezas.
"""

from app.modulos.acceso.permisos import P
from app.modulos.movimientos.models import FirmaModo, TipoVale
from app.modulos.movimientos.tipos.base import TipoPendiente


class TraspasoTipo(TipoPendiente):
    tipo = TipoVale.TRASPASO
    permiso = P.TRASPASOS_OPERAR
    firma_modo = FirmaModo.SESION
    nombre_texto = "El traspaso"
