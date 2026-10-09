"""Tabla de tipos de vale: un `ManejadorTipo` por valor de `TipoVale`.

Para enchufar un tipo nuevo: crea su clase en su archivo de este paquete y regístrala aquí. El
motor (`service.py`) y el router no cambian.
"""

from app.modulos.movimientos.models import TipoVale
from app.modulos.movimientos.tipos.ajuste import AjusteTipo
from app.modulos.movimientos.tipos.base import ManejadorTipo
from app.modulos.movimientos.tipos.cancelacion import CancelacionTipo
from app.modulos.movimientos.tipos.devolucion import DevolucionTipo
from app.modulos.movimientos.tipos.entrada import EntradaTipo
from app.modulos.movimientos.tipos.entrega import EntregaTipo
from app.modulos.movimientos.tipos.no_adeudo import NoAdeudoTipo
from app.modulos.movimientos.tipos.recepcion import RecepcionTipo
from app.modulos.movimientos.tipos.traspaso import TraspasoTipo

TIPOS: dict[TipoVale, ManejadorTipo] = {
    TipoVale.ENTRADA: EntradaTipo(),
    TipoVale.ENTREGA: EntregaTipo(),
    TipoVale.DEVOLUCION: DevolucionTipo(),
    TipoVale.TRASPASO: TraspasoTipo(),
    TipoVale.RECEPCION: RecepcionTipo(),
    TipoVale.NO_ADEUDO: NoAdeudoTipo(),
    TipoVale.CANCELACION: CancelacionTipo(),
    TipoVale.AJUSTE: AjusteTipo(),
}

assert set(TIPOS) == set(TipoVale), "Cada tipo de vale debe estar registrado"


def manejador_de(tipo: TipoVale | str) -> ManejadorTipo:
    return TIPOS[TipoVale(tipo)]
