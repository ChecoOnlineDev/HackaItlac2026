"""Alcance por almacén de los roles iniciales y del personal (AC-03, AC-06, AC-12, RG-07)."""

import pytest
from sqlalchemy import select

from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from tests.conftest import iniciar_sesion_en


def _sesion(client, usuario_por_rol, rol):
    r = iniciar_sesion_en(client, usuario_por_rol(rol))
    assert r.status_code == 200, r.text
    return r.json()


def test_AC_06_solo_el_administrador_tiene_almacenes_todos(client, usuario_por_rol):
    for rol in ("Supervisor", "Compras", "Almacenista", "Recursos Humanos"):
        assert P.ALMACENES_TODOS not in _sesion(client, usuario_por_rol, rol)["permisos"], rol
    assert P.ALMACENES_TODOS in _sesion(client, usuario_por_rol, "Administrador")["permisos"]


def test_RG_07_cada_almacen_tiene_su_supervisor_y_compras_es_de_kepler(session):
    usuarios = {
        u.usuario: u for u in session.scalars(select(Usuario).where(Usuario.activo.is_(True)))
    }
    esperado = {
        "supervisor": "KEP",
        "sup_con": "CON",
        "sup_mid": "MID",
        "sup_hyl": "HYL",
        "sup_lam": "LAM",
        "sup_min": "MIN",
        "compras": "KEP",
        "almacenista": "KEP",
        "alm_mid": "MID",
    }
    from app.modulos.almacenes.models import Almacen

    claves = {a.id: a.clave for a in session.scalars(select(Almacen))}
    for nombre, clave in esperado.items():
        assert claves[usuarios[nombre].almacen_id] == clave, nombre
    assert usuarios["admin"].almacen_id is None and usuarios["rh"].almacen_id is None
    for nombre in ("supervisor", "sup_con", "sup_mid", "sup_hyl", "sup_lam", "sup_min"):
        assert usuarios[nombre].rol.nombre == "Supervisor"


def test_AC_03_el_almacenista_no_tiene_etiquetas_traspasos_reportes_ni_catalogo_administrar(
    client, usuario_por_rol
):
    permisos = set(_sesion(client, usuario_por_rol, "Almacenista")["permisos"])
    for clave in (
        P.ETIQUETAS_IMPRIMIR,
        P.TRASPASOS_OPERAR,
        P.REPORTES_EXISTENCIAS,
        P.REPORTES_MOVIMIENTOS,
        P.REPORTES_ADEUDOS,
        P.CATALOGO_ADMINISTRAR,
    ):
        assert clave not in permisos, clave
    assert P.INVENTARIO_VER in permisos and P.CATALOGO_VER in permisos


def test_AC_12_el_supervisor_no_da_de_alta_trabajadores(cliente_como):
    # El alta es de RH (`trabajadores.administrar`); el Supervisor recibe 403.
    r = cliente_como("Supervisor").post("/api/trabajadores", json={"nombre": "Pedro Gómez"})
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"
    assert cliente_como("Recursos Humanos").post("/api/trabajadores", json={}).status_code != 403


# ------------------------------------------------------------------------ personal


def _personal(cliente, **params):
    r = cliente.get("/api/personal", params={"tamano": 100, **params})
    assert r.status_code == 200, r.text
    return {e["usuario"]: e for e in r.json()["elementos"]}


@pytest.fixture
def libre(crear_usuario, session):
    """Un usuario que opera un almacén (puede ver inventario) pero aún no tiene uno."""
    u = crear_usuario({P.INVENTARIO_VER, P.ENTREGAS_CREAR})
    return session.scalar(select(Usuario).where(Usuario.usuario == u.usuario))


def _id(session, nombre):
    return str(session.scalar(select(Usuario.id).where(Usuario.usuario == nombre)))


def test_AC_06_AC_12_el_supervisor_solo_ve_su_personal_y_a_quien_no_tiene_almacen(
    cliente_como, libre
):
    visto = _personal(cliente_como("Supervisor"))  # supervisor de Kepler
    assert "almacenista" in visto and libre.usuario in visto
    assert "alm_mid" not in visto and "alm_con" not in visto and "sup_mid" not in visto
    # RH y el Administrador no trabajan en un almacén: no son personal de almacén.
    assert "rh" not in visto and "admin" not in visto
    # Pedir otro almacén no filtra por fuera de su alcance.
    assert (
        _personal(
            cliente_como("Supervisor"), almacen_id=_id_almacen(cliente_como("Supervisor"), "MID")
        )
        == {}
    )


def _id_almacen(cliente, clave):
    lista = cliente.get("/api/almacenes").json()
    return next(a["id"] for a in lista if a["clave"] == clave)


def test_AC_06_AC_12_el_administrador_ve_el_personal_de_todos_los_almacenes(cliente_como):
    visto = _personal(cliente_como("Administrador"))
    assert {"almacenista", "alm_mid", "alm_con", "sup_mid", "supervisor"} <= set(visto)
    assert "rh" not in visto and "admin" not in visto


def test_AC_12_el_supervisor_trae_a_su_almacen_a_quien_no_tiene_y_lo_libera(
    cliente_como, libre, session
):
    sup = cliente_como("Supervisor")
    kep = _id_almacen(sup, "KEP")
    r = sup.patch(f"/api/usuarios/{libre.id}/almacen", json={"almacen_id": kep})
    assert r.status_code == 200 and r.json()["almacen"]["clave"] == "KEP"
    r = sup.patch(f"/api/usuarios/{libre.id}/almacen", json={"almacen_id": None})
    assert r.status_code == 200 and r.json()["almacen"] is None


def test_AC_06_AC_12_el_supervisor_no_mueve_personas_entre_almacenes(cliente_como, libre, session):
    sup = cliente_como("Supervisor")
    mid = _id_almacen(sup, "MID")
    # No puede mandar a alguien a otro almacén...
    r = sup.patch(f"/api/usuarios/{libre.id}/almacen", json={"almacen_id": mid})
    assert r.status_code == 403
    # ...ni tocar a quien está en otro almacén (no existe para él).
    r = sup.patch(f"/api/usuarios/{_id(session, 'alm_mid')}/almacen", json={"almacen_id": None})
    assert r.status_code == 404
    r = sup.patch(
        f"/api/usuarios/{_id(session, 'alm_mid')}/almacen",
        json={"almacen_id": _id_almacen(sup, "KEP")},
    )
    assert r.status_code == 404


def test_AC_12_el_administrador_mueve_personas_entre_almacenes(cliente_como, session):
    admin = cliente_como("Administrador")
    con = _id_almacen(admin, "CON")
    r = admin.patch(f"/api/usuarios/{_id(session, 'alm_mid')}/almacen", json={"almacen_id": con})
    assert r.status_code == 200 and r.json()["almacen"]["clave"] == "CON"


def test_AC_12_a_rh_no_se_le_asigna_almacen(cliente_como, session):
    r = cliente_como("Administrador").patch(
        f"/api/usuarios/{_id(session, 'rh')}/almacen",
        json={"almacen_id": _id_almacen(cliente_como("Administrador"), "KEP")},
    )
    assert r.status_code == 422
