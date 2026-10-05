"""Tipo DEVOLUCION: PENDIENTE (lo implementa otro agente sobre el motor ya hecho).

Hoy es un stub: todo lanza `TipoNoImplementado` (501). Para implementarlo, reemplaza `TipoPendiente`
por `ManejadorTipo` y llena los ganchos (ver `README.md` del módulo, sección "Qué falta"):

- Permiso `devoluciones.crear`; firma de sesión (F-08, `FirmaModo.SESION`).
- Movimientos: trabajador -> almacén; un artículo por cantidad dañado va a BAJA (V-05); una pieza
  dañada entra al almacén como No apta (estado vía `CatalogoService.actualizar_estado_pieza`).
- Reglas: V-01 a V-07, V-11 a V-14, SM-05 (la devolución de algo en resguardo NUNCA se bloquea:
  tampoco por E-02, trabajador no vigente).
- `bloqueos`: el trabajador, las existencias (ubicación del trabajador y del almacén, artículo) y
  las piezas.
"""

from app.modulos.acceso.permisos import P
from app.modulos.movimientos.models import FirmaModo, TipoVale
from app.modulos.movimientos.tipos.base import TipoPendiente


class DevolucionTipo(TipoPendiente):
    tipo = TipoVale.DEVOLUCION
    permiso = P.DEVOLUCIONES_CREAR
    firma_modo = FirmaModo.SESION
    nombre_texto = "La devolución"
