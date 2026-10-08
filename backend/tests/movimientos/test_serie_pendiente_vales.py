"""Serie pendiente en los vales (I-02, E-29) y permisos de enviar y recibir (X-01, X-10, AC-06)."""
# ruff: noqa: F811  (los fixtures importados se piden por nombre en cada prueba)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.modulos.acceso.permisos import P
from app.modulos.catalogo.models import Pieza
from tests.conftest import iniciar_sesion_en
from tests.movimientos.ayudas import (
    abastecer,
    crear_articulo,
    crear_trabajador,
    cuerpo_entrada,
    cuerpo_entrega,
    entrar_pieza,
    unico,
)
from tests.movimientos.ayudas_traspasos import (
    EVALUAR,
    POR_RECIBIR,
    VALES,
    cliente_almacen,  # noqa: F401  (fixture)
    cuerpo_recepcion,
    cuerpo_traspaso,
    enviar,
    recibir,
    renglon,
)
from tests.movimientos.test_entrega import motivos, pieza_en_kep
from tests.movimientos.test_entrega import renglon as renglon_entrega


def _entrar_sin_serie(compras, articulo) -> str:
    codigo = unico("PZA")
    r = compras.post(
        VALES,
        json=cuerpo_entrada(
            [{"codigo": articulo.codigo, "cantidad": 1, "pieza": {"codigo": codigo}}]
        ),
    )
    assert r.status_code == 201, r.text
    return codigo


def test_I_02_una_entrada_sin_serie_se_confirma_y_la_pieza_queda_con_serie_pendiente(
    compras, session
):
    arnes = crear_articulo(session, control="PIEZA")
    codigo = _entrar_sin_serie(compras, arnes)
    pieza = session.scalar(select(Pieza).where(Pieza.codigo == codigo))
    assert pieza.numero_serie is None


def test_I_02_una_serie_repetida_en_una_entrada_sigue_siendo_rojo(compras, session):
    arnes = crear_articulo(session, control="PIEZA")
    serie = unico("REPE")
    r, _ = entrar_pieza(compras, arnes, serie=serie)
    assert r.status_code == 201, r.text
    cuerpo = {
        "tipo": "ENTRADA",
        "renglones": [
            {"codigo": arnes.codigo, "pieza": {"codigo": unico("P"), "numero_serie": serie}}
        ],
    }
    ev = compras.post(EVALUAR, json=cuerpo).json()
    assert ev["renglones"][0]["nivel"] == "ROJO" and ev["puede_confirmar"] is False
    assert [m["regla"] for m in ev["renglones"][0]["motivos"]] == ["I-02"]


def test_E_29_entregar_una_pieza_sin_serie_es_aviso_amarillo_que_no_bloquea(
    compras, almacenista, session
):
    arnes = crear_articulo(session, control="PIEZA")
    codigo = _entrar_sin_serie(compras, arnes)
    trabajador = crear_trabajador(session)
    ev = almacenista.post(
        EVALUAR, json=cuerpo_entrega(trabajador, [renglon_entrega(codigo)]) | {"tipo": "ENTREGA"}
    ).json()
    r = ev["renglones"][0]
    aviso = [m for m in r["motivos"] if m["regla"] == "E-29"]
    assert len(aviso) == 1
    assert aviso[0]["codigo"] == "SERIE_PENDIENTE" and aviso[0]["nivel"] == "AMARILLO"
    assert r["pieza"]["serie_pendiente"] is True
    assert r["nivel"] == "AMARILLO" and ev["puede_confirmar"] is True
    assert "E-29" in motivos(ev)


def test_E_29_una_pieza_con_serie_no_trae_el_aviso(compras, almacenista, session):
    _, pieza = pieza_en_kep(compras, session)
    trabajador = crear_trabajador(session)
    ev = almacenista.post(
        EVALUAR, json=cuerpo_entrega(trabajador, [renglon_entrega(pieza.codigo)])
    ).json()
    assert "E-29" not in motivos(ev)
    assert ev["renglones"][0]["pieza"]["serie_pendiente"] is False


def test_E_29_el_traspaso_no_mira_la_serie(compras, cliente_almacen, session):
    arnes = crear_articulo(session, control="PIEZA")
    codigo = _entrar_sin_serie(compras, arnes)
    supervisor = cliente_almacen("KEP")
    ev = supervisor.post(EVALUAR, json=cuerpo_traspaso(session, "CON", [renglon(codigo)])).json()
    assert ev["puede_confirmar"] is True
    assert all(m["regla"] != "E-29" for r in ev["renglones"] for m in r["motivos"])


# ------------------------------------------------------------------- permisos de recibir


def _usuario_con(app, crear_usuario, permisos, almacen) -> TestClient:
    cliente = TestClient(app)
    assert (
        iniciar_sesion_en(cliente, crear_usuario(set(permisos), almacen=almacen)).status_code == 200
    )
    return cliente


def test_X_10_quien_tiene_traspasos_recibir_recibe_en_su_almacen(
    app, crear_usuario, cliente_almacen, compras, session
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 8)
    traspaso = enviar(cliente_almacen("KEP"), session, "CON", [renglon(guantes.codigo, 5)])
    # Un rol de almacenista de Contratistas al que se le dio `traspasos.recibir` (X-01).
    almacenista_con = _usuario_con(
        app, crear_usuario, {P.INVENTARIO_VER, P.TRASPASOS_RECIBIR}, "CON"
    )
    assert almacenista_con.get(POR_RECIBIR).status_code == 200
    recepcion = recibir(almacenista_con, traspaso, [renglon(guantes.codigo, 5)])
    assert recepcion["folio"].startswith("CON-REC-")


def test_X_10_recibir_fuera_del_destino_sigue_en_rojo_aunque_tenga_el_permiso(
    app, crear_usuario, cliente_almacen, compras, session
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 8)
    traspaso = enviar(cliente_almacen("KEP"), session, "CON", [renglon(guantes.codigo, 5)])
    en_mid = _usuario_con(app, crear_usuario, {P.INVENTARIO_VER, P.TRASPASOS_RECIBIR}, "MID")
    ev = en_mid.post(EVALUAR, json=cuerpo_recepcion(traspaso["id"], [renglon(guantes.codigo, 5)]))
    assert ev.status_code == 200 and ev.json()["puede_confirmar"] is False
    assert "X-10" in {m["regla"] for m in ev.json()["motivos"]}


def test_X_01_operar_solo_envia_y_recibir_solo_recibe(
    app, crear_usuario, cliente_almacen, compras, session
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 8)
    traspaso = enviar(cliente_almacen("KEP"), session, "CON", [renglon(guantes.codigo, 5)])
    solo_envia = _usuario_con(app, crear_usuario, {P.INVENTARIO_VER, P.TRASPASOS_OPERAR}, "CON")
    solo_recibe = _usuario_con(app, crear_usuario, {P.INVENTARIO_VER, P.TRASPASOS_RECIBIR}, "KEP")
    recepcion = cuerpo_recepcion(traspaso["id"], [renglon(guantes.codigo, 5)])
    envio = cuerpo_traspaso(session, "CON", [renglon(guantes.codigo, 1)])
    # Quien solo envía no recibe (ni ve la lista de por recibir).
    assert solo_envia.post(EVALUAR, json=recepcion).status_code == 403
    assert solo_envia.post(VALES, json=recepcion).status_code == 403
    assert solo_envia.get(POR_RECIBIR).status_code == 403
    # Quien solo recibe no envía.
    assert solo_recibe.post(EVALUAR, json=envio).status_code == 403
    assert solo_recibe.post(VALES, json=envio).status_code == 403


@pytest.mark.parametrize(
    "rol,puede", [("Supervisor", True), ("Almacenista", True), ("Compras", False)]
)
def test_X_01_el_supervisor_y_el_almacenista_reciben_los_demas_roles_no(cliente_como, rol, puede):
    assert (cliente_como(rol).get(POR_RECIBIR).status_code == 200) is puede
