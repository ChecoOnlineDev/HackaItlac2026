"""NO_ADEUDO (US-BAJ-001, fase 4): B-01, B-03, B-04, B-08, B-09 e invariante 8 de datos."""

import json
import uuid

import pytest
from sqlalchemy import select

from app.modulos.acceso.permisos import P
from app.modulos.movimientos.models import Movimiento, Vale
from app.modulos.trabajadores.models import EstadoTrabajador
from tests.movimientos.ayudas import (
    abastecer,
    almacen,
    crear_articulo,
    crear_trabajador,
    cuerpo_entrega,
    total_movimientos,
    total_vales,
)
from tests.movimientos.ayudas_devolucion import (
    EVALUAR,
    VALES,
    cantidad_entregada,
    cuerpo_devolucion,
    entregar,
    pieza_entregada,
    renglon,
)
from tests.movimientos.test_devolucion import cliente_de
from tests.movimientos.test_invariantes import revisar_folios, revisar_invariantes


@pytest.fixture
def trabajador(session):
    return crear_trabajador(session)


def ruta(trabajador) -> str:
    return f"/api/trabajadores/{trabajador.id}/no-adeudo"


def cuerpo(**extra) -> dict:
    return {"id_cliente": str(uuid.uuid4())} | extra


def vales_nad(session, trabajador) -> list[Vale]:
    return list(
        session.scalars(
            select(Vale).where(Vale.trabajador_id == trabajador.id, Vale.tipo == "NO_ADEUDO")
        )
    )


def estado_de(session, trabajador) -> str:
    session.refresh(trabajador)
    return trabajador.estado


# ----------------------------------------------------------------------------- B-04


def test_B_04_con_pendientes_responde_409_con_la_lista_y_no_emite(
    almacenista, compras, session, trabajador
):
    art, pieza = pieza_entregada(compras, almacenista, session, trabajador, costo_unitario=15)
    cantidad = cantidad_entregada(compras, almacenista, session, trabajador, entregado=2)
    vales, movs = total_vales(session), total_movimientos(session)
    r = almacenista.post(ruta(trabajador), json=cuerpo())
    assert r.status_code == 409 and r.json()["codigo"] == "CON_PENDIENTES", r.text
    detalles = r.json()["detalles"]
    assert detalles["regla"] == "B-04"
    por_codigo = {p["codigo"]: p for p in detalles["pendientes"]}
    assert set(por_codigo) == {pieza.codigo, cantidad.codigo}
    assert por_codigo[cantidad.codigo]["cantidad"] == 2
    assert por_codigo[pieza.codigo]["folio"].startswith("KEP-ENT-")
    assert por_codigo[pieza.codigo]["almacen_clave"] == "KEP"
    assert "costo" not in r.text.lower()
    assert (total_vales(session), total_movimientos(session)) == (vales, movs)
    assert vales_nad(session, trabajador) == []


def test_B_04_sin_pendientes_emite_el_vale_con_folio_y_el_trabajador_queda_inactivo(
    almacenista, session, trabajador
):
    r = almacenista.post(ruta(trabajador), json=cuerpo())
    assert r.status_code == 201, r.text
    vale = r.json()
    assert vale["folio"].startswith("KEP-NAD-") and vale["token"] and vale["renglones"] == []
    assert vale["trabajador"]["estado"] == "INACTIVO"
    assert vale["trabajador"]["estado_texto"] == "Inactivo"
    assert estado_de(session, trabajador) == EstadoTrabajador.INACTIVO  # B-08
    detalle = almacenista.get(f"{VALES}/{vale['id']}").json()
    assert detalle["tipo"] == "NO_ADEUDO" and detalle["renglones"] == []
    assert detalle["trabajador"]["id"] == str(trabajador.id)
    assert detalle["firma_modo"] == "SESION" and detalle["tiene_firma"] is False
    assert "costo" not in json.dumps(detalle).lower()
    # Un vale sin movimientos: las existencias no se tocaron.
    assert not session.scalars(
        select(Movimiento.id).where(Movimiento.vale_id == uuid.UUID(vale["id"]))
    ).all()
    revisar_invariantes(session)
    revisar_folios(session)


def test_B_04_quien_nunca_recibio_nada_obtiene_su_vale_de_inmediato(
    almacenista, session, trabajador
):
    r = almacenista.post(ruta(trabajador), json=cuerpo())
    assert r.status_code == 201 and len(vales_nad(session, trabajador)) == 1


def test_B_03_los_consumibles_no_cuentan_como_pendientes(almacenista, compras, session, trabajador):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 10)
    entregar(almacenista, trabajador, [{"codigo": guantes.codigo, "cantidad": 4}])
    r = almacenista.post(ruta(trabajador), json=cuerpo())
    assert r.status_code == 201, r.text
    assert estado_de(session, trabajador) == EstadoTrabajador.INACTIVO


def test_B_04_un_pendiente_de_otro_almacen_se_ve_igual_desde_kepler(
    app, almacenista, cliente_como, compras, crear_usuario, session, trabajador
):
    casco = crear_articulo(session, retornable=True)
    # Compras es de Kepler: Contratistas lo abastece el Administrador.
    abastecer(cliente_como("Administrador"), casco, 3, almacen_id=str(almacen(session, "CON").id))
    de_con = cliente_de(app, crear_usuario, {P.ENTREGAS_CREAR}, "CON")
    r = de_con.post(VALES, json=cuerpo_entrega(trabajador, [{"codigo": casco.codigo}]))
    assert r.status_code == 201, r.text
    r = almacenista.post(ruta(trabajador), json=cuerpo())
    assert r.status_code == 409 and r.json()["codigo"] == "CON_PENDIENTES"
    (pendiente,) = r.json()["detalles"]["pendientes"]
    assert pendiente["almacen_clave"] == "CON" and pendiente["folio"].startswith("CON-ENT-")


# ----------------------------------------------------------------------------- B-01


def test_B_01_el_almacenista_inicia_la_baja_al_pedir_el_vale_aunque_haya_pendientes(
    almacenista, compras, session, trabajador
):
    cantidad_entregada(compras, almacenista, session, trabajador, entregado=1)
    assert estado_de(session, trabajador) == EstadoTrabajador.ACTIVO
    r = almacenista.post(ruta(trabajador), json=cuerpo())
    assert r.status_code == 409 and r.json()["codigo"] == "CON_PENDIENTES"
    # El 409 no deshace la baja: ya está en proceso y ya no recibe entregas.
    assert estado_de(session, trabajador) == EstadoTrabajador.BAJA_EN_PROCESO
    nueva = crear_articulo(session)
    abastecer(compras, nueva, 2)
    ev = almacenista.post(
        EVALUAR,
        json={
            "tipo": "ENTREGA",
            "trabajador_id": str(trabajador.id),
            "renglones": [{"codigo": nueva.codigo}],
        },
    ).json()
    assert ev["motivos"][0]["regla"] == "E-02"


def test_B_01_ciclo_completo_baja_devolucion_y_no_adeudo(almacenista, compras, session, trabajador):
    art, pieza = pieza_entregada(compras, almacenista, session, trabajador)
    cantidad = cantidad_entregada(compras, almacenista, session, trabajador, entregado=2)
    assert almacenista.post(ruta(trabajador), json=cuerpo()).status_code == 409
    assert estado_de(session, trabajador) == EstadoTrabajador.BAJA_EN_PROCESO
    # SM-05: en baja en proceso todavía devuelve.
    r = almacenista.post(
        VALES,
        json=cuerpo_devolucion([renglon(pieza.codigo), renglon(cantidad.codigo, 2)], trabajador),
    )
    assert r.status_code == 201, r.text
    r = almacenista.post(ruta(trabajador), json=cuerpo())
    assert r.status_code == 201, r.text
    assert estado_de(session, trabajador) == EstadoTrabajador.INACTIVO
    ficha = almacenista.get(f"/api/trabajadores/{trabajador.id}").json()
    assert ficha["resguardo"] == [] and ficha["situacion"] == "NO_ADEUDO_EMITIDO"
    revisar_invariantes(session)
    revisar_folios(session)


def test_B_01_una_baja_que_ya_inicio_rh_tambien_se_completa(
    almacenista, cliente_como, session, trabajador
):
    rh = cliente_como("Recursos Humanos")
    assert rh.post(f"/api/trabajadores/{trabajador.id}/baja").status_code == 200
    assert estado_de(session, trabajador) == EstadoTrabajador.BAJA_EN_PROCESO
    r = almacenista.post(ruta(trabajador), json=cuerpo())
    assert r.status_code == 201 and r.json()["trabajador"]["estado"] == "INACTIVO"


# ----------------------------------------------------------------------------- B-08, B-09


def test_B_08_un_trabajador_inactivo_ya_no_recibe_entregas_ni_otro_no_adeudo(
    almacenista, compras, session, trabajador
):
    assert almacenista.post(ruta(trabajador), json=cuerpo()).status_code == 201
    nueva = crear_articulo(session)
    abastecer(compras, nueva, 2)
    r = almacenista.post(VALES, json=cuerpo_entrega(trabajador, [{"codigo": nueva.codigo}]))
    assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO"
    r = almacenista.post(ruta(trabajador), json=cuerpo())
    assert r.status_code == 409 and r.json()["detalles"]["regla"] == "B-08"
    assert len(vales_nad(session, trabajador)) == 1


def test_B_09_rh_ve_con_pendientes_y_despues_no_adeudo_emitido(
    almacenista, compras, cliente_como, session, trabajador
):
    rh = cliente_como("Recursos Humanos")
    art, pieza = pieza_entregada(compras, almacenista, session, trabajador)

    def situacion() -> str:
        lista = rh.get(f"/api/trabajadores?q={trabajador.numero_empleado}").json()
        (fila,) = lista["elementos"]
        return fila["situacion_texto"]

    assert situacion() == "Con pendientes"
    almacenista.post(VALES, json=cuerpo_devolucion([renglon(pieza.codigo)]))
    assert situacion() == "Sin pendientes"
    assert almacenista.post(ruta(trabajador), json=cuerpo()).status_code == 201
    assert situacion() == "No adeudo emitido"
    filtrada = rh.get("/api/trabajadores?situacion=NO_ADEUDO_EMITIDO").json()
    assert str(trabajador.id) in [e["id"] for e in filtrada["elementos"]]


# --------------------------------------------------------------------- invariante 8


def test_invariante_8_con_pendientes_tampoco_se_emite_por_el_endpoint_de_vales(
    almacenista, compras, session, trabajador
):
    cantidad_entregada(compras, almacenista, session, trabajador, entregado=1)
    ev = almacenista.post(
        EVALUAR, json={"tipo": "NO_ADEUDO", "trabajador_id": str(trabajador.id)}
    ).json()
    assert ev["nivel"] == "ROJO" and ev["puede_confirmar"] is False
    assert ev["motivos"][0]["regla"] == "B-04"
    assert [p["cantidad"] for p in ev["trabajador"]["resguardo"]] == [1]
    vales = total_vales(session)
    r = almacenista.post(
        VALES,
        json={"tipo": "NO_ADEUDO", "trabajador_id": str(trabajador.id)} | cuerpo(),
    )
    assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO"
    assert total_vales(session) == vales
    assert estado_de(session, trabajador) == EstadoTrabajador.ACTIVO


def test_B_04_la_evaluacion_sin_pendientes_es_verde_y_se_puede_confirmar(
    almacenista, session, trabajador
):
    ev = almacenista.post(
        EVALUAR, json={"tipo": "NO_ADEUDO", "trabajador_id": str(trabajador.id)}
    ).json()
    assert ev["nivel"] == "VERDE" and ev["puede_confirmar"] is True and ev["renglones"] == []
    assert estado_de(session, trabajador) == EstadoTrabajador.ACTIVO  # evaluar no escribe


def test_el_no_adeudo_no_lleva_renglones_y_exige_trabajador(almacenista, trabajador):
    r = almacenista.post(
        VALES,
        json={
            "tipo": "NO_ADEUDO",
            "trabajador_id": str(trabajador.id),
            "renglones": [{"codigo": "X"}],
        }
        | cuerpo(),
    )
    assert r.status_code == 422
    assert almacenista.post(VALES, json={"tipo": "NO_ADEUDO"} | cuerpo()).status_code == 422


# ------------------------------------------------------------------ idempotencia, permisos


def test_idempotencia_el_mismo_id_cliente_devuelve_el_mismo_vale(almacenista, session, trabajador):
    datos = cuerpo()
    r1 = almacenista.post(ruta(trabajador), json=datos)
    r2 = almacenista.post(ruta(trabajador), json=datos)
    assert (r1.status_code, r2.status_code) == (201, 200)
    assert r1.json() == r2.json()
    assert len(vales_nad(session, trabajador)) == 1


def test_el_id_cliente_de_otro_trabajador_no_se_reutiliza(almacenista, session, trabajador):
    otro = crear_trabajador(session)
    datos = cuerpo()
    assert almacenista.post(ruta(trabajador), json=datos).status_code == 201
    r = almacenista.post(ruta(otro), json=datos)
    assert r.status_code == 409
    assert estado_de(session, otro) == EstadoTrabajador.ACTIVO


def test_permisos_emitir_no_adeudo_exige_no_adeudo_emitir(
    app, client, almacenista, cliente_como, crear_usuario, session, trabajador
):
    assert client.post(ruta(trabajador), json=cuerpo()).status_code == 401
    sin = cliente_de(app, crear_usuario, {P.DEVOLUCIONES_CREAR, P.TRABAJADORES_INICIAR_BAJA}, "KEP")
    for c in (sin, cliente_como("Recursos Humanos"), cliente_como("Compras")):
        r = c.post(ruta(trabajador), json=cuerpo())
        assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"
    assert estado_de(session, trabajador) == EstadoTrabajador.ACTIVO
    assert vales_nad(session, trabajador) == []
    con = cliente_de(app, crear_usuario, {P.NO_ADEUDO_EMITIR, P.TRABAJADORES_INICIAR_BAJA}, "KEP")
    assert con.post(ruta(trabajador), json=cuerpo()).status_code == 201


def test_B_01_emitir_no_adeudo_a_un_activo_exige_tambien_iniciar_la_baja(
    app, crear_usuario, cliente_como, session, trabajador
):
    """Regresión: emitir el vale no da por sí solo el permiso de iniciar la baja (tabla 8.2)."""
    solo_emitir = cliente_de(app, crear_usuario, {P.NO_ADEUDO_EMITIR}, "KEP")
    r = solo_emitir.post(ruta(trabajador), json=cuerpo())
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"
    assert estado_de(session, trabajador) == EstadoTrabajador.ACTIVO
    assert vales_nad(session, trabajador) == []
    # Con ambos permisos emite.
    ambos = cliente_de(app, crear_usuario, {P.NO_ADEUDO_EMITIR, P.TRABAJADORES_INICIAR_BAJA}, "KEP")
    assert ambos.post(ruta(trabajador), json=cuerpo()).status_code == 201
    # Una baja que ya inició otro no necesita `iniciar_baja`.
    otro = crear_trabajador(session)
    assert (
        cliente_como("Recursos Humanos").post(f"/api/trabajadores/{otro.id}/baja").status_code
        == 200
    )
    r = solo_emitir.post(ruta(otro), json=cuerpo())
    assert r.status_code == 201 and r.json()["trabajador"]["estado"] == "INACTIVO"


def test_AC_06_quien_opera_todos_los_almacenes_indica_el_almacen_del_no_adeudo(
    app, crear_usuario, session, trabajador
):
    """Regresión: con `almacenes.todos` el cuerpo lleva `almacen_id` (antes pedía el almacén)."""
    todos = cliente_de(
        app,
        crear_usuario,
        {P.NO_ADEUDO_EMITIR, P.TRABAJADORES_INICIAR_BAJA, P.ALMACENES_TODOS},
        None,
    )
    sede = almacen(session)
    r = todos.post(ruta(trabajador), json=cuerpo(almacen_id=str(sede.id)))
    assert r.status_code == 201, r.text
    assert vales_nad(session, trabajador)[0].almacen_id == sede.id


def test_un_trabajador_inexistente_es_404(almacenista):
    r = almacenista.post(f"/api/trabajadores/{uuid.uuid4()}/no-adeudo", json=cuerpo())
    assert r.status_code == 404


def test_el_cuerpo_pide_id_cliente(almacenista, trabajador):
    assert almacenista.post(ruta(trabajador), json={}).status_code == 422
