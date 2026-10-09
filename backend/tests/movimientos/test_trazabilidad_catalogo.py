# ruff: noqa: F811  (los fixtures importados se piden por nombre en cada prueba)
"""Trazabilidad entre módulos: inspección, catálogo, reingreso y descontinuación de un modelo.

Cubre US-INS-001 / US-ENT-002 / ES-04 (inspección y ajuste de vigencia contra la entrega),
US-CAT-002 (cambiar el límite y volver a evaluar), US-TRB-002 / ES-02 (pendiente de un periodo
anterior) y ES-24 (un modelo se descontinúa).
"""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select, update

from app.core.tiempo import ahora_utc, hoy_mx
from app.modulos.movimientos.models import Movimiento
from app.modulos.trabajadores.models import PeriodoContrato
from tests.movimientos import ayudas_devolucion as dev
from tests.movimientos import ayudas_traspasos as tr
from tests.movimientos.ayudas import (
    abastecer,
    crear_articulo,
    crear_trabajador,
    cuerpo_entrada,
    cuerpo_entrega,
    existencia,
    existencia_de_trabajador,
    total_movimientos,
    total_vales,
)
from tests.movimientos.ayudas_traspasos import cliente_almacen  # noqa: F401  (fixture)
from tests.movimientos.test_autorizacion_integracion import aprobar, solicitar
from tests.movimientos.test_entrega import evaluar, motivos, pieza_en_kep, renglon
from tests.movimientos.test_invariantes import revisar_folios, revisar_invariantes

VALES = "/api/vales"


@pytest.fixture
def trabajador(session):
    return crear_trabajador(session)


def entregar(cliente, trabajador, articulo, cantidad=1):
    codigo = articulo if isinstance(articulo, str) else articulo.codigo
    r = cliente.post(VALES, json=cuerpo_entrega(trabajador, [renglon(codigo, cantidad)]))
    assert r.status_code == 201, r.text
    return r.json()


PUNTOS = {k: None for k in ("etiquetas", "costuras", "cintas", "herrajes", "conectores")}


def inspeccionar(cliente, pieza, resultado="APTO", **extra):
    return cliente.post(
        f"/api/piezas/{pieza.id}/inspecciones",
        json={"resultado": resultado, **extra, "puntos": PUNTOS | extra.get("puntos", {})},
    )


# ------------------------------------------------------------- US-INS-001 / US-ENT-002 / ES-04


def test_US_INS_001_ES_04_E_06_una_pieza_vencida_sale_roja_se_inspecciona_y_sale_verde(
    almacenista, compras, session, trabajador
):
    ayer = hoy_mx() - timedelta(days=1)
    _, pieza = pieza_en_kep(
        compras, session, requiere_inspeccion=True, vigencia_inspeccion_dias=30, vigente_hasta=ayer
    )

    # 1. Escanear el arnés vencido: rojo, con la fecha, sin pedir autorización.
    ev = evaluar(almacenista, trabajador, [renglon(pieza.codigo)])
    r = ev["renglones"][0]
    assert r["nivel"] == "ROJO" and motivos(ev) == ["E-06"]
    assert ayer.strftime("%d/%m/%Y") in r["motivos"][0]["mensaje"]
    assert r["autorizable"] is False and ev["puede_confirmar"] is False
    assert (
        almacenista.post(
            VALES, json=cuerpo_entrega(trabajador, [renglon(pieza.codigo)])
        ).status_code
        == 409
    )

    # 2. Se inspecciona ahí mismo, con resultado Apto.
    insp = inspeccionar(almacenista, pieza, puntos={"costuras": True, "herrajes": True})
    assert insp.status_code == 201, insp.text
    assert insp.json()["vigente_hasta"] == (hoy_mx() + timedelta(days=30)).isoformat()

    # 3. Al volver a escanearlo sale verde y se entrega.
    ev = evaluar(almacenista, trabajador, [renglon(pieza.codigo)])
    assert ev["renglones"][0]["nivel"] == "VERDE" and ev["renglones"][0]["motivos"] == []
    assert ev["puede_confirmar"] is True
    assert (
        ev["renglones"][0]["pieza"]["inspeccion_vigente_hasta"]
        == (hoy_mx() + timedelta(days=30)).isoformat()
    )
    vale = entregar(almacenista, trabajador, pieza.codigo)
    assert vale["renglones"][0]["nivel"] == "VERDE"


def test_US_INS_001_ES_04_E_05_si_se_marca_no_apto_ya_no_se_puede_entregar(
    almacenista, compras, session, trabajador
):
    ayer = hoy_mx() - timedelta(days=1)
    _, pieza = pieza_en_kep(
        compras, session, requiere_inspeccion=True, vigencia_inspeccion_dias=30, vigente_hasta=ayer
    )

    insp = inspeccionar(almacenista, pieza, "NO_APTO", observacion="Cinta deshilachada")
    assert insp.status_code == 201, insp.text

    ev = evaluar(almacenista, trabajador, [renglon(pieza.codigo)])
    r = ev["renglones"][0]
    assert r["nivel"] == "ROJO" and "E-05" in motivos(ev)
    assert r["autorizable"] is False and r["pieza"]["estado"] == "NO_APTO"
    assert ev["puede_confirmar"] is False
    # Solo una inspección nueva la regresa a Apta y a la entrega.
    assert inspeccionar(almacenista, pieza).status_code == 201
    assert evaluar(almacenista, trabajador, [renglon(pieza.codigo)])["nivel"] == "VERDE"


def test_US_ENT_002_P_07_un_ajuste_de_vigencia_cambia_la_siguiente_evaluacion_de_la_entrega(
    almacenista, supervisor, compras, session, trabajador
):
    _, pieza = pieza_en_kep(compras, session, requiere_inspeccion=True, vigencia_inspeccion_dias=30)
    assert inspeccionar(almacenista, pieza).status_code == 201
    assert evaluar(almacenista, trabajador, [renglon(pieza.codigo)])["nivel"] == "VERDE"

    # El supervisor acorta la vigencia a ayer: la inspección deja de valer.
    ayer = hoy_mx() - timedelta(days=1)
    ajuste = supervisor.post(
        f"/api/piezas/{pieza.id}/ajuste-vigencia",
        json={"vigente_hasta": ayer.isoformat(), "motivo": "Se golpeó en el área"},
    )
    assert ajuste.status_code == 201, ajuste.text

    ev = evaluar(almacenista, trabajador, [renglon(pieza.codigo)])
    r = ev["renglones"][0]
    assert r["nivel"] == "ROJO" and motivos(ev) == ["E-06"]
    assert ayer.strftime("%d/%m/%Y") in r["motivos"][0]["mensaje"]
    assert r["autorizable"] is False and ev["puede_confirmar"] is False
    vales = total_vales(session)
    assert (
        almacenista.post(
            VALES, json=cuerpo_entrega(trabajador, [renglon(pieza.codigo)])
        ).status_code
        == 409
    )
    assert total_vales(session) == vales
    # El ajuste quedó en el historial de la pieza, con las dos fechas y el motivo.
    historial = almacenista.get(f"/api/piezas/{pieza.id}").json()["historial"]
    (cambio,) = [h for h in historial if h["tipo"] == "AJUSTE_VIGENCIA"]
    assert cambio["vigente_hasta"] == ayer.isoformat()
    assert cambio["vigente_hasta_anterior"] == (hoy_mx() + timedelta(days=30)).isoformat()
    assert cambio["observacion"] == "Se golpeó en el área"

    # Alargarla (sin pasar del tope) devuelve la pieza a verde.
    otra = supervisor.post(
        f"/api/piezas/{pieza.id}/ajuste-vigencia",
        json={"vigente_hasta": (hoy_mx() + timedelta(days=5)).isoformat(), "motivo": "Revisada"},
    )
    assert otra.status_code == 201, otra.text
    # Vence en 5 días: ya no es rojo, solo el aviso E-11 (amarillo).
    ev = evaluar(almacenista, trabajador, [renglon(pieza.codigo)])
    assert ev["nivel"] == "AMARILLO" and ev["renglones"][0]["motivos"][0]["regla"] == "E-11"


# ------------------------------------------------------------------------------- US-CAT-002


def test_US_CAT_002_cambiar_el_limite_aplica_a_la_siguiente_evaluacion_y_no_toca_los_vales_viejos(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False, limite_cantidad=5, limite_periodo_dias=7)
    abastecer(compras, guantes, 30)
    viejo = entregar(almacenista, trabajador, guantes, 3)
    detalle_viejo = almacenista.get(f"{VALES}/{viejo['id']}").json()
    assert detalle_viejo["renglones"][0]["nivel"] == "VERDE"
    movimientos_antes = [
        (m.nivel, m.reglas, m.cantidad)
        for m in session.scalars(
            select(Movimiento).where(Movimiento.vale_id == uuid.UUID(viejo["id"]))
        )
    ]
    # Con límite 5 y 3 ya entregados, pedir 2 más cabe.
    assert evaluar(almacenista, trabajador, [renglon(guantes.codigo, 2)])["nivel"] == "VERDE"

    # Compras baja el límite a 3.
    cambio = compras.patch(f"/api/articulos/{guantes.id}", json={"limite_cantidad": 3})
    assert cambio.status_code == 200 and cambio.json()["limite_cantidad"] == 3

    ev = evaluar(almacenista, trabajador, [renglon(guantes.codigo, 2)])
    r = ev["renglones"][0]
    assert r["nivel"] == "NARANJA" and motivos(ev) == ["L-03"]
    assert "límite 3, tiene 3 en los últimos 7 días, pide 2" in r["motivos"][0]["mensaje"]
    assert ev["puede_confirmar"] is False
    # El vale anterior no cambió: ni su detalle ni sus movimientos.
    assert almacenista.get(f"{VALES}/{viejo['id']}").json() == detalle_viejo
    assert [
        (m.nivel, m.reglas, m.cantidad)
        for m in session.scalars(
            select(Movimiento).where(Movimiento.vale_id == uuid.UUID(viejo["id"]))
        )
    ] == movimientos_antes

    # Compras quita el límite: la siguiente evaluación ya no lo pide.
    quitar = compras.patch(
        f"/api/articulos/{guantes.id}", json={"limite_cantidad": None, "limite_periodo_dias": None}
    )
    assert quitar.status_code == 200, quitar.text
    assert evaluar(almacenista, trabajador, [renglon(guantes.codigo, 20)])["nivel"] == "VERDE"


# --------------------------------------------------------------------- US-TRB-002 / ES-02


def test_US_TRB_002_ES_02_el_casco_pendiente_de_un_periodo_anterior_cuenta_para_el_limite(
    almacenista, supervisor, compras, cliente_como, session, trabajador
):
    casco = crear_articulo(session, retornable=True, limite_cantidad=1)
    abastecer(compras, casco, 5)
    primero = entregar(almacenista, trabajador, casco, 1)
    # Pasa el tiempo: la entrega fue hace 90 días y el contrato terminó ayer.
    session.execute(
        update(Movimiento)
        .where(Movimiento.vale_id == uuid.UUID(primero["id"]))
        .values(creado_en=ahora_utc() - timedelta(days=90))
    )
    session.execute(
        update(PeriodoContrato)
        .where(PeriodoContrato.trabajador_id == trabajador.id)
        .values(inicio=hoy_mx() - timedelta(days=120), fin=hoy_mx() - timedelta(days=1))
    )
    session.expire_all()
    ev = evaluar(almacenista, trabajador, [renglon(casco.codigo)])
    assert ev["nivel"] == "ROJO" and ev["motivos"][0]["regla"] == "E-02"

    # RH lo reingresa con un periodo nuevo: sus pendientes se conservan.
    hoy = hoy_mx()
    rh = cliente_como("Recursos Humanos")
    reingreso = rh.post(
        f"/api/trabajadores/{trabajador.id}/periodos",
        json={"inicio": hoy.isoformat(), "fin": (hoy + timedelta(days=180)).isoformat()},
    )
    assert reingreso.status_code == 201, reingreso.text
    ficha = reingreso.json()
    assert ficha["estado"] == "ACTIVO" and ficha["vigencia"]["vigente"] is True
    assert ficha["pendientes"] == {"total": 1, "de_periodos_anteriores": 1, "regla": "E-12"}
    assert [(p["codigo"], p["de_periodo_anterior"]) for p in ficha["resguardo"]] == [
        (casco.codigo, True)
    ]

    # En Kepler: el aviso amarillo E-12 y el naranja del límite en posesión (L-02).
    ev = evaluar(almacenista, trabajador, [renglon(casco.codigo)])
    assert [(m["regla"], m["nivel"]) for m in ev["motivos"]] == [("E-12", "AMARILLO")]
    r = ev["renglones"][0]
    assert r["nivel"] == "NARANJA" and motivos(ev) == ["L-02"]
    assert "límite 1, tiene 1, pide 1" in r["motivos"][0]["mensaje"]
    assert ev["nivel"] == "NARANJA" and ev["puede_confirmar"] is False
    assert ev["trabajador"]["resguardo"][0]["de_periodo_anterior"] is True

    # O lo autoriza un supervisor con su motivo (E-07, A-01).
    autorizacion_id = solicitar(almacenista, trabajador, ev, motivo="Perdió el anterior")
    aprobar(supervisor, autorizacion_id)
    ok = almacenista.post(
        VALES,
        json=cuerpo_entrega(trabajador, [renglon(casco.codigo)], autorizacion_id=autorizacion_id),
    )
    assert ok.status_code == 201, ok.text
    assert existencia_de_trabajador(session, trabajador, casco) == 2


def test_US_TRB_002_L_02_si_el_trabajador_devuelve_el_casco_viejo_recibe_otro_sin_autorizacion(
    almacenista, compras, session, trabajador
):
    casco = crear_articulo(session, retornable=True, limite_cantidad=1)
    abastecer(compras, casco, 5)
    entregar(almacenista, trabajador, casco, 1)
    assert evaluar(almacenista, trabajador, [renglon(casco.codigo)])["nivel"] == "NARANJA"
    r = almacenista.post(
        VALES, json=dev.cuerpo_devolucion([dev.renglon(casco.codigo, 1, "BUENO")], trabajador)
    )
    assert r.status_code == 201, r.text
    ev = evaluar(almacenista, trabajador, [renglon(casco.codigo)])
    assert ev["renglones"][0]["nivel"] == "VERDE" and ev["puede_confirmar"] is True


# ------------------------------------------------------------------------------------ ES-24


def test_ES_24_un_modelo_descontinuado_no_se_entrega_ni_recibe_entradas_se_devuelve_y_se_traslada(
    almacenista, compras, supervisor, cliente_almacen, cliente_como, session, trabajador
):
    con = cliente_almacen("CON")  # su supervisor: los traspasos son del supervisor de cada almacén
    modelo = crear_articulo(session, retornable=True, nombre="Minipulidor modelo viejo")
    abastecer(compras, modelo, 10)
    entregar(almacenista, trabajador, modelo, 2)  # 2 con el trabajador, 8 en Kepler
    contenedor = tr.enviar(supervisor, session, "CON", [tr.renglon(modelo.codigo, 3)])
    tr.recibir(con, contenedor, [tr.renglon(modelo.codigo, 3)])  # 3 en el contenedor
    assert (existencia(session, "KEP", modelo), existencia(session, "CON", modelo)) == (5, 3)

    # 1. Luis lo inactiva con el motivo «Descontinuado».
    r = compras.post(f"/api/articulos/{modelo.id}/inactivacion", json={"motivo": "Descontinuado"})
    assert r.status_code == 200 and r.json()["activo"] is False

    # 2. Ya no se puede entregar...
    ev = evaluar(almacenista, trabajador, [renglon(modelo.codigo)])
    assert ev["renglones"][0]["nivel"] == "ROJO" and motivos(ev) == ["E-19"]
    assert "Descontinuado" in ev["renglones"][0]["motivos"][0]["mensaje"]
    vales = total_vales(session)
    no_entrega = almacenista.post(VALES, json=cuerpo_entrega(trabajador, [renglon(modelo.codigo)]))
    assert no_entrega.status_code == 409 and no_entrega.json()["codigo"] == "VALE_CAMBIO"
    # ... ni darle entrada.
    entrada = compras.post(VALES, json=cuerpo_entrada([{"codigo": modelo.codigo, "cantidad": 1}]))
    assert entrada.status_code == 409 and entrada.json()["codigo"] == "VALE_CAMBIO"
    assert entrada.json()["detalles"]["renglones"][0]["motivos"][0]["regla"] == "I-09"
    assert total_vales(session) == vales
    assert existencia(session, "KEP", modelo) == 5

    # 3. Lo que está con trabajadores se devuelve normal...
    devolucion = almacenista.post(
        VALES, json=dev.cuerpo_devolucion([dev.renglon(modelo.codigo, 2, "BUENO")], trabajador)
    )
    assert devolucion.status_code == 201, devolucion.text
    assert existencia_de_trabajador(session, trabajador, modelo) == 0
    assert existencia(session, "KEP", modelo) == 7
    # ... y lo que queda en el contenedor se traslada a Kepler.
    regreso = tr.enviar(con, session, "KEP", [tr.renglon(modelo.codigo, 3)])
    tr.recibir(supervisor, regreso, [tr.renglon(modelo.codigo, 3)])
    assert (existencia(session, "KEP", modelo), existencia(session, "CON", modelo)) == (10, 0)

    # 4. Su historial sigue completo y la ficha lo marca como inactivo.
    r = cliente_como("Administrador").get(
        "/api/reportes/movimientos", params={"articulo_id": str(modelo.id)}
    )
    assert r.status_code == 200
    tipos = {m["tipo"] for m in r.json()["elementos"]}
    assert tipos == {"ENTRADA", "ENTREGA", "TRASPASO", "RECEPCION", "DEVOLUCION"}
    folios = {m["folio"] for m in r.json()["elementos"]}
    assert {contenedor["folio"], regreso["folio"], devolucion.json()["folio"]} <= folios
    ficha = compras.get(f"/api/articulos/{modelo.id}").json()
    assert ficha["activo"] is False and ficha["motivo_inactivacion"] == "Descontinuado"
    assert total_movimientos(session) >= 7
    revisar_invariantes(session)
    revisar_folios(session)
