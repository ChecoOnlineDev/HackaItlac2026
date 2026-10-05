"""CANCELAR Y REHACER (K-05) y el escenario ES-11 (diez pares en lugar de uno)."""

import uuid

import pytest

from tests.movimientos.ayudas import (
    FIRMA,
    abastecer,
    crear_articulo,
    crear_trabajador,
    entrar_pieza,
    existencia,
    total_movimientos,
    total_vales,
)
from tests.movimientos.cancelacion_ayudas import VALES, cancelacion, entregar, url
from tests.movimientos.test_cancelacion_basica import detalle
from tests.movimientos.test_entrega import pieza_en_kep, renglon
from tests.movimientos.test_invariantes import revisar_folios, revisar_invariantes

EVALUAR = "/api/vales/evaluar"


@pytest.fixture
def trabajador(session):
    return crear_trabajador(session)


def rehacer(cliente, vale_id, **extra):
    r = cliente.post(url(vale_id), json=cancelacion(rehacer=True, **extra))
    assert r.status_code == 201, r.text
    return r.json()


def test_K_05_cancelar_y_rehacer_devuelve_el_borrador_con_los_renglones_del_original(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False)
    casco = crear_articulo(session, retornable=True)
    abastecer(compras, guantes, 20)
    abastecer(compras, casco, 20)
    vale = entregar(
        almacenista,
        trabajador,
        [
            renglon(guantes.codigo, 10, condicion="DESGASTE", observacion="Ya usados"),
            renglon(casco.codigo, 2),
        ],
    )
    cuerpo = rehacer(almacenista, vale["id"], motivo="Capturé mal")
    borrador = cuerpo["borrador"]
    assert borrador["tipo"] == "ENTREGA"
    assert borrador["trabajador_id"] == str(trabajador.id)
    assert borrador["destino_almacen_id"] is None
    assert borrador["almacen_id"] == detalle(almacenista, vale["id"])["almacen"]["id"]
    assert borrador["renglones"] == [
        {
            "codigo": guantes.codigo,
            "cantidad": 10,
            "condicion": "DESGASTE",
            "observacion": "Ya usados",
            "pieza": None,
        },
        {
            "codigo": casco.codigo,
            "cantidad": 2,
            "condicion": "BUENO",
            "observacion": None,
            "pieza": None,
        },
    ]
    # Sin firma ni autorización, ni nada que la interfaz no deba heredar (K-05, A-03).
    assert not ({"firma", "autorizacion_id", "id_cliente", "token", "folio"} & set(borrador))
    # Y el vale original sí quedó cancelado, completo (no es una cancelación parcial).
    assert cuerpo["vale_cancelado"]["estado"] == "CANCELADO"
    assert existencia(session, "KEP", guantes) == existencia(session, "KEP", casco) == 20


def test_K_05_sin_rehacer_no_hay_borrador(almacenista, compras, session, trabajador):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    vale = entregar(almacenista, trabajador, [renglon(guantes.codigo)])
    r = almacenista.post(url(vale["id"]), json=cancelacion())
    assert r.status_code == 201 and r.json()["borrador"] is None


def test_K_05_el_borrador_con_pieza_usa_el_codigo_de_la_pieza(
    almacenista, compras, session, trabajador
):
    from datetime import timedelta

    from app.core.tiempo import hoy_mx

    _, pieza = pieza_en_kep(compras, session, vigente_hasta=hoy_mx() + timedelta(days=60))
    vale = entregar(almacenista, trabajador, [renglon(pieza.codigo)])
    borrador = rehacer(almacenista, vale["id"])["borrador"]
    assert [r["codigo"] for r in borrador["renglones"]] == [pieza.codigo]
    # El borrador se evalúa de nuevo como un vale nuevo: la pieza ya está otra vez en el almacén.
    ev = almacenista.post(EVALUAR, json=borrador)
    assert ev.status_code == 200, ev.text
    assert ev.json()["nivel"] == "VERDE" and ev.json()["puede_confirmar"] is True


def test_K_05_el_borrador_no_hereda_la_autorizacion_y_se_evalua_de_nuevo(
    almacenista, supervisor, compras, session, trabajador
):
    from tests.movimientos.ayudas import cuerpo_entrega
    from tests.movimientos.test_autorizacion_integracion import aprobar, solicitar
    from tests.movimientos.test_entrega import evaluar

    arnes = crear_articulo(session, retornable=True, limite_cantidad=1)
    abastecer(compras, arnes, 10)
    entregar(almacenista, trabajador, [renglon(arnes.codigo)])
    ev = evaluar(almacenista, trabajador, [renglon(arnes.codigo)])
    autorizacion_id = solicitar(almacenista, trabajador, ev)
    aprobar(supervisor, autorizacion_id)
    r = almacenista.post(
        VALES,
        json=cuerpo_entrega(trabajador, [renglon(arnes.codigo)], autorizacion_id=autorizacion_id),
    )
    assert r.status_code == 201, r.text

    borrador = rehacer(almacenista, r.json()["id"])["borrador"]
    assert "autorizacion_id" not in borrador and "firma" not in borrador
    # Se evalúa otra vez completo: vuelve a ser naranja y no se puede confirmar sin autorización.
    ev = almacenista.post(EVALUAR, json=borrador).json()
    assert ev["nivel"] == "NARANJA" and ev["puede_confirmar"] is False
    assert ev["renglones"][0]["motivos"][0]["regla"] == "L-02"
    confirmar = almacenista.post(
        VALES, json=borrador | {"id_cliente": str(uuid.uuid4()), "firma": FIRMA}
    )
    assert confirmar.status_code == 409 and confirmar.json()["codigo"] == "VALE_CAMBIO"


def test_K_05_el_borrador_de_una_entrada_trae_los_datos_de_la_pieza(compras, session):
    arnes = crear_articulo(session, control="PIEZA", requiere_inspeccion=False)
    r, codigo = entrar_pieza(compras, arnes, serie="SERIE-77")
    assert r.status_code == 201
    cuerpo = compras.post(url(r.json()["id"]), json=cancelacion(rehacer=True))
    assert cuerpo.status_code == 201, cuerpo.text
    borrador = cuerpo.json()["borrador"]
    assert borrador["tipo"] == "ENTRADA" and borrador["trabajador_id"] is None
    assert borrador["renglones"] == [
        {
            "codigo": arnes.codigo,
            "cantidad": 1,
            "condicion": None,
            "observacion": None,
            "pieza": {"codigo": codigo, "numero_serie": "SERIE-77"},
        }
    ]


def test_ES_11_diez_pares_en_lugar_de_uno_cancelar_y_rehacer(
    almacenista, supervisor, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False, nombre="Guantes (par)")
    abastecer(compras, guantes, 50)

    def consumo():
        r = supervisor.get("/api/reportes/consumo", params={"articulo_id": str(guantes.id)})
        assert r.status_code == 200, r.text
        return sum(t["cantidad"] for i in r.json()["elementos"] for t in i["trabajadores"])

    # Marta confirma diez en vez de uno.
    mal = entregar(almacenista, trabajador, [renglon(guantes.codigo, 10)])
    assert existencia(session, "KEP", guantes) == 40 and consumo() == 10

    # Cancela y rehace: los diez regresan y el consumo vuelve a como estaba.
    cuerpo = rehacer(almacenista, mal["id"], motivo="error de captura")
    assert existencia(session, "KEP", guantes) == 50 and consumo() == 0
    borrador = cuerpo["borrador"]
    assert [(r["codigo"], r["cantidad"]) for r in borrador["renglones"]] == [(guantes.codigo, 10)]

    # Solo corrige la cantidad; el vale nuevo se evalúa de nuevo y el trabajador lo firma.
    borrador["renglones"][0]["cantidad"] = 1
    ev = almacenista.post(EVALUAR, json=borrador)
    assert ev.status_code == 200 and ev.json()["puede_confirmar"] is True
    bien = almacenista.post(
        VALES, json=borrador | {"id_cliente": str(uuid.uuid4()), "firma": FIRMA}
    )
    assert bien.status_code == 201, bien.text
    assert existencia(session, "KEP", guantes) == 49 and consumo() == 1

    # Los tres vales quedan en el historial del trabajador.
    historial = almacenista.get(VALES, params={"trabajador_id": str(trabajador.id)}).json()
    por_folio = {v["folio"]: v for v in historial["elementos"]}
    assert set(por_folio) == {mal["folio"], cuerpo["folio"], bien.json()["folio"]}
    assert por_folio[mal["folio"]]["estado"] == "CANCELADO"
    assert por_folio[cuerpo["folio"]]["tipo"] == "CANCELACION"
    assert por_folio[bien.json()["folio"]]["estado"] == "EMITIDO"
    assert detalle(almacenista, mal["id"])["cancelacion"]["motivo"] == "error de captura"
    # La cancelación no se pierde en el reporte de movimientos ni rompe las invariantes.
    revisar_invariantes(session)
    revisar_folios(session)
    assert total_vales(session) > 0 and total_movimientos(session) > 0
