"""Las siete categorías iniciales del catálogo (sección 5.1 de las reglas de negocio).

Es un punto de partida: la empresa las cambia cuando quiera desde la pantalla de categorías.
Las usan dos cosas: los datos de prueba (`datos_prueba.py`) y el comando de mantenimiento
`sembrar-categorias`, que las crea en una base nueva. Para cambiar el juego inicial, se edita
solo este archivo.
"""

from app.modulos.catalogo.models import Control, TipoCategoria

EPP = TipoCategoria.EPP
HERRAMIENTA = TipoCategoria.HERRAMIENTA

# Inspección de equipo de alturas: 180 días (5.4, supuesto). Límite de dotación: "en una semana
# no más de tres guantes" (plática min 36); el de consumibles de trabajo es un supuesto parecido.
VIGENCIA_ALTURAS = 180

# nombre: (tipo, control, retornable, reglas de la plantilla)
CATEGORIAS: dict[str, tuple[TipoCategoria, Control, bool, dict]] = {
    "EPP básico": (EPP, Control.CANTIDAD, True, {"limite_cantidad": 1}),
    "EPP de dotación": (
        EPP,
        Control.CANTIDAD,
        False,
        {"limite_cantidad": 3, "limite_periodo_dias": 7},
    ),
    "Equipo de alturas": (
        EPP,
        Control.PIEZA,
        True,
        {
            "requiere_inspeccion": True,
            "vigencia_inspeccion_dias": VIGENCIA_ALTURAS,
            "motivo_uso_especial": "Equipo de alturas",
        },
    ),
    "Herramienta manual": (HERRAMIENTA, Control.CANTIDAD, True, {}),
    "Herramienta eléctrica": (HERRAMIENTA, Control.PIEZA, True, {}),
    "Equipo de alto valor": (
        HERRAMIENTA,
        Control.PIEZA,
        True,
        {"limite_cantidad": 1, "alto_valor": True},
    ),
    "Consumibles de trabajo": (
        HERRAMIENTA,
        Control.CANTIDAD,
        False,
        {"limite_cantidad": 5, "limite_periodo_dias": 7},
    ),
}
