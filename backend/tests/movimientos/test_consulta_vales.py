"""Consulta de vales: GET /api/vales, /{id}, /por-token/{token}. AC-04, AC-06, C-04, C-11, C-12."""

import uuid
from datetime import timedelta

import pytest

from app.core.tiempo import hoy_mx
from app.modulos.acceso.permisos import P
from tests.movimientos.ayudas import (
    abastecer,
    almacen,
    crear_articulo,
    crear_trabajador,
    cuerpo_entrega,
)
from tests.movimientos.test_entrega import renglon

VALES = "/api/vales"


@pytest.fixture
def trabajador(session):
    return crear_trabajador(session)


@pytest.fixture
def entrega(almacenista, compras, session, trabajador):
    guantes = crear_articulo(session)
    abastecer(compras, guantes, 10)
    cuerpo = cuerpo_entrega(trabajador, [renglon(guantes.codigo)])
    cuerpo["observacion"] = "Entrega de prueba sin proyecto asignado."
    r = almacenista.post(VALES, json=cuerpo)
    assert r.status_code == 201
    return r.json()


def ids(respuesta) -> list[str]:
    return [e["id"] for e in respuesta.json()["elementos"]]


def test_AC_04_consultar_vales_exige_vales_ver(client, crear_usuario, iniciar_sesion, entrega):
    assert client.get(f"{VALES}/{entrega['id']}").status_code == 401
    sin = crear_usuario({P.ENTREGAS_CREAR}, almacen="KEP")
    iniciar_sesion(client, sin)
    for ruta in (VALES, f"{VALES}/{entrega['id']}", f"{VALES}/por-token/{entrega['token']}"):
        r = client.get(ruta)
        assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"
    con = crear_usuario({P.VALES_VER}, almacen="KEP")
    iniciar_sesion(client, con)
    assert client.get(f"{VALES}/{entrega['id']}").status_code == 200


def test_C_04_el_detalle_de_un_vale_inexistente_da_404(almacenista):
    r = almacenista.get(f"{VALES}/{uuid.uuid4()}")
    assert r.status_code == 404 and r.json()["codigo"] == "NO_ENCONTRADO"


def test_AC_06_sin_almacenes_todos_solo_se_ven_los_del_almacen_asignado(
    app, cliente_como, usuario_por_rol, crear_usuario, entrega, almacenista
):
    from fastapi.testclient import TestClient

    from tests.conftest import iniciar_sesion_en

    de_con = crear_usuario({P.VALES_VER}, almacen="CON")
    c_con = TestClient(app)
    assert iniciar_sesion_en(c_con, de_con).status_code == 200
    assert entrega["id"] not in ids(c_con.get(VALES))
    assert c_con.get(f"{VALES}/{entrega['id']}").status_code == 404
    assert c_con.get(f"{VALES}/por-token/{entrega['token']}").status_code == 404
    # El de su almacén sí lo ve; quien tiene `almacenes.todos`, todos.
    assert entrega["id"] in ids(almacenista.get(VALES))
    assert entrega["id"] in ids(cliente_como("Supervisor").get(VALES))
    assert entrega["id"] in ids(cliente_como("Compras").get(VALES))


def test_AC_06_filtrar_por_otro_almacen_o_usuario_no_sale_del_alcance(
    app, crear_usuario, entrega, almacenista, session
):
    from fastapi.testclient import TestClient

    from tests.conftest import iniciar_sesion_en

    kep = almacen(session, "KEP")
    con = almacen(session, "CON")
    de_con = crear_usuario({P.VALES_VER}, almacen="CON")
    c_con = TestClient(app)
    iniciar_sesion_en(c_con, de_con)
    assert ids(c_con.get(f"{VALES}?almacen_id={kep.id}")) == []
    yo = almacenista.get("/api/sesion").json()["usuario"]["id"]
    assert entrega["id"] not in ids(c_con.get(f"{VALES}?usuario_id={yo}"))
    assert c_con.get(f"{VALES}?almacen_id={con.id}").status_code == 200
    # El almacenista de Kepler no ve los de Contratistas aunque los pida.
    assert almacenista.get(f"{VALES}?almacen_id={con.id}").json()["total"] == 0


def test_C_05_filtros_por_tipo_trabajador_usuario_y_almacen(
    almacenista, compras, supervisor, session, entrega, trabajador
):
    kep = almacen(session, "KEP")
    assert entrega["id"] in ids(almacenista.get(f"{VALES}?tipo=ENTREGA"))
    assert entrega["id"] not in ids(almacenista.get(f"{VALES}?tipo=ENTRADA"))
    assert ids(almacenista.get(f"{VALES}?trabajador_id={trabajador.id}")) == [entrega["id"]]
    otro = crear_trabajador(session)
    assert ids(almacenista.get(f"{VALES}?trabajador_id={otro.id}")) == []
    yo = almacenista.get("/api/sesion").json()["usuario"]["id"]
    assert entrega["id"] in ids(almacenista.get(f"{VALES}?usuario_id={yo}"))
    assert entrega["id"] not in ids(
        compras.get(f"{VALES}?usuario_id={yo}&almacen_id={kep.id}&tipo=ENTRADA")
    )
    assert entrega["id"] in ids(supervisor.get(f"{VALES}?almacen_id={kep.id}"))


def test_C_12_mis_movimientos_de_hoy_filtra_por_mi_usuario_y_las_fechas_de_hoy(
    almacenista, entrega
):
    yo = almacenista.get("/api/sesion").json()["usuario"]["id"]
    hoy = hoy_mx().isoformat()
    r = almacenista.get(f"{VALES}?usuario_id={yo}&desde={hoy}&hasta={hoy}")
    assert entrega["id"] in ids(r)
    ayer = (hoy_mx() - timedelta(days=1)).isoformat()
    assert ids(almacenista.get(f"{VALES}?desde={ayer}&hasta={ayer}")) == []
    manana = (hoy_mx() + timedelta(days=1)).isoformat()
    assert entrega["id"] not in ids(almacenista.get(f"{VALES}?desde={manana}"))
    assert entrega["id"] in ids(almacenista.get(f"{VALES}?desde={ayer}"))


def test_la_lista_va_paginada_del_mas_nuevo_al_mas_viejo(almacenista, compras, session, trabajador):
    guantes = crear_articulo(session)
    abastecer(compras, guantes, 10)
    folios = []
    for _ in range(3):
        cuerpo = cuerpo_entrega(trabajador, [renglon(guantes.codigo)])
        cuerpo["observacion"] = "Entrega de prueba sin proyecto asignado."
        r = almacenista.post(VALES, json=cuerpo)
        folios.append(r.json()["folio"])
    r = almacenista.get(f"{VALES}?trabajador_id={trabajador.id}&tamano=2&pagina=1")
    cuerpo = r.json()
    assert cuerpo["total"] == 3 and [e["folio"] for e in cuerpo["elementos"]] == folios[::-1][:2]
    pagina2 = almacenista.get(f"{VALES}?trabajador_id={trabajador.id}&tamano=2&pagina=2").json()
    assert [e["folio"] for e in pagina2["elementos"]] == [folios[0]]


def test_la_lista_trae_lo_necesario_para_mostrar_cada_vale(almacenista, entrega, trabajador):
    elemento = next(
        e for e in almacenista.get(f"{VALES}?trabajador_id={trabajador.id}").json()["elementos"]
    )
    assert elemento["folio"] == entrega["folio"] and elemento["tipo"] == "ENTREGA"
    assert elemento["estado"] == "EMITIDO" and elemento["almacen"]["clave"] == "KEP"
    assert elemento["trabajador"]["nombre"] == trabajador.nombre
    assert elemento["numero_empleado"] == trabajador.numero_empleado
    assert elemento["responsable"]["nombre"] == "Almacenista Kepler" and elemento["renglones"] == 1
    assert elemento["creado_en"].endswith("Z")


def test_C_04_un_vale_de_entrada_se_ve_sin_trabajador(compras, session):
    articulo = crear_articulo(session)
    vale = abastecer(compras, articulo, 3)
    detalle = compras.get(f"{VALES}/{vale['id']}").json()
    assert detalle["tipo"] == "ENTRADA" and detalle["trabajador"] is None
    assert detalle["renglones"][0]["origen"]["tipo"] == "PROVEEDOR"
    assert detalle["renglones"][0]["destino"]["clave"] == "KEP"
    assert detalle["renglones"][0]["saldo_origen"] is None
    assert detalle["firma_modo"] == "SESION" and detalle["tiene_firma"] is False
