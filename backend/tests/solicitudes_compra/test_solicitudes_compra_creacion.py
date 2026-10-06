"""Crear una solicitud de compra urgente: SC-01, SC-02, SC-09 y SC-10."""

import uuid

import pytest
from sqlalchemy import func, select

from app.modulos.acceso.permisos import P
from app.modulos.almacenes.models import Almacen
from app.modulos.solicitudes_compra.models import (
    SolicitudCompra,
    SolicitudCompraEvento,
)
from tests.movimientos.ayudas import crear_articulo
from tests.solicitudes_compra.ayudas import RUTA, cuerpo, pedir


def _id_almacen(session, clave: str) -> str:
    return str(session.scalar(select(Almacen.id).where(Almacen.clave == clave)))


# ------------------------------------------------------------------------------- SC-01


def test_SC_01_un_almacenista_levanta_una_solicitud_pendiente_y_urgente_en_su_almacen(como):
    s = pedir(como("alm_mid"))
    assert s["estado"] == "PENDIENTE" and s["urgencia"] == "URGENTE"  # urgente por omisión
    assert s["almacen"]["clave"] == "MID"
    assert s["solicitante"]["nombre"] == "Almacenista Midrex"
    assert s["articulo"] is None and s["descripcion"] == "Llave métrica 24 mm"
    assert s["cantidad"] == 2 and s["vale_entrada"] is None and s["nota_compras"] is None
    assert s["acciones"] == ["cancelar"]
    assert [(e["estado_anterior"], e["estado_nuevo"]) for e in s["eventos"]] == [
        (None, "PENDIENTE")
    ]


def test_SC_01_un_supervisor_tambien_levanta_solicitudes(como):
    s = pedir(como("supervisor"), urgencia="NORMAL")
    assert s["almacen"]["clave"] == "KEP" and s["urgencia"] == "NORMAL"


def test_SC_01_el_almacen_sale_del_usuario_y_no_de_lo_que_diga_el_cuerpo(como, session):
    mid = como("alm_mid")
    propio = pedir(mid, almacen_id=_id_almacen(session, "MID"))  # el propio sí se acepta
    assert propio["almacen"]["clave"] == "MID"
    r = mid.post(RUTA, json=cuerpo(almacen_id=_id_almacen(session, "KEP")))
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"


def test_SC_01_con_almacenes_todos_se_indica_el_almacen(como, session):
    admin = como("admin")
    r = admin.post(RUTA, json=cuerpo())
    assert r.status_code == 422 and r.json()["codigo"] == "DATOS_INVALIDOS"
    s = pedir(admin, almacen_id=_id_almacen(session, "HYL"))
    assert (
        s["almacen"]["clave"] == "HYL" and s["solicitante"]["nombre"] == "Administrador de prueba"
    )


def test_SC_01_sin_almacen_asignado_y_sin_almacenes_todos_no_puede_pedir(con_permisos):
    sin_almacen = con_permisos({P.COMPRAS_SOLICITAR, P.CATALOGO_VER}, almacen=None)
    r = sin_almacen.post(RUTA, json=cuerpo())
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"


def test_SC_01_quien_solo_atiende_compras_no_puede_pedir(como):
    r = como("compras").post(RUTA, json=cuerpo())
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"


# ------------------------------------------------------------------------------- SC-02


def test_SC_02_con_articulo_de_catalogo_se_toma_su_nombre(como, session):
    articulo = crear_articulo(session, nombre="Torquímetro europeo 40-200 Nm")
    s = pedir(
        como("supervisor"),
        articulo_id=str(articulo.id),
        descripcion="texto que se ignora",
    )
    assert s["articulo"] == {
        "id": str(articulo.id),
        "codigo": articulo.codigo,
        "nombre": "Torquímetro europeo 40-200 Nm",
    }
    assert s["descripcion"] == "Torquímetro europeo 40-200 Nm"


def test_SC_02_sin_articulo_la_descripcion_es_obligatoria(como):
    almacenista = como("almacenista")
    for descripcion in (..., "", "    "):
        r = almacenista.post(RUTA, json=cuerpo(descripcion=descripcion))
        assert r.status_code == 422 and r.json()["codigo"] == "DATOS_INVALIDOS", descripcion


def test_SC_02_un_articulo_que_no_existe_da_404_y_uno_inactivo_422(como, session):
    almacenista = como("almacenista")
    r = almacenista.post(RUTA, json=cuerpo(articulo_id=str(uuid.uuid4()), descripcion=...))
    assert r.status_code == 404 and r.json()["codigo"] == "NO_ENCONTRADO"
    inactivo = crear_articulo(session, activo=False)
    r = almacenista.post(RUTA, json=cuerpo(articulo_id=str(inactivo.id), descripcion=...))
    assert r.status_code == 422
    assert r.json()["detalles"][0]["regla"] == "SC-02"


@pytest.mark.parametrize("cantidad", [0, -3, 1.5, "dos", None, 1_000_001])
def test_SC_02_la_cantidad_es_un_entero_de_uno_en_adelante(como, cantidad):
    r = como("almacenista").post(RUTA, json=cuerpo(cantidad=cantidad))
    assert r.status_code == 422 and r.json()["codigo"] == "DATOS_INVALIDOS"


@pytest.mark.parametrize("motivo", [..., "", "   ", None])
def test_SC_02_el_motivo_es_obligatorio(como, motivo):
    r = como("almacenista").post(RUTA, json=cuerpo(motivo=motivo))
    assert r.status_code == 422 and r.json()["codigo"] == "DATOS_INVALIDOS"


def test_SC_02_la_urgencia_es_urgente_o_normal(como):
    almacenista = como("almacenista")
    assert pedir(almacenista, urgencia="NORMAL")["urgencia"] == "NORMAL"
    r = almacenista.post(RUTA, json=cuerpo(urgencia="MUY_URGENTE"))
    assert r.status_code == 422


def test_SC_02_el_id_del_cliente_es_obligatorio(como):
    r = como("almacenista").post(RUTA, json=cuerpo(id_cliente=...))
    assert r.status_code == 422


# ------------------------------------------------------------------------------- SC-09


def test_SC_09_el_folio_es_consecutivo_por_almacen_y_nunca_sale_del_id(como):
    hyl, lam = como("alm_hyl"), como("alm_lam")
    primero, segundo, otro = pedir(hyl), pedir(hyl), pedir(lam)
    assert primero["folio"] == "HYL-SOL-000001"
    assert segundo["folio"] == "HYL-SOL-000002"
    assert otro["folio"] == "LAM-SOL-000001"  # cada almacén lleva su propio contador
    assert primero["id"] not in primero["folio"]


def test_SC_09_el_folio_no_avanza_si_la_solicitud_no_se_guarda(como):
    hyl = como("alm_hyl")
    assert hyl.post(RUTA, json=cuerpo(cantidad=0)).status_code == 422
    assert pedir(hyl)["folio"] == "HYL-SOL-000001"


# ------------------------------------------------------------------------------- SC-10


def test_SC_10_repetir_la_misma_peticion_devuelve_la_misma_solicitud_sin_duplicarla(como, session):
    almacenista = como("alm_min")
    datos = cuerpo()
    primera = almacenista.post(RUTA, json=datos)
    segunda = almacenista.post(RUTA, json=datos)
    assert primera.status_code == 201 and segunda.status_code == 200
    assert primera.json() == segunda.json()
    filas = session.scalar(
        select(func.count())
        .select_from(SolicitudCompra)
        .where(SolicitudCompra.id_cliente == uuid.UUID(datos["id_cliente"]))
    )
    eventos = session.scalar(
        select(func.count())
        .select_from(SolicitudCompraEvento)
        .where(SolicitudCompraEvento.solicitud_id == uuid.UUID(primera.json()["id"]))
    )
    assert filas == 1 and eventos == 1
    # El folio no avanzó por el reintento.
    assert pedir(almacenista)["folio"] == "MIN-SOL-000002"


def test_SC_10_repetir_con_el_almacen_explicito_o_sin_el_es_la_misma_peticion(como, session):
    mid = como("alm_mid")
    datos = cuerpo()
    assert mid.post(RUTA, json=datos).status_code == 201
    r = mid.post(RUTA, json=datos | {"almacen_id": _id_almacen(session, "MID")})
    assert r.status_code == 200


def test_SC_10_el_mismo_id_con_otro_cuerpo_es_409(como):
    almacenista = como("almacenista")
    datos = cuerpo()
    assert almacenista.post(RUTA, json=datos).status_code == 201
    for cambio in ({"cantidad": 9}, {"motivo": "Otro trabajo"}, {"urgencia": "NORMAL"}):
        r = almacenista.post(RUTA, json=datos | cambio)
        assert r.status_code == 409 and r.json()["codigo"] == "ID_CLIENTE_EN_USO", cambio
        assert r.json()["detalles"]["regla"] == "SC-10"


def test_SC_10_el_id_de_otro_usuario_no_devuelve_su_solicitud(como):
    datos = cuerpo()
    assert como("almacenista").post(RUTA, json=datos).status_code == 201
    r = como("supervisor").post(RUTA, json=datos)
    assert r.status_code == 409 and r.json()["codigo"] == "ID_CLIENTE_EN_USO"


def test_SC_02_dos_articulos_distintos_con_el_mismo_texto_no_se_confunden(como, session):
    """Con artículo, la descripción que mande el cliente no cambia la huella (se ignora)."""
    articulo = crear_articulo(session)
    almacenista = como("almacenista")
    datos = cuerpo(articulo_id=str(articulo.id), descripcion="uno")
    assert almacenista.post(RUTA, json=datos).status_code == 201
    assert almacenista.post(RUTA, json=datos | {"descripcion": "otro"}).status_code == 200
    otro = crear_articulo(session)
    r = almacenista.post(RUTA, json=datos | {"articulo_id": str(otro.id)})
    assert r.status_code == 409
