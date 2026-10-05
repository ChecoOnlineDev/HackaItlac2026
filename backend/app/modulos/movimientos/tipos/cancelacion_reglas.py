"""Reglas puras de la CANCELACION (K-01 a K-04, X-14): sin base de datos ni HTTP.

Cada función recibe hechos ya leídos y devuelve un `Motivo` (con el ID de su regla) o `None`.
La cancelación es genérica: no conoce las reglas del tipo que cancela; solo mira el tipo y el
estado del vale y las filas de `movimiento` (qué se movió y si ya se movió después).
"""

from dataclasses import dataclass

from app.modulos.movimientos.evaluador import Motivo
from app.modulos.movimientos.models import EstadoVale, Nivel, TipoVale

# Tipos que nunca se cancelan (K-04) y el texto que se le dice al usuario.
_NO_CANCELABLES: dict[str, str] = {
    TipoVale.RECEPCION: (
        "Una recepción no se cancela. Si algo llegó mal, regístralo como diferencia al recibir."
    ),
    TipoVale.NO_ADEUDO: "Un vale de no adeudo no se cancela.",
    TipoVale.CANCELACION: "Una cancelación no se cancela.",
}


@dataclass(frozen=True)
class HechosPiezaCancelacion:
    """Dónde está una pieza que movió el vale y si algo la movió después."""

    codigo: str
    esta_en_el_destino: bool  # `pieza.ubicacion_id` es el destino del movimiento del vale
    hay_movimiento_posterior: bool
    donde_esta: str  # "la tiene Juan Pérez (E-01)", "está en el almacén KEP (...)"


@dataclass(frozen=True)
class HechosExistenciaCancelacion:
    """Lo que revertir el movimiento le quita a su destino y lo que hay ahí."""

    articulo: str
    ubicacion: str  # "el almacén KEP", "Juan Pérez", "la baja"
    necesario: int  # acumulado de los renglones del vale hasta este
    disponible: int


def regla_k04_tipo(tipo: str) -> Motivo | None:
    """K-04: se cancelan entradas, entregas, devoluciones y traspasos en tránsito."""
    texto = _NO_CANCELABLES.get(tipo)
    if texto is None:
        return None
    return Motivo("K-04", Nivel.ROJO, texto)


def regla_k03_ya_cancelado(estado: str, folio_cancelacion: str | None) -> Motivo | None:
    """K-03: un vale ya cancelado no se cancela otra vez."""
    if estado != EstadoVale.CANCELADO:
        return None
    donde = f" (folio {folio_cancelacion})" if folio_cancelacion else ""
    return Motivo("K-03", Nivel.ROJO, f"Este vale ya está cancelado{donde}.")


def regla_x14_traspaso(tipo: str, estado: str) -> Motivo | None:
    """X-14: un traspaso solo se cancela en tránsito, antes de la recepción."""
    if tipo != TipoVale.TRASPASO or estado == EstadoVale.EN_TRANSITO:
        return None
    if estado in (EstadoVale.RECIBIDO, EstadoVale.RECIBIDO_CON_DIFERENCIAS):
        texto = "Este traspaso ya se recibió: solo se cancela antes de la recepción."
    else:
        texto = "Este traspaso ya no está en tránsito: solo se cancela antes de la recepción."
    return Motivo("X-14", Nivel.ROJO, texto)


def regla_k03_pieza(h: HechosPiezaCancelacion) -> Motivo | None:
    """K-03: si la pieza ya se movió después, el vale no se cancela."""
    if h.esta_en_el_destino and not h.hay_movimiento_posterior:
        return None
    if not h.esta_en_el_destino:
        texto = f"La pieza {h.codigo} ya se movió después de este vale: {h.donde_esta}."
    else:
        texto = f"La pieza {h.codigo} tuvo otros movimientos después de este vale."
    return Motivo("K-03", Nivel.ROJO, texto)


def regla_k03_existencia(h: HechosExistenciaCancelacion) -> Motivo | None:
    """K-03: las existencias deben alcanzar para revertir el vale (RG-04)."""
    if h.disponible >= h.necesario:
        return None
    return Motivo(
        "K-03",
        Nivel.ROJO,
        f"{h.articulo} ya no alcanza para revertir el vale: se necesitan {h.necesario} en "
        f"{h.ubicacion} y hay {h.disponible}.",
    )
