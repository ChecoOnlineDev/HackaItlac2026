"""El evaluador del semáforo, sin base de datos: una prueba por regla (SM-01, SM-06).

Funciones puras de `app/modulos/movimientos/evaluador.py` con hechos construidos a mano.
"""

import uuid
from datetime import date, timedelta

import pytest

from app.modulos.movimientos.evaluador import (
    HechosArticulo,
    HechosCuenta,
    HechosInspeccionInicial,
    HechosPieza,
    HechosRenglonEntrada,
    HechosRenglonEntrega,
    HechosTrabajador,
    Motivo,
    Titular,
    evaluar_renglon_entrada,
    evaluar_renglon_entrega,
    excedente_limite,
    peor_nivel,
    regla_e01_codigo,
    regla_e02_vigencia,
    regla_e03_ubicacion,
    regla_e04_existencia,
    regla_e05_estado,
    regla_e06_inspeccion,
    regla_e12_pendientes_anteriores,
    regla_e19_inactivo,
    regla_e26_autorizacion,
    regla_e27_cantidad_inusual,
    regla_limite,
)
from app.modulos.movimientos.models import Nivel

HOY = date(2026, 10, 5)
ALMACEN = uuid.uuid4()
OTRO = uuid.uuid4()


def articulo(**cambios) -> HechosArticulo:
    base = dict(
        id=uuid.uuid4(),
        codigo="ART-1",
        nombre="Arnés",
        marca=None,
        modelo=None,
        talla=None,
        unidad="pieza",
        control="CANTIDAD",
        retornable=True,
        activo=True,
        motivo_inactivacion=None,
        requiere_inspeccion=False,
        vigencia_inspeccion_dias=None,
        requiere_autorizacion=False,
        motivo_uso_especial=None,
        limite_cantidad=None,
        limite_periodo_dias=None,
        cantidad_aviso=None,
    )
    return HechosArticulo(**(base | cambios))


def pieza(**cambios) -> HechosPieza:
    base = dict(
        id=uuid.uuid4(),
        codigo="P-1",
        numero_serie="S-1",
        estado="APTO",
        inspeccion_vigente_hasta=None,
        ubicacion_id=ALMACEN,
    )
    return HechosPieza(**(base | cambios))


def renglon(**cambios) -> HechosRenglonEntrega:
    base = dict(
        codigo="ART-1",
        cantidad=1,
        articulo=articulo(),
        pieza=None,
        titular=None,
        ubicacion_almacen_id=ALMACEN,
        existencia_almacen=10,
        disponible=10,
        cuenta=HechosCuenta(0, 0),
        pedido_previo=0,
    )
    return HechosRenglonEntrega(**(base | cambios))


def reglas(motivos: list[Motivo]) -> list[str]:
    return [m.regla for m in motivos]


# ----------------------------------------------------------------------------- SM-01


def test_SM_01_el_nivel_mas_grave_gana():
    amarillo = Motivo("E-27", Nivel.AMARILLO, "")
    naranja = Motivo("E-26", Nivel.NARANJA, "")
    rojo = Motivo("E-05", Nivel.ROJO, "")
    assert peor_nivel([]) == Nivel.VERDE
    assert peor_nivel([amarillo]) == Nivel.AMARILLO
    assert peor_nivel([amarillo, naranja]) == Nivel.NARANJA
    assert peor_nivel([naranja, rojo, amarillo]) == Nivel.ROJO


# ----------------------------------------------------------------------------- código


def test_E_01_un_codigo_desconocido_es_rojo():
    motivo = regla_e01_codigo(renglon(articulo=None))
    assert motivo.regla == "E-01" and motivo.nivel == Nivel.ROJO and "ART-1" in motivo.mensaje


def test_E_01_un_articulo_por_pieza_pide_el_codigo_de_la_pieza():
    h = renglon(articulo=articulo(control="PIEZA"), pieza=None)
    assert regla_e01_codigo(h).regla == "E-01"
    assert regla_e01_codigo(renglon(articulo=articulo(control="PIEZA"), pieza=pieza())) is None
    assert regla_e01_codigo(renglon()) is None


def test_E_19_un_articulo_inactivo_es_rojo():
    h = renglon(articulo=articulo(activo=False, motivo_inactivacion="Obsoleto"))
    motivo = regla_e19_inactivo(h)
    assert motivo.regla == "E-19" and motivo.nivel == Nivel.ROJO and "Obsoleto" in motivo.mensaje
    assert regla_e19_inactivo(renglon()) is None


# -------------------------------------------------------------------------- trabajador


def test_E_02_un_trabajador_no_vigente_es_rojo_con_su_motivo():
    t = HechosTrabajador(False, "Ya no forma parte de la plantilla: su contrato terminó.", 0)
    motivo = regla_e02_vigencia(t)
    assert motivo.regla == "E-02" and motivo.nivel == Nivel.ROJO
    assert "plantilla" in motivo.mensaje
    assert regla_e02_vigencia(HechosTrabajador(True, None, 0)) is None


def test_E_12_pendientes_de_un_periodo_anterior_es_amarillo():
    motivo = regla_e12_pendientes_anteriores(HechosTrabajador(True, None, 2))
    assert motivo.regla == "E-12" and motivo.nivel == Nivel.AMARILLO
    assert "2 artículos" in motivo.mensaje
    assert regla_e12_pendientes_anteriores(HechosTrabajador(True, None, 0)) is None


# ------------------------------------------------------------ ubicación y existencias


def test_E_03_la_pieza_en_otro_lugar_es_rojo_con_su_ubicacion():
    donde = Titular("TRABAJADOR", uuid.uuid4(), "Juan", "la tiene Juan (EMP-1)", "EMP-1")
    h = renglon(articulo=articulo(control="PIEZA"), pieza=pieza(ubicacion_id=OTRO), titular=donde)
    motivo = regla_e03_ubicacion(h)
    assert motivo.regla == "E-03" and "la tiene Juan" in motivo.mensaje
    en_el_almacen = renglon(articulo=articulo(control="PIEZA"), pieza=pieza())
    assert regla_e03_ubicacion(en_el_almacen) is None


def test_E_04_la_cantidad_no_puede_superar_la_existencia():
    assert regla_e04_existencia(renglon(cantidad=11)).regla == "E-04"
    assert regla_e04_existencia(renglon(cantidad=10)) is None
    assert regla_e04_existencia(renglon(cantidad=1, existencia_almacen=0)).nivel == Nivel.ROJO


def test_RG_05_una_pieza_siempre_es_de_a_una():
    h = renglon(articulo=articulo(control="PIEZA"), pieza=pieza(), cantidad=2)
    assert regla_e04_existencia(h).regla == "RG-05"


# ------------------------------------------------------------------------- seguridad


@pytest.mark.parametrize("estado", ["NO_APTO", "EN_MANTENIMIENTO", "EN_CALIBRACION", "BAJA"])
def test_E_05_una_pieza_que_no_esta_apta_es_rojo(estado):
    h = renglon(articulo=articulo(control="PIEZA"), pieza=pieza(estado=estado))
    assert regla_e05_estado(h).regla == "E-05"


def test_E_05_una_pieza_apta_no_dispara_la_regla():
    assert regla_e05_estado(renglon(pieza=pieza(estado="APTO"))) is None
    assert regla_e05_estado(renglon()) is None


def test_E_06_sin_inspeccion_vigente_es_rojo_y_vencer_hoy_todavia_es_vigente():
    art = articulo(control="PIEZA", requiere_inspeccion=True)
    sin = renglon(articulo=art, pieza=pieza())
    assert regla_e06_inspeccion(sin, HOY).mensaje == "Sin inspección vigente."
    ayer = renglon(articulo=art, pieza=pieza(inspeccion_vigente_hasta=HOY - timedelta(days=1)))
    assert "04/10/2026" in regla_e06_inspeccion(ayer, HOY).mensaje
    hoy = renglon(articulo=art, pieza=pieza(inspeccion_vigente_hasta=HOY))
    assert regla_e06_inspeccion(hoy, HOY) is None
    manana = renglon(articulo=art, pieza=pieza(inspeccion_vigente_hasta=HOY + timedelta(days=1)))
    assert regla_e06_inspeccion(manana, HOY) is None


def test_E_06_no_aplica_si_el_articulo_no_requiere_inspeccion():
    h = renglon(articulo=articulo(control="PIEZA", requiere_inspeccion=False), pieza=pieza())
    assert regla_e06_inspeccion(h, HOY) is None


# ------------------------------------------------------------------------------ límites


def test_L_01_sin_limite_la_regla_no_aplica():
    assert regla_limite(renglon(cantidad=500)) is None


def test_L_02_retornable_cuenta_lo_que_tiene_mas_lo_que_pide():
    art = articulo(retornable=True, limite_cantidad=2)
    h = renglon(articulo=art, cuenta=HechosCuenta(2, 0), cantidad=1)
    motivo = regla_limite(h)
    assert motivo.regla == "L-02" and motivo.nivel == Nivel.NARANJA
    assert "límite 2, tiene 2, pide 1" in motivo.mensaje  # L-04
    assert regla_limite(renglon(articulo=art, cuenta=HechosCuenta(1, 0), cantidad=1)) is None
    assert excedente_limite(h) == 1


def test_L_02_los_renglones_anteriores_del_mismo_articulo_cuentan():
    art = articulo(retornable=True, limite_cantidad=2)
    sin_previo = renglon(articulo=art, cuenta=HechosCuenta(1, 0), cantidad=1, pedido_previo=0)
    assert regla_limite(sin_previo) is None  # 1 + 1 = 2: justo en el límite
    con_previo = renglon(articulo=art, cuenta=HechosCuenta(1, 0), cantidad=1, pedido_previo=1)
    motivo = regla_limite(con_previo)
    assert motivo.regla == "L-02" and "límite 2, tiene 2, pide 1" in motivo.mensaje


def test_L_03_consumible_cuenta_lo_entregado_en_los_ultimos_n_dias():
    art = articulo(retornable=False, limite_cantidad=3, limite_periodo_dias=7)
    h = renglon(articulo=art, cuenta=HechosCuenta(0, 3), cantidad=1)
    motivo = regla_limite(h)
    assert motivo.regla == "L-03" and "tiene 3 en los últimos 7 días" in motivo.mensaje
    assert regla_limite(renglon(articulo=art, cuenta=HechosCuenta(0, 2), cantidad=1)) is None
    assert excedente_limite(h) == 1


def test_L_05_un_consumible_sin_periodo_solo_cuenta_lo_que_pide_el_vale():
    art = articulo(retornable=False, limite_cantidad=2)
    assert regla_limite(renglon(articulo=art, cuenta=HechosCuenta(0, 99), cantidad=2)) is None
    assert regla_limite(renglon(articulo=art, cantidad=3)).regla == "L-03"


# ------------------------------------------------------------------------------ avisos


def test_E_26_un_articulo_de_uso_especial_es_naranja_con_su_motivo():
    art = articulo(requiere_autorizacion=True, motivo_uso_especial="Uso restringido")
    motivo = regla_e26_autorizacion(renglon(articulo=art))
    assert motivo.regla == "E-26" and motivo.nivel == Nivel.NARANJA
    assert "Uso restringido" in motivo.mensaje
    assert regla_e26_autorizacion(renglon()) is None


def test_E_27_la_cantidad_igual_o_mayor_al_aviso_es_amarillo():
    art = articulo(cantidad_aviso=5)
    assert regla_e27_cantidad_inusual(renglon(articulo=art, cantidad=4)) is None
    igual = regla_e27_cantidad_inusual(renglon(articulo=art, cantidad=5))
    assert igual.regla == "E-27" and igual.nivel == Nivel.AMARILLO
    assert regla_e27_cantidad_inusual(renglon(articulo=art, cantidad=9)) is not None
    assert regla_e27_cantidad_inusual(renglon(cantidad=500)) is None


# ----------------------------------------------------------------------------- SM-06


def test_SM_06_el_orden_es_codigo_trabajador_ubicacion_seguridad_limites_avisos():
    art = articulo(
        control="PIEZA",
        activo=False,
        requiere_inspeccion=True,
        requiere_autorizacion=True,
        limite_cantidad=1,
        cantidad_aviso=1,
    )
    h = renglon(
        articulo=art,
        pieza=pieza(estado="NO_APTO", ubicacion_id=OTRO),
        titular=Titular("ALMACEN", OTRO, "CON", "está en el almacén CON"),
        cuenta=HechosCuenta(1, 0),
        cantidad=1,
    )
    e02 = Motivo("E-02", Nivel.ROJO, "No vigente")
    resultado = evaluar_renglon_entrega(h, HOY, e02)
    assert reglas(resultado.motivos) == [
        "E-19",
        "E-02",
        "E-03",
        "E-05",
        "E-06",
        "L-02",
        "E-26",
        "E-27",
    ]
    assert resultado.nivel == Nivel.ROJO and resultado.requiere_confirmacion is True


def test_un_renglon_que_cumple_todo_es_verde():
    resultado = evaluar_renglon_entrega(renglon(), HOY)
    assert resultado.motivos == [] and resultado.nivel == Nivel.VERDE


def test_un_codigo_desconocido_no_evalua_nada_mas():
    resultado = evaluar_renglon_entrega(renglon(articulo=None), HOY)
    assert reglas(resultado.motivos) == ["E-01"]


# ------------------------------------------------------------------------------ entrada


def entrada(**cambios) -> HechosRenglonEntrada:
    base = dict(codigo="ART-1", cantidad=1, articulo=articulo())
    return HechosRenglonEntrada(**(base | cambios))


def test_I_01_un_renglon_por_cantidad_es_verde():
    assert evaluar_renglon_entrada(entrada(cantidad=10), HOY).nivel == Nivel.VERDE


def test_I_09_un_articulo_inactivo_no_recibe_entradas():
    r = evaluar_renglon_entrada(entrada(articulo=articulo(activo=False)), HOY)
    assert reglas(r.motivos) == ["I-09"] and r.nivel == Nivel.ROJO


def test_I_02_una_pieza_lleva_codigo_y_serie_unicos():
    art = articulo(control="PIEZA")
    base = dict(articulo=art, tiene_datos_pieza=True)
    ok = entrada(**base, pieza_codigo="P-9", pieza_serie="S-9")
    assert evaluar_renglon_entrada(ok, HOY).nivel == Nivel.VERDE
    sin_codigo = entrada(**base, pieza_serie="S-9")
    assert reglas(evaluar_renglon_entrada(sin_codigo, HOY).motivos) == ["I-02"]
    # I-02 (decisión de FEAT-009): la serie es opcional al entrar; sin ella la pieza queda con serie
    # pendiente y entra sin motivos (el aviso amarillo es de la entrega, E-29).
    sin_serie = entrada(**base, pieza_codigo="P-9")
    r_sin_serie = evaluar_renglon_entrada(sin_serie, HOY)
    assert r_sin_serie.nivel == Nivel.VERDE and r_sin_serie.motivos == []
    en_uso = entrada(**base, pieza_codigo="P-9", pieza_serie="S", codigo_pieza_en_uso="una pieza")
    assert "ya identifica una pieza" in evaluar_renglon_entrada(en_uso, HOY).motivos[0].mensaje
    serie_repe = entrada(**base, pieza_codigo="P-9", pieza_serie="S", serie_en_uso=True)
    assert reglas(evaluar_renglon_entrada(serie_repe, HOY).motivos) == ["I-02"]
    repe_vale = entrada(**base, pieza_codigo="P-9", pieza_serie="S", repetida_en_vale=True)
    assert "repetido en este vale" in evaluar_renglon_entrada(repe_vale, HOY).motivos[0].mensaje


def test_I_03_sin_inspeccion_inicial_queda_pendiente_con_aviso():
    art = articulo(control="PIEZA", requiere_inspeccion=True)
    h = entrada(articulo=art, tiene_datos_pieza=True, pieza_codigo="P-9", pieza_serie="S-9")
    r = evaluar_renglon_entrada(h, HOY)
    assert reglas(r.motivos) == ["I-03"] and r.nivel == Nivel.AMARILLO
    con = entrada(
        articulo=art,
        tiene_datos_pieza=True,
        pieza_codigo="P-9",
        pieza_serie="S-9",
        inspeccion=HechosInspeccionInicial(HOY, "APTO", None),
    )
    assert evaluar_renglon_entrada(con, HOY).nivel == Nivel.VERDE


def test_I_03_la_inspeccion_no_apta_exige_observacion_y_no_puede_ser_futura():
    art = articulo(control="PIEZA", requiere_inspeccion=True)
    base = dict(articulo=art, tiene_datos_pieza=True, pieza_codigo="P-9", pieza_serie="S-9")
    no_apta = entrada(**base, inspeccion=HechosInspeccionInicial(HOY, "NO_APTO", "  "))
    assert evaluar_renglon_entrada(no_apta, HOY).nivel == Nivel.ROJO
    con_obs = entrada(**base, inspeccion=HechosInspeccionInicial(HOY, "NO_APTO", "Costura rota"))
    assert evaluar_renglon_entrada(con_obs, HOY).nivel == Nivel.VERDE
    futura = entrada(
        **base, inspeccion=HechosInspeccionInicial(HOY + timedelta(days=1), "APTO", None)
    )
    assert evaluar_renglon_entrada(futura, HOY).nivel == Nivel.ROJO
