"""Reglas de los traspasos entre almacenes (TRASPASO y RECEPCION): funciones PURAS.

Sin base de datos: reciben hechos ya cargados y devuelven motivos con el ID de la regla. Los
tipos `tipos/traspaso.py` y `tipos/recepcion.py` los unen en una evaluación.

Salida (TRASPASO): X-02 (solo sale lo que está en el origen), X-03 (ruta), X-04 (pieza No apta),
X-09 (artículo inactivo). Recepción (RECEPCION): X-10 (solo el destino recibe), X-12 (lo escaneado
no pertenece al traspaso), X-13 (faltan renglones: quedan En tránsito) y el estado del traspaso.
"""

import uuid
from dataclasses import dataclass

from app.modulos.movimientos.evaluador import (
    ESTADO_PIEZA_TEXTO,
    HechosArticulo,
    HechosPieza,
    Motivo,
    Titular,
)
from app.modulos.movimientos.models import EstadoVale, Nivel

# ------------------------------------------------------------------------------ salida


@dataclass(frozen=True)
class HechosAlmacen:
    """Lo que la ruta necesita de un almacén."""

    id: uuid.UUID
    clave: str
    nombre: str
    padre_id: uuid.UUID | None
    activo: bool


@dataclass(frozen=True)
class HechosRenglonTraspaso:
    codigo: str
    cantidad: int
    # `None` si el código no es de un artículo ni de una pieza.
    articulo: HechosArticulo | None
    pieza: HechosPieza | None
    titular: Titular | None  # dónde está la pieza, si no está en el origen
    ubicacion_origen_id: uuid.UUID
    existencia_origen: int
    # Cantidad que piden los renglones anteriores del mismo artículo en este vale.
    pedido_previo: int = 0


def es_ruta_habitual(origen: HechosAlmacen, destino: HechosAlmacen) -> bool:
    """X-03: Kepler con Contratistas y Contratistas con las áreas, en ambos sentidos. La red se
    arma con `almacen.padre_id` (Kepler -> Contratistas -> áreas): una ruta es habitual si un
    almacén es el padre del otro."""
    return origen.padre_id == destino.id or destino.padre_id == origen.id


def regla_x03_ruta(origen: HechosAlmacen, destino: HechosAlmacen) -> Motivo:
    """X-03: el destino es otro almacén. Ruta habitual: verde; otra ruta: aviso amarillo.
    Mismo almacén, o un destino cerrado, es rojo."""
    if destino.id == origen.id:
        return Motivo("X-03", Nivel.ROJO, "El destino debe ser otro almacén, no el de origen.")
    if not destino.activo:
        return Motivo(
            "X-03", Nivel.ROJO, f"El almacén {destino.nombre} está cerrado y no recibe traspasos."
        )
    if es_ruta_habitual(origen, destino):
        return Motivo("X-03", Nivel.VERDE, f"Ruta habitual: de {origen.nombre} a {destino.nombre}.")
    return Motivo(
        "X-03",
        Nivel.AMARILLO,
        f"Ruta poco habitual: de {origen.nombre} a {destino.nombre}. Lo habitual es enviar entre "
        "Kepler y Contratistas, y entre Contratistas y las áreas. Revisa que sea correcto.",
    )


def regla_x02_codigo(h: HechosRenglonTraspaso) -> Motivo | None:
    """X-02: el código no es de algo que se pueda enviar (no existe, o es el de un artículo por
    pieza y falta escanear la pieza)."""
    if h.articulo is None:
        return Motivo("X-02", Nivel.ROJO, f"El código {h.codigo} no existe en el catálogo.")
    if h.articulo.control == "PIEZA" and h.pieza is None:
        return Motivo(
            "X-02",
            Nivel.ROJO,
            f"{h.articulo.nombre} se controla por pieza: escanea el código de la pieza, "
            "no el del artículo.",
        )
    return None


def regla_x02_origen(h: HechosRenglonTraspaso) -> Motivo | None:
    """X-02 (con RG-04 y RG-05): solo sale lo que está en el almacén de origen. Una pieza que
    está en otro lugar, o una cantidad mayor a la existencia, es rojo."""
    if h.articulo is None:
        return None
    if h.pieza is not None:
        if h.pieza.ubicacion_id != h.ubicacion_origen_id:
            donde = h.titular.descripcion if h.titular else "no está registrada en ningún almacén"
            return Motivo("X-02", Nivel.ROJO, f"La pieza no está en este almacén: {donde}.")
        if h.cantidad != 1:
            return Motivo("RG-05", Nivel.ROJO, "Una pieza se envía de una en una.")
        return None
    if h.cantidad + h.pedido_previo > h.existencia_origen:
        return Motivo(
            "X-02",
            Nivel.ROJO,
            f"Envías {h.cantidad + h.pedido_previo} y en este almacén hay {h.existencia_origen}.",
        )
    return None


def regla_x04_pieza_no_apta(h: HechosRenglonTraspaso) -> Motivo | None:
    """X-04: una pieza que no está Apta se puede trasladar (para reparación o baja) y conserva su
    estado. Aviso amarillo."""
    if h.pieza is None or h.pieza.estado == "APTO":
        return None
    estado = ESTADO_PIEZA_TEXTO.get(h.pieza.estado, h.pieza.estado.lower())
    return Motivo(
        "X-04",
        Nivel.AMARILLO,
        f"La pieza está {estado}. Se puede enviar y conserva su estado.",
    )


def regla_x09_inactivo(h: HechosRenglonTraspaso) -> Motivo | None:
    """X-09: un artículo inactivo sí puede trasladarse. No cambia el nivel: solo lo informa."""
    if h.articulo is None or h.articulo.activo:
        return None
    return Motivo(
        "X-09",
        Nivel.VERDE,
        f"{h.articulo.nombre} está inactivo; aun así se puede enviar a otro almacén.",
    )


def evaluar_renglon_traspaso(h: HechosRenglonTraspaso) -> list[Motivo]:
    """Orden SM-06: código, ubicación y existencia, avisos."""
    if (motivo := regla_x02_codigo(h)) is not None:
        return [motivo]
    motivos = [
        regla_x02_origen(h),
        regla_x04_pieza_no_apta(h),
        regla_x09_inactivo(h),
    ]
    return [m for m in motivos if m is not None]


# --------------------------------------------------------------------------- recepción


@dataclass(frozen=True)
class HechosRenglonRecepcion:
    codigo: str
    cantidad: int
    articulo: HechosArticulo | None
    pieza: HechosPieza | None
    # Lo que el traspaso envió de esta pieza o de este artículo, y lo ya recibido en
    # recepciones anteriores (0 si el traspaso no lo trae).
    enviada: int
    recibida: int
    # Cantidad que piden los renglones anteriores del mismo artículo en esta recepción.
    pedido_previo: int = 0

    @property
    def pendiente(self) -> int:
        return max(self.enviada - self.recibida, 0)


def regla_x10_destino(
    destino: HechosAlmacen, almacen_actual_id: uuid.UUID, almacen_actual_nombre: str
) -> Motivo | None:
    """X-10: solo el almacén de destino puede recibir. Rojo si es otro."""
    if destino.id == almacen_actual_id:
        return None
    return Motivo(
        "X-10",
        Nivel.ROJO,
        f"Este traspaso va al almacén {destino.nombre}. {almacen_actual_nombre} no puede "
        "recibirlo.",
    )


def regla_estado_del_traspaso(estado: str) -> Motivo | None:
    """Un traspaso cancelado (X-14) o ya recibido por completo no se recibe (X-12)."""
    if estado == EstadoVale.CANCELADO:
        return Motivo("X-14", Nivel.ROJO, "El traspaso fue cancelado. Ya no se puede recibir.")
    if estado == EstadoVale.RECIBIDO:
        return Motivo("X-12", Nivel.ROJO, "Este traspaso ya se recibió completo.")
    return None


def regla_x12_pertenece(h: HechosRenglonRecepcion) -> Motivo | None:
    """X-12: lo escaneado no pertenece a este traspaso (o ya se recibió). Rojo."""
    if h.articulo is None:
        return Motivo(
            "X-12", Nivel.ROJO, f"El código {h.codigo} no existe: no pertenece a este traspaso."
        )
    if h.articulo.control == "PIEZA" and h.pieza is None:
        return Motivo(
            "X-12",
            Nivel.ROJO,
            f"{h.articulo.nombre} se controla por pieza: escanea el código de la pieza, "
            "no el del artículo.",
        )
    if h.pieza is not None:
        if h.enviada == 0:
            return Motivo("X-12", Nivel.ROJO, "Esta pieza no viene en este traspaso.")
        if h.recibida >= h.enviada:
            return Motivo("X-12", Nivel.ROJO, "Esta pieza ya se recibió.")
        if h.cantidad != 1:
            return Motivo("RG-05", Nivel.ROJO, "Una pieza se recibe de una en una.")
        return None
    if h.enviada == 0:
        return Motivo("X-12", Nivel.ROJO, f"{h.articulo.nombre} no viene en este traspaso.")
    pendiente = h.pendiente - h.pedido_previo
    if pendiente <= 0:
        return Motivo("X-12", Nivel.ROJO, f"Ya se recibió todo lo de {h.articulo.nombre}.")
    if h.cantidad > pendiente:
        return Motivo(
            "X-12",
            Nivel.ROJO,
            f"Recibes {h.cantidad} y de este traspaso faltan por recibir {pendiente}.",
        )
    return None


def regla_x13_diferencias(faltan: int) -> Motivo | None:
    """X-13: si falta algo, lo no recibido sigue En tránsito y el traspaso queda "Recibido con
    diferencias". Aviso amarillo (no bloquea)."""
    if faltan <= 0:
        return None
    cosa = "1 pieza o artículo" if faltan == 1 else f"{faltan} piezas o artículos"
    return Motivo(
        "X-13",
        Nivel.AMARILLO,
        f"Con esta recepción faltarían {cosa}. Lo que falta sigue En tránsito y el traspaso "
        "queda como Recibido con diferencias.",
    )


def estado_despues_de_recibir(pendiente_total: int) -> EstadoVale:
    """X-13: sin nada pendiente el traspaso queda Recibido; con algo pendiente, Recibido con
    diferencias (lo no recibido sigue En tránsito)."""
    return EstadoVale.RECIBIDO if pendiente_total <= 0 else EstadoVale.RECIBIDO_CON_DIFERENCIAS
