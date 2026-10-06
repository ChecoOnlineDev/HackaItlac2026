"""Quién ve qué: SC-03, la lista con sus filtros, el contador y el detalle."""

import uuid
from datetime import timedelta

from sqlalchemy import select, update

from app.core.tiempo import ahora_utc, hoy_mx
from app.modulos.acceso.permisos import P
from app.modulos.almacenes.models import Almacen
from app.modulos.solicitudes_compra.models import SolicitudCompra
from tests.solicitudes_compra.ayudas import RUTA, estado, pedir


def _claves(cliente, **params) -> set[str]:
    r = cliente.get(RUTA, params={"tamano": 200} | params)
    assert r.status_code == 200, r.text
    return {s["folio"] for s in r.json()["elementos"]}


def _almacenes(cliente, **params) -> set[str]:
    r = cliente.get(RUTA, params={"tamano": 200} | params)
    assert r.status_code == 200, r.text
    return {s["almacen"]["clave"] for s in r.json()["elementos"]}


# ------------------------------------------------------------------------------- SC-03


def test_SC_03_un_almacenista_de_midrex_no_ve_las_de_kepler(como):
    # Los datos de prueba traen una de Midrex y dos de Kepler.
    mid = como("alm_mid")
    assert _almacenes(mid) == {"MID"}
    assert _claves(mid) == {"MID-SOL-000001"}
    assert "KEP-SOL-000001" not in _claves(mid)


def test_SC_03_el_almacenista_ve_tambien_las_que_pidio_su_supervisor(como):
    solicitud = pedir(como("supervisor"), descripcion="Pedida por el supervisor de Kepler")
    assert solicitud["folio"] in _claves(como("almacenista"))
    assert solicitud["folio"] in _claves(como("supervisor"))
    assert solicitud["folio"] not in _claves(como("alm_mid"))


def test_SC_03_compras_ve_las_de_todos_los_almacenes(como):
    pedir(como("alm_hyl"), descripcion="De HYL para Compras")
    compras = como("compras")
    assert _almacenes(compras) >= {"KEP", "MID", "HYL"}
    # Compras es de Kepler, pero atender solicitudes no es una operación de inventario.
    assert "MID-SOL-000001" in _claves(compras)


def test_SC_03_el_administrador_ve_todas(como):
    assert _almacenes(como("admin")) >= {"KEP", "MID"}


def test_SC_03_un_supervisor_sin_almacen_no_ve_nada(como, con_permisos):
    solicitud = pedir(como("alm_mid"))
    sin_almacen = con_permisos({P.COMPRAS_SOLICITAR, P.CATALOGO_VER}, almacen=None)
    r = sin_almacen.get(RUTA)
    assert r.status_code == 200 and r.json() == {"elementos": [], "total": 0}
    assert sin_almacen.get(RUTA, params={"solo_contar": "true"}).json() == {"total": 0}
    assert sin_almacen.get(f"{RUTA}/{solicitud['id']}").status_code == 404


def test_SC_03_pedir_otro_almacen_no_devuelve_nada_a_quien_solo_ve_el_suyo(como, session):
    kep = session.scalar(select(Almacen.id).where(Almacen.clave == "KEP"))
    r = como("alm_mid").get(RUTA, params={"almacen_id": str(kep)})
    assert r.status_code == 200 and r.json()["elementos"] == []


def test_SC_03_compras_filtra_por_almacen(como, session):
    kep = session.scalar(select(Almacen.id).where(Almacen.clave == "KEP"))
    assert _almacenes(como("compras"), almacen_id=str(kep)) == {"KEP"}


def test_SC_03_el_detalle_de_otro_almacen_es_404_y_el_de_compras_no(como):
    de_mid = pedir(como("alm_mid"))
    assert como("almacenista").get(f"{RUTA}/{de_mid['id']}").status_code == 404
    assert como("sup_mid").get(f"{RUTA}/{de_mid['id']}").status_code == 200
    assert como("compras").get(f"{RUTA}/{de_mid['id']}").status_code == 200
    assert como("admin").get(f"{RUTA}/{de_mid['id']}").status_code == 200
    r = como("compras").get(f"{RUTA}/{uuid.uuid4()}")
    assert r.status_code == 404 and r.json()["codigo"] == "NO_ENCONTRADO"


def test_SC_03_quien_no_pide_ni_atiende_recibe_403_en_la_lista_y_el_detalle(como, con_permisos):
    solicitud = pedir(como("almacenista"))
    for cliente in (como("rh"), con_permisos({P.CATALOGO_VER}, almacen="KEP")):
        r = cliente.get(RUTA)
        assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"
        r = cliente.get(f"{RUTA}/{solicitud['id']}")
        assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"


def test_SC_03_quien_solo_pide_o_solo_atiende_puede_consultar(con_permisos, como):
    solicitud = pedir(como("almacenista"))
    solo_pide = con_permisos({P.COMPRAS_SOLICITAR}, almacen="KEP")
    solo_atiende = con_permisos({P.COMPRAS_ATENDER}, almacen=None)
    assert solicitud["folio"] in _claves(solo_pide)
    assert solicitud["folio"] in _claves(solo_atiende)
    assert solo_pide.get(f"{RUTA}/{solicitud['id']}").status_code == 200
    assert solo_atiende.get(f"{RUTA}/{solicitud['id']}").status_code == 200


# --------------------------------------------------------------------------- filtros


def test_la_lista_filtra_por_estado_y_urgencia(como):
    compras = como("compras")
    pedir(como("alm_hyl"), urgencia="NORMAL", descripcion="Normal de HYL")
    assert {
        s["estado"] for s in compras.get(RUTA, params={"estado": "EN_COMPRA"}).json()["elementos"]
    } == {"EN_COMPRA"}
    r = compras.get(RUTA, params={"urgencia": "NORMAL", "tamano": 200}).json()["elementos"]
    assert r and {s["urgencia"] for s in r} == {"NORMAL"}
    assert compras.get(RUTA, params={"estado": "NO_EXISTE"}).status_code == 422


def test_la_lista_busca_por_folio_descripcion_articulo_y_motivo(como):
    compras = como("compras")
    assert _claves(compras, q="llave métrica") == {"MID-SOL-000001"}  # descripción (sin acento ok)
    assert _claves(compras, q="LLAVE METRICA") == {"MID-SOL-000001"}
    assert _claves(compras, q="KEP-SOL-000001") == {"KEP-SOL-000001"}  # folio
    assert _claves(compras, q="respirador") == {"KEP-SOL-000001"}  # nombre del artículo
    assert _claves(compras, q="RESP-6200") == {"KEP-SOL-000001"}  # código del artículo
    assert _claves(compras, q="cuadrillas") == {"KEP-SOL-000002"}  # motivo
    assert _claves(compras, q="no-existe-esto") == set()
    assert _claves(compras, q="50%") == set()  # el comodín de LIKE no se interpreta


def test_la_lista_filtra_por_fechas_de_mexico(como, session):
    compras = como("compras")
    vieja = pedir(como("alm_lam"), descripcion="De hace diez días")
    session.execute(
        update(SolicitudCompra)
        .where(SolicitudCompra.id == uuid.UUID(vieja["id"]))
        .values(creada_en=ahora_utc() - timedelta(days=10))
    )
    hoy = hoy_mx()
    hace_cinco = str(hoy - timedelta(days=5))
    assert vieja["folio"] not in _claves(compras, desde=hace_cinco)
    assert vieja["folio"] in _claves(compras, hasta=hace_cinco)
    assert _claves(compras, desde=str(hoy), hasta=str(hoy)) >= {"MID-SOL-000001"}
    r = compras.get(RUTA, params={"desde": str(hoy), "hasta": hace_cinco})
    assert r.status_code == 422 and r.json()["codigo"] == "DATOS_INVALIDOS"


def test_mias_deja_solo_las_que_pidio_el_usuario(como):
    pedir(como("supervisor"), descripcion="Del supervisor")
    mia = pedir(como("almacenista"), descripcion="Del almacenista")
    assert _claves(como("almacenista"), mias="true") == {mia["folio"]}
    assert mia["folio"] in _claves(como("almacenista"))
    assert mia["folio"] not in _claves(como("supervisor"), mias="true")


def test_solo_contar_responde_el_total_con_los_mismos_filtros(como):
    compras = como("compras")
    assert compras.get(RUTA, params={"solo_contar": "true", "estado": "PENDIENTE"}).json() == {
        "total": 1
    }
    todas = compras.get(RUTA).json()["total"]
    assert compras.get(RUTA, params={"solo_contar": "true"}).json() == {"total": todas}
    assert como("alm_mid").get(RUTA, params={"solo_contar": "true"}).json() == {"total": 1}
    r = compras.get(RUTA, params={"solo_contar": "true"}).json()
    assert set(r) == {"total"}


def test_la_lista_se_pagina(como):
    hyl = como("alm_hyl")
    for i in range(3):
        pedir(hyl, descripcion=f"Pieza {i}")
    primera = hyl.get(RUTA, params={"pagina": 1, "tamano": 2}).json()
    segunda = hyl.get(RUTA, params={"pagina": 2, "tamano": 2}).json()
    assert (
        primera["total"] == 3 and len(primera["elementos"]) == 2 and len(segunda["elementos"]) == 1
    )
    assert not ({s["id"] for s in primera["elementos"]} & {s["id"] for s in segunda["elementos"]})
    assert hyl.get(RUTA, params={"tamano": 0}).status_code == 422


def test_SC_03_el_orden_pone_primero_lo_pendiente_urgente_y_antiguo(como, session):
    """Pendientes antes que en compra y que cerradas; urgentes antes que normales; en cada grupo,
    las más antiguas primero. Lo cerrado, de la más reciente a la más antigua."""
    sup, compras = como("sup_lam"), como("compras")
    normal_vieja = pedir(sup, urgencia="NORMAL", descripcion="Normal vieja")
    urgente_nueva = pedir(sup, urgencia="URGENTE", descripcion="Urgente nueva")
    urgente_vieja = pedir(sup, urgencia="URGENTE", descripcion="Urgente vieja")
    en_compra = pedir(sup, urgencia="URGENTE", descripcion="Ya en compra")
    cerrada = pedir(sup, urgencia="URGENTE", descripcion="Rechazada")
    estado(compras, en_compra["id"], "EN_COMPRA")
    estado(compras, cerrada["id"], "RECHAZADA", nota="No se justifica")
    ahora = ahora_utc()
    for solicitud, dias in ((normal_vieja, 9), (urgente_vieja, 8), (urgente_nueva, 1)):
        session.execute(
            update(SolicitudCompra)
            .where(SolicitudCompra.id == uuid.UUID(solicitud["id"]))
            .values(creada_en=ahora - timedelta(days=dias))
        )
    elementos = compras.get(RUTA, params={"almacen_id": en_compra["almacen"]["id"]}).json()[
        "elementos"
    ]
    assert [s["descripcion"] for s in elementos] == [
        "Urgente vieja",
        "Urgente nueva",
        "Normal vieja",
        "Ya en compra",
        "Rechazada",
    ]
