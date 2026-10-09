"""AV-02/04: una sola definición de alto valor, calculada al leer."""

from decimal import Decimal

from sqlalchemy import or_

from app.config import get_settings
from app.modulos.catalogo.models import Articulo, Categoria


def expresion_alto_valor(articulo=Articulo, categoria=Categoria):
    return or_(
        categoria.alto_valor.is_(True),
        articulo.costo_unitario >= get_settings().alto_valor_costo_minimo,
    )


def expresion_vigilancia(articulo=Articulo, categoria=Categoria):
    return or_(expresion_alto_valor(articulo, categoria), articulo.requiere_inspeccion.is_(True))


def calcular_alto_valor(articulo, categoria):
    if categoria.alto_valor:
        return True, "Por su categoría"
    if (
        articulo.costo_unitario is not None
        and Decimal(str(articulo.costo_unitario)) >= get_settings().alto_valor_costo_minimo
    ):
        return True, "Por su costo"
    return False, None
