"""Reglas PURAS de la DEVOLUCION (V-01 a V-07, V-12, V-14, RG-05): sin base de datos.

Reciben hechos ya cargados (`HechosRenglonDevolucion`) y devuelven motivos con el ID de la regla.
Cada regla es una función aparte para probarla una por una. El tipo (`tipos/devolucion.py`) reúne
los hechos con el cargador y une las reglas con `evaluar_renglon_devolucion` (orden SM-06).

SM-05: la devolución de algo que está en resguardo NUNCA se bloquea. Por eso aquí no existe ninguna
regla sobre la vigencia del trabajador (E-02), los límites, la autorización ni el artículo inactivo
(CF-11): ninguna se evalúa.
"""

import uuid
from dataclasses import dataclass, field

from app.modulos.movimientos.evaluador import (
    HechosArticulo,
    HechosPieza,
    Motivo,
    Titular,
)
from app.modulos.movimientos.models import Condicion, Nivel


@dataclass(frozen=True)
class HechosRenglonDevolucion:
    codigo: str
    cantidad: int
    condicion: str | None
    observacion: str | None
    # `None` si el código no es de un artículo ni de una pieza.
    articulo: HechosArticulo | None
    pieza: HechosPieza | None
    # El código existe pero es de una credencial o de un vale, no de un equipo.
    codigo_ajeno: bool = False
    # Pieza: dónde está según el sistema. Por cantidad: el trabajador indicado (o `None`).
    titular: Titular | None = None
    # Por cantidad: lo que ese trabajador tiene en resguardo de este artículo, y lo que ya
    # devuelven los renglones anteriores del mismo artículo en este vale.
    en_resguardo: int = 0
    pedido_previo: int = 0
    # V-07: el almacén que lo entregó (si es otro del que recibe, se avisa).
    entrego_almacen_id: uuid.UUID | None = None
    entrego_almacen_texto: str | None = None
    ubicacion_almacen_id: uuid.UUID | None = None


@dataclass
class ResultadoDevolucion:
    motivos: list[Motivo] = field(default_factory=list)
    pide_observacion: bool = False
    # V-02: no hay nada que devolver; el renglón no genera movimiento.
    sin_movimiento: bool = False


def regla_v12_codigo(h: HechosRenglonDevolucion) -> Motivo | None:
    """V-12: el código no existe en el catálogo, o no es de un equipo. No es de la empresa."""
    if h.articulo is not None:
        return None
    if h.codigo_ajeno:
        return Motivo(
            "V-12",
            Nivel.ROJO,
            f"El código {h.codigo} no es de un equipo de la empresa. No se recibe.",
        )
    return Motivo(
        "V-12",
        Nivel.ROJO,
        f"No es de la empresa: el código {h.codigo} no existe en el catálogo. No se recibe y "
        "el pendiente del trabajador sigue abierto.",
    )


def regla_v14_pieza_sin_codigo(h: HechosRenglonDevolucion) -> Motivo | None:
    """V-14: un artículo por pieza no se devuelve con el código del artículo; se escanea la pieza,
    se elige de la lista del trabajador o se busca por su número de serie."""
    if h.articulo is None or h.articulo.control != "PIEZA" or h.pieza is not None:
        return None
    return Motivo(
        "V-14",
        Nivel.ROJO,
        f"{h.articulo.nombre} se controla por pieza: escanea la pieza, elígela de la lista del "
        "trabajador o búscala por su número de serie.",
    )


def regla_v02_sin_resguardo(h: HechosRenglonDevolucion) -> Motivo | None:
    """V-02: la pieza no está en resguardo de nadie. Nada que devolver; se dice dónde está."""
    if h.pieza is None:
        return None
    if h.titular is not None and h.titular.tipo == "TRABAJADOR":
        return None
    donde = h.titular.descripcion if h.titular else "no está registrada en ningún lugar"
    return Motivo(
        "V-02",
        Nivel.AMARILLO,
        f"No está en resguardo de nadie: la pieza {donde}. No hay nada que devolver.",
    )


def regla_rg05_pieza_de_una(h: HechosRenglonDevolucion) -> Motivo | None:
    """RG-05: una pieza se devuelve de una en una."""
    if h.pieza is not None and h.cantidad != 1:
        return Motivo("RG-05", Nivel.ROJO, "Una pieza se devuelve de una en una.")
    return None


def regla_v03_cantidad(h: HechosRenglonDevolucion) -> Motivo | None:
    """V-03: por cantidad se identifica al trabajador y no se acepta más de lo que tiene."""
    if h.articulo is None or h.articulo.control != "CANTIDAD":
        return None
    if h.titular is None:
        return Motivo("V-03", Nivel.ROJO, "Indica de qué trabajador es la devolución.")
    disponible = h.en_resguardo - h.pedido_previo
    if h.cantidad > max(disponible, 0):
        return Motivo(
            "V-03",
            Nivel.ROJO,
            f"{h.titular.nombre} tiene {max(disponible, 0)} de {h.articulo.nombre} y se "
            f"intenta devolver {h.cantidad}.",
        )
    return None


def regla_v04_condicion(h: HechosRenglonDevolucion) -> Motivo | None:
    """V-04: la condición al volver es obligatoria (Bueno, Desgaste por uso o Dañado)."""
    if h.condicion is None:
        return Motivo("V-04", Nivel.ROJO, "Elige cómo regresa: Bueno, Desgaste por uso o Dañado.")
    return None


def regla_v05_danado(h: HechosRenglonDevolucion) -> Motivo | None:
    """V-05: Dañado exige observación. La pieza entra como No apta; por cantidad va a Baja. Nunca
    hay cargo al trabajador."""
    if h.condicion != Condicion.DANADO or h.articulo is None:
        return None
    if not (h.observacion or "").strip():
        return Motivo("V-05", Nivel.ROJO, "Si regresa dañado, anota qué le pasó.")
    destino = (
        "la pieza entra al almacén como No apta"
        if h.pieza is not None
        else "no regresa a existencias: va a Baja"
    )
    return Motivo("V-05", Nivel.AMARILLO, f"Dañado: {destino}. No se cobra al trabajador.")


def regla_v06_desgaste(h: HechosRenglonDevolucion) -> Motivo | None:
    """V-06: Desgaste por uso no genera pendiente ni observación (informativo)."""
    if h.condicion != Condicion.DESGASTE or h.articulo is None:
        return None
    return Motivo("V-06", Nivel.VERDE, "Desgaste por uso: no genera pendiente ni observación.")


def regla_v07_otro_almacen(h: HechosRenglonDevolucion) -> Motivo | None:
    """V-07: lo entregó otro almacén; entra al almacén que lo recibe (aviso amarillo)."""
    if (
        h.entrego_almacen_id is None
        or h.ubicacion_almacen_id is None
        or h.entrego_almacen_id == h.ubicacion_almacen_id
    ):
        return None
    return Motivo(
        "V-07",
        Nivel.AMARILLO,
        f"Lo entregó otro almacén ({h.entrego_almacen_texto}). Entra al almacén que lo recibe.",
    )


def regla_v01_pieza_al_titular(h: HechosRenglonDevolucion) -> Motivo | None:
    """V-01: la pieza se abona a su titular, la traiga quien la traiga (informativo)."""
    if h.pieza is None or h.titular is None or h.titular.tipo != "TRABAJADOR":
        return None
    return Motivo(
        "V-01", Nivel.VERDE, f"Se abona a {h.titular.nombre} ({h.titular.numero_empleado})."
    )


def evaluar_renglon_devolucion(h: HechosRenglonDevolucion) -> ResultadoDevolucion:
    """Une las reglas de la devolución en el orden de SM-06: código, ubicación y existencias,
    condición, avisos. SM-05: ninguna regla del trabajador, de límites ni de autorización."""
    resultado = ResultadoDevolucion()
    motivos = resultado.motivos

    def agregar(motivo: Motivo | None) -> None:
        if motivo is not None:
            motivos.append(motivo)

    agregar(regla_v12_codigo(h))  # código
    if h.articulo is None:
        return resultado
    agregar(regla_v14_pieza_sin_codigo(h))
    if motivos:
        return resultado
    sin_resguardo = regla_v02_sin_resguardo(h)  # ubicación
    if sin_resguardo is not None:
        motivos.append(sin_resguardo)
        resultado.sin_movimiento = True
        return resultado
    agregar(regla_rg05_pieza_de_una(h))
    agregar(regla_v03_cantidad(h))  # existencias
    agregar(regla_v04_condicion(h))  # condición
    agregar(regla_v05_danado(h))
    resultado.pide_observacion = h.condicion == Condicion.DANADO
    agregar(regla_v06_desgaste(h))
    agregar(regla_v01_pieza_al_titular(h))  # avisos
    agregar(regla_v07_otro_almacen(h))
    return resultado
