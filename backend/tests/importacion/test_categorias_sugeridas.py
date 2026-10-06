"""Diccionario de inferencia de categoría (I-14): cada regla con un ejemplo y el orden importa."""

import pytest

from app.modulos.importacion.categorias_sugeridas import (
    ALTO_VALOR,
    ALTURAS,
    CONSUMIBLES,
    ELECTRICA,
    EPP_BASICO,
    EPP_DOTACION,
    EXCLUIR,
    MANUAL,
    PREFIJOS,
    es_servicio,
    limpiar_nombre,
    sugerir,
)

# Una descripción por regla, en el orden del anexo de FEAT-007.
POR_REGLA = [
    ("Servicio de calibración de manómetros", EXCLUIR),  # 1
    ("Arnés de cuerpo completo", ALTURAS),  # 2
    ("Línea de vida retráctil 3 m", ALTURAS),  # 2
    ("Boquilla para torcha", CONSUMIBLES),  # 3
    ("Gas lens 3/32", CONSUMIBLES),  # 3
    ("Porta electrodo 400 A", ELECTRICA),  # 4
    ("Regulador de argón", ALTO_VALOR),  # 5
    ("Detector de gases 4 en 1", ALTO_VALOR),  # 5
    ("Respirador media cara", EPP_BASICO),  # 6
    ("Casco dieléctrico", EPP_BASICO),  # 6
    ("Guantes de carnaza", EPP_DOTACION),  # 7
    ("Anteojo de seguridad claro", EPP_DOTACION),  # 7
    ("Filtro para vapores orgánicos", EPP_DOTACION),  # 7
    ("Hoja de lija de agua 220", CONSUMIBLES),  # 8
    ("Disco de corte 4 1/2", CONSUMIBLES),  # 8
    ("Taladro percutor 1/2", ELECTRICA),  # 9
    ("Esmeril angular", ELECTRICA),  # 9
    ("Araña para concreto", MANUAL),  # 10
    ("Extensión de 10 m", MANUAL),  # 10
    ("Foco led 9 w", CONSUMIBLES),  # 11
    ("Cinta de aislar", CONSUMIBLES),  # 11
    ("Pintura vinílica blanca", CONSUMIBLES),  # 12
    ("Tornillo de 1/4", CONSUMIBLES),  # 12
    ("Carretilla de carga", MANUAL),  # 13
    ("Escalera de tijera", MANUAL),  # 13
    ("Llave española de 3/4", MANUAL),  # 14
    ("Martillo de bola", MANUAL),  # 14
]


@pytest.mark.parametrize(("descripcion", "categoria"), POR_REGLA)
def test_I_14_cada_regla_del_diccionario_sugiere_su_categoria(descripcion, categoria):
    sugerencia = sugerir(descripcion)
    assert sugerencia is not None and sugerencia.categoria == categoria


def test_I_14_el_respaldo_por_clave_de_producto_solo_si_ninguna_regla_coincide():
    assert sugerir("Cosa rara", "46181504").categoria == EPP_DOTACION
    assert sugerir("Cosa rara", "27111700").categoria == MANUAL
    assert sugerir("Cosa rara", "23101500").categoria == ELECTRICA
    assert sugerir("Cosa rara", "31162800").categoria == CONSUMIBLES  # prefijo 3116
    assert sugerir("Cosa rara", "78101800").excluir
    assert sugerir("Cosa rara", "99999999") is None
    assert sugerir("Cosa rara") is None
    # Una regla de palabras gana a la clave.
    assert sugerir("Martillo de bola", "46181504").categoria == MANUAL


def test_I_14_el_orden_importa_la_primera_regla_que_coincide_gana():
    # «pinza de tierra» cae en la regla 4 antes de que la 14 (`\bPINZA`) la mande a manual.
    assert sugerir("Pinza de tierra 500 A").categoria == ELECTRICA
    assert sugerir("Pinza de presión").categoria == MANUAL
    # La regla 2 gana a la 7 (el arnés no es EPP de dotación aunque diga «guante»).
    assert sugerir("Arnés con guante").categoria == ALTURAS
    # La regla 12 (`CANDADO`) gana a la 14.
    assert sugerir("Candado con llave").categoria == CONSUMIBLES


def test_I_14_se_normaliza_sin_acentos_ni_mayusculas_y_el_motivo_dice_la_palabra():
    sugerencia = sugerir("ARNÉS de seguridad")
    assert sugerencia.motivo == "La descripción dice «arnés»"
    assert sugerir("arnes").categoria == ALTURAS
    assert sugerir("Lámpara BTICINO 25W") is None  # la excepción de la regla 9


def test_I_14_servicio_se_excluye_por_palabra_completa():
    assert es_servicio("Servicio de mantenimiento") and es_servicio("MANO DE OBRA SERVICIO")
    assert not es_servicio("Servicios")  # \b: palabra completa
    assert not es_servicio("Casco")


def test_I_14_los_prefijos_son_los_de_las_categorias_iniciales():
    assert PREFIJOS == {
        "EPP básico": "EPB",
        "EPP de dotación": "EPD",
        "Equipo de alturas": "ALT",
        "Herramienta manual": "HMA",
        "Herramienta eléctrica": "HEL",
        "Equipo de alto valor": "EAV",
        "Consumibles de trabajo": "CON",
    }


def test_I_06_limpieza_del_nombre():
    assert limpiar_nombre("/T/ MARTILLO  DE BOLA") == "MARTILLO DE BOLA"
    assert limpiar_nombre("/SP/ ANTEOJO ECO LINE GRIS HC .") == "ANTEOJO ECO LINE GRIS HC"
    assert limpiar_nombre("TALADRO 1/2 (RF005) URREA") == "TALADRO 1/2 URREA"
    assert limpiar_nombre("Cinta   doble   cara .") == "Cinta doble cara"
    assert limpiar_nombre("Llave de 3/4. Truper") == "Llave de 3/4. Truper"
