# ruff: noqa: F811  (los fixtures importados se piden por nombre en cada prueba)
"""RECEPCION (US-TRS-002): X-08, X-10 a X-13, F-09, RG-05 y `GET /api/traspasos/por-recibir`."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.tiempo import hoy_mx
from app.modulos.catalogo.models import EstadoPieza
from app.modulos.movimientos.models import Movimiento, Vale
from tests.movimientos.ayudas import (
    abastecer,
    crear_articulo,
    crear_trabajador,
    cuerpo_entrega,
    existencia,
    total_movimientos,
    total_vales,
)
from tests.movimientos.ayudas_traspasos import (
    EVALUAR,
    POR_RECIBIR,
    VALES,
    almacen_id,
    cliente_almacen,  # noqa: F401  (fixture)
    cuerpo_recepcion,
    en_transito,
    enviar,
    enviar_por_ruta_inusual,
    evaluar_recepcion,
    movimientos_del_vale,
    pieza,
    recibir,
    reglas,
    renglon,
    total_en_almacenes,
    ubicacion_de_pieza,
    vale,
)
from tests.movimientos.test_entrega import pieza_en_kep
from tests.movimientos.test_invariantes import revisar_folios, revisar_invariantes


@pytest.fixture
def almacenista(cliente_como):
    """El que opera los traspasos de Kepler: su supervisor (`traspasos.operar` es del Supervisor,
    tabla 8.2; el almacenista no los opera). Se llama `almacenista` por las pruebas ya escritas."""
    return cliente_como("Supervisor")


def vigencia():
    return hoy_mx() + timedelta(days=60)


def traspaso_mixto(almacenista, compras, session, cantidad=10, enviar_n=6, destino="CON"):
    """Un traspaso de KEP con un artículo por cantidad y dos piezas. Devuelve
    `(traspaso, guantes, (pieza_a, pieza_b))`."""
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, cantidad)
    _, p1 = pieza_en_kep(compras, session, vigente_hasta=vigencia())
    _, p2 = pieza_en_kep(compras, session, vigente_hasta=vigencia())
    traspaso = enviar(
        almacenista,
        session,
        destino,
        [renglon(guantes.codigo, enviar_n), renglon(p1.codigo), renglon(p2.codigo)],
    )
    return traspaso, guantes, (p1, p2)


# --------------------------------------------------------------- recepción total (X-01, X-08)


def test_X_08_la_recepcion_total_mete_todo_al_destino_y_el_traspaso_queda_recibido(
    almacenista, cliente_almacen, compras, session
):
    traspaso, guantes, (p1, p2) = traspaso_mixto(almacenista, compras, session)
    con = cliente_almacen("CON")
    antes_total = total_en_almacenes(session, guantes)

    recepcion = recibir(
        con, traspaso, [renglon(guantes.codigo, 6), renglon(p1.codigo), renglon(p2.codigo)]
    )

    assert recepcion["folio"].startswith("CON-REC-")  # folio del almacén que recibe
    assert vale(session, traspaso["id"]).estado == "RECIBIDO"
    assert existencia(session, "CON", guantes) == 6 and existencia(session, "KEP", guantes) == 4
    assert en_transito(session, guantes) == 0
    assert total_en_almacenes(session, guantes) == antes_total + 6  # vuelve a contar
    assert ubicacion_de_pieza(session, p1.codigo) == "CON"
    assert ubicacion_de_pieza(session, p2.codigo) == "CON"
    # X-08: quien recibe es el responsable de lo recibido; F-09: firma con su sesión.
    d = con.get(f"/api/vales/{recepcion['id']}").json()
    assert d["tipo"] == "RECEPCION" and d["responsable"]["nombre"] == "Supervisor Contratistas"
    assert d["firma_modo"] == "SESION" and d["tiene_firma"] is False
    assert d["vale_origen_id"] == traspaso["id"] and d["vale_origen_folio"] == traspaso["folio"]
    assert d["almacen"]["clave"] == "CON"
    # Cada movimiento sale de En tránsito y entra al almacén que recibe (X-07).
    for r in d["renglones"]:
        assert r["origen"]["tipo"] == "EN_TRANSITO" and r["destino"]["clave"] == "CON"
        assert "X-08" in r["reglas"]
    # El traspaso original conserva sus renglones: solo cambió su estado (invariante 5).
    assert len(movimientos_del_vale(session, traspaso["id"])) == 3
    revisar_invariantes(session)
    revisar_folios(session)


def test_X_11_se_puede_recibir_todo_de_una_vez_con_todos_los_renglones_pendientes(
    almacenista, cliente_almacen, compras, session
):
    traspaso, guantes, (p1, p2) = traspaso_mixto(almacenista, compras, session)
    con = cliente_almacen("CON")
    pendiente = con.get(POR_RECIBIR).json()["elementos"][0]["renglones"]
    todo = [renglon(r["codigo"], r["cantidad_pendiente"]) for r in pendiente]
    ev = evaluar_recepcion(con, traspaso, todo)
    assert ev["nivel"] == "VERDE" and ev["puede_confirmar"] is True and reglas(ev) == []
    recibir(con, traspaso, todo)
    assert vale(session, traspaso["id"]).estado == "RECIBIDO"
    assert con.get(POR_RECIBIR).json()["total"] == 0


def test_X_11_se_puede_recibir_renglon_por_renglon_escaneando(
    almacenista, cliente_almacen, compras, session
):
    """Cada escaneo agrega un renglón al borrador; lo que ya escaneó se confirma junto."""
    traspaso, guantes, (p1, p2) = traspaso_mixto(almacenista, compras, session, enviar_n=3)
    con = cliente_almacen("CON")
    # el artículo por cantidad se escanea de a uno: tres escaneos suman 3 (E-16)
    recibir(
        con,
        traspaso,
        [
            renglon(guantes.codigo),
            renglon(p1.codigo),
            renglon(guantes.codigo),
            renglon(p2.codigo),
            renglon(guantes.codigo),
        ],
    )
    assert existencia(session, "CON", guantes) == 3
    assert vale(session, traspaso["id"]).estado == "RECIBIDO"


# ------------------------------------------------------------------ X-13: recibir con faltantes


def test_X_13_lo_no_recibido_sigue_en_transito_y_el_traspaso_queda_con_diferencias(
    almacenista, cliente_almacen, compras, session
):
    traspaso, guantes, (p1, p2) = traspaso_mixto(almacenista, compras, session)
    con = cliente_almacen("CON")
    parcial = [renglon(guantes.codigo, 4), renglon(p1.codigo)]
    ev = evaluar_recepcion(con, traspaso, parcial)
    assert ev["nivel"] == "AMARILLO" and ev["puede_confirmar"] is True
    assert reglas(ev) == ["X-13"] and "faltarían 3" in ev["motivos"][0]["mensaje"]

    recepcion = recibir(con, traspaso, parcial)

    assert vale(session, traspaso["id"]).estado == "RECIBIDO_CON_DIFERENCIAS"
    assert existencia(session, "CON", guantes) == 4
    assert en_transito(session, guantes) == 2  # lo que falta sigue En tránsito
    assert ubicacion_de_pieza(session, p1.codigo) == "CON"
    assert ubicacion_de_pieza(session, p2.codigo) == "EN_TRANSITO"
    assert "X-13" in recepcion["renglones"][0]["reglas"]
    # Entra a la lista de revisión: sigue en por-recibir, con lo recibido y lo pendiente.
    lista = con.get(POR_RECIBIR).json()
    assert lista["total"] == 1
    t = lista["elementos"][0]
    assert t["estado"] == "RECIBIDO_CON_DIFERENCIAS" and t["pendiente_total"] == 3
    por_codigo = {r["codigo"]: r for r in t["renglones"]}
    assert (
        por_codigo[guantes.codigo]["cantidad_enviada"],
        por_codigo[guantes.codigo]["cantidad_recibida"],
        por_codigo[guantes.codigo]["cantidad_pendiente"],
    ) == (6, 4, 2)
    assert por_codigo[p1.codigo]["cantidad_pendiente"] == 0
    assert por_codigo[p2.codigo]["cantidad_pendiente"] == 1
    assert [r["folio"] for r in t["recepciones"]] == [recepcion["folio"]]
    revisar_invariantes(session)


def test_X_13_recepciones_sucesivas_hasta_completar_dejan_el_traspaso_recibido(
    almacenista, cliente_almacen, compras, session
):
    traspaso, guantes, (p1, p2) = traspaso_mixto(almacenista, compras, session)
    con = cliente_almacen("CON")
    recibir(con, traspaso, [renglon(guantes.codigo, 2)])
    assert vale(session, traspaso["id"]).estado == "RECIBIDO_CON_DIFERENCIAS"
    recibir(con, traspaso, [renglon(guantes.codigo, 3), renglon(p2.codigo)])
    assert vale(session, traspaso["id"]).estado == "RECIBIDO_CON_DIFERENCIAS"
    assert en_transito(session, guantes) == 1
    ultima = recibir(con, traspaso, [renglon(guantes.codigo, 1), renglon(p1.codigo)])
    assert vale(session, traspaso["id"]).estado == "RECIBIDO"
    assert "X-13" not in ultima["renglones"][0]["reglas"]
    assert en_transito(session, guantes) == 0 and existencia(session, "CON", guantes) == 6
    assert con.get(POR_RECIBIR).json()["total"] == 0
    recepciones = session.scalars(
        select(Vale).where(Vale.vale_origen_id == uuid.UUID(traspaso["id"])).order_by(Vale.folio)
    ).all()
    assert [v.folio.split("-")[1] for v in recepciones] == ["REC"] * 3
    revisar_invariantes(session)
    revisar_folios(session)


def test_X_13_un_traspaso_recibido_con_diferencias_sigue_en_la_lista_de_su_destino_y_no_en_otras(
    almacenista, cliente_almacen, compras, session
):
    traspaso, guantes, _ = traspaso_mixto(almacenista, compras, session)
    recibir(cliente_almacen("CON"), traspaso, [renglon(guantes.codigo, 1)])
    assert [t["id"] for t in cliente_almacen("CON").get(POR_RECIBIR).json()["elementos"]] == [
        traspaso["id"]
    ]
    assert cliente_almacen("MID").get(POR_RECIBIR).json() == {"total": 0, "elementos": []}
    assert almacenista.get(POR_RECIBIR).json() == {"total": 0, "elementos": []}  # el origen no


def test_X_13_RG_14_una_recepcion_con_diferencias_exige_observacion(
    almacenista, cliente_almacen, compras, session
):
    traspaso, guantes, (p1, p2) = traspaso_mixto(almacenista, compras, session)
    con = cliente_almacen("CON")
    parcial = [renglon(guantes.codigo, 4), renglon(p1.codigo)]
    sin = cuerpo_recepcion(traspaso["id"], parcial, observacion=None)

    # La evaluación lo marca en rojo antes de confirmar, con la regla.
    ev = con.post(EVALUAR, json=sin).json()
    assert ev["nivel"] == "ROJO" and ev["puede_confirmar"] is False
    assert reglas(ev) == ["X-13", "RG-14"]
    # Una observación en blanco tampoco cuenta.
    en_blanco = con.post(EVALUAR, json={**sin, "observacion": "   "}).json()
    assert en_blanco["nivel"] == "ROJO"

    vales = total_vales(session)
    r = con.post(VALES, json=sin)
    assert r.status_code == 422 and r.json()["codigo"] == "DATOS_INVALIDOS"
    assert r.json()["detalles"][0]["campo"] == "observacion"
    assert r.json()["detalles"][0]["regla"] == "RG-14"
    assert total_vales(session) == vales  # no se guardó nada
    assert vale(session, traspaso["id"]).estado == "EN_TRANSITO"

    # Con la observación se evalúa en amarillo y se confirma; queda en el vale.
    con_obs = cuerpo_recepcion(traspaso["id"], parcial, observacion="Faltó en el contenedor")
    assert con.post(EVALUAR, json=con_obs).json()["nivel"] == "AMARILLO"
    r = con.post(VALES, json=con_obs)
    assert r.status_code == 201, r.text
    assert vale(session, r.json()["id"]).observacion == "Faltó en el contenedor"
    assert vale(session, traspaso["id"]).estado == "RECIBIDO_CON_DIFERENCIAS"
    revisar_invariantes(session)


def test_X_13_RG_14_la_recepcion_completa_no_pide_observacion(
    almacenista, cliente_almacen, compras, session
):
    traspaso, guantes, (p1, p2) = traspaso_mixto(almacenista, compras, session)
    con = cliente_almacen("CON")
    todo = [renglon(guantes.codigo, 6), renglon(p1.codigo), renglon(p2.codigo)]
    ev = con.post(EVALUAR, json=cuerpo_recepcion(traspaso["id"], todo, observacion=None)).json()
    assert ev["nivel"] == "VERDE" and reglas(ev) == []
    r = con.post(VALES, json=cuerpo_recepcion(traspaso["id"], todo, observacion=None))
    assert r.status_code == 201, r.text
    assert vale(session, traspaso["id"]).estado == "RECIBIDO"


def test_X_13_RG_14_recepciones_sucesivas_piden_observacion_mientras_quede_algo_pendiente(
    almacenista, cliente_almacen, compras, session
):
    traspaso, guantes, (p1, p2) = traspaso_mixto(almacenista, compras, session)
    con = cliente_almacen("CON")
    recibir(con, traspaso, [renglon(guantes.codigo, 2)])  # con observación (ayuda)
    segunda = cuerpo_recepcion(traspaso["id"], [renglon(guantes.codigo, 2)], observacion=None)
    r = con.post(VALES, json=segunda)
    assert r.status_code == 422 and r.json()["detalles"][0]["campo"] == "observacion"
    # La que ya completa lo pendiente no la pide.
    resto = [renglon(guantes.codigo, 4), renglon(p1.codigo), renglon(p2.codigo)]
    ultima = cuerpo_recepcion(traspaso["id"], resto, observacion=None)
    assert con.post(VALES, json=ultima).status_code == 201
    assert vale(session, traspaso["id"]).estado == "RECIBIDO"


# ----------------------------------------------------------------------------- X-10


def test_X_10_solo_el_almacen_de_destino_puede_recibir(
    almacenista, cliente_almacen, compras, session
):
    traspaso, guantes, (p1, p2) = traspaso_mixto(almacenista, compras, session)
    vales, movs = total_vales(session), total_movimientos(session)
    # Ni el origen, ni otro almacén: rojo en todo el vale y en cada renglón.
    for clave in ("KEP", "MID"):
        cliente = almacenista if clave == "KEP" else cliente_almacen(clave)
        ev = evaluar_recepcion(cliente, traspaso, [renglon(guantes.codigo, 6), renglon(p1.codigo)])
        assert ev["nivel"] == "ROJO" and ev["puede_confirmar"] is False, clave
        assert reglas(ev) == ["X-10"] and reglas(ev, 0) == ["X-10"] and reglas(ev, 1) == ["X-10"]
        # no enseña el contenido del traspaso a quien no es el destino
        assert ev["renglones"][0]["articulo"] is None
        r = cliente.post(VALES, json=cuerpo_recepcion(traspaso["id"], [renglon(guantes.codigo, 6)]))
        assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO", clave
        assert r.json()["detalles"]["motivos"][0]["regla"] == "X-10"
    assert total_vales(session) == vales and total_movimientos(session) == movs
    assert en_transito(session, guantes) == 6 and existencia(session, "CON", guantes) == 0
    assert vale(session, traspaso["id"]).estado == "EN_TRANSITO"


def test_X_10_quien_opera_todos_los_almacenes_recibe_indicando_el_destino(
    almacenista, cliente_como, compras, session
):
    traspaso, guantes, _ = traspaso_mixto(almacenista, compras, session)
    supervisor = cliente_como("Administrador")  # el único con `almacenes.todos`
    en_kep = cuerpo_recepcion(
        traspaso["id"], [renglon(guantes.codigo, 6)], almacen_id=str(almacen_id(session, "KEP"))
    )
    assert supervisor.post("/api/vales/evaluar", json=en_kep).json()["nivel"] == "ROJO"
    assert supervisor.post(VALES, json=en_kep).status_code == 409
    en_con = cuerpo_recepcion(
        traspaso["id"], [renglon(guantes.codigo, 6)], almacen_id=str(almacen_id(session, "CON"))
    )
    r = supervisor.post(VALES, json=en_con)
    assert r.status_code == 201 and r.json()["folio"].startswith("CON-REC-")
    assert existencia(session, "CON", guantes) == 6


# ----------------------------------------------------------------------------- X-12


def test_X_12_lo_escaneado_que_no_pertenece_al_traspaso_es_rojo(
    almacenista, cliente_almacen, compras, session
):
    traspaso, guantes, (p1, p2) = traspaso_mixto(almacenista, compras, session)
    ajeno = crear_articulo(session, retornable=False)
    abastecer(compras, ajeno, 3)
    articulo_pieza, pieza_ajena = pieza_en_kep(compras, session, vigente_hasta=vigencia())
    con = cliente_almacen("CON")
    ev = evaluar_recepcion(
        con,
        traspaso,
        [
            renglon(ajeno.codigo),  # artículo que no viene
            renglon(pieza_ajena.codigo),  # pieza que no viene
            renglon("NO-EXISTE-Q"),  # código desconocido
            renglon(articulo_pieza.codigo),  # artículo por pieza escaneado por artículo
            renglon(guantes.codigo, 7),  # más de lo enviado
        ],
    )
    assert ev["nivel"] == "ROJO" and ev["puede_confirmar"] is False
    assert [reglas(ev, i) for i in range(5)] == [["X-12"]] * 5
    mensajes = [r["motivos"][0]["mensaje"] for r in ev["renglones"]]
    assert "no viene en este traspaso" in mensajes[0]
    assert "no viene en este traspaso" in mensajes[1]
    assert "no existe" in mensajes[2]
    assert "escanea el código de la pieza" in mensajes[3]
    assert "faltan por recibir 6" in mensajes[4]
    r = con.post(VALES, json=cuerpo_recepcion(traspaso["id"], [renglon(ajeno.codigo)]))
    assert (
        r.status_code == 409
        and r.json()["detalles"]["renglones"][0]["motivos"][0]["regla"] == "X-12"
    )
    assert existencia(session, "CON", ajeno) == 0 and en_transito(session, ajeno) == 0


def test_X_12_un_renglon_en_rojo_hace_que_no_se_reciba_nada(
    almacenista, cliente_almacen, compras, session
):
    traspaso, guantes, (p1, p2) = traspaso_mixto(almacenista, compras, session)
    ajeno = crear_articulo(session, retornable=False)
    abastecer(compras, ajeno, 3)
    vales, movs = total_vales(session), total_movimientos(session)
    r = cliente_almacen("CON").post(
        VALES,
        json=cuerpo_recepcion(traspaso["id"], [renglon(guantes.codigo, 6), renglon(ajeno.codigo)]),
    )
    assert r.status_code == 409
    assert total_vales(session) == vales and total_movimientos(session) == movs
    assert existencia(session, "CON", guantes) == 0 and en_transito(session, guantes) == 6
    assert vale(session, traspaso["id"]).estado == "EN_TRANSITO"
    revisar_invariantes(session)
    revisar_folios(session)


def test_X_12_no_se_recibe_dos_veces_lo_mismo(almacenista, cliente_almacen, compras, session):
    traspaso, guantes, (p1, p2) = traspaso_mixto(almacenista, compras, session)
    con = cliente_almacen("CON")
    recibir(con, traspaso, [renglon(guantes.codigo, 6), renglon(p1.codigo)])
    ev = evaluar_recepcion(con, traspaso, [renglon(p1.codigo), renglon(guantes.codigo)])
    assert (
        reglas(ev, 0) == ["X-12"] and "ya se recibió" in ev["renglones"][0]["motivos"][0]["mensaje"]
    )
    assert (
        reglas(ev, 1) == ["X-12"]
        and "Ya se recibió todo" in ev["renglones"][1]["motivos"][0]["mensaje"]
    )
    r = con.post(VALES, json=cuerpo_recepcion(traspaso["id"], [renglon(p1.codigo)]))
    assert r.status_code == 409
    # lo que faltaba (p2) sí se recibe, y con eso el traspaso se completa
    recibir(con, traspaso, [renglon(p2.codigo)])
    assert vale(session, traspaso["id"]).estado == "RECIBIDO"
    # y ya completo no se puede recibir nada más
    ev = evaluar_recepcion(con, traspaso, [renglon(p2.codigo)])
    assert ev["nivel"] == "ROJO" and "X-12" in reglas(ev)
    assert existencia(session, "CON", guantes) == 6
    revisar_invariantes(session)


def test_un_traspaso_cancelado_ya_no_se_recibe_X_14(almacenista, cliente_almacen, compras, session):
    """La cancelación la hace el tipo CANCELACION; aquí solo se comprueba que una recepción no
    pasa sobre un traspaso ya cancelado."""
    traspaso, guantes, _ = traspaso_mixto(almacenista, compras, session)
    vale(session, traspaso["id"]).estado = "CANCELADO"
    session.flush()
    con = cliente_almacen("CON")
    ev = evaluar_recepcion(con, traspaso, [renglon(guantes.codigo, 1)])
    assert ev["nivel"] == "ROJO" and "X-14" in reglas(ev)
    assert (
        con.post(
            VALES, json=cuerpo_recepcion(traspaso["id"], [renglon(guantes.codigo)])
        ).status_code
        == 409
    )
    assert con.get(POR_RECIBIR).json()["total"] == 0


# --------------------------------------------------------------------- cuerpo y errores


def test_una_recepcion_sin_renglones_o_sin_traspaso_se_rechaza(
    almacenista, cliente_almacen, compras, session
):
    traspaso, guantes, _ = traspaso_mixto(almacenista, compras, session)
    con = cliente_almacen("CON")
    r = con.post(VALES, json=cuerpo_recepcion(traspaso["id"], []))
    assert r.status_code == 422 and r.json()["detalles"][0]["campo"] == "renglones"
    sin_origen = cuerpo_recepcion(traspaso["id"], [renglon(guantes.codigo)])
    del sin_origen["vale_origen_id"]
    r = con.post(VALES, json=sin_origen)
    assert r.status_code == 422 and r.json()["detalles"][0]["campo"] == "vale_origen_id"
    r = con.post(VALES, json=cuerpo_recepcion(str(uuid.uuid4()), [renglon(guantes.codigo)]))
    assert r.status_code == 404
    # un vale que no es un traspaso (la entrada de Compras)
    entrada = abastecer(compras, guantes, 1)
    r = con.post(VALES, json=cuerpo_recepcion(entrada["id"], [renglon(guantes.codigo)]))
    assert r.status_code == 422 and r.json()["detalles"][0]["campo"] == "vale_origen_id"
    t = crear_trabajador(session)
    r = con.post(
        VALES,
        json=cuerpo_recepcion(traspaso["id"], [renglon(guantes.codigo)], trabajador_id=str(t.id)),
    )
    assert r.status_code == 422


def test_una_recepcion_pide_el_permiso_traspasos_operar(
    almacenista, cliente_como, compras, session
):
    traspaso, guantes, _ = traspaso_mixto(almacenista, compras, session)
    cuerpo = cuerpo_recepcion(traspaso["id"], [renglon(guantes.codigo)])
    for rol in ("Recursos Humanos", "Compras", "Almacenista"):  # el almacenista no opera traspasos
        c = cliente_como(rol)
        assert c.post("/api/vales/evaluar", json=cuerpo).status_code == 403, rol
        assert c.post(VALES, json=cuerpo).status_code == 403, rol
        assert c.get(POR_RECIBIR).status_code == 403, rol


def test_RG_08_la_recepcion_es_idempotente_con_el_mismo_id_cliente(
    almacenista, cliente_almacen, compras, session
):
    traspaso, guantes, _ = traspaso_mixto(almacenista, compras, session)
    con = cliente_almacen("CON")
    cuerpo = cuerpo_recepcion(traspaso["id"], [renglon(guantes.codigo, 6)])
    primero, segundo = con.post(VALES, json=cuerpo), con.post(VALES, json=cuerpo)
    assert (primero.status_code, segundo.status_code) == (201, 200)
    assert primero.json() == segundo.json()
    assert existencia(session, "CON", guantes) == 6  # una sola vez
    n = session.scalars(select(Vale.id).where(Vale.vale_origen_id == uuid.UUID(traspaso["id"])))
    assert len(n.all()) == 1


def test_RG_09_un_error_al_recibir_no_deja_a_medias_ni_el_estado_del_traspaso(
    almacenista, cliente_almacen, compras, session, monkeypatch
):
    import pytest

    from app.modulos.movimientos.repository import MovimientoRepository

    traspaso, guantes, (p1, p2) = traspaso_mixto(almacenista, compras, session)
    vales, movs = total_vales(session), total_movimientos(session)
    original = MovimientoRepository.add_movimiento
    llamadas = []

    def falla_en_el_tercero(self, movimiento):
        llamadas.append(movimiento.renglon)
        if len(llamadas) == 3:
            raise RuntimeError("falla simulada")
        return original(self, movimiento)

    monkeypatch.setattr(MovimientoRepository, "add_movimiento", falla_en_el_tercero)
    with pytest.raises(RuntimeError, match="falla simulada"):
        cliente_almacen("CON").post(
            VALES,
            json=cuerpo_recepcion(
                traspaso["id"],
                [renglon(guantes.codigo, 6), renglon(p1.codigo), renglon(p2.codigo)],
            ),
        )
    monkeypatch.undo()
    assert total_vales(session) == vales and total_movimientos(session) == movs
    assert vale(session, traspaso["id"]).estado == "EN_TRANSITO"
    assert en_transito(session, guantes) == 6 and existencia(session, "CON", guantes) == 0
    assert ubicacion_de_pieza(session, p1.codigo) == "EN_TRANSITO"
    revisar_invariantes(session)
    revisar_folios(session)


def test_la_pieza_no_apta_conserva_su_estado_al_recibirse_X_04(
    almacenista, cliente_almacen, compras, session
):
    _, p = pieza_en_kep(compras, session, estado=EstadoPieza.NO_APTO, vigente_hasta=vigencia())
    traspaso = enviar(almacenista, session, "CON", [renglon(p.codigo)])
    recibir(cliente_almacen("CON"), traspaso, [renglon(p.codigo)])
    assert pieza(session, p.codigo).estado == EstadoPieza.NO_APTO
    assert ubicacion_de_pieza(session, p.codigo) == "CON"


def test_el_vale_de_recepcion_no_trae_costos_RG_12(almacenista, cliente_almacen, compras, session):
    traspaso, guantes, _ = traspaso_mixto(almacenista, compras, session)
    con = cliente_almacen("CON")
    recepcion = recibir(con, traspaso, [renglon(guantes.codigo, 6)])
    texto = con.get(f"/api/vales/{recepcion['id']}").text.lower()
    assert "costo" not in texto and "precio" not in texto
    assert "costo" not in con.get(POR_RECIBIR).text.lower()


def test_el_qr_del_traspaso_lo_abren_el_origen_y_el_destino_pero_no_otro_almacen(
    almacenista, cliente_almacen, compras, session
):
    traspaso, _, _ = traspaso_mixto(almacenista, compras, session)
    ruta = f"/api/vales/por-token/{traspaso['token']}"
    assert cliente_almacen("CON").get(ruta).status_code == 200
    assert almacenista.get(ruta).status_code == 200
    assert cliente_almacen("MID").get(ruta).status_code == 404


def test_las_existencias_de_los_dos_almacenes_antes_y_despues(
    almacenista, cliente_almacen, compras, session
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 10)
    con = cliente_almacen("CON")

    def tabla():
        return (
            existencia(session, "KEP", guantes),
            en_transito(session, guantes),
            existencia(session, "CON", guantes),
        )

    assert tabla() == (10, 0, 0)
    traspaso = enviar(almacenista, session, "CON", [renglon(guantes.codigo, 7)])
    assert tabla() == (3, 7, 0)
    recibir(con, traspaso, [renglon(guantes.codigo, 5)])
    assert tabla() == (3, 2, 5)
    recibir(con, traspaso, [renglon(guantes.codigo, 2)])
    assert tabla() == (3, 0, 7)
    assert sum(tabla()) == 10  # nada se creó ni se perdió


# -------------------------------------------------------------------------- por-recibir


def test_por_recibir_cada_almacen_solo_ve_los_que_vienen_hacia_el_suyo(
    almacenista, cliente_almacen, cliente_como, compras, session
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 20)
    a_con = enviar(almacenista, session, "CON", [renglon(guantes.codigo, 2)])
    # Ruta inusual: solo la hace el Administrador (X-03).
    a_mid = enviar_por_ruta_inusual(
        cliente_como("Administrador"), session, "KEP", "MID", [renglon(guantes.codigo, 3)]
    )
    con, mid = cliente_almacen("CON"), cliente_almacen("MID")
    lista_con = con.get(POR_RECIBIR).json()
    assert lista_con["total"] == 1 and lista_con["elementos"][0]["id"] == a_con["id"]
    lista_mid = mid.get(POR_RECIBIR).json()
    assert lista_mid["total"] == 1 and lista_mid["elementos"][0]["id"] == a_mid["id"]
    t = lista_con["elementos"][0]
    assert t["folio"] == a_con["folio"] and t["token"] == a_con["token"]
    assert t["estado"] == "EN_TRANSITO" and t["pendiente_total"] == 2
    assert t["origen"]["clave"] == "KEP" and t["destino"]["clave"] == "CON"
    assert t["envio"]["nombre"] == "Supervisor Kepler"
    assert t["renglones"][0]["codigo"] == guantes.codigo and t["recepciones"] == []
    assert almacenista.get(POR_RECIBIR).json() == {"total": 0, "elementos": []}


def test_por_recibir_trae_el_codigo_de_la_pieza_y_su_serie(
    almacenista, cliente_almacen, compras, session
):
    _, p = pieza_en_kep(compras, session, vigente_hasta=vigencia())
    enviar(almacenista, session, "CON", [renglon(p.codigo)])
    r = cliente_almacen("CON").get(POR_RECIBIR).json()["elementos"][0]["renglones"][0]
    assert r["codigo"] == p.codigo and r["pieza_id"] == str(p.id)
    assert r["numero_serie"] == p.numero_serie and r["cantidad_pendiente"] == 1


def test_por_recibir_solo_contar_devuelve_el_total(almacenista, cliente_almacen, compras, session):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 20)
    con = cliente_almacen("CON")
    assert con.get(POR_RECIBIR, params={"solo_contar": "true"}).json() == {"total": 0}
    enviar(almacenista, session, "CON", [renglon(guantes.codigo, 2)])
    t = enviar(almacenista, session, "CON", [renglon(guantes.codigo, 2)])
    assert con.get(POR_RECIBIR, params={"solo_contar": "true"}).json() == {"total": 2}
    recibir(con, t, [renglon(guantes.codigo, 2)])
    assert con.get(POR_RECIBIR, params={"solo_contar": "true"}).json() == {"total": 1}


def test_por_recibir_quien_opera_todos_filtra_por_almacen_y_sin_filtro_ve_todos(
    almacenista, cliente_como, compras, session
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 20)
    enviar(almacenista, session, "CON", [renglon(guantes.codigo)])
    supervisor = cliente_como("Administrador")  # el único con `almacenes.todos`
    enviar_por_ruta_inusual(supervisor, session, "KEP", "MID", [renglon(guantes.codigo)])
    assert supervisor.get(POR_RECIBIR).json()["total"] >= 2
    solo_con = supervisor.get(POR_RECIBIR, params={"almacen_id": str(almacen_id(session, "CON"))})
    assert {t["destino"]["clave"] for t in solo_con.json()["elementos"]} == {"CON"}
    conteo = supervisor.get(
        POR_RECIBIR, params={"almacen_id": str(almacen_id(session, "MID")), "solo_contar": "true"}
    )
    assert conteo.json() == {"total": 1}
    assert supervisor.get(POR_RECIBIR, params={"almacen_id": str(uuid.uuid4())}).status_code == 404


def test_por_recibir_un_almacen_ajeno_se_rechaza_sin_almacenes_todos(
    almacenista, cliente_almacen, session
):
    r = cliente_almacen("CON").get(
        POR_RECIBIR, params={"almacen_id": str(almacen_id(session, "MID"))}
    )
    assert r.status_code == 409 and r.json()["codigo"] == "ALMACEN_CAMBIO"
    r = cliente_almacen("CON").get(
        POR_RECIBIR, params={"almacen_id": str(almacen_id(session, "CON"))}
    )
    assert r.status_code == 200


def test_por_recibir_va_del_mas_antiguo_al_mas_nuevo(
    almacenista, cliente_almacen, compras, session
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 20)
    primero = enviar(almacenista, session, "CON", [renglon(guantes.codigo)])
    segundo = enviar(almacenista, session, "CON", [renglon(guantes.codigo)])
    ids = [t["id"] for t in cliente_almacen("CON").get(POR_RECIBIR).json()["elementos"]]
    assert ids == [primero["id"], segundo["id"]]


def test_una_entrega_normal_no_se_afecta_por_los_traspasos(
    almacenista, cliente_almacen, compras, session
):
    """Lo recibido en Contratistas ya se puede entregar allá (E-04 con la existencia nueva)."""
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 10)
    con = cliente_almacen("CON")
    t = crear_trabajador(session)
    ev = con.post("/api/vales/evaluar", json=cuerpo_entrega(t, [renglon(guantes.codigo, 2)])).json()
    assert reglas(ev, 0) == ["E-04"]  # En tránsito o en Kepler, no hay nada en Contratistas
    traspaso = enviar(almacenista, session, "CON", [renglon(guantes.codigo, 5)])
    recibir(con, traspaso, [renglon(guantes.codigo, 5)])
    r = con.post(VALES, json=cuerpo_entrega(t, [renglon(guantes.codigo, 2)]))
    assert r.status_code == 201, r.text
    assert existencia(session, "CON", guantes) == 3
    movs = session.scalars(select(Movimiento.id).where(Movimiento.articulo_id == guantes.id)).all()
    assert len(movs) == 4  # entrada, traspaso, recepción y entrega
    revisar_invariantes(session)
