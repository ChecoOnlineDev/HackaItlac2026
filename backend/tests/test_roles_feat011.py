"""FEAT-011, sección D: permisos nuevos y roles iniciales (AC-30 a AC-34).

Cada prueba lleva en su nombre la regla que cubre.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.modulos.acceso import datos_prueba as semilla
from app.modulos.acceso.dependencias_permisos import REQUIERE
from app.modulos.acceso.models import Rol
from app.modulos.acceso.permisos import CATALOGO, CLAVES, CLAVES_DISPONIBLES, P
from app.modulos.acceso.repository import RolRepository
from tests.conftest import iniciar_sesion_en

NUEVOS = {
    P.BITACORA_VER,
    P.RESGUARDO_VER,
    P.INVENTARIO_IMPORTAR,
    P.CATALOGO_LIMITES,
    P.PIEZAS_MARCAR_ESTADO,
    P.ACCESO_USUARIOS,
    P.ACCESO_ROLES,
    P.AUDITORIA_VER,
}
SIN_USO = {
    P.REPORTES_VALOR_INVENTARIO,
    P.INVENTARIO_MINIMOS,
    P.PIEZAS_DAR_DE_BAJA,
    P.REVISION_VER,
}
CATEGORIA = {
    "nombre": "Prueba de límites",
    "tipo": "HERRAMIENTA",
    "control": "CANTIDAD",
    "retornable": False,
}


def _roles(cliente) -> dict[str, dict]:
    r = cliente.get("/api/roles")
    assert r.status_code == 200, r.text
    return {x["nombre"]: x for x in r.json()}


def _permisos_de(cliente_como, rol: str) -> set[str]:
    return set(cliente_como(rol).get("/api/sesion").json()["permisos"])


def _en_base(session, nombre: str) -> set[str]:
    rol = session.scalar(select(Rol).where(Rol.nombre == nombre))
    return RolRepository(session).permisos(rol.id)


# ---------------------------------------------------------------------- AC-30


def test_AC_24_el_catalogo_ofrece_los_permisos_nuevos_con_descripcion_y_grupo(cliente_como):
    r = cliente_como("Administrador").get("/api/permisos")
    permisos = {p["clave"]: p for p in r.json()}
    assert NUEVOS <= set(permisos)
    for clave in NUEVOS:
        assert permisos[clave]["descripcion"] and permisos[clave]["grupo"]
        assert permisos[clave]["disponible"] is True
    assert permisos[P.BITACORA_VER]["grupo"] == "inventario"
    assert permisos[P.ACCESO_ROLES]["grupo"] == "acceso"
    # Los cuatro de 8.3 sin uso se marcan como no disponibles en esta versión.
    assert {c for c, p in permisos.items() if not p["disponible"]} == SIN_USO


def test_AC_24_un_permiso_de_accion_nuevo_exige_el_de_ver_que_necesita(cliente_como):
    admin = cliente_como("Administrador")
    for clave in (P.BITACORA_VER, P.RESGUARDO_VER, P.CATALOGO_LIMITES, P.INVENTARIO_IMPORTAR):
        assert REQUIERE[clave]
        r = admin.post("/api/roles", json={"nombre": f"Solo {clave}", "permisos": [clave]})
        assert r.status_code == 422, clave
    r = admin.post(
        "/api/roles",
        json={
            "nombre": "Con limites",
            "permisos": [P.CATALOGO_LIMITES, P.CATALOGO_ADMINISTRAR, P.CATALOGO_VER],
        },
    )
    assert r.status_code == 201, r.text


def test_AC_24_usuarios_y_roles_son_permisos_separados(app, crear_usuario):
    solo_usuarios = crear_usuario({P.ACCESO_USUARIOS}, almacen="KEP")
    solo_roles = crear_usuario({P.ACCESO_ROLES}, almacen="KEP")
    con_u, con_r = TestClient(app), TestClient(app)
    assert iniciar_sesion_en(con_u, solo_usuarios).status_code == 200
    assert iniciar_sesion_en(con_r, solo_roles).status_code == 200
    assert con_u.get("/api/usuarios").status_code == 200
    assert con_u.get("/api/roles").status_code == 403
    assert con_u.get("/api/permisos").status_code == 403
    assert con_r.get("/api/roles").status_code == 200
    assert con_r.get("/api/permisos").status_code == 200
    assert con_r.get("/api/usuarios").status_code == 403


def test_AC_24_acceso_administrar_ya_no_abre_usuarios_ni_roles(app, crear_usuario):
    cliente = TestClient(app)
    usuario = crear_usuario({P.ACCESO_ADMINISTRAR}, almacen="KEP")
    assert iniciar_sesion_en(cliente, usuario).status_code == 200
    assert cliente.get("/api/usuarios").status_code == 403
    assert cliente.get("/api/roles").status_code == 403


def test_AC_24_cambiar_limites_pide_catalogo_limites_ademas_de_administrar(cliente_como):
    supervisor, compras = cliente_como("Supervisor"), cliente_como("Compras")
    con_limite = CATEGORIA | {"limite_cantidad": 2}
    r = supervisor.post("/api/categorias", json=con_limite)
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"
    # Sin tocar límites, el Supervisor sigue administrando el catálogo.
    assert supervisor.post("/api/categorias", json=CATEGORIA).status_code == 201
    creada = compras.post("/api/categorias", json=con_limite | {"nombre": "Con límite"})
    assert creada.status_code == 201, creada.text
    categoria_id = creada.json()["id"]
    r = supervisor.patch(f"/api/categorias/{categoria_id}", json={"limite_cantidad": 5})
    assert r.status_code == 403
    r = supervisor.patch(f"/api/categorias/{categoria_id}", json={"limite_cantidad": 2})
    assert r.status_code == 200  # el mismo valor no es un cambio
    r = compras.patch(f"/api/categorias/{categoria_id}", json={"limite_cantidad": 5})
    assert r.status_code == 200 and r.json()["limite_cantidad"] == 5


# ---------------------------------------------------------------------- AC-31


def test_AC_25_los_roles_iniciales_traen_los_permisos_que_dice_la_seccion_8_2(cliente_como):
    supervisor = _permisos_de(cliente_como, "Supervisor")
    almacenista = _permisos_de(cliente_como, "Almacenista")
    compras = _permisos_de(cliente_como, "Compras")
    rh = _permisos_de(cliente_como, "Recursos Humanos")
    admin = _permisos_de(cliente_como, "Administrador")
    assert P.CATALOGO_LIMITES not in supervisor
    assert {P.TRASPASOS_RECIBIR, P.BITACORA_VER, P.RESGUARDO_VER} <= supervisor
    assert {P.TRASPASOS_RECIBIR, P.RESGUARDO_VER, P.BITACORA_VER} <= almacenista
    assert {P.INVENTARIO_IMPORTAR, P.BITACORA_VER, P.CATALOGO_LIMITES} <= compras
    assert P.VALES_VER in rh
    assert admin == set(CLAVES_DISPONIBLES) and NUEVOS <= admin
    # Los cuatro permisos sin uso no se asignan a nadie.
    for permisos in (supervisor, almacenista, compras, rh, admin):
        assert not permisos & SIN_USO


def test_AC_25_los_permisos_sin_uso_siguen_en_el_catalogo_pero_no_estan_disponibles():
    assert SIN_USO <= CLAVES and not SIN_USO & CLAVES_DISPONIBLES
    assert all(not p.disponible for p in CATALOGO if p.clave in SIN_USO)


# ---------------------------------------------------------------------- AC-32


@pytest.mark.parametrize(
    "clave",
    [
        P.ACCESO_ADMINISTRAR,
        P.ACCESO_USUARIOS,
        P.ACCESO_ROLES,
        P.ALMACENES_TODOS,
        P.ALMACENES_ADMINISTRAR,
    ],
)
def test_AC_26_el_administrador_no_pierde_los_permisos_protegidos(cliente_como, clave):
    admin = cliente_como("Administrador")
    rol = _roles(admin)["Administrador"]
    r = admin.put(
        f"/api/roles/{rol['id']}/permisos",
        json={"permisos": sorted(CLAVES_DISPONIBLES - {clave})},
    )
    assert r.status_code == 409 and r.json()["codigo"] == "ROL_PROTEGIDO"
    assert clave in r.json()["mensaje"]
    assert clave in admin.get(f"/api/roles/{rol['id']}").json()["permisos"]


def test_AC_26_otro_permiso_del_administrador_si_se_puede_quitar_y_volver_a_poner(cliente_como):
    admin = cliente_como("Administrador")
    rol = _roles(admin)["Administrador"]
    sin = sorted(CLAVES_DISPONIBLES - {P.REPORTES_CONSUMO})
    r = admin.put(f"/api/roles/{rol['id']}/permisos", json={"permisos": sin})
    assert r.status_code == 200, r.text
    r = admin.put(f"/api/roles/{rol['id']}/permisos", json={"permisos": sorted(CLAVES_DISPONIBLES)})
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------------- AC-33


def test_AC_27_volver_a_correr_los_datos_de_prueba_no_pisa_lo_editado_en_roles(
    cliente_como, session
):
    admin = cliente_como("Administrador")
    almacenista = _roles(admin)["Almacenista"]
    editados = (set(almacenista["permisos"]) - {P.COMPRAS_SOLICITAR, P.TABLERO_VER}) | {
        P.REPORTES_EXISTENCIAS
    }
    r = admin.put(f"/api/roles/{almacenista['id']}/permisos", json={"permisos": sorted(editados)})
    assert r.status_code == 200, r.text
    semilla.cargar(session)
    assert _en_base(session, "Almacenista") == editados
    # Repetible: otra corrida deja lo mismo.
    semilla.cargar(session)
    assert _en_base(session, "Almacenista") == editados


def test_AC_27_la_semilla_agrega_los_permisos_nuevos_que_le_faltan_a_un_rol_inicial(session):
    supervisor = session.scalar(select(Rol).where(Rol.nombre == "Supervisor"))
    repo = RolRepository(session)
    repo.reemplazar_permisos(supervisor.id, repo.permisos(supervisor.id) - {P.BITACORA_VER})
    semilla.cargar(session)
    assert P.BITACORA_VER in _en_base(session, "Supervisor")


def test_AC_27_la_opcion_explicita_restablece_los_roles_iniciales(cliente_como, session):
    admin = cliente_como("Administrador")
    almacenista = _roles(admin)["Almacenista"]
    r = admin.put(
        f"/api/roles/{almacenista['id']}/permisos", json={"permisos": [P.TRABAJADORES_VER]}
    )
    assert r.status_code == 200, r.text
    semilla.cargar(session)
    assert _en_base(session, "Almacenista") == {P.TRABAJADORES_VER}
    semilla.cargar(session, restablecer_roles=True)
    assert _en_base(session, "Almacenista") == semilla.PERMISOS_INICIALES["Almacenista"]


# ---------------------------------------------------------------------- AC-34


def test_AC_28_quien_recibe_traspasos_se_cambia_desde_roles(cliente_como):
    admin = cliente_como("Administrador")
    roles = _roles(admin)
    sup, alm = roles["Supervisor"], roles["Almacenista"]
    # Solo el almacenista: se le quita al supervisor.
    r = admin.put(
        f"/api/roles/{sup['id']}/permisos",
        json={"permisos": sorted(set(sup["permisos"]) - {P.TRASPASOS_RECIBIR})},
    )
    assert r.status_code == 200, r.text
    assert P.TRASPASOS_RECIBIR not in _permisos_de(cliente_como, "Supervisor")
    assert P.TRASPASOS_RECIBIR in _permisos_de(cliente_como, "Almacenista")
    assert cliente_como("Supervisor").get("/api/traspasos/por-recibir").status_code == 403
    assert cliente_como("Almacenista").get("/api/traspasos/por-recibir").status_code == 200
    # Solo el supervisor: se le quita al almacenista y se le devuelve al supervisor.
    r = admin.put(
        f"/api/roles/{alm['id']}/permisos",
        json={"permisos": sorted(set(alm["permisos"]) - {P.TRASPASOS_RECIBIR})},
    )
    assert r.status_code == 200, r.text
    r = admin.put(f"/api/roles/{sup['id']}/permisos", json={"permisos": sup["permisos"]})
    assert r.status_code == 200
    assert cliente_como("Almacenista").get("/api/traspasos/por-recibir").status_code == 403
    assert cliente_como("Supervisor").get("/api/traspasos/por-recibir").status_code == 200
