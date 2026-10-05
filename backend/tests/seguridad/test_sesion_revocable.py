"""Endurecimiento (H5): el token de una sesión cerrada, restablecida o inactiva ya no sirve.

El token (cookie) lleva la versión de sesión del usuario (`ver`); cerrar sesión, restablecer la
contraseña o el PIN e inactivar al usuario la incrementan, así que un token copiado antes deja de
dar acceso (antes seguía valiendo las 12 horas de su vigencia).
"""

from fastapi.testclient import TestClient

from app.config import get_settings
from app.modulos.acceso.permisos import P


def _token(cliente: TestClient) -> str:
    token = cliente.cookies.get(get_settings().cookie_nombre)
    assert token
    return token


def _con_token(app, token: str) -> TestClient:
    cliente = TestClient(app)
    cliente.cookies.set(get_settings().cookie_nombre, token)
    return cliente


def test_US_ACC_001_H5_el_token_copiado_deja_de_servir_al_cerrar_sesion(
    app, client, usuario_por_rol, iniciar_sesion
):
    assert iniciar_sesion(client, usuario_por_rol("Almacenista")).status_code == 200
    token = _token(client)
    copia = _con_token(app, token)
    assert copia.get("/api/sesion").status_code == 200

    assert client.delete("/api/sesion").status_code == 204

    r = copia.get("/api/sesion")
    assert r.status_code == 401 and r.json()["codigo"] == "NO_AUTENTICADO"
    assert client.get("/api/sesion").status_code == 401


def test_US_ACC_001_H5_un_login_nuevo_funciona_despues_de_cerrar_sesion(
    app, client, usuario_por_rol, iniciar_sesion
):
    usuario = usuario_por_rol("Almacenista")
    iniciar_sesion(client, usuario)
    viejo = _token(client)
    client.delete("/api/sesion")

    assert iniciar_sesion(client, usuario).status_code == 200
    assert client.get("/api/sesion").status_code == 200
    assert _con_token(app, _token(client)).get("/api/sesion").status_code == 200
    assert _con_token(app, viejo).get("/api/sesion").status_code == 401


def test_US_ACC_001_H5_cerrar_sesion_cierra_todas_las_sesiones_del_usuario(
    app, client, usuario_por_rol, iniciar_sesion
):
    usuario = usuario_por_rol("Almacenista")
    iniciar_sesion(client, usuario)
    otro_dispositivo = TestClient(app)
    iniciar_sesion(otro_dispositivo, usuario)

    client.delete("/api/sesion")

    assert otro_dispositivo.get("/api/sesion").status_code == 401


def test_US_ACC_001_H5_el_token_copiado_deja_de_servir_al_restablecer_la_contrasena(
    app, client, cliente_como, crear_usuario, iniciar_sesion, session
):
    objetivo = crear_usuario({P.VALES_VER}, almacen="KEP")
    iniciar_sesion(client, objetivo)
    copia = _con_token(app, _token(client))
    assert copia.get("/api/sesion").status_code == 200

    r = cliente_como("Administrador").post(
        f"/api/usuarios/{_id_de(session, objetivo.usuario)}/contrasena",
        json={"contrasena": "Clave-nueva-123"},
    )
    assert r.status_code == 200, r.text

    assert copia.get("/api/sesion").status_code == 401
    assert client.get("/api/sesion").status_code == 401
    # Con la contraseña nueva se entra de nuevo.
    assert iniciar_sesion(client, objetivo, "Clave-nueva-123").status_code == 200
    assert client.get("/api/sesion").status_code == 200


def test_US_ACC_001_H5_el_token_copiado_deja_de_servir_al_inactivar_al_usuario(
    app, client, cliente_como, crear_usuario, iniciar_sesion, session
):
    objetivo = crear_usuario({P.VALES_VER}, almacen="KEP")
    iniciar_sesion(client, objetivo)
    copia = _con_token(app, _token(client))
    admin = cliente_como("Administrador")
    usuario_id = _id_de(session, objetivo.usuario)

    assert admin.patch(f"/api/usuarios/{usuario_id}", json={"activo": False}).status_code == 200
    assert copia.get("/api/sesion").status_code == 401

    # Aunque se reactive, el token de antes no revive.
    assert admin.patch(f"/api/usuarios/{usuario_id}", json={"activo": True}).status_code == 200
    assert copia.get("/api/sesion").status_code == 401
    assert iniciar_sesion(client, objetivo).status_code == 200


def test_US_ACC_001_H5_un_token_con_otra_version_se_rechaza(
    app, client, usuario_por_rol, iniciar_sesion, session
):
    from app.seguridad import crear_token

    assert iniciar_sesion(client, usuario_por_rol("Almacenista")).status_code == 200
    futuro = crear_token(_id_de(session, "almacenista"), version=99)

    assert _con_token(app, futuro).get("/api/sesion").status_code == 401


def _id_de(session, nombre_usuario: str):
    from app.modulos.acceso.repository import UsuarioRepository

    return UsuarioRepository(session).get_by_usuario(nombre_usuario).id
