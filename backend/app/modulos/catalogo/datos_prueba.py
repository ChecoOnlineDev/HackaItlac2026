"""Datos de prueba de `catalogo`: las siete categorías iniciales y los artículos del PDF.

Idempotente: lo que ya existe (por nombre de categoría o código de artículo) no se toca, así no
pisa lo que alguien haya editado. Solo hace `flush`; el commit lo hace `app/datos_prueba.py`.
NO carga piezas ni existencias: las escribe `movimientos`.

Fuentes: categorías, sección 5.1 de las reglas; artículos, páginas 7 y 10 del PDF del reto. Los
costos son los de la página 10 (sin IVA); los artículos de la página 7 no traen costo en el PDF.

Puestos y dotación (FEAT-003): PROPUESTAS DE DATOS DE PRUEBA a partir del PDF. El PDF no dice qué
puestos existen: solo lista el EPP por trabajador (p. 10, con cantidades) y el equipo y herramienta
para un trabajador dentro de Mittal (p. 7 del documento, p. 8 del PDF). Los puestos reales y su
dotación los define la empresa. Cada cantidad recomendada respeta el límite del artículo (D-04).
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modulos.catalogo.categorias_iniciales import CATEGORIAS
from app.modulos.catalogo.codigos import CodigoService
from app.modulos.catalogo.models import (
    Articulo,
    Categoria,
    Dotacion,
    Puesto,
    TipoCodigo,
)

# (código, nombre, marca, modelo, categoría, unidad, costo sin IVA o None)
ARTICULOS: tuple[tuple[str, str, str | None, str | None, str, str, str | None], ...] = (
    # Página 7: equipo y herramienta para un trabajador dentro de Mittal.
    ("ARN-KEV", "Arnés Kevlar", None, None, "Equipo de alturas", "pieza", None),
    ("ARN-POL", "Arnés Poliéster", None, None, "Equipo de alturas", "pieza", None),
    ("BANDOLA", "Bandola", None, None, "Equipo de alturas", "pieza", None),
    ("GAN-DOB", "Gancho doble de vida", None, None, "Equipo de alturas", "pieza", None),
    ("RET-3M", "Retráctil 3 mts", None, None, "Equipo de alturas", "pieza", None),
    ("MINIPUL", "Minipulidor", None, None, "Herramienta eléctrica", "pieza", None),
    ("FLEXOM", "Flexómetro", None, None, "Herramienta manual", "pieza", None),
    ("DET-GAS", "Detector de gases", None, None, "Equipo de alto valor", "pieza", None),
    ("MARRO-B", "Marro bola", None, None, "Herramienta manual", "pieza", None),
    ("CINCEL", "Cincel", None, None, "Herramienta manual", "pieza", None),
    ("EXT-ELE", "Extensión eléctrica", None, None, "Herramienta manual", "pieza", None),
    ("REFLECT", "Reflector o lámpara", None, None, "Herramienta eléctrica", "pieza", None),
    ("PETO", "Peto", None, None, "EPP básico", "pieza", None),
    ("POLAINAS", "Polainas", None, None, "EPP básico", "pieza", None),
    ("DISCO-9", "Discos de corte 9 pulgadas", None, None, "Consumibles de trabajo", "pieza", None),
    (
        "DISCO-4M",
        "Discos de corte 4 1/2 pulgadas",
        None,
        None,
        "Consumibles de trabajo",
        "pieza",
        None,
    ),
    # Página 10: costo de EPP por trabajador (precios unitarios sin IVA).
    ("LENTE-CL", "Lente claro", None, None, "EPP de dotación", "pieza", "12.00"),
    ("TAPON-AU", "Tapón auditivo", None, None, "EPP de dotación", "par", "6.02"),
    ("RESP-6200", "Respirador 3M 6200", "3M", "6200", "EPP básico", "pieza", "269.35"),
    ("FILTRO-7093", "Filtro 7093 3M", "3M", "7093", "EPP de dotación", "pieza", "172.93"),
    ("FILTRO-2097", "Filtro 2097 3M", "3M", "2097", "EPP de dotación", "pieza", "115.58"),
    ("CACHUCHA", "Cachucha MSA", "MSA", None, "EPP de dotación", "pieza", "178.00"),
    ("CAMISOLA", "Camisola mezclilla", None, None, "EPP de dotación", "pieza", "255.00"),
    ("LOGO-FR", "Logo frontal", None, None, "EPP de dotación", "pieza", "28.00"),
    ("LOGO-CON", "Logo contratista", None, None, "EPP de dotación", "pieza", "48.00"),
    (
        "GUANTE-DIE",
        "Guantes dieléctricos clase 0 (1000 V)",
        None,
        None,
        "EPP de dotación",
        "par",
        "1250.00",
    ),
    (
        "GUANTE-CAR",
        "Guante protector de carnaza/piel",
        None,
        None,
        "EPP de dotación",
        "par",
        "800.00",
    ),
    (
        "ZAPATO-755",
        "Zapato metatarsal 755 MT",
        None,
        "755 MT",
        "EPP de dotación",
        "par",
        "695.00",
    ),
)


# EPP por trabajador (PDF p. 10): código del artículo -> cantidad recomendada. El filtro 2097 es la
# opción alternativa del 7093 y no entra en la dotación.
EPP_ESTANDAR: dict[str, int] = {
    "LENTE-CL": 1,
    "TAPON-AU": 2,
    "RESP-6200": 1,
    "FILTRO-7093": 2,
    "CACHUCHA": 1,
    "CAMISOLA": 1,
    "LOGO-FR": 1,
    "LOGO-CON": 1,
    "GUANTE-DIE": 1,
    "GUANTE-CAR": 1,
    "ZAPATO-755": 1,
}

# Puestos de los cuatro trabajadores de prueba. Equipo y herramienta: PDF p. 7 del documento.
PUESTOS: dict[str, dict[str, int]] = {
    "Ayudante general": EPP_ESTANDAR,
    "Soldador": {**EPP_ESTANDAR, "PETO": 1, "POLAINAS": 1, "MINIPUL": 1, "DISCO-4M": 2},
    "Electricista": {
        **EPP_ESTANDAR,
        "FLEXOM": 1,
        "EXT-ELE": 1,
        "REFLECT": 1,
        "DET-GAS": 1,
    },
    # Trabajo en alturas: EPP estándar más el equipo de alturas.
    "Rigger": {**EPP_ESTANDAR, "ARN-KEV": 1, "BANDOLA": 1, "RET-3M": 1},
}


def _cargar_puestos(session: Session) -> None:
    """Crea los puestos y su dotación si faltan. Un puesto que ya tiene dotación no se toca."""
    for nombre, renglones in PUESTOS.items():
        puesto = session.scalar(select(Puesto).where(Puesto.nombre == nombre))
        if puesto is None:
            puesto = Puesto(nombre=nombre)
            session.add(puesto)
            session.flush()
        ya_tiene = session.scalar(select(Dotacion.id).where(Dotacion.puesto_id == puesto.id))
        if ya_tiene is not None:
            continue
        for codigo, cantidad in renglones.items():
            articulo = session.scalar(select(Articulo).where(Articulo.codigo == codigo))
            if articulo is None:
                raise RuntimeError(f"Falta el artículo {codigo} para el puesto {nombre}")
            session.add(Dotacion(puesto_id=puesto.id, articulo_id=articulo.id, cantidad=cantidad))
    session.flush()


def cargar(session: Session) -> None:
    codigos = CodigoService(session)

    por_nombre: dict[str, Categoria] = {}
    for nombre, (tipo, control, retornable, reglas) in CATEGORIAS.items():
        categoria = session.scalar(select(Categoria).where(Categoria.nombre == nombre))
        if categoria is None:
            categoria = Categoria(
                nombre=nombre, tipo=tipo, control=control, retornable=retornable, **reglas
            )
            session.add(categoria)
            session.flush()
        por_nombre[nombre] = categoria

    for codigo, nombre, marca, modelo, categoria_nombre, unidad, costo in ARTICULOS:
        if session.scalar(select(Articulo).where(Articulo.codigo == codigo)) is not None:
            continue
        categoria = por_nombre[categoria_nombre]
        articulo = Articulo(
            codigo=codigo,
            nombre=nombre,
            marca=marca,
            modelo=modelo,
            categoria_id=categoria.id,
            control=categoria.control,
            retornable=categoria.retornable,
            unidad=unidad,
            costo_unitario=Decimal(costo) if costo else None,
            requiere_inspeccion=categoria.requiere_inspeccion,
            vigencia_inspeccion_dias=categoria.vigencia_inspeccion_dias,
            requiere_autorizacion=categoria.requiere_autorizacion,
            motivo_uso_especial=categoria.motivo_uso_especial,
            limite_cantidad=categoria.limite_cantidad,
            limite_periodo_dias=categoria.limite_periodo_dias,
            cantidad_aviso=categoria.cantidad_aviso,
        )
        session.add(articulo)
        session.flush()
        codigos.registrar(codigo, TipoCodigo.ARTICULO, articulo.id)
    session.flush()
    _cargar_puestos(session)
