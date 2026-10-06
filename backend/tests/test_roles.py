"""Pruebas de FEAT-006: roles y permisos editables (AC-08 a AC-11) y el catálogo (AC-01).

Cada prueba lleva en su nombre la regla que cubre.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.modulos.acceso.exceptions import UltimoAdministrador
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import CLAVES, P
from app.modulos.acceso.repository import UsuarioRepository
from app.modulos.acceso.service_roles import RolAdminService
from app.modulos.almacenes.repository import AlmacenRepository
from app.modulos.auditoria.models import Auditoria
from tests.conftest import UsuarioPrueba, iniciar_sesion_en

CLAVE_NUEVA = "Clave-inicial-1"


def _roles(cliente: TestClient) -> dict[str, dict]:
    r = cliente.get("/api/roles")
    assert r.status_code == 200, r.text
    return {x["nombre"]: x for x in r.json()}


def _crear_rol(cliente: TestClient, nombre="Rol nuevo", permisos=(), **extra):
    return cliente.post(
        "/api/roles",
        json={"nombre": nombre, "permisos": list(permisos), "descripcion": None} | extra,
    )


def _crear_usuario(
    cliente: TestClient, session, rol_id: str, nombre_usuario="usuario.nuevo", **extra
):
    cuerpo = {
        "nombre": "Usuario Nuevo",
        "usuario": nombre_usuario,
        "contrasena": CLAVE_NUEVA,
        "rol_id": rol_id,
        "almacen_id": str(AlmacenRepository(session).get_by_clave("KEP").id),
    } | extra
    r = cliente.post("/api/usuarios", json=cuerpo)
    assert r.status_code == 201, r.text
    return r.json()


def _entrar(app, nombre_usuario: str) -> TestClient:
    cliente = TestClient(app)
    r = iniciar_sesion_en(cliente, UsuarioPrueba(nombre_usuario, CLAVE_NUEVA))
    assert r.status_code == 200, r.text
    return cliente


def _auditoria(session, accion: str, entidad_id) -> list[Auditoria]:
    return list(
        session.scalars(
            select(Auditoria)
            .where(Auditoria.accion == accion, Auditoria.entidad_id == str(entidad_id))
            .order_by(Auditoria.creado_en)
        )
    )


# ------------------------------------------------------------------ catálogo (AC-01)


def test_AC_01_el_catalogo_de_permisos_trae_todas_las_claves_y_marca_los_reservados(cliente_como):
    r = cliente_como("Administrador").get("/api/permisos")
    assert r.status_code == 200
    permisos = {p["clave"]: p for p in r.json()}
    assert set(permisos) == set(CLAVES)
    assert permisos[P.CATALOGO_COSTOS]["es_de_informacion"] is True
    assert permisos[P.TRABAJADORES_VER_DATOS_PERSONALES]["es_de_informacion"] is True
    assert permisos[P.ENTREGAS_CREAR]["es_de_informacion"] is False
    assert permisos[P.ENTREGAS_CREAR]["modulo"] == "entregas"
    assert P.TRABAJADORES_VER in permisos[P.ENTREGAS_CREAR]["requiere"]


def test_AC_07_el_catalogo_no_ofrece_permisos_prohibidos(cliente_como):
    claves = {p["clave"] for p in cliente_como("Administrador").get("/api/permisos").json()}
    for clave in claves:
        assert not any(
            palabra in clave
            for palabra in ("movimientos.editar", "movimientos.borrar", "autorizarse")
        )
    assert not any(c.startswith(("movimientos.", "vales.costos")) for c in claves)


# ------------------------------------------------------------------ lectura


def test_AC_08_la_lista_de_roles_trae_usuarios_permisos_y_marcas(cliente_como):
    roles = _roles(cliente_como("Administrador"))
    assert set(roles) >= {
        "Administrador",
        "Almacenista",
        "Supervisor",
        "Compras",
        "Recursos Humanos",
    }
    admin = roles["Administrador"]
    assert admin["protegido"] is True and admin["inicial"] is True
    assert admin["total_permisos"] == len(CLAVES)
    assert admin["total_usuarios"] >= 1
    assert roles["Almacenista"]["protegido"] is False and roles["Almacenista"]["inicial"] is True


def test_AC_08_ver_un_rol_trae_sus_permisos_y_404_si_no_existe(cliente_como):
    cliente = cliente_como("Administrador")
    rol = _roles(cliente)["Recursos Humanos"]
    r = cliente.get(f"/api/roles/{rol['id']}")
    assert r.status_code == 200
    assert P.TRABAJADORES_VER_DATOS_PERSONALES in r.json()["permisos"]
    assert cliente.get("/api/roles/00000000-0000-7000-8000-000000000000").status_code == 404


# ------------------------------------------------------------------ AC-08: crear y editar


def test_AC_08_el_administrador_crea_un_rol_con_permisos(cliente_como, session):
    cliente = cliente_como("Administrador")
    r = _crear_rol(
        cliente,
        "Jefe de turno",
        [P.CATALOGO_VER, P.CATALOGO_COSTOS],
        descripcion="  Revisa costos ",
    )
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["nombre"] == "Jefe de turno"
    assert cuerpo["descripcion"] == "Revisa costos"
    assert cuerpo["permisos"] == sorted([P.CATALOGO_VER, P.CATALOGO_COSTOS])
    assert cuerpo["protegido"] is False and cuerpo["inicial"] is False
    assert cuerpo["total_usuarios"] == 0 and cuerpo["total_permisos"] == 2
    asientos = _auditoria(session, "rol.crear", cuerpo["id"])
    assert len(asientos) == 1
    assert asientos[0].despues["nombre"] == "Jefe de turno"


def test_AC_08_un_nombre_repetido_responde_409_rol_existe(cliente_como):
    cliente = cliente_como("Administrador")
    assert _crear_rol(cliente, "Jefe de turno").status_code == 201
    for nombre in ("Jefe de turno", "jefe de turno", "Almacenista"):
        r = _crear_rol(cliente, nombre)
        assert r.status_code == 409 and r.json()["codigo"] == "ROL_EXISTE", nombre


def test_AC_01_una_clave_que_no_existe_se_rechaza_con_422(cliente_como):
    cliente = cliente_como("Administrador")
    r = _crear_rol(cliente, "Rol raro", ["magia.hacer"])
    assert r.status_code == 422 and r.json()["codigo"] == "DATOS_INVALIDOS"
    rol = _crear_rol(cliente, "Rol normal").json()
    r = cliente.put(f"/api/roles/{rol['id']}/permisos", json={"permisos": ["magia.hacer"]})
    assert r.status_code == 422


def test_AC_08_un_permiso_de_accion_exige_el_de_ver_su_modulo(cliente_como):
    cliente = cliente_como("Administrador")
    r = _crear_rol(cliente, "Sin ver", [P.ENTREGAS_CREAR])
    assert r.status_code == 422
    assert "necesita también" in r.json()["mensaje"]
    rol = _crear_rol(cliente, "Con ver", [P.TRABAJADORES_VER]).json()
    r = cliente.put(
        f"/api/roles/{rol['id']}/permisos",
        json={"permisos": [P.TRABAJADORES_VER, P.TRABAJADORES_ADMINISTRAR]},
    )
    assert r.status_code == 200
    r = cliente.put(
        f"/api/roles/{rol['id']}/permisos", json={"permisos": [P.TRABAJADORES_ADMINISTRAR]}
    )
    assert r.status_code == 422


def test_AC_08_los_cinco_roles_iniciales_cumplen_las_dependencias_de_ver(cliente_como):
    """Sin tocar nada se pueden guardar tal cual: la lista de cada rol inicial es válida."""
    cliente = cliente_como("Administrador")
    for rol in _roles(cliente).values():
        if not rol["inicial"]:
            continue
        actuales = cliente.get(f"/api/roles/{rol['id']}").json()["permisos"]
        r = cliente.put(f"/api/roles/{rol['id']}/permisos", json={"permisos": actuales})
        assert r.status_code == 200, (rol["nombre"], r.text)


def test_AC_08_editar_nombre_y_descripcion_deja_registro(cliente_como, session):
    cliente = cliente_como("Administrador")
    rol = _crear_rol(cliente, "Provisional").json()
    r = cliente.patch(
        f"/api/roles/{rol['id']}", json={"nombre": "Definitivo", "descripcion": "Ya con nombre"}
    )
    assert r.status_code == 200 and r.json()["nombre"] == "Definitivo"
    asiento = _auditoria(session, "rol.editar", rol["id"])[0]
    assert asiento.antes["nombre"] == "Provisional"
    assert asiento.despues["nombre"] == "Definitivo"
    assert _crear_rol(cliente, "Otro").status_code == 201
    r = cliente.patch(f"/api/roles/{rol['id']}", json={"nombre": "Otro"})
    assert r.status_code == 409 and r.json()["codigo"] == "ROL_EXISTE"
    r = cliente.patch(f"/api/roles/{rol['id']}", json={"protegido": True})
    assert r.status_code == 422


def test_AC_09_los_roles_iniciales_conservan_su_nombre(cliente_como):
    cliente = cliente_como("Administrador")
    r = cliente.patch(f"/api/roles/{_roles(cliente)['Compras']['id']}", json={"nombre": "Otro"})
    assert r.status_code == 409 and r.json()["codigo"] == "ROL_PROTEGIDO"


# ------------------------------------------------------------------ AC-10: aplica de inmediato


def test_AC_08_un_rol_nuevo_sin_permisos_no_ve_ningun_modulo(app, cliente_como, session):
    admin = cliente_como("Administrador")
    rol = _crear_rol(admin, "Sin nada").json()
    _crear_usuario(admin, session, rol["id"])
    cliente = _entrar(app, "usuario.nuevo")
    assert cliente.get("/api/sesion").json()["permisos"] == []
    for ruta in ("/api/categorias", "/api/trabajadores", "/api/usuarios", "/api/roles"):
        r = cliente.get(ruta)
        assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO", ruta


def test_AC_10_un_cambio_de_permisos_aplica_en_la_siguiente_peticion(app, cliente_como, session):
    admin = cliente_como("Administrador")
    rol = _crear_rol(admin, "Consulta").json()
    _crear_usuario(admin, session, rol["id"])
    cliente = _entrar(app, "usuario.nuevo")
    assert cliente.get("/api/categorias").status_code == 403

    r = admin.put(f"/api/roles/{rol['id']}/permisos", json={"permisos": [P.CATALOGO_VER]})
    assert r.status_code == 200
    assert cliente.get("/api/categorias").status_code == 200  # sin cerrar sesión
    assert cliente.get("/api/sesion").json()["permisos"] == [P.CATALOGO_VER]

    r = admin.put(f"/api/roles/{rol['id']}/permisos", json={"permisos": []})
    assert r.status_code == 200
    assert cliente.get("/api/categorias").status_code == 403


def test_AC_10_los_datos_de_informacion_dejan_de_enviarse_al_quitar_el_permiso(
    app, cliente_como, session
):
    """CURP y NSS (trabajadores.ver_datos_personales) siguen al permiso del rol."""
    admin = cliente_como("Administrador")
    rol = _crear_rol(admin, "Consulta RH", [P.TRABAJADORES_VER]).json()
    _crear_usuario(admin, session, rol["id"])
    cliente = _entrar(app, "usuario.nuevo")
    trabajadores = cliente.get("/api/trabajadores")
    assert trabajadores.status_code == 200
    assert "curp" not in str(trabajadores.json())
    admin.put(
        f"/api/roles/{rol['id']}/permisos",
        json={"permisos": [P.TRABAJADORES_VER, P.TRABAJADORES_VER_DATOS_PERSONALES]},
    )
    assert cliente.get("/api/trabajadores").status_code == 200
    assert cliente.get("/api/sesion").json()["permisos"] == sorted(
        [P.TRABAJADORES_VER, P.TRABAJADORES_VER_DATOS_PERSONALES]
    )


def test_AC_10_el_cambio_de_permisos_queda_con_antes_y_despues(cliente_como, session):
    admin = cliente_como("Administrador")
    rol = _crear_rol(admin, "Auditado", [P.CATALOGO_VER]).json()
    admin.put(
        f"/api/roles/{rol['id']}/permisos",
        json={"permisos": [P.CATALOGO_VER, P.CATALOGO_ADMINISTRAR]},
    )
    asiento = _auditoria(session, "rol.permisos", rol["id"])[0]
    assert asiento.antes["permisos"] == [P.CATALOGO_VER]
    assert sorted(asiento.despues["permisos"]) == sorted([P.CATALOGO_VER, P.CATALOGO_ADMINISTRAR])
    assert asiento.despues["agregados"] == [P.CATALOGO_ADMINISTRAR]
    assert asiento.despues["quitados"] == []
    assert asiento.usuario_id is not None


def test_AC_10_guardar_la_misma_lista_no_deja_registro(cliente_como, session):
    admin = cliente_como("Administrador")
    rol = _crear_rol(admin, "Igual", [P.CATALOGO_VER]).json()
    r = admin.put(f"/api/roles/{rol['id']}/permisos", json={"permisos": [P.CATALOGO_VER]})
    assert r.status_code == 200
    assert _auditoria(session, "rol.permisos", rol["id"]) == []


# ------------------------------------------------------------------ AC-09: protecciones


def test_AC_09_el_administrador_no_pierde_acceso_administrar(cliente_como, session):
    admin = cliente_como("Administrador")
    rol = _roles(admin)["Administrador"]
    otros = sorted(CLAVES - {P.ACCESO_ADMINISTRAR})
    r = admin.put(f"/api/roles/{rol['id']}/permisos", json={"permisos": otros})
    assert r.status_code == 409 and r.json()["codigo"] == "ROL_PROTEGIDO"
    assert P.ACCESO_ADMINISTRAR in admin.get(f"/api/roles/{rol['id']}").json()["permisos"]


def test_AC_09_el_administrador_se_puede_ajustar_sin_quitarle_ese_permiso(cliente_como):
    admin = cliente_como("Administrador")
    rol = _roles(admin)["Administrador"]
    r = admin.put(
        f"/api/roles/{rol['id']}/permisos",
        json={"permisos": sorted(CLAVES - {P.TABLERO_VER})},
    )
    assert r.status_code == 200
    assert P.TABLERO_VER not in r.json()["permisos"]


def test_AC_09_el_administrador_no_se_inactiva_ni_se_elimina(cliente_como):
    admin = cliente_como("Administrador")
    rol = _roles(admin)["Administrador"]
    r = admin.patch(f"/api/roles/{rol['id']}", json={"activo": False})
    assert r.status_code == 409 and r.json()["codigo"] == "ROL_PROTEGIDO"
    r = admin.delete(f"/api/roles/{rol['id']}")
    assert r.status_code == 409 and r.json()["codigo"] == "ROL_PROTEGIDO"


def test_AC_09_los_roles_iniciales_no_se_eliminan(cliente_como):
    """Sin usuarios asignados tampoco: nacen con el sistema (AC-03)."""
    admin = cliente_como("Administrador")
    # Recursos Humanos tiene un usuario de prueba; se prueba con el rol vacío tras reasignarlo.
    for nombre in ("Almacenista", "Supervisor", "Compras", "Recursos Humanos"):
        r = admin.delete(f"/api/roles/{_roles(admin)[nombre]['id']}")
        assert r.status_code == 409, nombre
        assert r.json()["codigo"] in ("ROL_PROTEGIDO", "ROL_EN_USO"), nombre


def test_AC_09_nadie_se_quita_a_si_mismo_el_acceso_a_administrar(app, cliente_como, session):
    admin = cliente_como("Administrador")
    rol = _crear_rol(admin, "Admin de turno", [P.ACCESO_ADMINISTRAR]).json()
    _crear_usuario(admin, session, rol["id"])
    yo = _entrar(app, "usuario.nuevo")
    r = yo.put(f"/api/roles/{rol['id']}/permisos", json={"permisos": []})
    assert r.status_code == 409 and r.json()["codigo"] == "AUTO_BLOQUEO"
    r = yo.patch(f"/api/roles/{rol['id']}", json={"activo": False})
    assert r.status_code == 409 and r.json()["codigo"] == "ROL_EN_USO"
    # Otro administrador sí puede quitarle ese permiso a ese rol, y su sesión lo nota al instante.
    r = admin.put(f"/api/roles/{rol['id']}/permisos", json={"permisos": []})
    assert r.status_code == 200
    assert yo.get("/api/roles").status_code == 403


def test_AC_09_no_se_quita_acceso_administrar_si_no_queda_otro_administrador(session):
    """El servicio lo rechaza aunque lo intente alguien de fuera del rol (por ejemplo, otra
    petición simultánea): siempre queda un administrador activo."""
    from app.modulos.acceso.models import Rol

    servicio = RolAdminService(session)
    usuarios = UsuarioRepository(session)
    rol = servicio.roles.add(Rol(nombre="Único admin"))
    servicio.roles.reemplazar_permisos(rol.id, {P.ACCESO_ADMINISTRAR})
    unico = usuarios.get_by_usuario("admin")
    assert unico is not None
    unico.rol_id = rol.id
    unico.rol = rol
    session.flush()
    actor = usuarios.get_by_usuario("almacenista")
    assert actor is not None
    with pytest.raises(UltimoAdministrador):
        servicio.reemplazar_permisos(actor, rol.id, [])


def test_AC_09_el_unico_administrador_no_se_inactiva_ni_cambia_de_rol(cliente_como, session):
    admin = cliente_como("Administrador")
    yo = UsuarioRepository(session).get_by_usuario("admin")
    r = admin.patch(f"/api/usuarios/{yo.id}", json={"activo": False})
    assert r.status_code == 409 and r.json()["codigo"] == "ULTIMO_ADMINISTRADOR"
    r = admin.patch(f"/api/usuarios/{yo.id}", json={"rol_id": _roles(admin)["Compras"]["id"]})
    assert r.status_code == 409 and r.json()["codigo"] == "ULTIMO_ADMINISTRADOR"


# ------------------------------------------------------------------ AC-11: rol en uso


def test_AC_11_un_rol_con_usuarios_no_se_inactiva_ni_se_elimina(cliente_como, session):
    admin = cliente_como("Administrador")
    rol = _crear_rol(admin, "En uso", [P.CATALOGO_VER]).json()
    usuario = _crear_usuario(admin, session, rol["id"])
    assert _roles(admin)["En uso"]["total_usuarios"] == 1
    r = admin.patch(f"/api/roles/{rol['id']}", json={"activo": False})
    assert r.status_code == 409 and r.json()["codigo"] == "ROL_EN_USO"
    r = admin.delete(f"/api/roles/{rol['id']}")
    assert r.status_code == 409 and r.json()["codigo"] == "ROL_EN_USO"

    # Aunque el usuario esté inactivo, sigue asignado.
    admin.patch(f"/api/usuarios/{usuario['id']}", json={"activo": False})
    assert admin.delete(f"/api/roles/{rol['id']}").status_code == 409

    # Reasignado, ya se puede.
    r = admin.patch(
        f"/api/usuarios/{usuario['id']}",
        json={"rol_id": _roles(admin)["Compras"]["id"]},
    )
    assert r.status_code == 200, r.text
    assert admin.patch(f"/api/roles/{rol['id']}", json={"activo": False}).status_code == 200
    r = admin.delete(f"/api/roles/{rol['id']}")
    assert r.status_code == 204
    assert admin.get(f"/api/roles/{rol['id']}").status_code == 404
    asiento = _auditoria(session, "rol.eliminar", rol["id"])[0]
    assert asiento.antes["nombre"] == "En uso"


def test_AC_11_un_rol_inactivo_no_se_asigna_a_usuarios(cliente_como, session):
    admin = cliente_como("Administrador")
    rol = _crear_rol(admin, "Dormido").json()
    admin.patch(f"/api/roles/{rol['id']}", json={"activo": False})
    r = admin.post(
        "/api/usuarios",
        json={
            "nombre": "X",
            "usuario": "x.dormido",
            "contrasena": CLAVE_NUEVA,
            "rol_id": rol["id"],
        },
    )
    assert r.status_code == 422


# ------------------------------------------------------------------ RG-07 y alcance


def test_RG_07_un_rol_que_recibe_almacenes_todos_deja_a_sus_usuarios_sin_almacen(
    cliente_como, session
):
    admin = cliente_como("Administrador")
    rol = _crear_rol(admin, "Operativo", [P.CATALOGO_VER]).json()
    kep = AlmacenRepository(session).get_by_clave("KEP")
    usuario = _crear_usuario(admin, session, rol["id"], almacen_id=str(kep.id))
    assert usuario["almacen"]["clave"] == "KEP"
    admin.put(
        f"/api/roles/{rol['id']}/permisos",
        json={"permisos": [P.CATALOGO_VER, P.ALMACENES_TODOS]},
    )
    fila = session.get(Usuario, uuid.UUID(usuario["id"]))
    session.refresh(fila)
    assert fila.almacen_id is None
    asientos = _auditoria(session, "usuario.almacen", usuario["id"])
    assert asientos and asientos[-1].despues["almacen"] is None


def test_RG_07_un_rol_sin_almacenes_todos_exige_almacen_al_crear_usuarios(cliente_como, session):
    admin = cliente_como("Administrador")
    rol = _crear_rol(admin, "Operativo", [P.CATALOGO_VER]).json()
    r = admin.post(
        "/api/usuarios",
        json={"nombre": "X", "usuario": "x.op", "contrasena": CLAVE_NUEVA, "rol_id": rol["id"]},
    )
    assert r.status_code == 422
    assert r.json()["detalles"][0]["campo"] == "almacen_id"


# ------------------------------------------------------------------ permisos de los endpoints


@pytest.mark.parametrize("rol", ["Almacenista", "Supervisor", "Compras", "Recursos Humanos"])
@pytest.mark.parametrize(
    ("metodo", "ruta", "cuerpo"),
    [
        ("GET", "/api/permisos", None),
        ("GET", "/api/roles", None),
        ("POST", "/api/roles", {"nombre": "Colado", "permisos": []}),
        ("PUT", "/api/roles/{id}/permisos", {"permisos": [P.ACCESO_ADMINISTRAR]}),
        ("PATCH", "/api/roles/{id}", {"nombre": "Colado"}),
        ("DELETE", "/api/roles/{id}", None),
    ],
)
def test_AC_08_solo_acceso_administrar_toca_roles_y_permisos(
    metodo, ruta, cuerpo, rol, cliente_como
):
    # El Supervisor tiene almacenes.asignar_personal y, aun así, no puede (AC-12).
    id_rol = _roles(cliente_como("Administrador"))["Almacenista"]["id"]
    r = cliente_como(rol).request(metodo, ruta.replace("{id}", id_rol), json=cuerpo)
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"


def test_AC_04_se_verifica_la_clave_y_no_el_nombre_del_rol(app, cliente_como, session):
    """Un rol que no se llama Administrador pero tiene `acceso.administrar` puede; y el
    Administrador sin ese permiso (si pudiera quitarse) no. Aquí: el rol copiado funciona."""
    admin = cliente_como("Administrador")
    rol = _crear_rol(admin, "Segundo admin", [P.ACCESO_ADMINISTRAR]).json()
    _crear_usuario(admin, session, rol["id"])
    otro = _entrar(app, "usuario.nuevo")
    assert otro.get("/api/roles").status_code == 200
    assert otro.get("/api/usuarios").status_code == 200
