"""Avisos de la entrega por dotación (FEAT-003): E-09, E-10 y E-11, y la observación obligatoria.

E-09 se prueba en sus tres casos (dentro, fuera y combinada con el límite). Son avisos amarillos
que no bloquean; con E-09 la confirmación pide una observación. Un puesto sin dotación no avisa.
"""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.tiempo import hoy_mx
from app.modulos.movimientos.models import Movimiento
from tests.ayudas_dotacion import asignar_puesto, dotacion_de_prueba, puesto_de_prueba
from tests.movimientos.ayudas import (
    abastecer,
    crear_articulo,
    crear_trabajador,
    cuerpo_entrega,
)
from tests.movimientos.test_entrega import evaluar, motivos, pieza_en_kep, renglon

VALES = "/api/vales"


@pytest.fixture
def trabajador(session):
    return crear_trabajador(session)


def confirmar(cliente, trabajador, renglones, **extra):
    return cliente.post(VALES, json=cuerpo_entrega(trabajador, renglones, **extra))


# ------------------------------------------------------------------------------- E-09


def test_E_09_dentro_de_la_dotacion_el_renglon_es_verde(almacenista, compras, session, trabajador):
    lentes = crear_articulo(session, retornable=False)
    abastecer(compras, lentes, 50)
    dotacion_de_prueba(session, trabajador, {lentes: 2})
    ev = evaluar(almacenista, trabajador, [renglon(lentes.codigo, 2)])
    assert ev["renglones"][0]["nivel"] == "VERDE" and motivos(ev) == []
    assert ev["pide_observacion"] is False and ev["renglones"][0]["pide_observacion"] is False
    assert confirmar(almacenista, trabajador, [renglon(lentes.codigo, 2)]).status_code == 201


def test_E_09_fuera_de_la_dotacion_es_amarillo_y_pide_observacion(
    almacenista, compras, session, trabajador
):
    lentes = crear_articulo(session, retornable=False)
    tapones = crear_articulo(session, retornable=False)
    abastecer(compras, tapones, 50)
    dotacion_de_prueba(session, trabajador, {lentes: 1})
    ev = evaluar(almacenista, trabajador, [renglon(tapones.codigo)])
    r = ev["renglones"][0]
    assert r["nivel"] == "AMARILLO" and motivos(ev) == ["E-09"]
    assert "no está en la dotación" in r["motivos"][0]["mensaje"]
    assert r["pide_observacion"] is True and ev["pide_observacion"] is True
    assert ev["puede_confirmar"] is True  # no bloquea


def test_E_09_mas_de_lo_recomendado_es_amarillo_y_pide_observacion(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 50)
    dotacion_de_prueba(session, trabajador, {guantes: 1})
    ev = evaluar(almacenista, trabajador, [renglon(guantes.codigo, 2)])
    r = ev["renglones"][0]
    assert r["nivel"] == "AMARILLO" and motivos(ev) == ["E-09"]
    assert "Supera lo recomendado" in r["motivos"][0]["mensaje"]
    assert ev["pide_observacion"] is True and ev["puede_confirmar"] is True


def test_E_09_combinada_con_el_limite_gana_el_naranja_y_se_muestran_los_dos_motivos(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False, limite_cantidad=2, limite_periodo_dias=7)
    abastecer(compras, guantes, 50)
    dotacion_de_prueba(session, trabajador, {guantes: 1})
    ev = evaluar(almacenista, trabajador, [renglon(guantes.codigo, 3)])
    r = ev["renglones"][0]
    assert r["nivel"] == "NARANJA" and ev["nivel"] == "NARANJA"
    assert set(motivos(ev)) == {"L-03", "E-09"}
    assert r["pide_observacion"] is True and ev["pide_observacion"] is True
    assert ev["puede_confirmar"] is False  # el naranja necesita al supervisor


def test_E_09_cuenta_lo_ya_consumido_en_el_periodo_de_contrato(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 50)
    dotacion_de_prueba(session, trabajador, {guantes: 1})
    assert confirmar(almacenista, trabajador, [renglon(guantes.codigo)]).status_code == 201
    ev = evaluar(almacenista, trabajador, [renglon(guantes.codigo)])
    assert motivos(ev) == ["E-09"]  # ya recibió lo recomendado: otro es de más
    assert "lleva 1" in ev["renglones"][0]["motivos"][0]["mensaje"]


def test_E_09_un_retornable_cuenta_lo_que_tiene_ahora(almacenista, compras, session, trabajador):
    detector = crear_articulo(session, retornable=True)
    abastecer(compras, detector, 5)
    dotacion_de_prueba(session, trabajador, {detector: 1})
    assert confirmar(almacenista, trabajador, [renglon(detector.codigo)]).status_code == 201
    ev = evaluar(almacenista, trabajador, [renglon(detector.codigo)])
    assert motivos(ev) == ["E-09"]


def test_E_09_dos_renglones_del_mismo_articulo_cuentan_juntos(
    almacenista, compras, session, trabajador
):
    arnes = crear_articulo(session, control="PIEZA", retornable=True)
    from tests.movimientos.ayudas import entrar_pieza

    _, a = entrar_pieza(compras, arnes)
    _, b = entrar_pieza(compras, arnes)
    dotacion_de_prueba(session, trabajador, {arnes: 1})
    ev = evaluar(almacenista, trabajador, [renglon(a), renglon(b)])
    assert motivos(ev, 0) == [] and motivos(ev, 1) == ["E-09"]


def test_E_09_el_renglon_en_rojo_no_pide_observacion(almacenista, session, trabajador):
    sin_existencia = crear_articulo(session, retornable=False)
    otro = crear_articulo(session, retornable=False)
    dotacion_de_prueba(session, trabajador, {otro: 1})
    ev = evaluar(almacenista, trabajador, [renglon(sin_existencia.codigo)])
    r = ev["renglones"][0]
    assert r["nivel"] == "ROJO" and "E-04" in motivos(ev)
    assert r["pide_observacion"] is False and ev["pide_observacion"] is False


def test_E_09_confirmar_sin_observacion_se_rechaza_con_la_regla(
    almacenista, compras, session, trabajador
):
    lentes = crear_articulo(session, retornable=False)
    otro = crear_articulo(session, retornable=False)
    abastecer(compras, otro, 10)
    dotacion_de_prueba(session, trabajador, {lentes: 1})
    r = confirmar(almacenista, trabajador, [renglon(otro.codigo)])
    assert r.status_code == 422, r.text
    assert r.json()["codigo"] == "DATOS_INVALIDOS"
    detalle = r.json()["detalles"][0]
    assert detalle["regla"] == "E-09" and detalle["campo"] == "renglones.0.observacion"
    # Una observación en blanco tampoco sirve.
    r = confirmar(almacenista, trabajador, [renglon(otro.codigo, observacion="   ")])
    assert r.status_code == 422 and r.json()["detalles"][0]["regla"] == "E-09"


def test_E_09_con_observacion_en_el_renglon_se_confirma_y_queda_en_el_movimiento(
    almacenista, compras, session, trabajador
):
    lentes = crear_articulo(session, retornable=False)
    otro = crear_articulo(session, retornable=False)
    abastecer(compras, otro, 10)
    dotacion_de_prueba(session, trabajador, {lentes: 1})
    r = confirmar(almacenista, trabajador, [renglon(otro.codigo, observacion="Se mojaron")])
    assert r.status_code == 201, r.text
    assert r.json()["renglones"][0]["reglas"] == ["E-09"]
    mov = session.scalar(
        select(Movimiento).where(
            Movimiento.vale_id == uuid.UUID(r.json()["id"]), Movimiento.articulo_id == otro.id
        )
    )
    assert mov.observacion == "Se mojaron" and mov.nivel == "AMARILLO"


def test_E_09_con_observacion_del_vale_tambien_se_confirma(
    almacenista, compras, session, trabajador
):
    lentes = crear_articulo(session, retornable=False)
    otro = crear_articulo(session, retornable=False)
    abastecer(compras, otro, 10)
    dotacion_de_prueba(session, trabajador, {lentes: 1})
    r = confirmar(
        almacenista, trabajador, [renglon(otro.codigo)], observacion="Se llenaron de grasa"
    )
    assert r.status_code == 201, r.text
    mov = session.scalar(
        select(Movimiento).where(
            Movimiento.vale_id == uuid.UUID(r.json()["id"]), Movimiento.articulo_id == otro.id
        )
    )
    assert mov.observacion == "Se llenaron de grasa"


def test_E_09_el_reporte_de_movimientos_muestra_la_observacion(
    almacenista, supervisor, compras, session, trabajador
):
    lentes = crear_articulo(session, retornable=False)
    otro = crear_articulo(session, retornable=False)
    abastecer(compras, otro, 10)
    dotacion_de_prueba(session, trabajador, {lentes: 1})
    r = confirmar(almacenista, trabajador, [renglon(otro.codigo, observacion="Se mojaron")])
    assert r.status_code == 201, r.text
    # El almacenista no tiene reportes (tabla 8.2): lo consulta el supervisor de su almacén.
    reporte = supervisor.get(
        "/api/reportes/movimientos", params={"articulo_id": str(otro.id), "tipo": "ENTREGA"}
    )
    assert reporte.status_code == 200, reporte.text
    filas = reporte.json()["elementos"]
    assert [f["observacion"] for f in filas] == ["Se mojaron"]


def test_E_09_un_puesto_sin_dotacion_no_genera_avisos(almacenista, compras, session, trabajador):
    cualquiera = crear_articulo(session, retornable=False)
    abastecer(compras, cualquiera, 10)
    asignar_puesto(session, trabajador, puesto_de_prueba(session))  # puesto sin renglones
    ev = evaluar(almacenista, trabajador, [renglon(cualquiera.codigo, 5)])
    assert ev["renglones"][0]["nivel"] == "VERDE" and ev["pide_observacion"] is False
    assert confirmar(almacenista, trabajador, [renglon(cualquiera.codigo, 5)]).status_code == 201


def test_E_09_un_trabajador_sin_puesto_del_catalogo_no_genera_avisos(
    almacenista, compras, session, trabajador
):
    cualquiera = crear_articulo(session, retornable=False)
    abastecer(compras, cualquiera, 10)
    # `crear_trabajador` deja el texto "Soldador" sin `puesto_id`: no hay dotación.
    ev = evaluar(almacenista, trabajador, [renglon(cualquiera.codigo)])
    assert ev["renglones"][0]["nivel"] == "VERDE" and ev["pide_observacion"] is False


# ------------------------------------------------------------------------------- E-10


def test_E_10_la_talla_distinta_a_la_del_trabajador_avisa_sin_pedir_observacion(
    almacenista, compras, session, trabajador
):
    camisola = crear_articulo(session, retornable=False, talla="XL")
    abastecer(compras, camisola, 10)
    trabajador.tallas = {"camisa": "M", "calzado": "27"}
    session.flush()
    ev = evaluar(almacenista, trabajador, [renglon(camisola.codigo)])
    r = ev["renglones"][0]
    assert r["nivel"] == "AMARILLO" and motivos(ev) == ["E-10"]
    assert r["pide_observacion"] is False and ev["pide_observacion"] is False
    assert ev["puede_confirmar"] is True
    # Se confirma sin observación.
    assert confirmar(almacenista, trabajador, [renglon(camisola.codigo)]).status_code == 201


def test_E_10_la_talla_que_coincide_no_avisa(almacenista, compras, session, trabajador):
    camisola = crear_articulo(session, retornable=False, talla="m")
    abastecer(compras, camisola, 10)
    trabajador.tallas = {"camisa": "M", "calzado": "27"}
    session.flush()
    assert motivos(evaluar(almacenista, trabajador, [renglon(camisola.codigo)])) == []


def test_E_10_sin_tallas_del_trabajador_o_del_articulo_no_avisa(
    almacenista, compras, session, trabajador
):
    con_talla = crear_articulo(session, retornable=False, talla="XL")
    sin_talla = crear_articulo(session, retornable=False)
    abastecer(compras, con_talla, 10)
    abastecer(compras, sin_talla, 10)
    trabajador.tallas = None
    session.flush()
    assert motivos(evaluar(almacenista, trabajador, [renglon(con_talla.codigo)])) == []
    trabajador.tallas = {"camisa": "M"}
    session.flush()
    assert motivos(evaluar(almacenista, trabajador, [renglon(sin_talla.codigo)])) == []


# ------------------------------------------------------------------------------- E-11


def test_E_11_la_inspeccion_que_vence_en_7_dias_o_menos_avisa(
    almacenista, compras, session, trabajador
):
    hoy = hoy_mx()
    for dias in (0, 1, 7):
        _, pieza = pieza_en_kep(
            compras,
            session,
            vigente_hasta=hoy + timedelta(days=dias),
            requiere_inspeccion=True,
            vigencia_inspeccion_dias=180,
        )
        ev = evaluar(almacenista, trabajador, [renglon(pieza.codigo)])
        r = ev["renglones"][0]
        assert r["nivel"] == "AMARILLO" and motivos(ev) == ["E-11"], dias
        assert r["pide_observacion"] is False and ev["puede_confirmar"] is True


def test_E_11_con_8_dias_o_mas_no_avisa(almacenista, compras, session, trabajador):
    _, pieza = pieza_en_kep(
        compras,
        session,
        vigente_hasta=hoy_mx() + timedelta(days=8),
        requiere_inspeccion=True,
        vigencia_inspeccion_dias=180,
    )
    ev = evaluar(almacenista, trabajador, [renglon(pieza.codigo)])
    assert ev["renglones"][0]["nivel"] == "VERDE" and motivos(ev) == []


def test_E_11_una_inspeccion_vencida_sigue_siendo_E_06_en_rojo(
    almacenista, compras, session, trabajador
):
    _, pieza = pieza_en_kep(
        compras,
        session,
        vigente_hasta=hoy_mx() - timedelta(days=1),
        requiere_inspeccion=True,
        vigencia_inspeccion_dias=180,
    )
    ev = evaluar(almacenista, trabajador, [renglon(pieza.codigo)])
    assert motivos(ev) == ["E-06"] and ev["renglones"][0]["nivel"] == "ROJO"
