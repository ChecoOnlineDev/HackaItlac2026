"""Evaluador del semáforo: funciones PURAS, sin base de datos (SM-01, SM-06).

Reciben hechos ya cargados (dataclasses de este archivo) y devuelven motivos con el ID de la
regla. Cada regla es una función aparte para probarla una por una. El cargador de contexto
(`cargador.py`) reúne los hechos de la base; el tipo de vale (`tipos/`) los une en una evaluación.

Orden de evaluación (SM-06): código, trabajador, ubicación y existencias, seguridad, límites,
avisos. Si un renglón cae en varias reglas se muestra el nivel más grave y todos los motivos
(SM-01). Los bloques de este archivo los reutilizan los demás tipos de vale; las reglas propias
de un tipo nuevo van en su archivo de `tipos/` (o en un `evaluador_<tipo>.py`), no aquí.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date

from app.modulos.movimientos.models import Nivel

# --------------------------------------------------------------------------- niveles

GRAVEDAD: dict[Nivel, int] = {Nivel.VERDE: 0, Nivel.AMARILLO: 1, Nivel.NARANJA: 2, Nivel.ROJO: 3}

ESTADO_PIEZA_TEXTO: dict[str, str] = {
    "APTO": "apta",
    "NO_APTO": "no apta",
    "EN_MANTENIMIENTO": "en mantenimiento",
    "EN_CALIBRACION": "en calibración",
    "BAJA": "de baja",
}


@dataclass(frozen=True)
class Motivo:
    """Por qué un renglón (o el vale) tiene su nivel. `regla` es el ID, por ejemplo `E-06`."""

    regla: str
    nivel: Nivel
    mensaje: str


def peor_nivel(motivos: list[Motivo]) -> Nivel:
    """SM-01: el nivel más grave de la lista; sin motivos es verde."""
    return max((m.nivel for m in motivos), key=GRAVEDAD.__getitem__, default=Nivel.VERDE)


def fecha_texto(valor: date) -> str:
    return valor.strftime("%d/%m/%Y")


# ----------------------------------------------------------------------------- hechos


@dataclass(frozen=True)
class HechosArticulo:
    """Lo que las reglas necesitan de un artículo. Sin costo (RG-12)."""

    id: uuid.UUID
    codigo: str
    nombre: str
    marca: str | None
    modelo: str | None
    talla: str | None
    unidad: str
    control: str  # PIEZA o CANTIDAD
    retornable: bool
    activo: bool
    motivo_inactivacion: str | None
    requiere_inspeccion: bool
    vigencia_inspeccion_dias: int | None
    requiere_autorizacion: bool
    motivo_uso_especial: str | None
    limite_cantidad: int | None
    limite_periodo_dias: int | None
    cantidad_aviso: int | None


@dataclass(frozen=True)
class HechosPieza:
    id: uuid.UUID
    codigo: str
    numero_serie: str | None
    estado: str
    inspeccion_vigente_hasta: date | None
    ubicacion_id: uuid.UUID | None


@dataclass(frozen=True)
class Titular:
    """Dónde está una pieza según el sistema (E-03): un trabajador, un almacén o una virtual."""

    tipo: str | None  # TRABAJADOR, ALMACEN, VIRTUAL o None (sin ubicación)
    id: uuid.UUID | None
    nombre: str
    descripcion: str  # "la tiene Juan Pérez", "está en el almacén CON", ...
    numero_empleado: str | None = None


@dataclass(frozen=True)
class HechosTrabajador:
    vigente: bool
    motivo_no_vigente: str | None
    pendientes_periodo_anterior: int


@dataclass(frozen=True)
class HechosCuenta:
    """Lo que el trabajador tiene o consumió, para el límite (L-02, L-03)."""

    en_posesion: int
    consumido_en_periodo: int


@dataclass(frozen=True)
class HechosRenglonEntrega:
    codigo: str
    cantidad: int
    # `None` si el código no es de un artículo ni de una pieza.
    articulo: HechosArticulo | None
    pieza: HechosPieza | None
    titular: Titular | None
    ubicacion_almacen_id: uuid.UUID
    existencia_almacen: int
    disponible: int
    cuenta: HechosCuenta
    # Cantidad de renglones anteriores del mismo artículo en este vale (límite acumulado).
    pedido_previo: int = 0


@dataclass(frozen=True)
class HechosInspeccionInicial:
    fecha: date
    resultado: str  # APTO o NO_APTO
    observacion: str | None


@dataclass(frozen=True)
class HechosRenglonEntrada:
    codigo: str
    cantidad: int
    articulo: HechosArticulo | None
    # Datos de la pieza que entra (solo artículos por pieza).
    pieza_codigo: str | None = None
    pieza_serie: str | None = None
    tiene_datos_pieza: bool = False
    codigo_pieza_en_uso: str | None = None  # a qué cosa ya identifica ese código
    serie_en_uso: bool = False
    repetida_en_vale: bool = False
    inspeccion: HechosInspeccionInicial | None = None
    # El código existe pero es de una pieza, una credencial o un vale, no de un artículo.
    codigo_no_es_articulo: bool = False


# ----------------------------------------------------------------------------- trabajador


def regla_e02_vigencia(h: HechosTrabajador) -> Motivo | None:
    """E-02: el trabajador no es vigente. Rojo en todo el vale."""
    if h.vigente:
        return None
    return Motivo(
        "E-02",
        Nivel.ROJO,
        h.motivo_no_vigente or "Ya no forma parte de la plantilla.",
    )


def regla_e12_pendientes_anteriores(h: HechosTrabajador) -> Motivo | None:
    """E-12: trae pendientes de un periodo anterior. Aviso amarillo, no bloquea."""
    if h.pendientes_periodo_anterior <= 0:
        return None
    n = h.pendientes_periodo_anterior
    cosa = "un artículo pendiente" if n == 1 else f"{n} artículos pendientes"
    return Motivo(
        "E-12",
        Nivel.AMARILLO,
        f"Trae {cosa} de un periodo anterior. Revisa su resguardo.",
    )


# ------------------------------------------------------------------------------ entrega


def regla_e01_codigo(h: HechosRenglonEntrega) -> Motivo | None:
    """E-01: el código no existe en el catálogo (o no sirve para entregar)."""
    if h.articulo is None:
        return Motivo(
            "E-01",
            Nivel.ROJO,
            f"El código {h.codigo} no existe en el catálogo.",
        )
    if h.articulo.control == "PIEZA" and h.pieza is None:
        return Motivo(
            "E-01",
            Nivel.ROJO,
            f"{h.articulo.nombre} se controla por pieza: escanea el código de la pieza, "
            "no el del artículo.",
        )
    return None


def regla_e19_inactivo(h: HechosRenglonEntrega) -> Motivo | None:
    """E-19 (CF-10): el artículo está inactivo y no se entrega."""
    if h.articulo is None or h.articulo.activo:
        return None
    motivo = f" ({h.articulo.motivo_inactivacion})" if h.articulo.motivo_inactivacion else ""
    return Motivo("E-19", Nivel.ROJO, f"{h.articulo.nombre} está inactivo{motivo}. No se entrega.")


def regla_e03_ubicacion(h: HechosRenglonEntrega) -> Motivo | None:
    """E-03: la pieza no está en este almacén según el sistema. Se dice dónde está."""
    if h.pieza is None or h.pieza.ubicacion_id == h.ubicacion_almacen_id:
        return None
    donde = h.titular.descripcion if h.titular else "no está registrada en ningún almacén"
    return Motivo("E-03", Nivel.ROJO, f"La pieza no está en este almacén: {donde}.")


def regla_e04_existencia(h: HechosRenglonEntrega) -> Motivo | None:
    """E-04 y RG-05: la cantidad supera la existencia del almacén (una pieza es de a una)."""
    if h.articulo is None:
        return None
    if h.pieza is not None:
        if h.cantidad != 1:
            return Motivo("RG-05", Nivel.ROJO, "Una pieza se entrega de una en una.")
        return None  # que la pieza esté en el almacén ya lo dice E-03
    if h.cantidad > h.existencia_almacen:
        return Motivo(
            "E-04",
            Nivel.ROJO,
            f"Pides {h.cantidad} y en este almacén hay {h.existencia_almacen}.",
        )
    return None


def regla_e05_estado(h: HechosRenglonEntrega) -> Motivo | None:
    """E-05: la pieza está No apta, En mantenimiento, En calibración o de Baja (rojo de
    seguridad: no se autoriza, SM-04)."""
    if h.pieza is None or h.pieza.estado == "APTO":
        return None
    estado = ESTADO_PIEZA_TEXTO.get(h.pieza.estado, h.pieza.estado.lower())
    return Motivo("E-05", Nivel.ROJO, f"La pieza está {estado}. No se puede entregar.")


def regla_e06_inspeccion(h: HechosRenglonEntrega, hoy: date) -> Motivo | None:
    """E-06: la pieza requiere inspección y no tiene una vigente. Una inspección que vence
    hoy todavía es vigente (rojo de seguridad: no se autoriza, SM-04)."""
    if h.pieza is None or h.articulo is None or not h.articulo.requiere_inspeccion:
        return None
    hasta = h.pieza.inspeccion_vigente_hasta
    if hasta is None:
        return Motivo("E-06", Nivel.ROJO, "Sin inspección vigente.")
    if hasta < hoy:
        return Motivo("E-06", Nivel.ROJO, f"Inspección vencida el {fecha_texto(hasta)}.")
    return None


def regla_limite(h: HechosRenglonEntrega) -> Motivo | None:
    """E-07 con L-01 a L-05: supera el límite del artículo. Naranja con el detalle.

    Retornables (L-02): lo que tiene ahora más lo que lleva este vale. Consumibles (L-03): lo
    entregado en los últimos N días más lo que lleva este vale. Sin límite, no aplica (L-01).
    El pedido de renglones anteriores del mismo artículo cuenta: el límite se puede alcanzar
    sumando dos renglones.
    """
    art = h.articulo
    if art is None or art.limite_cantidad is None:
        return None
    if art.retornable:
        regla = "L-02"
        tiene = h.cuenta.en_posesion + h.pedido_previo
        contexto = ""
    else:
        regla = "L-03"
        en_periodo = art.limite_periodo_dias is not None
        base = h.cuenta.consumido_en_periodo if en_periodo else 0
        tiene = base + h.pedido_previo
        contexto = f" en los últimos {art.limite_periodo_dias} días" if en_periodo else ""
    if tiene + h.cantidad <= art.limite_cantidad:
        return None
    return Motivo(
        regla,
        Nivel.NARANJA,
        f"Supera el límite del artículo (límite {art.limite_cantidad}, "
        f"tiene {tiene}{contexto}, pide {h.cantidad}). Requiere autorización.",
    )


def tiene_para_limite(h: HechosRenglonEntrega) -> int | None:
    """Lo que cuenta contra el límite antes de este renglón (lo que tiene o consumió en el periodo
    más lo de renglones anteriores del vale); `None` si el artículo no tiene límite."""
    art = h.articulo
    if art is None or art.limite_cantidad is None:
        return None
    if art.retornable:
        return h.cuenta.en_posesion + h.pedido_previo
    base = h.cuenta.consumido_en_periodo if art.limite_periodo_dias is not None else 0
    return base + h.pedido_previo


def excedente_limite(h: HechosRenglonEntrega) -> int:
    """Cuánto pasa del límite (para la solicitud de autorización); 0 si no pasa."""
    art = h.articulo
    if art is None or art.limite_cantidad is None:
        return 0
    base = (
        h.cuenta.en_posesion
        if art.retornable
        else (h.cuenta.consumido_en_periodo if art.limite_periodo_dias is not None else 0)
    )
    return max(0, base + h.pedido_previo + h.cantidad - art.limite_cantidad)


def regla_e26_autorizacion(h: HechosRenglonEntrega) -> Motivo | None:
    """E-26: el artículo pide autorización del supervisor en cada entrega. Naranja."""
    if h.articulo is None or not h.articulo.requiere_autorizacion:
        return None
    detalle = f": {h.articulo.motivo_uso_especial}" if h.articulo.motivo_uso_especial else ""
    return Motivo(
        "E-26",
        Nivel.NARANJA,
        f"Artículo de uso especial{detalle}. Requiere autorización del supervisor.",
    )


def regla_e27_cantidad_inusual(h: HechosRenglonEntrega) -> Motivo | None:
    """E-27: la cantidad alcanza el aviso de cantidad inusual. Amarillo; pide confirmar."""
    art = h.articulo
    if art is None or art.cantidad_aviso is None or h.cantidad < art.cantidad_aviso:
        return None
    return Motivo(
        "E-27",
        Nivel.AMARILLO,
        f"Cantidad inusual: {h.cantidad} alcanza el aviso de {art.cantidad_aviso}. "
        "Confirma que es correcta.",
    )


@dataclass
class ResultadoRenglon:
    motivos: list[Motivo] = field(default_factory=list)
    requiere_confirmacion: bool = False
    pide_observacion: bool = False

    @property
    def nivel(self) -> Nivel:
        return peor_nivel(self.motivos)


def evaluar_renglon_entrega(
    h: HechosRenglonEntrega, hoy: date, motivo_trabajador: Motivo | None = None
) -> ResultadoRenglon:
    """Une las reglas de la entrega en el orden de SM-06.

    `motivo_trabajador` es el de E-02 (rojo en todo el vale), que se copia a cada renglón.
    """
    motivos: list[Motivo] = []

    def agregar(motivo: Motivo | None) -> None:
        if motivo is not None:
            motivos.append(motivo)

    agregar(regla_e01_codigo(h))  # código
    agregar(regla_e19_inactivo(h))
    agregar(motivo_trabajador)  # trabajador
    if h.articulo is None:
        return ResultadoRenglon(motivos)
    agregar(regla_e03_ubicacion(h))  # ubicación y existencias
    agregar(regla_e04_existencia(h))
    agregar(regla_e05_estado(h))  # seguridad
    agregar(regla_e06_inspeccion(h, hoy))
    agregar(regla_limite(h))  # límites
    agregar(regla_e26_autorizacion(h))
    aviso = regla_e27_cantidad_inusual(h)  # avisos
    agregar(aviso)
    return ResultadoRenglon(motivos, requiere_confirmacion=aviso is not None)


# ------------------------------------------------------------------------------ entrada


def evaluar_renglon_entrada(h: HechosRenglonEntrada, hoy: date) -> ResultadoRenglon:
    """Reglas I-01 a I-04 y I-09 de un renglón de entrada.

    - E-01: el código del artículo no existe.
    - I-09: un artículo inactivo no recibe entradas.
    - I-02: cada pieza entra con su código único y su número de serie.
    - I-03: una pieza que requiere inspección entra con su inspección inicial; sin ella queda
      pendiente (aviso amarillo; no se puede entregar).
    """
    motivos: list[Motivo] = []
    art = h.articulo
    if art is None:
        texto = (
            f"El código {h.codigo} no es de un artículo del catálogo."
            if h.codigo_no_es_articulo
            else f"El código {h.codigo} no existe en el catálogo."
        )
        motivos.append(Motivo("E-01", Nivel.ROJO, texto))
        return ResultadoRenglon(motivos)
    if not art.activo:
        motivo = f" ({art.motivo_inactivacion})" if art.motivo_inactivacion else ""
        motivos.append(
            Motivo("I-09", Nivel.ROJO, f"{art.nombre} está inactivo{motivo}. No recibe entradas.")
        )
    if art.control == "CANTIDAD":
        if h.tiene_datos_pieza:
            motivos.append(
                Motivo(
                    "I-02",
                    Nivel.ROJO,
                    f"{art.nombre} se controla por cantidad: no lleva código de pieza.",
                )
            )
        return ResultadoRenglon(motivos)

    # Artículo por pieza.
    if h.cantidad != 1:
        motivos.append(Motivo("RG-05", Nivel.ROJO, "Una pieza entra de una en una."))
    codigo_pieza = (h.pieza_codigo or "").strip()
    serie = (h.pieza_serie or "").strip()
    if not codigo_pieza:
        motivos.append(Motivo("I-02", Nivel.ROJO, "Captura el código de la pieza."))
    elif h.codigo_pieza_en_uso:
        motivos.append(
            Motivo(
                "I-02",
                Nivel.ROJO,
                f"El código {codigo_pieza} ya identifica {h.codigo_pieza_en_uso}.",
            )
        )
    elif h.repetida_en_vale:
        motivos.append(
            Motivo("I-02", Nivel.ROJO, f"El código {codigo_pieza} está repetido en este vale.")
        )
    if not serie:
        motivos.append(Motivo("I-02", Nivel.ROJO, "Captura el número de serie de la pieza."))
    elif h.serie_en_uso:
        motivos.append(
            Motivo(
                "I-02",
                Nivel.ROJO,
                f"Ya existe una pieza de este artículo con el número de serie {serie}.",
            )
        )
    if art.requiere_inspeccion:
        insp = h.inspeccion
        if insp is None:
            motivos.append(
                Motivo(
                    "I-03",
                    Nivel.AMARILLO,
                    "Entra sin inspección inicial: queda pendiente y no se puede entregar.",
                )
            )
        else:
            if insp.fecha > hoy:
                motivos.append(
                    Motivo("I-03", Nivel.ROJO, "La fecha de la inspección no puede ser futura.")
                )
            if insp.resultado == "NO_APTO" and not (insp.observacion or "").strip():
                motivos.append(
                    Motivo(
                        "I-03",
                        Nivel.ROJO,
                        "Una inspección No apta necesita observación.",
                    )
                )
    return ResultadoRenglon(motivos)
