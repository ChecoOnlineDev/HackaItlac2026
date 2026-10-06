"""CANCELACION (US-CAN-001): K-01, K-02, K-03, K-04, A-03, L-03, C-08, RG-02, RG-06, RG-09, F-12."""

import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.tiempo import hoy_mx
from app.modulos.acceso.permisos import P
from app.modulos.almacenes.models import UbicacionVirtual
from app.modulos.auditoria.models import Auditoria
from app.modulos.autorizaciones.models import Autorizacion
from app.modulos.catalogo.models import Pieza
from app.modulos.movimientos.models import Movimiento, TipoVale, Vale
from tests.movimientos.ayudas import (
    abastecer,
    crear_articulo,
    crear_trabajador,
    cuerpo_entrega,
    entrar_pieza,
    existencia,
    existencia_de_trabajador,
    total_movimientos,
    total_vales,
)
from tests.movimientos.cancelacion_ayudas import (
    VALES,
    Mov,
    cancelacion,
    entregar,
    insertar_vale,
    ub_almacen,
    ub_trabajador,
    ub_virtual,
    ultimo_folio,
    url,
)
from tests.movimientos.test_entrega import evaluar, pieza_en_kep, renglon
from tests.movimientos.test_invariantes import revisar_folios, revisar_invariantes


@pytest.fixture
def trabajador(session):
    return crear_trabajador(session)


@pytest.fixture
def otro_almacenista(app, crear_usuario, iniciar_sesion):
    """Otro almacenista de Kepler (sin `vales.cancelar_todos`)."""
    usuario = crear_usuario(
        {P.ENTREGAS_CREAR, P.VALES_CANCELAR, P.VALES_VER, P.CATALOGO_VER}, almacen="KEP"
    )
    cliente = TestClient(app)
    assert iniciar_sesion(cliente, usuario).status_code == 200
    yield cliente
    cliente.close()


def detalle(cliente, vale_id) -> dict:
    r = cliente.get(f"{VALES}/{vale_id}")
    assert r.status_code == 200, r.text
    return r.json()


def cancelar(cliente, vale_id, **extra):
    return cliente.post(url(vale_id), json=cancelacion(**extra))


def foto(session) -> tuple[int, int, int]:
    return (
        total_vales(session),
        total_movimientos(session),
        ultimo_folio(session, "KEP", "CANCELACION"),
    )


def devolver_pieza(session, arnes, pieza, trabajador):
    """Una DEVOLUCION insertada (otro agente la implementa): el trabajador regresa la pieza."""
    return insertar_vale(
        session,
        TipoVale.DEVOLUCION,
        "KEP",
        [Mov(arnes, 1, ub_trabajador(session, trabajador), ub_almacen(session, "KEP"), pieza)],
        trabajador=trabajador,
    )


# ------------------------------------------------------------------------------ K-02


def test_K_02_cancelar_una_entrega_regresa_las_existencias_y_el_resguardo_exactos(
    almacenista, compras, session, trabajador
):
    casco = crear_articulo(session, retornable=True)
    abastecer(compras, casco, 10)
    vale = entregar(almacenista, trabajador, [renglon(casco.codigo, 4)])
    assert existencia(session, "KEP", casco) == 6
    assert existencia_de_trabajador(session, trabajador, casco) == 4

    r = cancelar(almacenista, vale["id"], motivo="Era para otro trabajador")
    assert r.status_code == 201, r.text
    assert existencia(session, "KEP", casco) == 10
    assert existencia_de_trabajador(session, trabajador, casco) == 0
    revisar_invariantes(session)
    revisar_folios(session)


def test_K_02_el_original_queda_visible_cancelado_con_el_motivo_y_el_folio_de_su_cancelacion(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 10)
    vale = entregar(almacenista, trabajador, [renglon(guantes.codigo, 3)])

    cuerpo = cancelar(almacenista, vale["id"], motivo="Capturé el artículo equivocado").json()
    original = detalle(almacenista, vale["id"])
    assert original["estado"] == "CANCELADO" and original["folio"] == vale["folio"]
    assert original["cancelacion"]["folio"] == cuerpo["folio"]
    assert original["cancelacion"]["motivo"] == "Capturé el artículo equivocado"
    assert original["cancelacion"]["id"] == cuerpo["id"]
    assert original["cancelacion"]["responsable"]["nombre"] == "Almacenista Kepler"
    # Sus renglones no cambian (RG-02: nada se edita ni se borra).
    assert [x["cantidad"] for x in original["renglones"]] == [3]
    assert original["renglones"][0]["origen"]["clave"] == "KEP"
    listado = almacenista.get(VALES, params={"trabajador_id": str(trabajador.id)}).json()
    estados = {v["folio"]: v["estado"] for v in listado["elementos"]}
    assert estados[vale["folio"]] == "CANCELADO" and estados[cuerpo["folio"]] == "EMITIDO"


def test_K_02_la_cancelacion_es_un_vale_con_su_propio_folio_y_apunta_al_original(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 10)
    vale = entregar(almacenista, trabajador, [renglon(guantes.codigo, 3)])

    cuerpo = cancelar(almacenista, vale["id"]).json()
    assert "-CAN-" in cuerpo["folio"] and cuerpo["folio"] != vale["folio"]
    assert cuerpo["vale_cancelado"] == {
        "id": vale["id"],
        "folio": vale["folio"],
        "estado": "CANCELADO",
    }
    assert cuerpo["borrador"] is None and cuerpo["motivo"] == "Lo capturé mal"
    vale_can = detalle(almacenista, cuerpo["id"])
    assert vale_can["tipo"] == "CANCELACION" and vale_can["estado"] == "EMITIDO"
    assert vale_can["vale_origen_id"] == vale["id"]
    assert vale_can["vale_origen_folio"] == vale["folio"]
    assert vale_can["observacion"] == "Lo capturé mal"
    assert vale_can["trabajador"]["id"] == str(trabajador.id)
    assert vale_can["firma_modo"] == "SESION" and vale_can["tiene_firma"] is False
    # Origen y destino invertidos: sale de CONSUMIDO hacia el almacén.
    renglon_can = vale_can["renglones"][0]
    assert renglon_can["origen"]["tipo"] == "CONSUMIDO" and renglon_can["destino"]["clave"] == "KEP"
    assert renglon_can["cantidad"] == 3 and renglon_can["reglas"] == ["K-02"]
    assert renglon_can["saldo_destino"] == 10


def test_K_02_los_movimientos_inversos_copian_trabajador_y_condicion_del_original(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 10)
    vale = entregar(
        almacenista,
        trabajador,
        [renglon(guantes.codigo, 2, condicion="DESGASTE", observacion="Usados")],
    )
    cuerpo = cancelar(almacenista, vale["id"]).json()
    inverso = session.scalars(
        select(Movimiento).where(Movimiento.vale_id == uuid.UUID(cuerpo["id"]))
    ).one()
    original = session.scalars(
        select(Movimiento).where(Movimiento.vale_id == uuid.UUID(vale["id"]))
    ).one()
    assert (inverso.origen_id, inverso.destino_id) == (original.destino_id, original.origen_id)
    assert inverso.trabajador_id == trabajador.id == original.trabajador_id
    assert inverso.condicion == "DESGASTE" and inverso.cantidad == original.cantidad == 2
    assert inverso.articulo_id == original.articulo_id and inverso.renglon == original.renglon


def test_K_02_la_pieza_regresa_a_su_origen_y_a_su_existencia(
    almacenista, compras, session, trabajador
):
    arnes, pieza = pieza_en_kep(compras, session, vigente_hasta=hoy_mx() + timedelta(days=60))
    vale = entregar(almacenista, trabajador, [renglon(pieza.codigo)])
    assert pieza.ubicacion_id == ub_trabajador(session, trabajador).id

    assert cancelar(almacenista, vale["id"]).status_code == 201
    session.refresh(pieza)
    assert pieza.ubicacion_id == ub_almacen(session, "KEP").id
    assert existencia(session, "KEP", arnes) == 1
    assert existencia_de_trabajador(session, trabajador, arnes) == 0
    revisar_invariantes(session)
    # La pieza se puede volver a entregar, ahora a otro trabajador.
    otro = crear_trabajador(session)
    r = almacenista.post(VALES, json=cuerpo_entrega(otro, [renglon(pieza.codigo)]))
    assert r.status_code == 201


def test_K_02_los_folios_no_se_reutilizan_al_cancelar(almacenista, compras, session, trabajador):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 20)
    a = entregar(almacenista, trabajador, [renglon(guantes.codigo)])
    b = entregar(almacenista, trabajador, [renglon(guantes.codigo)])
    c1 = cancelar(almacenista, a["id"]).json()
    c2 = cancelar(almacenista, b["id"]).json()
    nueva = entregar(almacenista, trabajador, [renglon(guantes.codigo)])

    def numero(folio):
        return int(folio.rsplit("-", 1)[1])

    assert numero(c2["folio"]) == numero(c1["folio"]) + 1
    assert numero(nueva["folio"]) == numero(b["folio"]) + 1  # el ENT del vale cancelado no se reusa
    assert len({a["folio"], b["folio"], nueva["folio"], c1["folio"], c2["folio"]}) == 5
    revisar_folios(session)


def test_K_02_el_vale_de_cancelacion_no_trae_costos_F_12(almacenista, compras, session, trabajador):
    guantes = crear_articulo(session, retornable=False, costo_unitario=987654)
    abastecer(compras, guantes, 5)
    vale = entregar(almacenista, trabajador, [renglon(guantes.codigo)])
    cuerpo = cancelar(almacenista, vale["id"], rehacer=True)
    vale_can = almacenista.get(f"{VALES}/{cuerpo.json()['id']}")
    for texto in (cuerpo.text, vale_can.text):
        assert "costo" not in texto.lower() and "987654" not in texto


def test_K_02_cancelar_una_entrada_saca_lo_que_entro_y_no_toca_a_proveedor(compras, session):
    guantes = crear_articulo(session, retornable=False)
    vale = abastecer(compras, guantes, 7)
    assert existencia(session, "KEP", guantes) == 7
    r = cancelar(compras, vale["id"], motivo="Cantidad equivocada")
    assert r.status_code == 201, r.text
    assert existencia(session, "KEP", guantes) == 0
    inverso = session.scalars(
        select(Movimiento).where(Movimiento.vale_id == uuid.UUID(r.json()["id"]))
    ).one()
    assert inverso.saldo_origen == 0 and inverso.saldo_destino is None  # PROVEEDOR sin saldo
    revisar_invariantes(session)


def test_K_02_cancelar_una_entrada_de_pieza_la_deja_fuera_del_almacen(compras, session):
    arnes = crear_articulo(session, control="PIEZA", requiere_inspeccion=False)
    r, codigo = entrar_pieza(compras, arnes)
    assert r.status_code == 201
    assert cancelar(compras, r.json()["id"]).status_code == 201
    pieza = session.scalar(select(Pieza).where(Pieza.codigo == codigo))
    session.refresh(pieza)
    assert existencia(session, "KEP", arnes) == 0
    assert pieza.ubicacion_id == ub_virtual(session, UbicacionVirtual.PROVEEDOR).id
    revisar_invariantes(session)


def test_K_02_varias_cancelaciones_seguidas_cumplen_las_invariantes(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False)
    casco = crear_articulo(session, retornable=True)
    abastecer(compras, guantes, 10)
    abastecer(compras, casco, 10)
    for cantidad in (2, 3):
        vale = entregar(
            almacenista,
            trabajador,
            [renglon(guantes.codigo, cantidad), renglon(casco.codigo, cantidad)],
        )
        assert cancelar(almacenista, vale["id"]).status_code == 201
    assert existencia(session, "KEP", guantes) == existencia(session, "KEP", casco) == 10
    revisar_invariantes(session)
    revisar_folios(session)


# ------------------------------------------------------------------------------ K-01


def test_K_01_quien_hizo_el_vale_lo_cancela_y_queda_en_la_lista_de_revision(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    vale = entregar(almacenista, trabajador, [renglon(guantes.codigo)])
    r = cancelar(almacenista, vale["id"], motivo="Duplicado")
    assert r.status_code == 201
    fila = session.scalars(
        select(Auditoria).where(
            Auditoria.accion == "vale.cancelar", Auditoria.entidad_id == vale["id"]
        )
    ).one()
    assert fila.despues["motivo"] == "Duplicado" and fila.despues["para_revision"] is True
    assert fila.despues["folio_cancelacion"] == r.json()["folio"]
    assert fila.antes["estado"] == "EMITIDO"


def test_K_01_un_almacenista_no_cancela_los_vales_de_otro(
    almacenista, otro_almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    vale = entregar(almacenista, trabajador, [renglon(guantes.codigo)])
    antes = foto(session)

    r = cancelar(otro_almacenista, vale["id"])
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"
    assert "que tú hiciste" in r.json()["mensaje"]
    assert foto(session) == antes
    assert detalle(almacenista, vale["id"])["estado"] == "EMITIDO"


def test_K_01_el_supervisor_cancela_los_vales_de_cualquiera(
    almacenista, supervisor, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    vale = entregar(almacenista, trabajador, [renglon(guantes.codigo, 2)])
    r = cancelar(supervisor, vale["id"], motivo="Revisión del supervisor")
    assert r.status_code == 201, r.text
    assert existencia(session, "KEP", guantes) == 5
    assert detalle(supervisor, r.json()["id"])["responsable"]["nombre"] == "Supervisor Kepler"


def test_K_01_sin_el_permiso_de_cancelar_es_403(
    almacenista, cliente_como, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    vale = entregar(almacenista, trabajador, [renglon(guantes.codigo)])
    assert cancelar(cliente_como("Recursos Humanos"), vale["id"]).status_code == 403
    assert detalle(almacenista, vale["id"])["estado"] == "EMITIDO"


def test_K_01_el_motivo_es_obligatorio(almacenista, compras, session, trabajador):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    vale = entregar(almacenista, trabajador, [renglon(guantes.codigo)])
    base = {"id_cliente": str(uuid.uuid4()), "rehacer": False}
    for cuerpo in ({}, {"motivo": ""}, {"motivo": "   "}):
        r = almacenista.post(url(vale["id"]), json=base | cuerpo)
        assert r.status_code == 422 and r.json()["codigo"] == "DATOS_INVALIDOS", r.text
    assert detalle(almacenista, vale["id"])["estado"] == "EMITIDO"
    assert existencia(session, "KEP", guantes) == 4


def test_K_01_un_vale_que_no_existe_o_de_otro_almacen_es_404(
    almacenista, compras, session, trabajador, crear_usuario, iniciar_sesion, app
):
    assert cancelar(almacenista, uuid.uuid4()).status_code == 404
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    vale = entregar(almacenista, trabajador, [renglon(guantes.codigo)])
    ajeno = crear_usuario({P.VALES_CANCELAR, P.VALES_CANCELAR_TODOS, P.VALES_VER}, almacen="CON")
    with TestClient(app) as cliente:
        iniciar_sesion(cliente, ajeno)
        assert cancelar(cliente, vale["id"]).status_code == 404


# ------------------------------------------------------------------------------ K-03


def test_K_03_si_las_existencias_ya_no_alcanzan_no_se_cancela_y_no_se_escribe_nada(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False)
    entrada = abastecer(compras, guantes, 10)
    entregar(almacenista, trabajador, [renglon(guantes.codigo, 8)])
    antes = foto(session)
    r = cancelar(compras, entrada["id"])
    assert r.status_code == 409 and r.json()["codigo"] == "NO_CANCELABLE", r.text
    assert "se necesitan 10" in r.json()["mensaje"] and "hay 2" in r.json()["mensaje"]
    (detalle_k03,) = r.json()["detalles"]
    assert detalle_k03["regla"] == "K-03" and detalle_k03["renglon"] == 1
    assert foto(session) == antes  # ni vale, ni movimientos, ni folio quemado
    assert existencia(session, "KEP", guantes) == 2
    assert detalle(compras, entrada["id"])["estado"] == "EMITIDO"


def test_K_03_si_la_pieza_ya_se_devolvio_no_se_cancela_la_entrega(
    almacenista, compras, session, trabajador
):
    arnes, pieza = pieza_en_kep(compras, session, vigente_hasta=hoy_mx() + timedelta(days=60))
    vale = entregar(almacenista, trabajador, [renglon(pieza.codigo)])
    devolver_pieza(session, arnes, pieza, trabajador)
    antes = foto(session)
    r = cancelar(almacenista, vale["id"])
    assert r.status_code == 409 and r.json()["codigo"] == "NO_CANCELABLE", r.text
    assert f"La pieza {pieza.codigo} ya se movió después" in r.json()["mensaje"]
    assert "está en el almacén KEP" in r.json()["mensaje"]
    assert [d["regla"] for d in r.json()["detalles"]] == ["K-03"]
    assert foto(session) == antes
    assert detalle(almacenista, vale["id"])["estado"] == "EMITIDO"
    revisar_invariantes(session)


def test_K_03_si_la_pieza_ya_se_entrego_a_otro_se_dice_quien_la_tiene(
    almacenista, compras, session, trabajador
):
    arnes, pieza = pieza_en_kep(compras, session, vigente_hasta=hoy_mx() + timedelta(days=60))
    vale = entregar(almacenista, trabajador, [renglon(pieza.codigo)])
    devolver_pieza(session, arnes, pieza, trabajador)
    otro = crear_trabajador(session)
    entregar(almacenista, otro, [renglon(pieza.codigo)])
    r = cancelar(almacenista, vale["id"])
    assert r.status_code == 409 and r.json()["codigo"] == "NO_CANCELABLE"
    assert otro.numero_empleado in r.json()["mensaje"]


def test_K_03_una_pieza_que_volvio_al_mismo_lugar_tampoco_se_cancela(
    almacenista, compras, session, trabajador
):
    """Devuelta y entregada otra vez al mismo trabajador: ya se movió después del vale."""
    arnes, pieza = pieza_en_kep(compras, session, vigente_hasta=hoy_mx() + timedelta(days=60))
    primero = entregar(almacenista, trabajador, [renglon(pieza.codigo)])
    devolver_pieza(session, arnes, pieza, trabajador)
    segundo = entregar(almacenista, trabajador, [renglon(pieza.codigo)])
    r = cancelar(almacenista, primero["id"])
    assert r.status_code == 409 and "tuvo otros movimientos" in r.json()["mensaje"]
    assert cancelar(almacenista, segundo["id"]).status_code == 201  # el último sí


def test_K_03_un_vale_ya_cancelado_no_se_cancela_otra_vez(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    vale = entregar(almacenista, trabajador, [renglon(guantes.codigo, 2)])
    primera = cancelar(almacenista, vale["id"]).json()
    antes = foto(session)
    r = cancelar(almacenista, vale["id"])  # otro id_cliente: no es un doble toque
    assert r.status_code == 409 and r.json()["codigo"] == "NO_CANCELABLE"
    assert "ya está cancelado" in r.json()["mensaje"] and primera["folio"] in r.json()["mensaje"]
    assert r.json()["detalles"][0]["regla"] == "K-03"
    assert foto(session) == antes
    assert existencia(session, "KEP", guantes) == 5  # no se devolvió dos veces


def test_K_03_un_doble_toque_con_el_mismo_id_cliente_no_genera_dos_cancelaciones(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    vale = entregar(almacenista, trabajador, [renglon(guantes.codigo, 2)])
    cuerpo = cancelacion()
    r1 = almacenista.post(url(vale["id"]), json=cuerpo)
    antes = foto(session)
    r2 = almacenista.post(url(vale["id"]), json=cuerpo)
    assert (r1.status_code, r2.status_code) == (201, 200), (r1.text, r2.text)
    assert r1.json() == r2.json()
    assert foto(session) == antes
    assert existencia(session, "KEP", guantes) == 5


def test_K_03_el_id_cliente_de_otra_operacion_no_se_reutiliza(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    uno = entregar(almacenista, trabajador, [renglon(guantes.codigo)])
    dos = entregar(almacenista, trabajador, [renglon(guantes.codigo)])
    cuerpo = cancelacion()
    assert almacenista.post(url(uno["id"]), json=cuerpo).status_code == 201
    r = almacenista.post(url(dos["id"]), json=cuerpo)  # mismo id_cliente, otro vale
    assert r.status_code == 409 and detalle(almacenista, dos["id"])["estado"] == "EMITIDO"


def test_K_03_la_evaluacion_de_una_cancelacion_dice_por_que_no_sin_escribir(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False)
    entrada = abastecer(compras, guantes, 4)
    entregar(almacenista, trabajador, [renglon(guantes.codigo, 3)])
    antes = foto(session)
    r = compras.post(
        "/api/vales/evaluar", json={"tipo": "CANCELACION", "vale_origen_id": entrada["id"]}
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["nivel"] == "ROJO" and cuerpo["puede_confirmar"] is False
    assert cuerpo["renglones"][0]["motivos"][0]["regla"] == "K-03"
    assert cuerpo["renglones"][0]["disponible"] == 1
    assert foto(session) == antes


# ------------------------------------------------------------------------------ K-04


def test_K_04_el_tipo_tambien_se_confirma_por_el_motor_generico(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    vale = entregar(almacenista, trabajador, [renglon(guantes.codigo, 2)])
    r = almacenista.post(
        VALES,
        json={
            "tipo": "CANCELACION",
            "vale_origen_id": vale["id"],
            "id_cliente": str(uuid.uuid4()),
            "observacion": "Por el motor genérico",
        },
    )
    assert r.status_code == 201, r.text
    assert "-CAN-" in r.json()["folio"] and existencia(session, "KEP", guantes) == 5
    # Sin motivo, sin vale a cancelar o con renglones, no.
    sin_motivo = almacenista.post(
        VALES,
        json={"tipo": "CANCELACION", "vale_origen_id": vale["id"], "id_cliente": str(uuid.uuid4())},
    )
    assert sin_motivo.status_code == 422
    sin_vale = almacenista.post(
        VALES, json={"tipo": "CANCELACION", "id_cliente": str(uuid.uuid4()), "observacion": "x"}
    )
    assert sin_vale.status_code == 422
    con_renglones = almacenista.post(
        VALES,
        json={
            "tipo": "CANCELACION",
            "vale_origen_id": vale["id"],
            "id_cliente": str(uuid.uuid4()),
            "observacion": "x",
            "renglones": [renglon(guantes.codigo)],
        },
    )
    assert con_renglones.status_code == 422


def test_K_04_una_cancelacion_no_se_cancela(almacenista, compras, session, trabajador):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    vale = entregar(almacenista, trabajador, [renglon(guantes.codigo)])
    cuerpo = cancelar(almacenista, vale["id"]).json()
    r = cancelar(almacenista, cuerpo["id"])
    assert r.status_code == 409 and r.json()["codigo"] == "NO_CANCELABLE"
    assert [d["regla"] for d in r.json()["detalles"]] == ["K-04"]
    assert "Una cancelación no se cancela" in r.json()["mensaje"]


# ------------------------------------------------------------------------- A-03 y L-03


def test_L_03_tras_cancelar_el_trabajador_puede_volver_a_recibir_lo_que_le_correspondia(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False, limite_cantidad=3, limite_periodo_dias=7)
    abastecer(compras, guantes, 20)
    vale = entregar(almacenista, trabajador, [renglon(guantes.codigo, 3)])
    ev = evaluar(almacenista, trabajador, [renglon(guantes.codigo, 3)])
    assert ev["renglones"][0]["nivel"] == "NARANJA"  # ya agotó el límite

    assert cancelar(almacenista, vale["id"]).status_code == 201
    ev = evaluar(almacenista, trabajador, [renglon(guantes.codigo, 3)])
    assert ev["renglones"][0]["nivel"] == "VERDE" and ev["puede_confirmar"] is True
    entregar(almacenista, trabajador, [renglon(guantes.codigo, 3)])  # y se confirma
    ev = evaluar(almacenista, trabajador, [renglon(guantes.codigo, 1)])
    assert ev["renglones"][0]["nivel"] == "NARANJA"  # otra vez en el límite


def test_C_08_la_cancelacion_resta_el_consumo_del_trabajador(
    almacenista, supervisor, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 20)
    entregar(almacenista, trabajador, [renglon(guantes.codigo, 4)])
    vale = entregar(almacenista, trabajador, [renglon(guantes.codigo, 6)])

    def total():
        r = supervisor.get("/api/reportes/consumo", params={"articulo_id": str(guantes.id)})
        assert r.status_code == 200, r.text
        return sum(i["total"] for i in r.json()["elementos"])

    assert total() == 10
    assert cancelar(almacenista, vale["id"]).status_code == 201
    assert total() == 4


def test_A_03_cancelar_una_entrega_con_autorizacion_no_la_libera_para_otro_vale(
    almacenista, supervisor, compras, session, trabajador
):
    from tests.movimientos.test_autorizacion_integracion import aprobar, solicitar

    arnes = crear_articulo(session, retornable=True, limite_cantidad=1)
    abastecer(compras, arnes, 10)
    entregar(almacenista, trabajador, [renglon(arnes.codigo)])
    ev = evaluar(almacenista, trabajador, [renglon(arnes.codigo)])
    autorizacion_id = solicitar(almacenista, trabajador, ev)
    aprobar(supervisor, autorizacion_id)
    cuerpo = cuerpo_entrega(trabajador, [renglon(arnes.codigo)], autorizacion_id=autorizacion_id)
    r = almacenista.post(VALES, json=cuerpo)
    assert r.status_code == 201, r.text

    assert cancelar(almacenista, r.json()["id"]).status_code == 201
    assert session.get(Autorizacion, uuid.UUID(autorizacion_id)).estado == "USADA"  # sigue USADA
    de_nuevo = cuerpo_entrega(trabajador, [renglon(arnes.codigo)], autorizacion_id=autorizacion_id)
    r2 = almacenista.post(VALES, json=de_nuevo)
    assert r2.status_code == 409 and r2.json()["codigo"] == "AUTORIZACION_INVALIDA"
    # El vale cancelado conserva su "Validó".
    assert detalle(almacenista, r.json()["id"])["valido"]["autorizacion_id"] == autorizacion_id


# ------------------------------------------------------------------------ atomicidad


def test_RG_09_si_falla_la_cancelacion_no_queda_nada(
    almacenista, compras, session, trabajador, monkeypatch
):
    from app.modulos.auditoria.service import AuditoriaService

    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    vale = entregar(almacenista, trabajador, [renglon(guantes.codigo, 2)])
    antes = foto(session)
    original = AuditoriaService.registrar

    def falla(self, **datos):
        raise RuntimeError("falla simulada al final")

    monkeypatch.setattr(AuditoriaService, "registrar", falla)
    cuerpo = cancelacion()
    with pytest.raises(RuntimeError):
        almacenista.post(url(vale["id"]), json=cuerpo)
    monkeypatch.setattr(AuditoriaService, "registrar", original)
    session.rollback()
    assert foto(session) == antes  # ni vale, ni movimientos, ni folio quemado
    assert existencia(session, "KEP", guantes) == 3
    assert detalle(almacenista, vale["id"])["estado"] == "EMITIDO"
    # Y el mismo `id_cliente` se puede volver a confirmar.
    assert almacenista.post(url(vale["id"]), json=cuerpo).status_code == 201
    assert existencia(session, "KEP", guantes) == 5
    estado = session.scalar(select(Vale.estado).where(Vale.id == uuid.UUID(vale["id"])))
    assert estado == "CANCELADO"
