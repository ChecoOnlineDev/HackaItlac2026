"""Tipos de valor que el motor y los tipos de vale se pasan (sin HTTP).

- `ContextoVale`: lo que un tipo necesita para evaluar y confirmar (sesión, usuario, almacén...).
- `Evaluacion` y `RenglonEvaluado`: el resultado del semáforo.
- `PlanBloqueo`: qué filas se bloquean antes de volver a evaluar al confirmar.
- `MovimientoNuevo` y `DatosVale`: lo que el tipo le pide escribir al motor.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from app.modulos.acceso.models import Usuario
from app.modulos.almacenes.models import Almacen, Ubicacion
from app.modulos.movimientos.evaluador import GRAVEDAD, Motivo, peor_nivel
from app.modulos.movimientos.models import EstadoVale, FirmaModo, Nivel

if TYPE_CHECKING:
    from app.modulos.movimientos.cargador import Cargador
    from app.modulos.trabajadores.schemas import FichaBreveOut


@dataclass
class ContextoVale:
    """Se arma una vez por evaluación o confirmación. `cargador` lee los hechos de la base;
    `bloqueado` es verdadero al confirmar (las filas ya están bloqueadas)."""

    session: Session
    usuario: Usuario
    almacen: Almacen
    ubicacion_almacen: Ubicacion
    cargador: Cargador
    hoy: date
    ahora: datetime
    bloqueado: bool = False


@dataclass
class RenglonEvaluado:
    """Un renglón con su nivel y motivos. Los campos `*_id` y `extra` son internos del motor:
    no se envían tal cual al cliente."""

    renglon: int
    codigo: str
    cantidad: int
    motivos: list[Motivo] = field(default_factory=list)
    articulo_id: uuid.UUID | None = None
    pieza_id: uuid.UUID | None = None
    articulo: dict[str, Any] | None = None
    pieza: dict[str, Any] | None = None
    titular: dict[str, Any] | None = None
    disponible: int | None = None
    pide_observacion: bool = False
    requiere_confirmacion: bool = False
    # Un naranja que la autorización del vale ya cubre.
    autorizado: bool = False
    # Datos del tipo para construir los movimientos (por ejemplo, la pieza que entra).
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def nivel(self) -> Nivel:
        return peor_nivel(self.motivos)

    @property
    def autorizable(self) -> bool:
        """Solo un naranja se autoriza; con un rojo en el renglón no (SM-04, A-06)."""
        return self.nivel == Nivel.NARANJA


@dataclass(frozen=True)
class RutaEvaluada:
    """La ruta de un TRASPASO tal como la evaluó el servidor (X-03, X-16 a X-18): la interfaz
    muestra esto y no decide nada. `clase` y `autoriza` son valores de `ClaseRuta` y
    `QuienAutoriza`; `autorizadores_disponibles` solo se llena en X-17."""

    clase: str
    autoriza: str
    autorizadores_disponibles: int | None = None


@dataclass
class Evaluacion:
    renglones: list[RenglonEvaluado] = field(default_factory=list)
    # Motivos que valen para todo el vale (E-12).
    motivos_vale: list[Motivo] = field(default_factory=list)
    trabajador: FichaBreveOut | None = None
    # Mensaje de la autorización indicada si no sirve (solo en `evaluar`).
    autorizacion_error: str | None = None
    # Lo fija el motor según el tipo: el vale de no adeudo no lleva renglones.
    admite_sin_renglones: bool = False
    # El vale mismo pide una observación (X-03: ruta no habitual del Administrador).
    pide_observacion_vale: bool = False
    # Solo en TRASPASO: la clase de la ruta y quién la autoriza (FEAT-015).
    ruta: RutaEvaluada | None = None
    # X-17: la autorización de traslado indicada sirve para este vale.
    autorizado_vale: bool = False
    proyecto: dict[str, Any] | None = None
    proyectos_del_trabajador: list[dict[str, Any]] = field(default_factory=list)
    pide_proyecto: bool = False
    requiere_aprobacion_despacho: bool = False
    despacho_modo: str = "NO_APLICA"
    # Datos internos que el tipo le deja al motor (nunca salen al cliente).
    datos: dict[str, Any] = field(default_factory=dict)

    @property
    def nivel(self) -> Nivel:
        niveles = [*(m.nivel for m in self.motivos_vale), *(r.nivel for r in self.renglones)]
        return max(niveles, key=GRAVEDAD.__getitem__, default=Nivel.VERDE)

    @property
    def pide_observacion(self) -> bool:
        """Algún renglón pide observación (E-09 en la entrega); uno en rojo no cuenta."""
        if self.pide_observacion_vale and self.nivel != Nivel.ROJO:
            return True
        return any(r.pide_observacion and r.nivel != Nivel.ROJO for r in self.renglones)

    @property
    def puede_confirmar(self) -> bool:
        """SM-03: sin rojos y con todos los naranjas autorizados. Debe haber algún renglón (salvo
        en los tipos que no los llevan)."""
        if not self.renglones and not self.admite_sin_renglones:
            return False
        if self.nivel == Nivel.ROJO:
            return False
        if self.pide_proyecto and self.proyecto is None:
            return False
        if self.requiere_aprobacion_despacho and not self.autorizado_vale:
            return False
        # X-17: el traslado lateral de quien no es supervisor del origen pide la autorización.
        if not self.autorizado_vale and any(m.regla == "X-17" for m in self.motivos_vale):
            return False
        return all(r.autorizado for r in self.renglones if r.nivel == Nivel.NARANJA)


@dataclass
class PlanBloqueo:
    """Filas que la confirmación bloquea antes de volver a evaluar. El motor las toma en el
    orden canónico (vales, trabajador, existencias, piezas, serie de folio)."""

    trabajador_id: uuid.UUID | None = None
    vales: set[uuid.UUID] = field(default_factory=set)
    # (ubicacion_id, articulo_id)
    existencias: set[tuple[uuid.UUID, uuid.UUID]] = field(default_factory=set)
    piezas: set[uuid.UUID] = field(default_factory=set)


@dataclass
class MovimientoNuevo:
    """Un movimiento que el tipo le pide escribir al motor. El motor agrega el vale, los saldos
    y la fecha. `origen_id` y `destino_id` son ubicaciones."""

    renglon: int
    articulo_id: uuid.UUID
    cantidad: int
    origen_id: uuid.UUID
    destino_id: uuid.UUID
    pieza_id: uuid.UUID | None = None
    trabajador_id: uuid.UUID | None = None
    condicion: str | None = None
    motivo_baja: str | None = None
    nivel: Nivel = Nivel.VERDE
    reglas: list[str] = field(default_factory=list)
    observacion: str | None = None


@dataclass
class DatosVale:
    """Los campos del vale que fija el tipo (el motor pone folio, token, firma y responsable)."""

    trabajador_id: uuid.UUID | None = None
    periodo_contrato_id: uuid.UUID | None = None
    proyecto_id: uuid.UUID | None = None
    destino_almacen_id: uuid.UUID | None = None
    vale_origen_id: uuid.UUID | None = None
    estado: str = EstadoVale.EMITIDO
    firma_modo: FirmaModo | None = None
    observacion: str | None = None
