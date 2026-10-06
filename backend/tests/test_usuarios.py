"""Pruebas de FEAT-006: usuarios, asignación de personal a almacenes y ALMACEN_CAMBIO.

Reglas: AC-09 (último administrador), AC-12 (asignar personal), AC-13 (el cambio aplica en la
siguiente petición, queda en el registro y `ALMACEN_CAMBIO`), RG-07 y RG-03.
"""

import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.excepciones import NoEncontrado
from app.modulos.acceso.exceptions import AlmacenCambio
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.acceso.repository import UsuarioRepository
from app.modulos.acceso.service import AccesoService
from app.modulos.almacenes.models import EstadoAlmacen
from app.modulos.almacenes.repository import AlmacenRepository
from app.modulos.auditoria.models import Auditoria
from tests.conftest import iniciar_sesion_en

CONTRASENA_NUEVA = "Otra-clave-2026"


def _usuario(session, nombre: str) -> Usuario:
    usuario = UsuarioRepository(session).get_by_usuario(nombre)
    assert usuario is not None
    return usuario


def _almacen(session, clave: str):
    almacen = AlmacenRepository(session).get_by_clave(clave)
    assert almacen is not None
    return almacen


def _auditoria(session, accion: str, entidad_id) -> list[Auditoria]:
    return list(
        session.scalars(
            select(Auditoria)
            .where(Auditoria.accion == accion, Auditoria.entidad_id == str(entidad_id))
            .order_by(Auditoria.creado_en)
        )
    )


def _rol_id(cliente: TestClient, nombre: str) -> str:
    roles = cliente.get("/api/roles").json()
    return next(r["id"] for r in roles if r["nombre"] == nombre)


def _alta(cliente: TestClient, session, **cambios):
    cuerpo = {
        "nombre": "Persona Nueva",
        "usuario": "persona.nueva",
        "contrasena": "Clave-inicial-1",
        "rol_id": _rol_id(cliente, "Almacenista"),
        "almacen_id": str(_almacen(session, "MID").id),
    } | cambios
    return cliente.post("/api/usuarios", json=cuerpo)


# ----------------------------------------------------------------- permisos


ENDPOINTS_PERSONAL = [
    ("GET", "/api/personal", None),
    ("PATCH", "/api/usuarios/{id}/almacen", {"almacen_id": None}),
]
ENDPOINTS_ADMIN = [
    ("GET", "/api/usuarios", None),
    ("GET", "/api/roles", None),
    ("GET", "/api/usuarios/{id}", None),
    ("POST", "/api/usuarios", {"nombre": "x", "usuario": "xxx", "contrasena": "Clave-1234"}),
    ("PATCH", "/api/usuarios/{id}", {"nombre": "Otro nombre"}),
    ("POST", "/api/usuarios/{id}/contrasena", {"contrasena": "Clave-nueva-1"}),
]


def _llamar(cliente, metodo, ruta, cuerpo, usuario_id):
    return cliente.request(metodo, ruta.replace("{id}", str(usuario_id)), json=cuerpo)


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo"), ENDPOINTS_PERSONAL + ENDPOINTS_ADMIN)
def test_AC_12_el_almacenista_no_puede_ningun_endpoint_de_usuarios(
    metodo, ruta, cuerpo, cliente_como, session
):
    objetivo = _usuario(session, "alm_hyl").id
    r = _llamar(cliente_como("Almacenista"), metodo, ruta, cuerpo, objetivo)
    assert r.status_code == 403
    assert r.json()["codigo"] == "SIN_PERMISO"


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo"), ENDPOINTS_ADMIN)
def test_AC_12_el_supervisor_no_toca_usuarios_ni_roles(metodo, ruta, cuerpo, cliente_como, session):
    objetivo = _usuario(session, "alm_hyl").id
    r = _llamar(cliente_como("Supervisor"), metodo, ruta, cuerpo, objetivo)
    assert r.status_code == 403
    assert r.json()["codigo"] == "SIN_PERMISO"


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo"), ENDPOINTS_PERSONAL)
def test_AC_12_el_administrador_y_el_supervisor_pueden_los_de_personal(
    metodo, ruta, cuerpo, cliente_como, session
):
    # El Supervisor (de Kepler) alcanza a su personal; el Administrador, a cualquiera.
    for rol, nombre in (("Supervisor", "almacenista"), ("Administrador", "alm_hyl")):
        objetivo = _usuario(session, nombre).id
        r = _llamar(cliente_como(rol), metodo, ruta, cuerpo, objetivo)
        assert r.status_code == 200, r.text
    # El administrador puede además todos los de administración.


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo"), ENDPOINTS_PERSONAL + ENDPOINTS_ADMIN)
def test_AC_12_sin_sesion_responde_401(metodo, ruta, cuerpo, client, session):
    r = _llamar(client, metodo, ruta, cuerpo, _usuario(session, "alm_hyl").id)
    assert r.status_code == 401


def test_AC_12_el_administrador_puede_los_endpoints_de_administracion(cliente_como, session):
    admin = cliente_como("Administrador")
    objetivo = _usuario(session, "alm_hyl").id
    assert admin.get("/api/usuarios").status_code == 200
    assert admin.get("/api/roles").status_code == 200
    assert admin.get(f"/api/usuarios/{objetivo}").status_code == 200
    assert (
        admin.patch(f"/api/usuarios/{objetivo}", json={"nombre": "Nuevo nombre"}).status_code == 200
    )
    assert (
        admin.post(
            f"/api/usuarios/{objetivo}/contrasena", json={"contrasena": CONTRASENA_NUEVA}
        ).status_code
        == 200
    )
    assert _alta(admin, session).status_code == 201


# Estas pruebas usan al Administrador (`almacenes.todos`): mover personas entre almacenes es
# suyo. El Supervisor, limitado a su almacén, se prueba en `tests/test_alcance_roles.py`.

# ------------------------------------------------------------ GET /api/personal


def test_AC_12_la_lista_de_personal_solo_trae_a_quienes_operan_un_almacen(cliente_como):
    r = cliente_como("Administrador").get("/api/personal", params={"tamano": 200})
    assert r.status_code == 200
    cuerpo = r.json()
    usuarios = {e["usuario"] for e in cuerpo["elementos"]}
    assert {"almacenista", "alm_con", "alm_mid", "alm_hyl", "alm_lam", "alm_min"} <= usuarios
    # Quien tiene `almacenes.todos` y RH (que no opera inventario) no son personal de almacén.
    assert not usuarios & {"admin", "rh"}
    assert {"supervisor", "sup_hyl", "compras"} <= usuarios
    assert cuerpo["total"] == len(cuerpo["elementos"])
    hyl = next(e for e in cuerpo["elementos"] if e["usuario"] == "alm_hyl")
    assert hyl["almacen"]["clave"] == "HYL"
    assert hyl["rol"]["nombre"] == "Almacenista"
    assert hyl["activo"] is True


def test_AC_12_el_filtro_por_almacen_y_el_de_sin_almacen(cliente_como, session, crear_usuario):
    sup = cliente_como("Administrador")
    hyl = str(_almacen(session, "HYL").id)
    r = sup.get("/api/personal", params={"almacen_id": hyl}).json()
    assert [e["usuario"] for e in r["elementos"]] == ["alm_hyl", "sup_hyl"]

    sin = crear_usuario({P.ENTREGAS_CREAR})  # opera un almacén y no tiene ninguno asignado
    r = sup.get("/api/personal", params={"sin_almacen": True}).json()
    # Recursos Humanos no opera ningún almacén: no es personal de almacén, aunque no tenga uno.
    assert {e["usuario"] for e in r["elementos"]} == {sin.usuario}
    assert all(e["almacen"] is None for e in r["elementos"])

    r = sup.get("/api/personal", params={"q": "Laminador"}).json()
    assert [e["usuario"] for e in r["elementos"]] == ["alm_lam", "sup_lam"]


def test_AC_12_un_almacen_puede_tener_varios_usuarios(cliente_como, session, crear_usuario):
    otro = crear_usuario({P.ENTREGAS_CREAR}, almacen="HYL")
    r = cliente_como("Administrador").get(
        "/api/personal", params={"almacen_id": str(_almacen(session, "HYL").id)}
    )
    assert {e["usuario"] for e in r.json()["elementos"]} == {"alm_hyl", "sup_hyl", otro.usuario}
    assert r.json()["total"] == 3


def test_AC_12_no_se_puede_pedir_un_almacen_y_sin_almacen_a_la_vez(cliente_como, session):
    r = cliente_como("Administrador").get(
        "/api/personal",
        params={"almacen_id": str(_almacen(session, "HYL").id), "sin_almacen": True},
    )
    assert r.status_code == 422
    assert r.json()["codigo"] == "DATOS_INVALIDOS"


def test_AC_12_la_lista_de_personal_se_pagina(cliente_como):
    r = cliente_como("Administrador").get("/api/personal", params={"tamano": 2, "pagina": 1}).json()
    assert len(r["elementos"]) == 2 and r["total"] >= 6


# ----------------------------------------------------- PATCH .../almacen


def test_AC_13_el_cambio_de_almacen_aplica_en_la_siguiente_peticion_del_usuario(
    app, cliente_como, session, usuario_por_rol
):
    # El almacenista entra de verdad y conserva su cookie.
    almacenista = TestClient(app)
    entrada = iniciar_sesion_en(almacenista, _como_usuario("alm_hyl"))
    assert entrada.status_code == 200 and entrada.json()["almacen"]["clave"] == "HYL"

    destino = _almacen(session, "KEP")
    r = cliente_como("Administrador").patch(
        f"/api/usuarios/{_usuario(session, 'alm_hyl').id}/almacen",
        json={"almacen_id": str(destino.id)},
    )
    assert r.status_code == 200, r.text
    assert r.json()["almacen"]["clave"] == "KEP"

    # Misma cookie, sin volver a entrar: ya opera el almacén nuevo.
    siguiente = almacenista.get("/api/sesion")
    assert siguiente.status_code == 200
    assert siguiente.json()["almacen"]["clave"] == "KEP"
    almacenista.close()


def _como_usuario(nombre: str):
    from app.config import get_settings
    from tests.conftest import UsuarioPrueba

    return UsuarioPrueba(nombre, get_settings().clave_datos_prueba)


def test_AC_13_el_cambio_queda_en_auditoria_con_almacen_anterior_y_nuevo(cliente_como, session):
    objetivo = _usuario(session, "alm_hyl")
    quien_mueve = _usuario(session, "admin")
    destino = _almacen(session, "LAM")
    r = cliente_como("Administrador").patch(
        f"/api/usuarios/{objetivo.id}/almacen", json={"almacen_id": str(destino.id)}
    )
    assert r.status_code == 200
    (registro,) = _auditoria(session, "usuario.almacen", objetivo.id)
    assert registro.usuario_id == quien_mueve.id  # quién
    assert registro.creado_en is not None  # cuándo
    assert registro.antes["almacen"]["codigo"] == "HYL"
    assert registro.despues["almacen"]["codigo"] == "LAM"
    assert registro.despues["almacen"]["id"] == str(destino.id)


def test_AC_12_dejar_a_un_usuario_sin_almacen(cliente_como, session):
    objetivo = _usuario(session, "alm_hyl")
    r = cliente_como("Administrador").patch(
        f"/api/usuarios/{objetivo.id}/almacen", json={"almacen_id": None}
    )
    assert r.status_code == 200
    assert r.json()["almacen"] is None
    (registro,) = _auditoria(session, "usuario.almacen", objetivo.id)
    assert registro.antes["almacen"]["codigo"] == "HYL" and registro.despues["almacen"] is None


def test_AC_12_asignar_al_mismo_almacen_no_deja_registro(cliente_como, session):
    objetivo = _usuario(session, "alm_hyl")
    r = cliente_como("Administrador").patch(
        f"/api/usuarios/{objetivo.id}/almacen",
        json={"almacen_id": str(_almacen(session, "HYL").id)},
    )
    assert r.status_code == 200
    assert _auditoria(session, "usuario.almacen", objetivo.id) == []


def test_AC_12_un_almacen_inexistente_se_rechaza(cliente_como, session):
    objetivo = _usuario(session, "alm_hyl")
    r = cliente_como("Administrador").patch(
        f"/api/usuarios/{objetivo.id}/almacen", json={"almacen_id": str(uuid.uuid4())}
    )
    assert r.status_code == 422
    assert r.json()["detalles"][0]["campo"] == "almacen_id"
    session.refresh(objetivo)
    assert objetivo.almacen_id == _almacen(session, "HYL").id


def test_AC_12_un_almacen_cerrado_se_rechaza(cliente_como, session):
    destino = _almacen(session, "MIN")
    destino.estado = EstadoAlmacen.CERRADO
    session.commit()
    objetivo = _usuario(session, "alm_hyl")
    r = cliente_como("Administrador").patch(
        f"/api/usuarios/{objetivo.id}/almacen", json={"almacen_id": str(destino.id)}
    )
    assert r.status_code == 422
    assert r.json()["detalles"][0]["campo"] == "almacen_id"


def test_AC_12_no_se_asigna_almacen_a_quien_puede_operar_todos(cliente_como, session):
    destino = str(_almacen(session, "KEP").id)
    sup = cliente_como("Administrador")
    for nombre in ("rh", "admin"):  # RH no opera almacén y el Administrador opera todos
        objetivo = _usuario(session, nombre)
        r = sup.patch(f"/api/usuarios/{objetivo.id}/almacen", json={"almacen_id": destino})
        assert r.status_code == 422, nombre
        assert r.json()["codigo"] == "DATOS_INVALIDOS"
        session.refresh(objetivo)
        assert objetivo.almacen_id is None


def test_AC_12_un_usuario_inactivo_no_se_mueve(cliente_como, session):
    objetivo = _usuario(session, "alm_hyl")
    objetivo.activo = False
    session.commit()
    r = cliente_como("Administrador").patch(
        f"/api/usuarios/{objetivo.id}/almacen",
        json={"almacen_id": str(_almacen(session, "KEP").id)},
    )
    assert r.status_code == 422
    assert objetivo.almacen_id == _almacen(session, "HYL").id


def test_AC_12_un_usuario_que_no_existe_responde_404(cliente_como):
    r = cliente_como("Administrador").patch(
        f"/api/usuarios/{uuid.uuid4()}/almacen", json={"almacen_id": None}
    )
    assert r.status_code == 404
    assert r.json()["codigo"] == "NO_ENCONTRADO"


def test_AC_12_el_cuerpo_exige_almacen_id_y_no_admite_otros_campos(cliente_como, session):
    sup = cliente_como("Administrador")
    ruta = f"/api/usuarios/{_usuario(session, 'alm_hyl').id}/almacen"
    assert sup.patch(ruta, json={}).status_code == 422
    r = sup.patch(ruta, json={"almacen_id": None, "rol_id": str(uuid.uuid4())})
    assert r.status_code == 422


def test_AC_12_asignar_personal_no_cambia_el_rol_ni_los_permisos(cliente_como, session):
    objetivo = _usuario(session, "alm_hyl")
    rol_antes = objetivo.rol_id
    cliente_como("Administrador").patch(
        f"/api/usuarios/{objetivo.id}/almacen",
        json={"almacen_id": str(_almacen(session, "KEP").id)},
    )
    session.refresh(objetivo)
    assert objetivo.rol_id == rol_antes


# ------------------------------------------------- ALMACEN_CAMBIO (AC-13)


def test_AC_13_exigir_mismo_almacen_deja_pasar_si_coincide_o_no_se_indica(session):
    servicio = AccesoService(session)
    almacenista = _usuario(session, "alm_hyl")
    servicio.exigir_mismo_almacen(almacenista, almacenista.almacen_id)
    servicio.exigir_mismo_almacen(almacenista, None)


def test_AC_13_exigir_mismo_almacen_rechaza_con_el_almacen_nuevo(session):
    servicio = AccesoService(session)
    almacenista = _usuario(session, "alm_hyl")
    capturado_en = _almacen(session, "KEP").id
    with pytest.raises(AlmacenCambio) as error:
        servicio.exigir_mismo_almacen(almacenista, capturado_en)
    assert error.value.codigo == "ALMACEN_CAMBIO"
    assert error.value.detalles["almacen"]["clave"] == "HYL"
    assert error.value.detalles["almacen_captura_id"] == str(capturado_en)


def test_AC_13_exigir_mismo_almacen_sin_almacen_asignado_devuelve_almacen_nulo(session):
    servicio = AccesoService(session)
    almacenista = _usuario(session, "alm_hyl")
    almacenista.almacen_id = None
    with pytest.raises(AlmacenCambio) as error:
        servicio.exigir_mismo_almacen(almacenista, _almacen(session, "KEP").id)
    assert error.value.detalles["almacen"] is None


def test_AC_13_exigir_mismo_almacen_no_aplica_a_quien_opera_todos(session):
    # Con `almacenes.todos` el almacén se indica en cada vale (AC-06).
    AccesoService(session).exigir_mismo_almacen(
        _usuario(session, "supervisor"), _almacen(session, "KEP").id
    )


def test_AC_13_almacen_cambio_responde_409_con_codigo_estable(app, client):
    from fastapi import APIRouter

    router = APIRouter()

    @router.get("/_prueba/almacen-cambio")
    def _lanzar():
        raise AlmacenCambio(detalles={"almacen": None})

    app.include_router(router, prefix="/api")
    r = client.get("/api/_prueba/almacen-cambio")
    assert r.status_code == 409
    assert r.json()["codigo"] == "ALMACEN_CAMBIO"
    assert issubclass(AlmacenCambio, Exception) and not issubclass(AlmacenCambio, NoEncontrado)


# ----------------------------------------------------------- alta de usuarios


def test_AC_12_alta_de_un_almacenista_con_almacen(cliente_como, session):
    admin = cliente_como("Administrador")
    r = _alta(admin, session)
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["usuario"] == "persona.nueva"
    assert cuerpo["almacen"]["clave"] == "MID"
    assert cuerpo["activo"] is True and cuerpo["tiene_pin"] is False
    # Puede entrar con la contraseña inicial y opera su almacén.
    nuevo = TestClient(admin.app)
    entrada = nuevo.post(
        "/api/sesion", json={"usuario": "persona.nueva", "contrasena": "Clave-inicial-1"}
    )
    assert entrada.status_code == 200 and entrada.json()["almacen"]["clave"] == "MID"
    nuevo.close()


def test_AC_12_alta_con_usuario_repetido_responde_409_estable(cliente_como, session):
    admin = cliente_como("Administrador")
    assert _alta(admin, session).status_code == 201
    r = _alta(admin, session, nombre="Otra persona")
    assert r.status_code == 409
    assert r.json()["codigo"] == "USUARIO_EXISTE"
    # Mayúsculas y minúsculas cuentan como el mismo usuario.
    assert _alta(admin, session, usuario="PERSONA.NUEVA").status_code == 409


def test_RG_07_el_almacenista_lleva_almacen_y_quien_opera_todos_no(cliente_como, session):
    admin = cliente_como("Administrador")
    r = _alta(admin, session, almacen_id=None)
    assert r.status_code == 422 and r.json()["detalles"][0]["campo"] == "almacen_id"
    r = _alta(
        admin,
        session,
        usuario="otro.sup",
        rol_id=_rol_id(admin, "Administrador"),  # opera todos: no lleva almacén (AC-06)
        almacen_id=str(_almacen(session, "MID").id),
    )
    assert r.status_code == 422 and r.json()["detalles"][0]["campo"] == "almacen_id"
    r = _alta(
        admin, session, usuario="otro.comp", rol_id=_rol_id(admin, "Administrador"), almacen_id=None
    )
    assert r.status_code == 201 and r.json()["almacen"] is None
    # Compras ya no opera todos: es de un almacén (Kepler) y sin almacén se rechaza.
    r = _alta(admin, session, usuario="otro.c2", rol_id=_rol_id(admin, "Compras"), almacen_id=None)
    assert r.status_code == 422 and r.json()["detalles"][0]["campo"] == "almacen_id"


def test_AC_12_alta_con_almacen_inexistente_o_rol_inexistente(cliente_como, session):
    admin = cliente_como("Administrador")
    assert _alta(admin, session, almacen_id=str(uuid.uuid4())).status_code == 422
    assert _alta(admin, session, rol_id=str(uuid.uuid4())).status_code == 422


def test_AC_12_el_pin_solo_va_en_quien_puede_autorizar(cliente_como, session):
    admin = cliente_como("Administrador")
    r = _alta(admin, session, pin="4321")
    assert r.status_code == 422 and r.json()["detalles"][0]["campo"] == "pin"
    r = _alta(
        admin, session, usuario="otro.sup", rol_id=_rol_id(admin, "Supervisor"), almacen_id=None,
        pin="4321",
    )  # fmt: skip
    assert r.status_code == 201 and r.json()["tiene_pin"] is True
    r = _alta(
        admin, session, usuario="otro.sup2", rol_id=_rol_id(admin, "Supervisor"), almacen_id=None,
        contrasena="12345678", pin="12345678",
    )  # fmt: skip
    assert r.status_code == 422  # el PIN debe ser distinto de la contraseña
    assert _alta(admin, session, usuario="otro.x", contrasena="corta").status_code == 422
    assert _alta(admin, session, usuario="otro.y", rol_id=_rol_id(admin, "Supervisor"),
                 almacen_id=None, pin="abc").status_code == 422  # fmt: skip


# ---------------------------------------------------------- edición de usuarios


def test_AC_12_editar_nombre_rol_activo_y_almacen(cliente_como, session):
    admin = cliente_como("Administrador")
    objetivo = _usuario(session, "alm_hyl")
    r = admin.patch(
        f"/api/usuarios/{objetivo.id}",
        json={"nombre": "Nombre cambiado", "almacen_id": str(_almacen(session, "KEP").id)},
    )
    assert r.status_code == 200, r.text
    assert r.json()["nombre"] == "Nombre cambiado" and r.json()["almacen"]["clave"] == "KEP"
    r = admin.patch(f"/api/usuarios/{objetivo.id}", json={"activo": False})
    assert r.json()["activo"] is False
    (registro,) = _auditoria(session, "usuario.editar", objetivo.id)[:1]
    assert registro.antes["nombre"] != registro.despues["nombre"]
    assert registro.antes["almacen"]["codigo"] == "HYL"
    assert registro.despues["almacen"]["codigo"] == "KEP"
    assert len(_auditoria(session, "usuario.editar", objetivo.id)) == 2


def test_AC_12_cambiar_el_rol_a_uno_que_opera_todos_quita_el_almacen(cliente_como, session):
    admin = cliente_como("Administrador")
    objetivo = _usuario(session, "alm_hyl")
    r = admin.patch(
        f"/api/usuarios/{objetivo.id}", json={"rol_id": _rol_id(admin, "Administrador")}
    )
    assert r.status_code == 200 and r.json()["almacen"] is None
    assert r.json()["rol"]["nombre"] == "Administrador"
    # Y de vuelta a un rol que opera un almacén, hay que indicar cuál.
    de_vuelta = admin.patch(
        f"/api/usuarios/{objetivo.id}", json={"rol_id": _rol_id(admin, "Almacenista")}
    )
    assert de_vuelta.status_code == 422
    de_vuelta = admin.patch(
        f"/api/usuarios/{objetivo.id}",
        json={
            "rol_id": _rol_id(admin, "Almacenista"),
            "almacen_id": str(_almacen(session, "KEP").id),
        },
    )
    assert de_vuelta.status_code == 200 and de_vuelta.json()["almacen"]["clave"] == "KEP"


def test_AC_12_editar_no_admite_contrasenas_ni_hashes(cliente_como, session):
    admin = cliente_como("Administrador")
    objetivo = _usuario(session, "alm_hyl")
    hash_antes = objetivo.contrasena_hash
    for campo in ("contrasena", "contrasena_hash", "pin_hash", "intentos_fallidos"):
        r = admin.patch(f"/api/usuarios/{objetivo.id}", json={campo: "x"})
        assert r.status_code == 422, campo
    session.refresh(objetivo)
    assert objetivo.contrasena_hash == hash_antes


def test_AC_12_editar_un_usuario_que_no_existe_responde_404(cliente_como):
    r = cliente_como("Administrador").patch(f"/api/usuarios/{uuid.uuid4()}", json={"nombre": "x"})
    assert r.status_code == 404


def test_AC_12_el_filtro_de_usuarios(cliente_como, session):
    admin = cliente_como("Administrador")
    r = admin.get("/api/usuarios", params={"q": "hyl"}).json()
    assert [e["usuario"] for e in r["elementos"]] == ["alm_hyl", "sup_hyl"]
    r = admin.get("/api/usuarios", params={"rol_id": _rol_id(admin, "Administrador")}).json()
    assert [e["usuario"] for e in r["elementos"]] == ["admin"]
    r = admin.get("/api/usuarios", params={"activo": False}).json()
    assert r["total"] == 0
    assert admin.get("/api/usuarios", params={"q": "%"}).json()["total"] == 0  # el % no es comodín


# --------------------------------------------------- AC-09: último administrador


def test_AC_09_el_ultimo_administrador_no_se_inactiva(cliente_como, session):
    admin = cliente_como("Administrador")
    objetivo = _usuario(session, "admin")
    r = admin.patch(f"/api/usuarios/{objetivo.id}", json={"activo": False})
    assert r.status_code == 409
    assert r.json()["codigo"] == "ULTIMO_ADMINISTRADOR"
    session.refresh(objetivo)
    assert objetivo.activo is True


def test_AC_09_el_ultimo_administrador_no_pierde_el_rol(cliente_como, session):
    admin = cliente_como("Administrador")
    objetivo = _usuario(session, "admin")
    for rol in ("Almacenista", "Supervisor", "Compras"):
        r = admin.patch(f"/api/usuarios/{objetivo.id}", json={"rol_id": _rol_id(admin, rol)})
        assert r.status_code == 409, rol
        assert r.json()["codigo"] == "ULTIMO_ADMINISTRADOR"
    session.refresh(objetivo)
    assert objetivo.rol.nombre == "Administrador"


def _segundo_administrador(app, admin, session) -> tuple[TestClient, str]:
    """Crea otro administrador y devuelve su cliente (con sesión) y su id."""
    r = _alta(
        admin, session, usuario="segundo.admin", rol_id=_rol_id(admin, "Administrador"),
        almacen_id=None,
    )  # fmt: skip
    assert r.status_code == 201
    cliente = TestClient(app)
    entrada = cliente.post(
        "/api/sesion", json={"usuario": "segundo.admin", "contrasena": "Clave-inicial-1"}
    )
    assert entrada.status_code == 200
    return cliente, r.json()["id"]


def test_AC_09_con_otro_administrador_activo_ya_se_puede(app, cliente_como, session):
    admin = cliente_como("Administrador")
    segundo, segundo_id = _segundo_administrador(app, admin, session)
    objetivo = _usuario(session, "admin")
    assert segundo.patch(f"/api/usuarios/{objetivo.id}", json={"activo": False}).status_code == 200
    # Ahora el segundo es el último: no se puede inactivar.
    r = segundo.patch(f"/api/usuarios/{segundo_id}", json={"activo": False})
    assert r.status_code == 409 and r.json()["codigo"] == "ULTIMO_ADMINISTRADOR"
    segundo.close()


def test_AC_09_un_administrador_inactivo_no_cuenta(app, cliente_como, session):
    admin = cliente_como("Administrador")
    segundo, segundo_id = _segundo_administrador(app, admin, session)
    compras = _rol_id(segundo, "Compras")
    primero = _usuario(session, "admin")
    assert segundo.patch(f"/api/usuarios/{primero.id}", json={"activo": False}).status_code == 200
    r = segundo.patch(f"/api/usuarios/{segundo_id}", json={"rol_id": compras})
    assert r.status_code == 409
    segundo.close()


def test_AC_09_cambiar_el_nombre_del_ultimo_administrador_si_se_puede(cliente_como, session):
    admin = cliente_como("Administrador")
    objetivo = _usuario(session, "admin")
    r = admin.patch(f"/api/usuarios/{objetivo.id}", json={"nombre": "Admin renombrado"})
    assert r.status_code == 200


# ---------------------------------------------------- restablecer contraseña


def test_AC_12_restablecer_la_contrasena_permite_entrar_y_reinicia_bloqueos(
    app, cliente_como, session
):
    objetivo = _usuario(session, "alm_hyl")
    anonimo = TestClient(app)
    for _ in range(5):
        anonimo.post("/api/sesion", json={"usuario": "alm_hyl", "contrasena": "mala"})
    bloqueado = anonimo.post("/api/sesion", json={"usuario": "alm_hyl", "contrasena": "mala"})
    assert bloqueado.status_code == 429
    objetivo.pin_intentos_fallidos = 3

    r = cliente_como("Administrador").post(
        f"/api/usuarios/{objetivo.id}/contrasena", json={"contrasena": CONTRASENA_NUEVA}
    )
    assert r.status_code == 200
    assert r.json()["usuario"] == "alm_hyl"
    session.refresh(objetivo)
    assert objetivo.bloqueado_hasta is None and objetivo.intentos_fallidos == 0
    assert objetivo.pin_intentos_fallidos == 0 and objetivo.pin_bloqueado_hasta is None

    entrada = anonimo.post(
        "/api/sesion", json={"usuario": "alm_hyl", "contrasena": CONTRASENA_NUEVA}
    )
    assert entrada.status_code == 200
    # La contraseña anterior ya no sirve.
    vieja = TestClient(app).post(
        "/api/sesion", json={"usuario": "alm_hyl", "contrasena": "Prueba-2026!"}
    )
    assert vieja.status_code == 401
    anonimo.close()


def test_AC_12_restablecer_tambien_el_pin(cliente_como, session):
    admin = cliente_como("Administrador")
    objetivo = _usuario(session, "supervisor")
    pin_antes = objetivo.pin_hash
    r = admin.post(
        f"/api/usuarios/{objetivo.id}/contrasena",
        json={"contrasena": CONTRASENA_NUEVA, "pin": "9876"},
    )
    assert r.status_code == 200 and r.json()["tiene_pin"] is True
    session.refresh(objetivo)
    assert objetivo.pin_hash != pin_antes
    from app.seguridad import verificar_secreto

    assert verificar_secreto("9876", objetivo.pin_hash)
    # A quien no puede autorizar no se le pone PIN.
    almacenista = _usuario(session, "alm_hyl")
    r = admin.post(
        f"/api/usuarios/{almacenista.id}/contrasena",
        json={"contrasena": CONTRASENA_NUEVA, "pin": "9876"},
    )
    assert r.status_code == 422


# ------------------------------------------------- secretos fuera de todo


def test_AC_12_ninguna_respuesta_trae_hashes_ni_contrasenas(cliente_como, session):
    admin = cliente_como("Administrador")
    objetivo = _usuario(session, "supervisor")
    textos = [
        admin.get("/api/usuarios", params={"tamano": 200}).text,
        admin.get(f"/api/usuarios/{objetivo.id}").text,
        admin.get("/api/roles").text,
        cliente_como("Supervisor").get("/api/personal", params={"tamano": 200}).text,
        _alta(admin, session).text,
        admin.patch(f"/api/usuarios/{objetivo.id}", json={"nombre": "Otro"}).text,
        admin.post(
            f"/api/usuarios/{objetivo.id}/contrasena",
            json={"contrasena": CONTRASENA_NUEVA, "pin": "9876"},
        ).text,
    ]
    prohibidos = ("hash", "$argon2", CONTRASENA_NUEVA, "Clave-inicial-1", "Prueba-2026!")
    for texto in textos:
        for fragmento in prohibidos:
            assert fragmento not in texto, fragmento
        for llave in ("contrasena", "pin_hash", "contrasena_hash"):
            assert f'"{llave}"' not in texto
    assert '"tiene_pin"' in textos[0]


def test_AC_10_la_auditoria_guarda_antes_y_despues_sin_secretos(cliente_como, session):
    admin = cliente_como("Administrador")
    r = _alta(admin, session, contrasena="Clave-inicial-1")
    nuevo = uuid.UUID(r.json()["id"])
    admin.post(f"/api/usuarios/{nuevo}/contrasena", json={"contrasena": CONTRASENA_NUEVA})
    admin.patch(f"/api/usuarios/{nuevo}", json={"rol_id": _rol_id(admin, "Compras")})
    registros = list(session.scalars(select(Auditoria).where(Auditoria.entidad_id == str(nuevo))))
    assert {r.accion for r in registros} == {
        "usuario.crear",
        "usuario.restablecer",
        "usuario.editar",
    }
    texto = json.dumps([[r.antes, r.despues] for r in registros])
    for secreto in ("Clave-inicial-1", CONTRASENA_NUEVA, "argon2"):
        assert secreto not in texto
    editar = next(r for r in registros if r.accion == "usuario.editar")
    assert editar.antes["rol"]["nombre"] == "Almacenista"
    assert editar.despues["rol"]["nombre"] == "Compras"
    assert editar.usuario_id == _usuario(session, "admin").id


# -------------------------------------------------------------- roles


def test_AC_12_la_lista_de_roles_trae_los_cinco_iniciales(cliente_como):
    roles = cliente_como("Administrador").get("/api/roles").json()
    assert {r["nombre"] for r in roles} >= {
        "Administrador",
        "Almacenista",
        "Supervisor",
        "Compras",
        "Recursos Humanos",
    }
    admin = next(r for r in roles if r["nombre"] == "Administrador")
    assert admin["protegido"] is True
    assert set(admin) == {"id", "nombre", "descripcion", "activo", "protegido"}


def test_AC_12_los_datos_de_prueba_dan_asignar_personal_al_supervisor_y_no_a_otros(
    session, cliente_como
):
    permisos = {
        rol: set(cliente_como(rol).get("/api/sesion").json()["permisos"])
        for rol in ("Supervisor", "Almacenista", "Compras", "Recursos Humanos")
    }
    assert P.ALMACENES_ASIGNAR_PERSONAL in permisos["Supervisor"]
    for rol in ("Almacenista", "Compras", "Recursos Humanos"):
        assert P.ALMACENES_ASIGNAR_PERSONAL not in permisos[rol]
    assert P.ACCESO_ADMINISTRAR not in permisos["Supervisor"]
