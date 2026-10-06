"""Sesiones por dispositivo: token de acceso de 15 minutos y token de renovación de 7 días
(AC-14 a AC-24).

Una prueba por regla (o por caso de la regla). Los vencimientos mueven las fechas en la base; no
hay pausas. Rotación, tolerancia y reutilización: `tests/seguridad/test_refresh.py`.
"""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import select

from app.config import get_settings
from app.core.tiempo import ahora_utc
from app.modulos.acceso.models import Rol, SesionDispositivo, Usuario
from app.modulos.acceso.permisos import P
from app.modulos.acceso.repository import RolRepository, UsuarioRepository
from app.modulos.auditoria.models import Auditoria
from app.seguridad import ALGORITMO_JWT, huella_refresh
from tests.ayudas_sesion import (
    CHROME_WINDOWS,
    SAFARI_IPHONE,
    cliente_con,
    cookie_acceso,
    cookie_refresh,
    cookies_de_respuesta,
    entrar,
    fila_de_token,
    filas_de,
    mover_fechas,
    vencer_acceso,
)
from tests.conftest import iniciar_sesion_en

DIA = timedelta(days=1)


def _cerca(valor: datetime, esperado: datetime, margen_s: int = 120) -> bool:
    return abs((valor - esperado).total_seconds()) <= margen_s


# ------------------------------------------------------------------------------------- AC-14


def test_AC_14_entrar_abre_la_sesion_del_dispositivo_con_su_token_de_renovacion(
    app, usuario_por_rol, session
):
    usuario = usuario_por_rol("Almacenista")
    cliente = entrar(app, usuario, agente=CHROME_WINDOWS)
    refresh = cookie_refresh(cliente)

    (fila,) = filas_de(session, usuario.usuario)
    ahora = ahora_utc()
    assert fila.refresh_hash == huella_refresh(refresh) != refresh  # solo la huella, no el token
    assert _cerca(fila.inicio, ahora) and _cerca(fila.ultimo_uso, ahora)
    assert _cerca(fila.expira_en, ahora + 7 * DIA)  # REFRESH_DIAS
    assert _cerca(fila.vence_absoluto, ahora + 30 * DIA)  # REFRESH_TOPE_DIAS
    assert fila.revocada_en is None and fila.reemplazada_por is None
    assert fila.agente == "Chrome en Windows"  # resumido, sin versión ni IP
    assert len(refresh) >= 60 and "." not in refresh  # opaco: no es un JWT
    # El token en claro no está en ninguna columna de ninguna fila.
    assert all(refresh not in str(v) for v in vars(fila).values())


def test_AC_14_el_token_de_acceso_vive_15_minutos_y_no_lleva_rol_ni_permisos(app, usuario_por_rol):
    assert get_settings().acceso_minutos == 15
    cliente = entrar(app, usuario_por_rol("Supervisor"))

    carga = jwt.decode(
        cookie_acceso(cliente), get_settings().clave_sesion, algorithms=[ALGORITMO_JWT]
    )

    assert set(carga) == {"sub", "ver", "fam", "iat", "exp"}  # nada de rol, permisos ni almacén
    assert carga["exp"] - carga["iat"] == 15 * 60


def test_AC_14_cada_dispositivo_tiene_su_propia_familia(app, usuario_por_rol, session):
    usuario = usuario_por_rol("Almacenista")
    entrar(app, usuario)
    entrar(app, usuario)

    primera, segunda = filas_de(session, usuario.usuario)
    assert primera.familia_id != segunda.familia_id
    assert primera.refresh_hash != segunda.refresh_hash


def test_AC_14_una_entrada_fallida_no_abre_ninguna_sesion(client, usuario_por_rol, session):
    usuario = usuario_por_rol("Almacenista")

    r = iniciar_sesion_en(client, usuario, "no-es")

    assert r.status_code == 401 and r.json()["mensaje"] == "Usuario o contraseña incorrectos"
    assert cookies_de_respuesta(r) == []
    assert filas_de(session, usuario.usuario) == []


def test_AC_14_el_bloqueo_por_intentos_sigue_igual_y_no_deja_sesiones(
    client, usuario_por_rol, session
):
    usuario = usuario_por_rol("Almacenista")
    for _ in range(4):
        assert iniciar_sesion_en(client, usuario, "mala").status_code == 401

    quinto = iniciar_sesion_en(client, usuario, "mala")
    sexto = iniciar_sesion_en(client, usuario)  # la contraseña buena también espera

    assert quinto.status_code == 429 and sexto.status_code == 429
    assert filas_de(session, usuario.usuario) == []


def test_AC_14_entrar_de_nuevo_en_el_mismo_navegador_cierra_la_sesion_anterior(
    app, usuario_por_rol, session
):
    usuario = usuario_por_rol("Almacenista")
    cliente = entrar(app, usuario)
    anterior = cookie_refresh(cliente)

    r = iniciar_sesion_en(cliente, usuario)

    assert r.status_code == 200
    previa = fila_de_token(session, anterior)
    assert previa.revocada_en is not None and previa.motivo_revocacion == "nueva_entrada"
    assert cliente.get("/api/sesion").status_code == 200
    assert len([f for f in filas_de(session, usuario.usuario) if f.revocada_en is None]) == 1


def test_AC_14_al_entrar_se_borran_las_familias_que_pasaron_su_tope_hace_tiempo(
    app, usuario_por_rol, session
):
    usuario = usuario_por_rol("Almacenista")
    vieja = entrar(app, usuario)
    familia_vieja = fila_de_token(session, cookie_refresh(vieja)).familia_id
    mover_fechas(session, familia_vieja, vence_absoluto=ahora_utc() - 3 * DIA)

    nueva = entrar(app, usuario)

    familias = {f.familia_id for f in filas_de(session, usuario.usuario)}
    assert familia_vieja not in familias
    assert len(familias) == 1 and nueva.get("/api/sesion").status_code == 200


# ------------------------------------------------------------------------------------- AC-15


def test_AC_15_el_token_de_acceso_vencido_se_recupera_con_el_de_renovacion(app, usuario_por_rol):
    usuario = usuario_por_rol("Almacenista")
    cliente = entrar(app, usuario)
    vencer_acceso(cliente)

    vencido = cliente.get("/api/sesion")
    assert vencido.status_code == 401 and vencido.json()["codigo"] == "NO_AUTENTICADO"

    r = cliente.post("/api/sesion/refresh")

    assert r.status_code == 200
    assert r.json()["usuario"]["usuario"] == usuario.usuario
    assert "permisos" in r.json() and r.json()["rol"]["nombre"] == "Almacenista"
    assert cliente.get("/api/sesion").status_code == 200


def test_AC_15_renovar_no_necesita_un_token_de_acceso_vigente(app, usuario_por_rol):
    usuario = usuario_por_rol("Almacenista")
    original = entrar(app, usuario)
    solo_refresh = cliente_con(app, refresh=cookie_refresh(original))

    r = solo_refresh.post("/api/sesion/refresh")

    assert r.status_code == 200
    assert solo_refresh.get("/api/sesion").status_code == 200


def test_AC_15_sin_token_de_renovacion_responde_sesion_vencida_y_limpia_las_cookies(
    client, usuario_por_rol
):
    r = client.post("/api/sesion/refresh")

    assert r.status_code == 401
    cuerpo = r.json()
    assert cuerpo["codigo"] == "SESION_VENCIDA"
    assert cuerpo["mensaje"] == "Tu sesión venció. Entra de nuevo para continuar."
    nombres = " ".join(cookies_de_respuesta(r)).lower()
    assert get_settings().cookie_nombre in nombres
    assert get_settings().cookie_refresh_nombre in nombres
    assert nombres.count("max-age=0") == 2


@pytest.mark.parametrize("basura", ["x", "no-es-un-token", "a" * 400, "<>'\"--;=", "{}"])
def test_AC_15_un_token_de_renovacion_inventado_se_rechaza_sin_error_interno(app, basura):
    cliente = cliente_con(app, refresh=basura)

    r = cliente.post("/api/sesion/refresh")

    assert r.status_code == 401 and r.json()["codigo"] == "SESION_VENCIDA"


def test_AC_15_el_token_de_renovacion_solo_viaja_a_la_ruta_de_sesion(app, usuario_por_rol):
    cliente = entrar(app, usuario_por_rol("Almacenista"))

    ajeno = cliente.get("/api/salud")
    propio = cliente.get("/api/sesion")

    refresh = get_settings().cookie_refresh_nombre
    assert refresh not in ajeno.request.headers.get("cookie", "")
    assert refresh in propio.request.headers.get("cookie", "")
    # El de acceso sí viaja a todo /api.
    assert get_settings().cookie_nombre in ajeno.request.headers.get("cookie", "")


# ------------------------------------------------------------------------------------- AC-18


def test_AC_18_cada_renovacion_da_otros_siete_dias(app, usuario_por_rol, session):
    cliente = entrar(app, usuario_por_rol("Almacenista"))
    fila = fila_de_token(session, cookie_refresh(cliente))
    mover_fechas(session, fila.familia_id, expira_en=ahora_utc() + 1 * DIA)  # le queda un día

    assert cliente.post("/api/sesion/refresh").status_code == 200

    nueva = fila_de_token(session, cookie_refresh(cliente))
    assert _cerca(nueva.expira_en, ahora_utc() + 7 * DIA)
    assert nueva.inicio == fila.inicio  # el inicio de la sesión no cambia al renovar
    assert nueva.vence_absoluto == fila.vence_absoluto  # tampoco el tope


def test_AC_18_la_renovacion_no_pasa_del_tope_de_30_dias(app, usuario_por_rol, session):
    cliente = entrar(app, usuario_por_rol("Almacenista"))
    familia = fila_de_token(session, cookie_refresh(cliente)).familia_id
    tope = ahora_utc() + 2 * DIA  # a la sesión le quedan dos días de tope
    mover_fechas(session, familia, vence_absoluto=tope)

    r = cliente.post("/api/sesion/refresh")

    assert r.status_code == 200
    nueva = fila_de_token(session, cookie_refresh(cliente))
    assert nueva.expira_en == tope  # no se extienden 7 días: se queda en el tope
    renovar = next(c for c in cookies_de_respuesta(r) if get_settings().cookie_refresh_nombre in c)
    max_age = int(renovar.lower().split("max-age=")[1].split(";")[0])
    assert 2 * 86400 - 120 <= max_age <= 2 * 86400


def test_AC_18_pasado_el_tope_hay_que_entrar_de_nuevo(app, usuario_por_rol, session):
    usuario = usuario_por_rol("Almacenista")
    cliente = entrar(app, usuario)
    familia = fila_de_token(session, cookie_refresh(cliente)).familia_id
    mover_fechas(session, familia, vence_absoluto=ahora_utc() - timedelta(seconds=1))

    r = cliente.post("/api/sesion/refresh")

    assert r.status_code == 401 and r.json()["codigo"] == "SESION_VENCIDA"
    assert all(f.revocada_en is not None for f in filas_de(session, usuario.usuario))
    assert cliente.get("/api/sesion").status_code == 401
    assert iniciar_sesion_en(cliente, usuario).status_code == 200  # con la contraseña, sí
    assert cliente.get("/api/sesion").status_code == 200


def test_AC_18_siete_dias_sin_usar_la_sesion_vence(app, usuario_por_rol, session):
    cliente = entrar(app, usuario_por_rol("Almacenista"))
    familia = fila_de_token(session, cookie_refresh(cliente)).familia_id
    mover_fechas(session, familia, expira_en=ahora_utc() - timedelta(seconds=1))

    r = cliente.post("/api/sesion/refresh")

    assert r.status_code == 401 and r.json()["codigo"] == "SESION_VENCIDA"


def test_AC_18_sin_renovar_la_sesion_dura_al_menos_siete_dias(app, usuario_por_rol, session):
    # A los 6 días 23 horas sin usarla todavía sirve (el JWT de acceso ya venció hace mucho).
    cliente = entrar(app, usuario_por_rol("Almacenista"))
    familia = fila_de_token(session, cookie_refresh(cliente)).familia_id
    mover_fechas(session, familia, expira_en=ahora_utc() + timedelta(hours=1))
    vencer_acceso(cliente)

    assert cliente.get("/api/sesion").status_code == 401
    assert cliente.post("/api/sesion/refresh").status_code == 200
    assert cliente.get("/api/sesion").status_code == 200


# ------------------------------------------------------------------------------------- AC-19


def test_AC_19_salir_cierra_solo_la_sesion_de_este_dispositivo(app, usuario_por_rol, session):
    usuario = usuario_por_rol("Almacenista")
    este = entrar(app, usuario)
    otro = entrar(app, usuario)
    refresh_este = cookie_refresh(este)
    acceso_copiado = cliente_con(app, acceso=cookie_acceso(este))

    r = este.delete("/api/sesion")

    assert r.status_code == 204
    # Este dispositivo: ni acceso ni renovación, y borra las dos cookies.
    assert este.get("/api/sesion").status_code == 401
    assert acceso_copiado.get("/api/sesion").status_code == 401  # el token copiado, de inmediato
    assert cliente_con(app, refresh=refresh_este).post("/api/sesion/refresh").status_code == 401
    borradas = " ".join(cookies_de_respuesta(r)).lower()
    assert get_settings().cookie_nombre in borradas
    assert get_settings().cookie_refresh_nombre in borradas
    assert fila_de_token(session, refresh_este).motivo_revocacion == "salida"
    # El otro dispositivo sigue abierto, también al renovar.
    assert otro.get("/api/sesion").status_code == 200
    assert otro.post("/api/sesion/refresh").status_code == 200
    assert otro.get("/api/sesion").status_code == 200


def test_AC_19_salir_se_registra_en_el_registro_de_cambios(app, usuario_por_rol, session):
    usuario = usuario_por_rol("Almacenista")
    cliente = entrar(app, usuario)

    cliente.delete("/api/sesion")

    acciones = list(
        session.scalars(select(Auditoria.accion).where(Auditoria.accion.like("sesion.%")))
    )
    assert "sesion.salida" in acciones


def test_AC_19_salir_sin_sesion_responde_401(client):
    assert client.delete("/api/sesion").status_code == 401


# ------------------------------------------------------------------------------------- AC-20


def test_AC_20_cerrar_todas_cierra_todos_los_dispositivos_y_sube_la_version(
    app, usuario_por_rol, session
):
    usuario = usuario_por_rol("Almacenista")
    a, b, c = entrar(app, usuario), entrar(app, usuario), entrar(app, usuario)
    refresh_b = cookie_refresh(b)
    version = UsuarioRepository(session).get_by_usuario(usuario.usuario).version_sesion

    r = a.delete("/api/sesion/todas")

    assert r.status_code == 204
    assert UsuarioRepository(session).get_by_usuario(usuario.usuario).version_sesion == version + 1
    for cliente in (a, b, c):
        assert cliente.get("/api/sesion").status_code == 401
    assert cliente_con(app, refresh=refresh_b).post("/api/sesion/refresh").status_code == 401
    assert all(f.revocada_en is not None for f in filas_de(session, usuario.usuario))
    assert iniciar_sesion_en(a, usuario).status_code == 200  # con la contraseña, sí


def test_AC_20_cerrar_todas_de_un_usuario_no_toca_a_los_demas(app, usuario_por_rol):
    uno = entrar(app, usuario_por_rol("Almacenista"))
    otro = entrar(app, usuario_por_rol("Supervisor"))

    assert uno.delete("/api/sesion/todas").status_code == 204

    assert uno.get("/api/sesion").status_code == 401
    assert otro.get("/api/sesion").status_code == 200


def test_AC_20_cerrar_las_demas_deja_abierta_solo_esta(app, usuario_por_rol, session):
    usuario = usuario_por_rol("Almacenista")
    a, b, c = entrar(app, usuario), entrar(app, usuario), entrar(app, usuario)
    version = UsuarioRepository(session).get_by_usuario(usuario.usuario).version_sesion

    r = a.delete("/api/sesion/otras")

    assert r.status_code == 200 and r.json() == {"cerradas": 2}
    assert a.get("/api/sesion").status_code == 200
    assert a.post("/api/sesion/refresh").status_code == 200
    assert b.get("/api/sesion").status_code == 401 and c.get("/api/sesion").status_code == 401
    assert UsuarioRepository(session).get_by_usuario(usuario.usuario).version_sesion == version
    assert a.delete("/api/sesion/otras").json() == {"cerradas": 0}


def test_AC_20_cerrar_todas_y_las_demas_piden_sesion(client):
    assert client.delete("/api/sesion/todas").status_code == 401
    assert client.delete("/api/sesion/otras").status_code == 401


# ------------------------------------------------------------------------------------- AC-21


def test_AC_21_lista_los_dispositivos_con_sesion_abierta_y_marca_el_actual(
    app, usuario_por_rol, session
):
    usuario = usuario_por_rol("Almacenista")
    este = entrar(app, usuario, agente=CHROME_WINDOWS)
    entrar(app, usuario, agente=SAFARI_IPHONE)
    entrar(app, usuario_por_rol("Supervisor"))  # de otra persona: no sale

    r = este.get("/api/sesion/dispositivos")

    assert r.status_code == 200
    dispositivos = r.json()["dispositivos"]
    assert len(dispositivos) == 2
    assert sorted(d["agente"] for d in dispositivos) == ["Chrome en Windows", "Safari en iOS"]
    assert [d["actual"] for d in dispositivos].count(True) == 1
    actual = next(d for d in dispositivos if d["actual"])
    assert actual["agente"] == "Chrome en Windows"
    for d in dispositivos:
        assert set(d) == {"id", "inicio", "ultimo_uso", "vence_en", "agente", "actual"}
        assert d["inicio"].endswith("Z") and d["ultimo_uso"].endswith("Z")
    # Sin huellas ni tokens ni IP en ninguna parte de la respuesta.
    texto = r.text.lower()
    for fila in filas_de(session, usuario.usuario):
        assert fila.refresh_hash not in texto
    assert "hash" not in texto and "refresh" not in texto and "ip" not in set(actual)


def test_AC_21_no_lista_las_sesiones_cerradas_ni_vencidas(app, usuario_por_rol, session):
    usuario = usuario_por_rol("Almacenista")
    este = entrar(app, usuario)
    cerrada = entrar(app, usuario)
    vencida = entrar(app, usuario)
    tope = entrar(app, usuario)
    cerrada.delete("/api/sesion")
    mover_fechas(
        session,
        fila_de_token(session, cookie_refresh(vencida)).familia_id,
        expira_en=ahora_utc() - timedelta(seconds=1),
    )
    mover_fechas(
        session,
        fila_de_token(session, cookie_refresh(tope)).familia_id,
        vence_absoluto=ahora_utc() - timedelta(seconds=1),
    )

    dispositivos = este.get("/api/sesion/dispositivos").json()["dispositivos"]

    assert len(dispositivos) == 1 and dispositivos[0]["actual"] is True


def test_AC_21_una_renovacion_no_duplica_el_dispositivo(app, usuario_por_rol):
    usuario = usuario_por_rol("Almacenista")
    este = entrar(app, usuario)
    este.post("/api/sesion/refresh")
    este.post("/api/sesion/refresh")

    assert len(este.get("/api/sesion/dispositivos").json()["dispositivos"]) == 1


def test_AC_21_pide_sesion(client):
    assert client.get("/api/sesion/dispositivos").status_code == 401


@pytest.mark.parametrize(
    ("agente", "esperado"),
    [
        (CHROME_WINDOWS, "Chrome en Windows"),
        (CHROME_WINDOWS + " Edg/126.0.0.0", "Edge en Windows"),
        (SAFARI_IPHONE, "Safari en iOS"),
        (
            "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/126.0 Mobile Safari/537.36",
            "Chrome en Android",
        ),
        (
            "Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0",
            "Firefox en Linux",
        ),
        ("curl/8.0", "Dispositivo desconocido"),
        ("", None),
    ],
)
def test_AC_21_el_agente_se_resume_sin_versiones(agente, esperado):
    from app.modulos.acceso.service_sesiones import resumir_agente

    assert resumir_agente(agente) == esperado


def test_AC_21_un_agente_larguisimo_se_recorta(app, usuario_por_rol, session):
    usuario = usuario_por_rol("Almacenista")
    entrar(app, usuario, agente="Chrome/1 Windows " + "x" * 5000)

    (fila,) = filas_de(session, usuario.usuario)
    assert fila.agente is not None and len(fila.agente) <= 120


# ------------------------------------------------------------------------------------- AC-22


def test_AC_22_restablecer_la_contrasena_revoca_todas_las_sesiones_incluida_la_renovacion(
    app, cliente_como, crear_usuario, session
):
    objetivo = crear_usuario({P.VALES_VER}, almacen="KEP")
    a, b = entrar(app, objetivo), entrar(app, objetivo)
    refresh_a, refresh_b = cookie_refresh(a), cookie_refresh(b)
    usuario_id = UsuarioRepository(session).get_by_usuario(objetivo.usuario).id

    r = cliente_como("Administrador").post(
        f"/api/usuarios/{usuario_id}/contrasena", json={"contrasena": "Clave-nueva-123"}
    )
    assert r.status_code == 200, r.text

    for cliente in (a, b):
        assert cliente.get("/api/sesion").status_code == 401
    for refresh in (refresh_a, refresh_b):
        malo = cliente_con(app, refresh=refresh).post("/api/sesion/refresh")
        assert malo.status_code == 401 and malo.json()["codigo"] == "SESION_VENCIDA"
    assert fila_de_token(session, refresh_a).motivo_revocacion == "version"


def test_AC_22_restablecer_el_pin_tambien_revoca_las_sesiones(
    app, cliente_como, crear_usuario, session
):
    objetivo = crear_usuario({P.AUTORIZACIONES_RESOLVER}, almacen="KEP", pin="1111")
    cliente = entrar(app, objetivo)
    usuario_id = UsuarioRepository(session).get_by_usuario(objetivo.usuario).id

    r = cliente_como("Administrador").post(
        f"/api/usuarios/{usuario_id}/contrasena",
        json={"contrasena": "Clave-nueva-123", "pin": "2222"},
    )
    assert r.status_code == 200, r.text

    assert cliente.get("/api/sesion").status_code == 401
    assert cliente.post("/api/sesion/refresh").status_code == 401


def test_AC_22_inactivar_y_reactivar_al_usuario_revoca_sus_sesiones(
    app, cliente_como, crear_usuario, session
):
    objetivo = crear_usuario({P.VALES_VER}, almacen="KEP")
    cliente = entrar(app, objetivo)
    refresh = cookie_refresh(cliente)
    admin = cliente_como("Administrador")
    usuario_id = UsuarioRepository(session).get_by_usuario(objetivo.usuario).id

    assert admin.patch(f"/api/usuarios/{usuario_id}", json={"activo": False}).status_code == 200
    assert cliente.get("/api/sesion").status_code == 401
    assert cliente_con(app, refresh=refresh).post("/api/sesion/refresh").status_code == 401

    # Aunque se reactive, la sesión de antes no revive: hay que entrar de nuevo.
    assert admin.patch(f"/api/usuarios/{usuario_id}", json={"activo": True}).status_code == 200
    assert cliente_con(app, refresh=refresh).post("/api/sesion/refresh").status_code == 401
    assert iniciar_sesion_en(cliente, objetivo).status_code == 200


def test_AC_22_un_token_de_renovacion_de_una_version_vieja_se_rechaza(
    app, usuario_por_rol, session
):
    usuario = usuario_por_rol("Almacenista")
    cliente = entrar(app, usuario)
    refresh = cookie_refresh(cliente)
    UsuarioRepository(session).get_by_usuario(usuario.usuario).version_sesion = (
        Usuario.version_sesion + 1
    )
    session.flush()

    r = cliente.post("/api/sesion/refresh")

    assert r.status_code == 401 and r.json()["codigo"] == "SESION_VENCIDA"
    fila = fila_de_token(session, refresh)
    assert fila.revocada_en is not None and fila.motivo_revocacion == "version"
    assert cliente.get("/api/sesion").status_code == 401


def test_AC_22_un_usuario_inactivo_no_puede_renovar(app, usuario_por_rol, session):
    usuario = usuario_por_rol("Almacenista")
    cliente = entrar(app, usuario)
    vencer_acceso(cliente)
    UsuarioRepository(session).get_by_usuario(usuario.usuario).activo = False
    session.flush()

    assert cliente.post("/api/sesion/refresh").status_code == 401


# ------------------------------------------------------------------------------------- AC-23


def test_AC_23_los_permisos_y_el_almacen_se_leen_de_la_base_en_cada_peticion_tambien_al_renovar(
    app, crear_usuario, session
):
    objetivo = crear_usuario({P.VALES_VER}, almacen="KEP")
    cliente = entrar(app, objetivo)
    assert cliente.get("/api/sesion").json()["permisos"] == ["vales.ver"]
    assert cliente.get("/api/sesion").json()["almacen"]["clave"] == "KEP"

    usuario = UsuarioRepository(session).get_by_usuario(objetivo.usuario)
    RolRepository(session).reemplazar_permisos(usuario.rol_id, {P.VALES_VER, P.INVENTARIO_VER})
    usuario.almacen_id = None
    session.flush()

    # Sin volver a entrar y sin renovar: ya aplica.
    cambiada = cliente.get("/api/sesion").json()
    assert cambiada["permisos"] == ["inventario.ver", "vales.ver"] and cambiada["almacen"] is None

    # Tras renovar, igual: la renovación no congela nada.
    renovada = cliente.post("/api/sesion/refresh").json()
    assert renovada["permisos"] == ["inventario.ver", "vales.ver"] and renovada["almacen"] is None

    RolRepository(session).reemplazar_permisos(usuario.rol_id, {P.VALES_VER})
    session.flush()
    assert cliente.get("/api/sesion").json()["permisos"] == ["vales.ver"]


def test_AC_23_un_rol_inactivo_quita_los_permisos_aunque_la_sesion_siga_abierta(
    app, crear_usuario, session
):
    objetivo = crear_usuario({P.VALES_VER}, almacen="KEP")
    cliente = entrar(app, objetivo)
    usuario = UsuarioRepository(session).get_by_usuario(objetivo.usuario)
    session.get(Rol, usuario.rol_id).activo = False
    session.flush()

    assert cliente.get("/api/sesion").json()["permisos"] == []
    assert cliente.post("/api/sesion/refresh").json()["permisos"] == []


# ------------------------------------------------------------------------------------- AC-24


def _atributos(cookie: str) -> dict[str, str | bool]:
    partes = [p.strip() for p in cookie.split(";")]
    atributos: dict[str, str | bool] = {"valor": partes[0].split("=", 1)[1]}
    for parte in partes[1:]:
        nombre, _, valor = parte.partition("=")
        atributos[nombre.lower()] = valor or True
    return atributos


def _cookies_por_nombre(respuesta) -> dict[str, dict[str, str | bool]]:
    return {c.split("=", 1)[0]: _atributos(c) for c in cookies_de_respuesta(respuesta)}


def test_AC_24_las_cookies_son_httponly_samesite_lax_y_cada_una_con_su_ruta_y_vida(
    client, usuario_por_rol
):
    ajustes = get_settings()

    r = iniciar_sesion_en(client, usuario_por_rol("Almacenista"))

    cookies = _cookies_por_nombre(r)
    assert set(cookies) == {ajustes.cookie_nombre, ajustes.cookie_refresh_nombre}
    acceso = cookies[ajustes.cookie_nombre]
    renovar = cookies[ajustes.cookie_refresh_nombre]
    for cookie in (acceso, renovar):
        assert cookie["httponly"] is True
        assert str(cookie["samesite"]).lower() == "lax"
        assert "secure" not in cookie  # las pruebas corren con COOKIE_SEGURA=false
    assert acceso["path"] == "/" and int(acceso["max-age"]) == ajustes.acceso_minutos * 60
    assert renovar["path"] == "/api/sesion"
    assert 7 * 86400 - 120 <= int(renovar["max-age"]) <= 7 * 86400


def test_AC_24_con_cookie_segura_las_dos_cookies_llevan_secure(
    client, usuario_por_rol, monkeypatch
):
    monkeypatch.setattr(get_settings(), "cookie_segura", True)

    r = iniciar_sesion_en(client, usuario_por_rol("Almacenista"))

    cookies = _cookies_por_nombre(r)
    assert len(cookies) == 2 and all(c.get("secure") is True for c in cookies.values())


def test_AC_24_salir_borra_las_dos_cookies_con_los_mismos_atributos(client, usuario_por_rol):
    ajustes = get_settings()
    iniciar_sesion_en(client, usuario_por_rol("Almacenista"))

    r = client.delete("/api/sesion")

    cookies = _cookies_por_nombre(r)
    assert cookies[ajustes.cookie_nombre]["path"] == "/"
    assert cookies[ajustes.cookie_refresh_nombre]["path"] == "/api/sesion"
    assert all(int(c["max-age"]) == 0 and c["httponly"] is True for c in cookies.values())


def test_AC_24_el_servidor_no_deja_configurar_un_tope_menor_que_la_ventana():
    from app.config import Settings

    with pytest.raises(ValueError, match="REFRESH_TOPE_DIAS"):
        Settings(refresh_dias=10, refresh_tope_dias=5)
    with pytest.raises(ValueError):
        Settings(acceso_minutos=0)
    with pytest.raises(ValueError, match="COOKIE_REFRESH_NOMBRE"):
        Settings(cookie_refresh_nombre="sesion", cookie_nombre="sesion")
    ajustes = Settings()
    assert (ajustes.acceso_minutos, ajustes.refresh_dias, ajustes.refresh_tope_dias) == (15, 7, 30)


def test_AC_24_sesion_horas_ya_no_cambia_nada(client, usuario_por_rol, monkeypatch):
    monkeypatch.setattr(get_settings(), "sesion_horas", 1)

    r = iniciar_sesion_en(client, usuario_por_rol("Almacenista"))

    assert int(_cookies_por_nombre(r)[get_settings().cookie_nombre]["max-age"]) == 15 * 60


def test_AC_24_un_token_sin_familia_de_antes_de_las_sesiones_por_dispositivo_no_sirve(
    app, usuario_por_rol, session
):
    usuario = usuario_por_rol("Almacenista")
    cliente = entrar(app, usuario)
    fila = filas_de(session, usuario.usuario)[0]
    ahora = datetime.now(UTC)
    antiguo = jwt.encode(
        {"sub": str(fila.usuario_id), "ver": 0, "iat": ahora, "exp": ahora + timedelta(hours=12)},
        get_settings().clave_sesion,
        algorithm=ALGORITMO_JWT,
    )

    assert cliente_con(app, acceso=antiguo).get("/api/sesion").status_code == 401
    assert cliente.get("/api/sesion").status_code == 200


def test_AC_24_un_token_de_acceso_con_la_familia_de_otro_usuario_no_sirve(
    app, usuario_por_rol, session
):
    from app.seguridad import crear_token_acceso

    almacenista = usuario_por_rol("Almacenista")
    supervisor = usuario_por_rol("Supervisor")
    entrar(app, almacenista)
    entrar(app, supervisor)
    (fila_a,) = filas_de(session, almacenista.usuario)
    (fila_s,) = filas_de(session, supervisor.usuario)

    falso = crear_token_acceso(fila_s.usuario_id, 0, fila_a.familia_id)  # familia ajena

    assert cliente_con(app, acceso=falso).get("/api/sesion").status_code == 401


def test_AC_24_la_tabla_nunca_guarda_el_token_en_claro(app, usuario_por_rol, session):
    usuario = usuario_por_rol("Almacenista")
    cliente = entrar(app, usuario)
    refresh = cookie_refresh(cliente)
    cliente.post("/api/sesion/refresh")

    columnas = session.execute(select(SesionDispositivo)).scalars().all()
    for fila in columnas:
        assert refresh not in "|".join(str(v) for v in vars(fila).values())
