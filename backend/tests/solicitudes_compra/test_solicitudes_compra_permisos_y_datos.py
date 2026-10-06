"""Permisos por clave de las solicitudes de compra (AC-01, AC-04) y sus datos de prueba."""

import uuid

import pytest
from sqlalchemy import func, select

from app.modulos.acceso.dependencias_permisos import faltantes
from app.modulos.acceso.permisos import CATALOGO, P
from app.modulos.movimientos.models import TipoVale, Vale
from app.modulos.solicitudes_compra import datos_prueba
from app.modulos.solicitudes_compra.models import (
    SerieSolicitudCompra,
    SolicitudCompra,
    SolicitudCompraEvento,
)
from tests.solicitudes_compra.ayudas import RUTA, cuerpo, pedir

FALSO = str(uuid.uuid4())


def test_AC_01_los_permisos_nuevos_estan_en_el_catalogo_con_su_descripcion():
    por_clave = {p.clave: p for p in CATALOGO}
    assert por_clave["compras.solicitar"].descripcion == "Pedir una compra urgente"
    assert por_clave["compras.atender"].descripcion == "Atender las solicitudes de compra"
    assert por_clave["compras.solicitar"].mvp and por_clave["compras.atender"].mvp


def test_AC_03_quien_tiene_cada_permiso_en_los_roles_iniciales(como):
    esperado = {
        "almacenista": (True, False),
        "supervisor": (True, False),
        "compras": (False, True),
        "rh": (False, False),
        "admin": (True, True),
    }
    for usuario, (solicita, atiende) in esperado.items():
        permisos = set(como(usuario).get("/api/sesion").json()["permisos"])
        assert (P.COMPRAS_SOLICITAR in permisos, P.COMPRAS_ATENDER in permisos) == (
            solicita,
            atiende,
        ), usuario


def test_AC_01_un_permiso_de_accion_exige_los_de_ver_que_necesita():
    assert faltantes({P.COMPRAS_SOLICITAR}) == {P.COMPRAS_SOLICITAR: [P.CATALOGO_VER]}
    assert faltantes({P.COMPRAS_ATENDER}) == {P.COMPRAS_ATENDER: [P.CATALOGO_VER, P.VALES_VER]}
    assert faltantes({P.COMPRAS_ATENDER, P.CATALOGO_VER, P.VALES_VER}) == {}


@pytest.mark.parametrize(
    "metodo,ruta,cuerpo_,exige",
    [
        ("POST", RUTA, {}, P.COMPRAS_SOLICITAR),
        ("POST", f"{RUTA}/{FALSO}/cancelacion", None, P.COMPRAS_SOLICITAR),
        ("POST", f"{RUTA}/{FALSO}/estado", {"estado": "EN_COMPRA"}, P.COMPRAS_ATENDER),
    ],
)
def test_AC_04_cada_endpoint_exige_su_permiso_por_clave(con_permisos, metodo, ruta, cuerpo_, exige):
    otro = P.COMPRAS_ATENDER if exige == P.COMPRAS_SOLICITAR else P.COMPRAS_SOLICITAR
    sin_nada = con_permisos(set())
    con_el_otro = con_permisos({otro, P.CATALOGO_VER, P.VALES_VER})
    con_el_suyo = con_permisos({exige, P.CATALOGO_VER, P.VALES_VER})
    for cliente in (sin_nada, con_el_otro):
        r = cliente.request(metodo, ruta, json=cuerpo_)
        assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO", (ruta, r.text)
    r = con_el_suyo.request(metodo, ruta, json=cuerpo_)
    assert r.status_code not in (401, 403), (ruta, r.text)


def test_AC_04_sin_sesion_todo_es_401(client):
    for metodo, ruta in (
        ("GET", RUTA),
        ("POST", RUTA),
        ("GET", f"{RUTA}/{FALSO}"),
        ("POST", f"{RUTA}/{FALSO}/estado"),
        ("POST", f"{RUTA}/{FALSO}/cancelacion"),
    ):
        r = client.request(metodo, ruta, json={} if metodo == "POST" else None)
        assert r.status_code == 401 and r.json()["codigo"] == "NO_AUTENTICADO", (metodo, ruta)


def test_AC_04_el_permiso_cambia_en_la_siguiente_peticion(como, con_permisos):
    """Quitar `compras.solicitar` a un rol lo deja sin poder pedir de inmediato (AC-10)."""
    cliente = con_permisos({P.COMPRAS_SOLICITAR, P.CATALOGO_VER}, almacen="KEP")
    assert cliente.post(RUTA, json=cuerpo()).status_code == 201
    admin = como("admin")
    sesion = cliente.get("/api/sesion").json()
    rol_id = sesion["rol"]["id"]
    r = admin.put(f"/api/roles/{rol_id}/permisos", json={"permisos": [P.CATALOGO_VER]})
    assert r.status_code == 200, r.text
    assert cliente.post(RUTA, json=cuerpo()).status_code == 403


# ------------------------------------------------------------------------ datos de prueba


def test_los_datos_de_prueba_dejan_tres_solicitudes_en_tres_estados(como, session):
    compras = como("compras")
    lista = {s["folio"]: s for s in compras.get(RUTA, params={"tamano": 100}).json()["elementos"]}
    midrex = lista["MID-SOL-000001"]
    assert midrex["estado"] == "PENDIENTE" and midrex["urgencia"] == "URGENTE"
    assert midrex["descripcion"] == "Llave métrica 24 mm" and midrex["articulo"] is None
    assert midrex["almacen"]["clave"] == "MID"
    en_compra = lista["KEP-SOL-000001"]
    assert en_compra["estado"] == "EN_COMPRA" and en_compra["articulo"]["codigo"] == "RESP-6200"
    ingresada = lista["KEP-SOL-000002"]
    assert ingresada["estado"] == "INGRESADA" and ingresada["articulo"]["codigo"] == "FLEXOM"
    assert ingresada["vale_entrada"]["folio"] == "KEP-ING-000001"
    # El vale ligado es una entrada real, no cancelada, de la carga inicial.
    vale = session.scalar(select(Vale).where(Vale.id == uuid.UUID(ingresada["vale_entrada"]["id"])))
    assert vale.tipo == TipoVale.ENTRADA and vale.estado != "CANCELADO"
    detalle = compras.get(f"{RUTA}/{ingresada['id']}").json()
    assert [e["estado_nuevo"] for e in detalle["eventos"]] == [
        "PENDIENTE",
        "EN_COMPRA",
        "COMPRADA",
        "INGRESADA",
    ]


def test_los_datos_de_prueba_son_repetibles_y_no_duplican_ni_mueven_nada(session):
    def foto():
        return (
            session.scalar(select(func.count()).select_from(SolicitudCompra)),
            session.scalar(select(func.count()).select_from(SolicitudCompraEvento)),
            session.scalar(select(func.sum(SerieSolicitudCompra.ultimo))),
            session.scalars(select(SolicitudCompra.estado).order_by(SolicitudCompra.folio)).all(),
        )

    antes = foto()
    assert antes[0] == 3
    datos_prueba.cargar(session)
    datos_prueba.cargar(session)
    assert foto() == antes


def test_los_datos_de_prueba_no_tocan_el_folio_de_los_que_se_crean_despues(como):
    # Kepler ya usó dos folios; el siguiente continúa la serie.
    assert pedir(como("almacenista"))["folio"] == "KEP-SOL-000003"
    assert pedir(como("alm_mid"))["folio"] == "MID-SOL-000002"
