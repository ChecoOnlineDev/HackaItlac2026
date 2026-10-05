"""Las reglas de la DEVOLUCION sin base de datos: una prueba por regla (V-01 a V-07, V-12, V-14,
RG-05, SM-05). Funciones puras de `app/modulos/movimientos/evaluador_devolucion.py`."""

import uuid

from app.modulos.movimientos.evaluador import Motivo, Titular
from app.modulos.movimientos.evaluador_devolucion import (
    HechosRenglonDevolucion,
    evaluar_renglon_devolucion,
    regla_rg05_pieza_de_una,
    regla_v01_pieza_al_titular,
    regla_v02_sin_resguardo,
    regla_v03_cantidad,
    regla_v04_condicion,
    regla_v05_danado,
    regla_v06_desgaste,
    regla_v07_otro_almacen,
    regla_v12_codigo,
    regla_v14_pieza_sin_codigo,
)
from app.modulos.movimientos.models import Nivel
from tests.movimientos.test_evaluador import articulo, pieza

ALMACEN = uuid.uuid4()
OTRO = uuid.uuid4()
TRABAJADOR = Titular("TRABAJADOR", uuid.uuid4(), "Juan Pérez", "la tiene Juan", "EMP-1")


def hechos(**cambios) -> HechosRenglonDevolucion:
    base = dict(
        codigo="ART-1",
        cantidad=1,
        condicion="BUENO",
        observacion=None,
        articulo=articulo(),
        pieza=None,
        titular=TRABAJADOR,
        en_resguardo=3,
        ubicacion_almacen_id=ALMACEN,
    )
    return HechosRenglonDevolucion(**(base | cambios))


def de_pieza(**cambios) -> HechosRenglonDevolucion:
    return hechos(
        articulo=articulo(control="PIEZA"),
        pieza=pieza(),
        en_resguardo=1,
        **cambios,
    )


def reglas(motivos: list[Motivo]) -> list[str]:
    return [m.regla for m in motivos]


def test_V_12_un_codigo_que_no_existe_es_rojo_y_no_es_de_la_empresa():
    m = regla_v12_codigo(hechos(articulo=None, pieza=None))
    assert m.nivel == Nivel.ROJO and "No es de la empresa" in m.mensaje
    assert regla_v12_codigo(hechos()) is None


def test_V_12_el_codigo_de_una_credencial_o_vale_tampoco_es_un_equipo():
    m = regla_v12_codigo(hechos(articulo=None, codigo_ajeno=True))
    assert m.nivel == Nivel.ROJO and m.regla == "V-12"


def test_V_14_el_codigo_de_un_articulo_por_pieza_pide_escanear_la_pieza_o_buscar_su_serie():
    m = regla_v14_pieza_sin_codigo(hechos(articulo=articulo(control="PIEZA"), pieza=None))
    assert m.nivel == Nivel.ROJO and "número de serie" in m.mensaje
    assert regla_v14_pieza_sin_codigo(de_pieza()) is None
    assert regla_v14_pieza_sin_codigo(hechos()) is None


def test_V_02_una_pieza_que_no_esta_con_nadie_es_amarillo_y_dice_donde_esta():
    en_almacen = Titular("ALMACEN", ALMACEN, "Kepler", "está en el almacén KEP (Kepler)")
    m = regla_v02_sin_resguardo(de_pieza(titular=en_almacen))
    assert m.nivel == Nivel.AMARILLO and "almacén KEP" in m.mensaje
    assert regla_v02_sin_resguardo(de_pieza(titular=None)).nivel == Nivel.AMARILLO
    assert regla_v02_sin_resguardo(de_pieza()) is None  # la tiene un trabajador


def test_V_02_el_renglon_no_genera_movimiento_y_no_se_evalua_lo_demas():
    en_almacen = Titular("ALMACEN", ALMACEN, "Kepler", "está en el almacén KEP (Kepler)")
    r = evaluar_renglon_devolucion(de_pieza(titular=en_almacen, condicion=None))
    assert reglas(r.motivos) == ["V-02"] and r.sin_movimiento is True


def test_RG_05_una_pieza_se_devuelve_de_una_en_una():
    assert regla_rg05_pieza_de_una(de_pieza(cantidad=2)).nivel == Nivel.ROJO
    assert regla_rg05_pieza_de_una(de_pieza()) is None


def test_V_03_por_cantidad_no_se_acepta_mas_de_lo_que_tiene():
    assert regla_v03_cantidad(hechos(cantidad=3, en_resguardo=3)) is None
    m = regla_v03_cantidad(hechos(cantidad=4, en_resguardo=3))
    assert m.nivel == Nivel.ROJO and "tiene 3" in m.mensaje


def test_V_03_lo_que_ya_devuelven_los_renglones_anteriores_cuenta():
    m = regla_v03_cantidad(hechos(cantidad=2, en_resguardo=3, pedido_previo=2))
    assert m.nivel == Nivel.ROJO and "tiene 1" in m.mensaje


def test_V_03_por_cantidad_hay_que_identificar_al_trabajador():
    m = regla_v03_cantidad(hechos(titular=None))
    assert m.nivel == Nivel.ROJO and "trabajador" in m.mensaje


def test_V_04_la_condicion_es_obligatoria():
    assert regla_v04_condicion(hechos(condicion=None)).nivel == Nivel.ROJO
    for condicion in ("BUENO", "DESGASTE", "DANADO"):
        assert regla_v04_condicion(hechos(condicion=condicion)) is None


def test_V_05_danado_sin_observacion_es_rojo_y_pide_observacion():
    m = regla_v05_danado(hechos(condicion="DANADO", observacion=None))
    assert m.nivel == Nivel.ROJO
    assert regla_v05_danado(hechos(condicion="DANADO", observacion="   ")).nivel == Nivel.ROJO
    r = evaluar_renglon_devolucion(hechos(condicion="DANADO", observacion=None))
    assert r.pide_observacion is True


def test_V_05_danado_con_observacion_es_amarillo_y_no_cobra():
    pieza_danada = regla_v05_danado(de_pieza(condicion="DANADO", observacion="Se rompió"))
    assert pieza_danada.nivel == Nivel.AMARILLO and "No apta" in pieza_danada.mensaje
    cantidad = regla_v05_danado(hechos(condicion="DANADO", observacion="Se rompió"))
    assert "Baja" in cantidad.mensaje and "No se cobra" in cantidad.mensaje
    assert regla_v05_danado(hechos(condicion="BUENO")) is None


def test_V_06_desgaste_por_uso_no_pide_observacion_ni_avisa():
    r = evaluar_renglon_devolucion(hechos(condicion="DESGASTE", observacion=None))
    assert reglas(r.motivos) == ["V-06"]
    assert r.pide_observacion is False
    assert regla_v06_desgaste(hechos(condicion="DESGASTE")).nivel == Nivel.VERDE


def test_V_07_si_lo_entrego_otro_almacen_se_avisa_en_amarillo():
    m = regla_v07_otro_almacen(
        hechos(entrego_almacen_id=OTRO, entrego_almacen_texto="CON, Contratistas")
    )
    assert m.nivel == Nivel.AMARILLO and "CON" in m.mensaje
    assert regla_v07_otro_almacen(hechos(entrego_almacen_id=ALMACEN)) is None
    assert regla_v07_otro_almacen(hechos()) is None


def test_V_01_una_pieza_se_abona_a_su_titular_en_verde():
    m = regla_v01_pieza_al_titular(de_pieza())
    assert m.nivel == Nivel.VERDE and "Juan Pérez" in m.mensaje
    r = evaluar_renglon_devolucion(de_pieza())
    assert reglas(r.motivos) == ["V-01"] and r.sin_movimiento is False


def test_SM_05_ninguna_regla_de_trabajador_limites_o_articulo_inactivo_bloquea():
    """Un artículo inactivo con límite y autorización especial se devuelve normal: la
    devolución no evalúa E-02, E-07, E-19 ni E-26 (SM-05, CF-11)."""
    inactivo = articulo(
        activo=False,
        motivo_inactivacion="Ya no se usa",
        limite_cantidad=1,
        requiere_autorizacion=True,
    )
    r = evaluar_renglon_devolucion(hechos(articulo=inactivo, cantidad=2))
    assert r.motivos == [] and r.sin_movimiento is False
    assert not {"E-02", "E-07", "L-02", "E-19", "E-26"} & set(reglas(r.motivos))


def test_SM_01_el_nivel_del_renglon_es_el_mas_grave():
    r = evaluar_renglon_devolucion(
        de_pieza(condicion="DANADO", observacion="Roto", entrego_almacen_id=OTRO)
    )
    assert set(reglas(r.motivos)) == {"V-05", "V-01", "V-07"}
    from app.modulos.movimientos.evaluador import peor_nivel

    assert peor_nivel(r.motivos) == Nivel.AMARILLO
