"""Pruebas del módulo `acceso` (US-ACC-001): sesión, bloqueo, permisos y roles iniciales."""

import uuid
from datetime import timedelta
from typing import Annotated

import pytest
from fastapi import APIRouter, Depends

from app.config import get_settings
from app.core.excepciones import DatosInvalidos, DemasiadosIntentos, NoEncontrado, SinPermiso
from app.core.tiempo import ahora_utc
from app.modulos.acceso.dependencies import requiere_permiso
from app.modulos.acceso.exceptions import PinIncorrecto
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import CATALOGO, CLAVES, CLAVES_MVP, P
from app.modulos.acceso.repository import RolRepository, UsuarioRepository
from app.modulos.acceso.service import AccesoService
from tests.conftest import iniciar_sesion_en

MENSAJE_CREDENCIALES = "Usuario o contraseña incorrectos"


@pytest.fixture
def cliente_permisos(app, client):
    """Agrega un endpoint de prueba por cada permiso del catálogo, protegido con él."""
    router = APIRouter()
    for clave in sorted(CLAVES):

        def endpoint(
            usuario: Annotated[Usuario, Depends(requiere_permiso(clave))],
        ):
            return {"ok": True}

        router.add_api_route(f"/_prueba/{clave}", endpoint, methods=["GET"])
    app.include_router(router, prefix="/api")
    return client


def _usuario(session, nombre: str) -> Usuario:
    usuario = UsuarioRepository(session).get_by_usuario(nombre)
    assert usuario is not None
    return usuario


# ------------------------------------------------------------------- sesión


def test_US_ACC_001_login_correcto_devuelve_usuario_rol_almacen_y_permisos(client, usuario_por_rol):
    r = iniciar_sesion_en(client, usuario_por_rol("Almacenista"))
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["usuario"]["usuario"] == "almacenista"
    assert cuerpo["rol"]["nombre"] == "Almacenista"
    assert cuerpo["almacen"]["clave"] == "KEP"
    assert P.ENTREGAS_CREAR in cuerpo["permisos"]
    assert P.CATALOGO_COSTOS not in cuerpo["permisos"]
    # La cookie es HttpOnly y SameSite=Lax.
    cabecera = r.headers["set-cookie"].lower()
    assert "httponly" in cabecera and "samesite=lax" in cabecera
    # Con la cookie, GET /api/sesion responde lo mismo.
    assert client.get("/api/sesion").json() == cuerpo


def test_US_ACC_001_usuario_con_todos_los_almacenes_no_trae_almacen(client, usuario_por_rol):
    r = iniciar_sesion_en(client, usuario_por_rol("Supervisor"))
    assert r.json()["almacen"] is None
    assert P.ALMACENES_TODOS in r.json()["permisos"]


def test_US_ACC_001_credenciales_incorrectas_no_dicen_cual_fallo(client, usuario_por_rol):
    mal_clave = client.post("/api/sesion", json={"usuario": "almacenista", "contrasena": "x"})
    mal_usuario = client.post("/api/sesion", json={"usuario": "no_existe", "contrasena": "x"})
    for r in (mal_clave, mal_usuario):
        assert r.status_code == 401
        assert r.json()["codigo"] == "NO_AUTENTICADO"
        assert r.json()["mensaje"] == MENSAJE_CREDENCIALES
    assert mal_clave.json() == mal_usuario.json()


def test_US_ACC_001_usuario_inactivo_no_entra(client, session, usuario_por_rol):
    _usuario(session, "almacenista").activo = False
    session.commit()
    r = iniciar_sesion_en(client, usuario_por_rol("Almacenista"))
    assert r.status_code == 401
    assert r.json()["mensaje"] == MENSAJE_CREDENCIALES


def test_US_ACC_001_cinco_intentos_fallidos_bloquean_cinco_minutos(
    client, session, usuario_por_rol
):
    u = usuario_por_rol("Compras")
    for _ in range(4):
        assert iniciar_sesion_en(client, u, "mala").status_code == 401
    quinto = iniciar_sesion_en(client, u, "mala")
    assert quinto.status_code == 429
    assert quinto.json()["codigo"] == "DEMASIADOS_INTENTOS"
    assert quinto.json()["detalles"]["segundos_espera"] == 300
    # Aun con la contraseña correcta, mientras dura el bloqueo no entra.
    sexto = iniciar_sesion_en(client, u)
    assert sexto.status_code == 429
    assert 0 < sexto.json()["detalles"]["segundos_espera"] <= 300
    # Pasados los cinco minutos, entra de nuevo.
    _usuario(session, "compras").bloqueado_hasta = ahora_utc() - timedelta(seconds=1)
    session.commit()
    assert iniciar_sesion_en(client, u).status_code == 200


def test_US_ACC_001_un_exito_reinicia_el_contador_de_intentos(client, usuario_por_rol):
    u = usuario_por_rol("Compras")
    for _ in range(4):
        iniciar_sesion_en(client, u, "mala")
    assert iniciar_sesion_en(client, u).status_code == 200
    for _ in range(4):
        assert iniciar_sesion_en(client, u, "mala").status_code == 401


def test_US_ACC_001_sin_sesion_responde_401(client):
    r = client.get("/api/sesion")
    assert r.status_code == 401
    assert r.json() == {
        "codigo": "NO_AUTENTICADO",
        "mensaje": "Inicia sesión para continuar.",
        "detalles": None,
    }


def test_US_ACC_001_cookie_alterada_responde_401(client, usuario_por_rol):
    iniciar_sesion_en(client, usuario_por_rol("Almacenista"))
    client.cookies.set(get_settings().cookie_nombre, "token.falso.alterado")
    assert client.get("/api/sesion").status_code == 401


def test_US_ACC_001_salir_cierra_la_sesion(client, usuario_por_rol):
    iniciar_sesion_en(client, usuario_por_rol("Almacenista"))
    assert client.delete("/api/sesion").status_code == 204
    assert client.get("/api/sesion").status_code == 401


def test_US_ACC_001_usuario_inactivado_con_sesion_abierta_pierde_acceso(
    client, session, usuario_por_rol
):
    iniciar_sesion_en(client, usuario_por_rol("Almacenista"))
    assert client.get("/api/sesion").status_code == 200
    _usuario(session, "almacenista").activo = False
    session.commit()
    assert client.get("/api/sesion").status_code == 401


def test_US_ACC_001_datos_incorrectos_responden_422_con_el_campo(client):
    r = client.post("/api/sesion", json={})
    assert r.status_code == 422
    assert r.json()["codigo"] == "DATOS_INVALIDOS"
    assert {d["campo"] for d in r.json()["detalles"]} == {"usuario", "contrasena"}


def test_US_ACC_001_la_sesion_deja_registro_en_la_auditoria(client, session, usuario_por_rol):
    from sqlalchemy import select

    from app.modulos.auditoria.models import Auditoria

    iniciar_sesion_en(client, usuario_por_rol("Supervisor"))
    acciones = session.scalars(select(Auditoria.accion)).all()
    assert "sesion.entrada" in acciones


# ----------------------------------------------------------------- permisos


@pytest.mark.parametrize("clave", sorted(CLAVES))
def test_AC_04_con_el_permiso_el_endpoint_responde_y_sin_el_da_403(
    clave, cliente_permisos, crear_usuario
):
    """Una prueba por permiso: un rol con solo esa clave entra; con todas las demás, 403."""
    solo = crear_usuario({clave})
    todos_menos = crear_usuario(CLAVES - {clave})

    cliente_permisos.cookies.clear()
    assert iniciar_sesion_en(cliente_permisos, solo).status_code == 200
    assert cliente_permisos.get(f"/api/_prueba/{clave}").status_code == 200

    cliente_permisos.cookies.clear()
    assert iniciar_sesion_en(cliente_permisos, todos_menos).status_code == 200
    r = cliente_permisos.get(f"/api/_prueba/{clave}")
    assert r.status_code == 403
    assert r.json() == {
        "codigo": "SIN_PERMISO",
        "mensaje": "Tu rol no puede hacer esto.",
        "detalles": None,
    }


def test_AC_04_un_rol_con_un_solo_permiso_usa_ese_endpoint_y_ningun_otro(
    cliente_permisos, crear_usuario
):
    # Aunque el rol se llame como uno inicial, solo importan sus permisos.
    u = crear_usuario({P.ENTREGAS_CREAR}, nombre_rol="Administrador de planta")
    iniciar_sesion_en(cliente_permisos, u)
    assert cliente_permisos.get(f"/api/_prueba/{P.ENTREGAS_CREAR}").status_code == 200
    for otra in sorted(CLAVES - {P.ENTREGAS_CREAR}):
        assert cliente_permisos.get(f"/api/_prueba/{otra}").status_code == 403


def test_AC_04_el_endpoint_sin_sesion_responde_401(cliente_permisos):
    assert cliente_permisos.get(f"/api/_prueba/{P.ENTREGAS_CREAR}").status_code == 401


def test_AC_10_un_cambio_de_permisos_aplica_en_la_siguiente_peticion(
    cliente_permisos, crear_usuario, session
):
    u = crear_usuario({P.CATALOGO_VER})
    iniciar_sesion_en(cliente_permisos, u)
    assert cliente_permisos.get(f"/api/_prueba/{P.CATALOGO_VER}").status_code == 200
    assert cliente_permisos.get(f"/api/_prueba/{P.VALES_VER}").status_code == 403

    rol_id = _usuario(session, u.usuario).rol_id
    RolRepository(session).reemplazar_permisos(rol_id, {P.VALES_VER})
    session.commit()

    # Sin volver a entrar.
    assert cliente_permisos.get(f"/api/_prueba/{P.CATALOGO_VER}").status_code == 403
    assert cliente_permisos.get(f"/api/_prueba/{P.VALES_VER}").status_code == 200
    assert cliente_permisos.get("/api/sesion").json()["permisos"] == [P.VALES_VER]


def test_AC_10_un_rol_inactivo_no_tiene_permisos(cliente_permisos, crear_usuario, session):
    u = crear_usuario({P.CATALOGO_VER})
    iniciar_sesion_en(cliente_permisos, u)
    _usuario(session, u.usuario).rol.activo = False
    session.commit()
    assert cliente_permisos.get(f"/api/_prueba/{P.CATALOGO_VER}").status_code == 403


def test_AC_01_el_catalogo_trae_todas_las_claves_de_las_secciones_8_2_y_8_3():
    esperadas_mvp = {
        "acceso.administrar", "trabajadores.ver", "trabajadores.ver_datos_personales",
        "trabajadores.administrar", "trabajadores.iniciar_baja", "catalogo.ver",
        "catalogo.administrar", "catalogo.costos", "inventario.ver", "inventario.entradas",
        "entregas.crear", "devoluciones.crear", "traspasos.operar", "no_adeudo.emitir",
        "vales.ver", "vales.cancelar", "vales.cancelar_todos", "autorizaciones.resolver",
        "piezas.inspeccionar", "piezas.ajustar_vigencia", "reportes.existencias",
        "reportes.movimientos", "reportes.adeudos", "reportes.consumo", "almacenes.todos",
        "etiquetas.imprimir", "almacenes.asignar_personal",
    }  # fmt: skip
    esperadas_features = {
        "almacenes.administrar", "reportes.valor_inventario", "inventario.minimos",
        "piezas.dar_de_baja", "revision.ver", "tablero.ver",
    }  # fmt: skip
    assert CLAVES_MVP == esperadas_mvp
    assert CLAVES == esperadas_mvp | esperadas_features
    assert all(not p.mvp for p in CATALOGO if p.clave in esperadas_features)
    assert {p.clave for p in CATALOGO if p.es_de_informacion} >= {
        "catalogo.costos",
        "trabajadores.ver_datos_personales",
    }


def test_AC_01_una_clave_fuera_del_catalogo_falla_al_declarar_el_endpoint():
    with pytest.raises(ValueError):
        requiere_permiso("entregas.crear_de_mas")


# Tabla 8.2 de las reglas de negocio, escrita aquí a propósito (no se importa del código).
# Letras: A Almacenista, S Supervisor, C Compras, R Recursos Humanos.
TABLA_8_2 = {
    "acceso.administrar": "",
    "trabajadores.ver": "ASR",
    "trabajadores.ver_datos_personales": "R",
    "trabajadores.administrar": "R",
    "trabajadores.iniciar_baja": "AR",
    "catalogo.ver": "ASC",
    "catalogo.administrar": "SC",
    "catalogo.costos": "C",
    "inventario.ver": "ASC",
    "inventario.entradas": "C",
    "entregas.crear": "AS",
    "devoluciones.crear": "AS",
    "traspasos.operar": "AS",
    "no_adeudo.emitir": "AS",
    "vales.ver": "ASC",
    "vales.cancelar": "ASC",
    "vales.cancelar_todos": "S",
    "autorizaciones.resolver": "S",
    "piezas.inspeccionar": "AS",
    "piezas.ajustar_vigencia": "S",
    "reportes.existencias": "ASC",
    "reportes.movimientos": "ASC",
    "reportes.adeudos": "ASR",
    "reportes.consumo": "SC",
    "almacenes.todos": "SC",
    "etiquetas.imprimir": "SCR",
    "almacenes.asignar_personal": "S",
}  # fmt: skip

ROL_POR_LETRA = {
    "A": "Almacenista",
    "S": "Supervisor",
    "C": "Compras",
    "R": "Recursos Humanos",
}


@pytest.mark.parametrize("letra", sorted(ROL_POR_LETRA))
def test_AC_03_los_roles_iniciales_traen_los_permisos_de_la_seccion_8_2(
    letra, client, usuario_por_rol
):
    rol = ROL_POR_LETRA[letra]
    esperados = {clave for clave, letras in TABLA_8_2.items() if letra in letras}
    r = iniciar_sesion_en(client, usuario_por_rol(rol))
    assert r.status_code == 200
    assert r.json()["rol"]["nombre"] == rol
    assert set(r.json()["permisos"]) == esperados


def test_AC_03_el_administrador_tiene_todos_los_permisos_como_datos(
    client, usuario_por_rol, session
):
    r = iniciar_sesion_en(client, usuario_por_rol("Administrador"))
    assert set(r.json()["permisos"]) == CLAVES
    # Son filas reales de rol_permiso, no una excepción en el código.
    rol_id = _usuario(session, "admin").rol_id
    assert RolRepository(session).permisos(rol_id) == CLAVES
    assert _usuario(session, "admin").rol.protegido is True


def test_AC_03_existe_un_usuario_de_prueba_por_cada_rol_y_un_almacenista_por_almacen(session):
    from sqlalchemy import select

    roles = set(
        session.scalars(
            select(Usuario.usuario).where(
                Usuario.usuario.in_(["admin", "almacenista", "supervisor", "compras", "rh"])
            )
        )
    )
    assert roles == {"admin", "almacenista", "supervisor", "compras", "rh"}
    almacenistas = session.scalars(
        select(Usuario.almacen_id).where(Usuario.usuario.like("alm%"))
    ).all()
    assert len(set(almacenistas)) == 6


# ----------------------------------------------------------- almacén operativo


def test_RG_07_el_almacen_de_la_operacion_sale_del_usuario_de_la_sesion(session):
    servicio = AccesoService(session)
    almacenista = _usuario(session, "almacenista")
    assert servicio.resolver_almacen(almacenista) == almacenista.almacen_id
    assert servicio.resolver_almacen(almacenista, almacenista.almacen_id) == almacenista.almacen_id


def test_AC_06_un_almacenista_no_opera_otro_almacen(session):
    servicio = AccesoService(session)
    otro = _usuario(session, "alm_con").almacen_id
    with pytest.raises(SinPermiso):
        servicio.resolver_almacen(_usuario(session, "almacenista"), otro)


def test_AC_06_con_almacenes_todos_se_indica_el_almacen(session):
    servicio = AccesoService(session)
    supervisor = _usuario(session, "supervisor")
    assert servicio.puede_operar_todos_los_almacenes(supervisor)
    destino = _usuario(session, "alm_hyl").almacen_id
    assert servicio.resolver_almacen(supervisor, destino) == destino
    with pytest.raises(DatosInvalidos):
        servicio.resolver_almacen(supervisor, None)
    with pytest.raises(NoEncontrado):
        servicio.resolver_almacen(supervisor, uuid.uuid4())


def test_RG_07_un_usuario_sin_almacen_ni_almacenes_todos_no_puede_operar(session, crear_usuario):
    u = crear_usuario({P.ENTREGAS_CREAR})
    with pytest.raises(SinPermiso):
        AccesoService(session).resolver_almacen(_usuario(session, u.usuario))


# ---------------------------------------------------------------------- PIN


def test_US_ACC_001_el_pin_correcto_se_verifica_y_es_distinto_de_la_contrasena(
    session, usuario_por_rol
):
    servicio = AccesoService(session)
    supervisor = _usuario(session, "supervisor")
    pin = usuario_por_rol("Supervisor").pin
    servicio.verificar_pin(supervisor, pin)
    with pytest.raises(PinIncorrecto):
        servicio.verificar_pin(supervisor, usuario_por_rol("Supervisor").contrasena)


def test_US_ACC_001_cinco_pines_fallidos_bloquean_cinco_minutos(session, usuario_por_rol):
    servicio = AccesoService(session)
    supervisor = _usuario(session, "supervisor")
    for _ in range(4):
        with pytest.raises(PinIncorrecto):
            servicio.verificar_pin(supervisor, "0000")
    with pytest.raises(DemasiadosIntentos) as bloqueo:
        servicio.verificar_pin(supervisor, "0000")
    assert bloqueo.value.detalles == {"segundos_espera": 300}
    with pytest.raises(DemasiadosIntentos):
        servicio.verificar_pin(supervisor, usuario_por_rol("Supervisor").pin)


def test_US_ACC_001_quien_no_tiene_pin_no_puede_verificarlo(session):
    with pytest.raises(PinIncorrecto):
        AccesoService(session).verificar_pin(_usuario(session, "almacenista"), "1234")


def test_US_ACC_001_un_pin_incorrecto_responde_403_con_su_codigo_en_http(
    app, client, session, usuario_por_rol
):
    """El handler traduce PIN_INCORRECTO a 403 (no 401: no debe cerrar la sesión en la interfaz)."""
    from app.modulos.acceso.dependencies import AccesoServiceDep, UsuarioActual

    router = APIRouter()

    @router.post("/_prueba/pin")
    def verificar(usuario: UsuarioActual, servicio: AccesoServiceDep):
        servicio.verificar_pin(usuario, "0000")

    app.include_router(router, prefix="/api")
    iniciar_sesion_en(client, usuario_por_rol("Supervisor"))
    r = client.post("/api/_prueba/pin")
    assert r.status_code == 403
    assert r.json()["codigo"] == "PIN_INCORRECTO"
