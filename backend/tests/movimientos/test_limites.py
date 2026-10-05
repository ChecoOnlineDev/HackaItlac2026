"""Límite por artículo (US-LIM-001): L-01 a L-05, E-07, SM-03."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import update

from app.core.tiempo import ahora_utc
from app.modulos.almacenes.service import AlmacenService
from app.modulos.movimientos.models import Existencia, Movimiento, Vale
from tests.movimientos.ayudas import (
    abastecer,
    crear_articulo,
    crear_trabajador,
    cuerpo_entrega,
    entrar_pieza,
)
from tests.movimientos.test_entrega import evaluar, motivos, renglon

VALES = "/api/vales"


@pytest.fixture
def trabajador(session):
    return crear_trabajador(session)


def entregar(cliente, trabajador, articulo, cantidad=1):
    codigo = articulo if isinstance(articulo, str) else articulo.codigo
    r = cliente.post(VALES, json=cuerpo_entrega(trabajador, [renglon(codigo, cantidad)]))
    assert r.status_code == 201, r.text
    return r.json()


def test_L_01_sin_limite_configurado_la_regla_no_aplica(almacenista, compras, session, trabajador):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 100)
    ev = evaluar(almacenista, trabajador, [renglon(guantes.codigo, 99)])
    assert ev["renglones"][0]["nivel"] == "VERDE" and ev["puede_confirmar"] is True


def test_L_02_retornable_la_cuenta_es_lo_que_tiene_mas_lo_que_pide(
    almacenista, compras, session, trabajador
):
    arnes = crear_articulo(session, retornable=True, limite_cantidad=2)
    abastecer(compras, arnes, 10)
    entregar(almacenista, trabajador, arnes, 2)
    ev = evaluar(almacenista, trabajador, [renglon(arnes.codigo, 1)])
    r = ev["renglones"][0]
    assert r["nivel"] == "NARANJA" and motivos(ev) == ["L-02"] and r["autorizable"] is True
    # L-04: el detalle del límite.
    assert "límite 2, tiene 2, pide 1" in r["motivos"][0]["mensaje"]
    assert ev["puede_confirmar"] is False  # SM-03


def test_L_02_justo_en_el_limite_no_es_naranja(almacenista, compras, session, trabajador):
    arnes = crear_articulo(session, retornable=True, limite_cantidad=2)
    abastecer(compras, arnes, 10)
    entregar(almacenista, trabajador, arnes, 1)
    ev = evaluar(almacenista, trabajador, [renglon(arnes.codigo, 1)])
    assert ev["renglones"][0]["nivel"] == "VERDE"


def test_L_02_si_devuelve_el_suyo_puede_recibir_otro_sin_autorizacion(
    almacenista, compras, session, trabajador
):
    arnes = crear_articulo(session, retornable=True, limite_cantidad=1)
    abastecer(compras, arnes, 5)
    entregar(almacenista, trabajador, arnes, 1)
    assert evaluar(almacenista, trabajador, [renglon(arnes.codigo)])["nivel"] == "NARANJA"
    # Simula la devolución (el tipo DEVOLUCION lo construye otro agente): el trabajador ya no lo
    # tiene y vuelve al almacén.
    ubicacion = AlmacenService(session).ubicacion_de_trabajador(trabajador.id)
    session.execute(
        update(Existencia)
        .where(Existencia.ubicacion_id == ubicacion.id, Existencia.articulo_id == arnes.id)
        .values(cantidad=0)
    )
    ev = evaluar(almacenista, trabajador, [renglon(arnes.codigo)])
    assert ev["renglones"][0]["nivel"] == "VERDE" and ev["puede_confirmar"] is True


def test_L_02_el_limite_se_alcanza_sumando_dos_renglones_del_mismo_articulo_en_un_vale(
    almacenista, compras, session, trabajador
):
    arnes = crear_articulo(session, control="PIEZA", retornable=True, limite_cantidad=1)
    _, codigo_a = entrar_pieza(compras, arnes)
    _, codigo_b = entrar_pieza(compras, arnes)
    ev = evaluar(almacenista, trabajador, [renglon(codigo_a), renglon(codigo_b)])
    primero, segundo = ev["renglones"]
    assert primero["nivel"] == "VERDE"
    assert (
        segundo["nivel"] == "NARANJA"
        and "límite 1, tiene 1, pide 1" in segundo["motivos"][0]["mensaje"]
    )


def test_L_02_cuenta_las_piezas_que_el_trabajador_ya_tiene(
    almacenista, compras, session, trabajador
):
    arnes = crear_articulo(session, control="PIEZA", retornable=True, limite_cantidad=1)
    _, codigo_a = entrar_pieza(compras, arnes)
    _, codigo_b = entrar_pieza(compras, arnes)
    entregar(almacenista, trabajador, codigo_a)
    ev = evaluar(almacenista, trabajador, [renglon(codigo_b)])
    assert motivos(ev) == ["L-02"]


def test_L_03_consumible_la_cuenta_es_lo_entregado_en_los_ultimos_n_dias(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False, limite_cantidad=3, limite_periodo_dias=7)
    abastecer(compras, guantes, 20)
    entregar(almacenista, trabajador, guantes, 3)
    ev = evaluar(almacenista, trabajador, [renglon(guantes.codigo, 1)])
    r = ev["renglones"][0]
    assert r["nivel"] == "NARANJA" and motivos(ev) == ["L-03"]
    assert "límite 3, tiene 3 en los últimos 7 días, pide 1" in r["motivos"][0]["mensaje"]


def test_L_03_lo_entregado_hace_mas_de_n_dias_ya_no_cuenta(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False, limite_cantidad=3, limite_periodo_dias=7)
    abastecer(compras, guantes, 20)
    vale = entregar(almacenista, trabajador, guantes, 3)
    session.execute(
        update(Movimiento)
        .where(Movimiento.vale_id == uuid.UUID(vale["id"]))
        .values(creado_en=ahora_utc() - timedelta(days=8))
    )
    ev = evaluar(almacenista, trabajador, [renglon(guantes.codigo, 3)])
    assert ev["renglones"][0]["nivel"] == "VERDE"


def test_L_03_una_entrega_hecha_hace_exactamente_n_dias_ya_no_cuenta(
    almacenista, compras, session, trabajador, monkeypatch
):
    guantes = crear_articulo(session, retornable=False, limite_cantidad=3, limite_periodo_dias=7)
    abastecer(compras, guantes, 20)
    ahora = ahora_utc()
    reloj = {"t": ahora - timedelta(days=7)}
    monkeypatch.setattr("app.modulos.movimientos.service.ahora_utc", lambda: reloj["t"])
    entregar(almacenista, trabajador, guantes, 3)  # hace exactamente 7 días
    reloj["t"] = ahora
    assert evaluar(almacenista, trabajador, [renglon(guantes.codigo, 3)])["nivel"] == "VERDE"
    # Un segundo antes todavía cuenta.
    reloj["t"] = ahora - timedelta(seconds=1)
    assert evaluar(almacenista, trabajador, [renglon(guantes.codigo, 1)])["nivel"] == "NARANJA"


def test_L_03_el_consumo_es_del_trabajador_y_del_articulo(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False, limite_cantidad=3, limite_periodo_dias=7)
    lentes = crear_articulo(session, retornable=False, limite_cantidad=3, limite_periodo_dias=7)
    abastecer(compras, guantes, 20)
    abastecer(compras, lentes, 20)
    otro = crear_trabajador(session)
    entregar(almacenista, otro, guantes, 3)  # lo consumió otro
    entregar(almacenista, trabajador, lentes, 3)  # otro artículo
    ev = evaluar(almacenista, trabajador, [renglon(guantes.codigo, 3)])
    assert ev["renglones"][0]["nivel"] == "VERDE"


def test_L_03_un_vale_cancelado_no_cuenta_en_el_consumo(almacenista, compras, session, trabajador):
    guantes = crear_articulo(session, retornable=False, limite_cantidad=3, limite_periodo_dias=7)
    abastecer(compras, guantes, 20)
    vale = entregar(almacenista, trabajador, guantes, 3)
    assert evaluar(almacenista, trabajador, [renglon(guantes.codigo)])["nivel"] == "NARANJA"
    session.execute(update(Vale).where(Vale.id == uuid.UUID(vale["id"])).values(estado="CANCELADO"))
    assert evaluar(almacenista, trabajador, [renglon(guantes.codigo)])["nivel"] == "VERDE"


def test_L_03_lo_que_pide_este_vale_cuenta_contra_el_limite(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False, limite_cantidad=3, limite_periodo_dias=7)
    abastecer(compras, guantes, 20)
    ev = evaluar(almacenista, trabajador, [renglon(guantes.codigo, 4)])
    r = ev["renglones"][0]
    assert (
        r["nivel"] == "NARANJA"
        and "límite 3, tiene 0 en los últimos 7 días, pide 4" in (r["motivos"][0]["mensaje"])
    )


def test_L_05_consumible_sin_periodo_compara_solo_contra_lo_que_pide_el_vale(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False, limite_cantidad=2)
    abastecer(compras, guantes, 20)
    entregar(almacenista, trabajador, guantes, 2)
    assert evaluar(almacenista, trabajador, [renglon(guantes.codigo, 2)])["nivel"] == "VERDE"
    assert evaluar(almacenista, trabajador, [renglon(guantes.codigo, 3)])["nivel"] == "NARANJA"


def test_L_05_el_periodo_vacio_de_un_retornable_significa_en_posesion(
    almacenista, compras, session, trabajador
):
    casco = crear_articulo(session, retornable=True, limite_cantidad=1, limite_periodo_dias=None)
    abastecer(compras, casco, 5)
    entregar(almacenista, trabajador, casco, 1)
    # Aunque pase el tiempo, sigue en su poder: la cuenta no depende de días.
    assert evaluar(almacenista, trabajador, [renglon(casco.codigo)])["nivel"] == "NARANJA"


def test_E_07_un_naranja_por_limite_impide_confirmar_hasta_autorizar_o_quitar(
    almacenista, compras, session, trabajador
):
    arnes = crear_articulo(session, retornable=True, limite_cantidad=1)
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, arnes, 5)
    abastecer(compras, guantes, 5)
    entregar(almacenista, trabajador, arnes, 1)
    r = almacenista.post(
        VALES,
        json=cuerpo_entrega(trabajador, [renglon(arnes.codigo), renglon(guantes.codigo)]),
    )
    assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO"
    # Quitando el renglón excedente se entrega lo demás (A-07).
    ok = almacenista.post(VALES, json=cuerpo_entrega(trabajador, [renglon(guantes.codigo)]))
    assert ok.status_code == 201


def test_L_01_el_limite_no_aplica_a_un_articulo_sin_limite_aunque_haya_mucho_en_posesion(
    almacenista, compras, session, trabajador
):
    casco = crear_articulo(session, retornable=True)
    abastecer(compras, casco, 50)
    entregar(almacenista, trabajador, casco, 40)
    assert evaluar(almacenista, trabajador, [renglon(casco.codigo, 5)])["nivel"] == "VERDE"


def test_E_07_E_26_se_muestran_los_dos_motivos(almacenista, compras, session, trabajador):
    arnes = crear_articulo(
        session,
        retornable=True,
        limite_cantidad=1,
        requiere_autorizacion=True,
        motivo_uso_especial="Equipo restringido",
    )
    abastecer(compras, arnes, 5)
    ev = evaluar(almacenista, trabajador, [renglon(arnes.codigo, 2)])
    r = ev["renglones"][0]
    assert r["nivel"] == "NARANJA" and motivos(ev) == ["L-02", "E-26"]  # SM-01: todos los motivos
