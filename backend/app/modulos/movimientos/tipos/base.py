"""Contrato común de los tipos de vale: `ManejadorTipo`.

Cada tipo de vale es una clase en su archivo de `tipos/` que hereda de `ManejadorTipo`, se
registra en `tipos/__init__.py` (tabla `TIPOS`) y llena los ganchos de abajo. El motor
(`service.py`) no cambia por un tipo nuevo: evalúa, bloquea, confirma y escribe llamando a estos
ganchos. Ver `README.md` del módulo para el recorrido completo y el orden de llamadas.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from app.modulos.movimientos.contexto import (
    ContextoVale,
    DatosVale,
    Evaluacion,
    MovimientoNuevo,
    PlanBloqueo,
    RenglonEvaluado,
)
from app.modulos.movimientos.evaluador import HechosArticulo, HechosPieza, Titular
from app.modulos.movimientos.exceptions import TipoNoImplementado
from app.modulos.movimientos.models import FirmaModo, TipoVale, Vale
from app.modulos.movimientos.schemas import RenglonIn, ValeIn

if TYPE_CHECKING:
    import uuid

    from app.modulos.acceso.models import Usuario
    from app.modulos.almacenes.models import Almacen
    from app.modulos.movimientos.service import MovimientoService


class ManejadorTipo(ABC):
    """Lo que un tipo de vale le pone al motor.

    Atributos de clase:
      `tipo`          el valor de `TipoVale` que atiende.
      `permiso`       la clave de permiso que exige (se verifica por clave, nunca por rol).
      `requiere_firma` si la confirmación necesita la firma del trabajador en pantalla (F-02).
      `firma_modo`    `PANTALLA` (firma el trabajador) o `SESION` (basta la sesión, F-03); `None`
                      si el vale no lleva firma.
      `admite_sin_renglones` si el vale puede confirmarse sin renglones (solo NO_ADEUDO).
    """

    tipo: TipoVale
    permiso: str
    requiere_firma: bool = False
    firma_modo: FirmaModo | None = None
    # Verdadero solo en NO_ADEUDO: un vale sin renglones ni movimientos.
    admite_sin_renglones: bool = False

    # ---------------------------------------------------------- antes de tocar la base

    def validar_cuerpo(self, cuerpo: ValeIn, *, confirmar: bool) -> None:
        """Valida los campos propios del tipo (422 `DATOS_INVALIDOS`). Corre antes de cualquier
        consulta. `confirmar` es verdadero en `POST /api/vales` (ahí se exige firma, renglones)."""
        return None

    def exigir_al_confirmar(self, cuerpo: ValeIn, evaluacion: Evaluacion) -> None:
        """Gancho de la confirmación, ya con la evaluación hecha bajo bloqueo: el tipo puede
        rechazar con un 422 propio lo que `validar_cuerpo` no ve (depende de la base)."""
        return None

    def almacenes_involucrados(self, ctx: ContextoVale, cuerpo: ValeIn) -> list[Almacen]:
        """Los almacenes que el vale mueve (AL-04: ninguno puede estar cerrado). Por defecto, el
        del vale; el traspaso suma el de destino."""
        return [ctx.almacen]

    def almacen_operativo(
        self, servicio: MovimientoService, usuario: Usuario, cuerpo: ValeIn
    ) -> uuid.UUID:
        """El almacén sobre el que opera el vale. Por defecto, el del usuario (RG-07, AC-06) o el
        `almacen_id` del cuerpo si tiene `almacenes.todos`."""
        return servicio.resolver_almacen_del_vale(usuario, cuerpo.almacen_id)

    def normalizar_renglones(self, ctx: ContextoVale, cuerpo: ValeIn) -> list[RenglonIn]:
        """Ajusta los renglones antes de evaluar (por ejemplo E-15 y E-16: pieza repetida se
        ignora, artículo por cantidad repetido suma). Por defecto, tal como llegaron."""
        return list(cuerpo.renglones)

    # ------------------------------------------------------------------- evaluación

    @abstractmethod
    def evaluar(self, ctx: ContextoVale, cuerpo: ValeIn) -> Evaluacion:
        """El semáforo: nivel y motivos (con ID de regla) por renglón. NO escribe nada: lee con
        `ctx.cargador` y usa las funciones puras de `evaluador.py`. `cuerpo.renglones` ya viene
        normalizado."""

    # ----------------------------------------------------------------- confirmación

    @abstractmethod
    def bloqueos(self, ctx: ContextoVale, cuerpo: ValeIn) -> PlanBloqueo:
        """Qué filas bloquear antes de volver a evaluar: el trabajador, las existencias
        `(ubicacion_id, articulo_id)` que el vale va a leer o cambiar y las piezas. Se calcula con
        lecturas sin bloqueo (identificar códigos); el motor las toma en orden canónico."""

    @abstractmethod
    def datos_vale(self, ctx: ContextoVale, cuerpo: ValeIn, evaluacion: Evaluacion) -> DatosVale:
        """Los campos propios del vale: trabajador, periodo, destino, vale de origen, estado
        inicial y modo de firma."""

    @abstractmethod
    def construir_movimientos(
        self, ctx: ContextoVale, cuerpo: ValeIn, evaluacion: Evaluacion
    ) -> list[MovimientoNuevo]:
        """Los movimientos del vale (origen y destino son ubicaciones). Puede crear entidades
        propias del tipo con `flush` (la ENTRADA crea sus piezas): corre ya con las filas
        bloqueadas y dentro de la transacción de la confirmación. El motor escribe saldos,
        existencias y `pieza.ubicacion_id`."""

    def al_confirmar(
        self,
        ctx: ContextoVale,
        cuerpo: ValeIn,
        evaluacion: Evaluacion,
        vale: Vale,
        movimientos: list[Any],
    ) -> None:
        """Efectos propios del tipo, ya con el vale y sus movimientos insertados y en la misma
        transacción (inspección inicial de la ENTRADA, `vale.estado` del original en una
        RECEPCION o CANCELACION, dejar Inactivo al trabajador en NO_ADEUDO...)."""
        return None

    # ------------------------------------------- operaciones propias de otros endpoints

    def por_recibir(
        self,
        servicio: MovimientoService,
        usuario: Usuario,
        solo_contar: bool = False,
        almacen_id: uuid.UUID | None = None,
    ) -> Any:
        """`GET /api/traspasos/por-recibir` (permiso `traspasos.recibir`). Solo RECEPCION.
        `solo_contar` devuelve solo `{total}`; `almacen_id` lo usa quien tiene `almacenes.todos`."""
        raise TipoNoImplementado()

    def emitir_no_adeudo(
        self,
        servicio: MovimientoService,
        usuario: Usuario,
        trabajador_id: uuid.UUID,
        datos: Any,
    ) -> Any:
        """`POST /api/trabajadores/{id}/no-adeudo` (permiso `no_adeudo.emitir`). Solo NO_ADEUDO."""
        raise TipoNoImplementado()

    def cancelar(
        self,
        servicio: MovimientoService,
        usuario: Usuario,
        vale_id: uuid.UUID,
        datos: Any,
    ) -> Any:
        """`POST /api/vales/{id}/cancelacion` (permiso `vales.cancelar`; con
        `vales.cancelar_todos`, los de cualquiera). Solo CANCELACION."""
        raise TipoNoImplementado()


class TipoPendiente(ManejadorTipo):
    """Stub de un tipo que otro agente va a implementar: todo lanza `TipoNoImplementado` (501).

    Quien lo implemente reemplaza la herencia por `ManejadorTipo` y llena los ganchos."""

    nombre_texto: str = "Esta operación"

    def _pendiente(self) -> TipoNoImplementado:
        return TipoNoImplementado(f"{self.nombre_texto} todavía no está disponible.")

    def validar_cuerpo(self, cuerpo: ValeIn, *, confirmar: bool) -> None:
        raise self._pendiente()

    def evaluar(self, ctx: ContextoVale, cuerpo: ValeIn) -> Evaluacion:
        raise self._pendiente()

    def bloqueos(self, ctx: ContextoVale, cuerpo: ValeIn) -> PlanBloqueo:
        raise self._pendiente()

    def datos_vale(self, ctx: ContextoVale, cuerpo: ValeIn, evaluacion: Evaluacion) -> DatosVale:
        raise self._pendiente()

    def construir_movimientos(
        self, ctx: ContextoVale, cuerpo: ValeIn, evaluacion: Evaluacion
    ) -> list[MovimientoNuevo]:
        raise self._pendiente()

    def por_recibir(self, servicio, usuario, solo_contar=False, almacen_id=None) -> Any:
        raise self._pendiente()

    def emitir_no_adeudo(self, servicio, usuario, trabajador_id, datos) -> Any:
        raise self._pendiente()

    def cancelar(self, servicio, usuario, vale_id, datos) -> Any:
        raise self._pendiente()


# ------------------------------------------------------------- vistas para la evaluación


def vista_articulo(a: HechosArticulo) -> dict[str, Any]:
    """Lo que la evaluación dice de un artículo. Nunca incluye costos (RG-12)."""
    return {
        "id": a.id,
        "codigo": a.codigo,
        "nombre": a.nombre,
        "marca": a.marca,
        "modelo": a.modelo,
        "talla": a.talla,
        "unidad": a.unidad,
        "control": a.control,
        "retornable": a.retornable,
        "activo": a.activo,
        "motivo_uso_especial": a.motivo_uso_especial,
    }


def vista_pieza(p: HechosPieza) -> dict[str, Any]:
    return {
        "id": p.id,
        "codigo": p.codigo,
        "numero_serie": p.numero_serie,
        "estado": p.estado,
        "inspeccion_vigente_hasta": p.inspeccion_vigente_hasta,
    }


def vista_titular(t: Titular) -> dict[str, Any]:
    return {
        "tipo": t.tipo,
        "id": t.id,
        "nombre": t.nombre,
        "descripcion": t.descripcion,
        "numero_empleado": t.numero_empleado,
    }


def motivos_ids(renglon: RenglonEvaluado) -> list[str]:
    """IDs de regla de un renglón, sin repetir y en orden (se guardan en `movimiento.reglas`)."""
    vistos: list[str] = []
    for motivo in renglon.motivos:
        if motivo.regla not in vistos:
            vistos.append(motivo.regla)
    return vistos
