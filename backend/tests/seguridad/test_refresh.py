"""Rotación del token de renovación, tolerancia y detección de reutilización (AC-15 a AC-17).

Cada renovación entrega un token nuevo y deja el anterior revocado. Usar un token ya rotado hace
más de la tolerancia (10 s) es señal de robo o de dos dispositivos con la misma sesión: se revoca
toda la familia. Dentro de la tolerancia se atiende como una carrera legítima (dos pestañas, un
reintento de red) sin revocar. El tiempo se simula moviendo `revocada_en` en la base.
"""

from collections import Counter

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import get_settings
from app.main import create_app
from app.modulos.acceso.permisos import P
from app.modulos.auditoria.models import Auditoria
from tests.ayudas_sesion import (
    cliente_con,
    cookie_refresh,
    cookies_de_respuesta,
    entrar,
    envejecer_rotacion,
    fila_de_token,
    filas_de,
)
from tests.seguridad.conftest import en_paralelo


def _renueva_la_cookie_de_renovacion(respuesta) -> bool:
    return any(get_settings().cookie_refresh_nombre in c for c in cookies_de_respuesta(respuesta))


# ------------------------------------------------------------------------------------- AC-15


def test_AC_15_renovar_rota_el_token_y_el_anterior_queda_revocado_y_encadenado(
    app, usuario_por_rol, session
):
    usuario = usuario_por_rol("Almacenista")
    cliente = entrar(app, usuario)
    viejo = cookie_refresh(cliente)

    r = cliente.post("/api/sesion/refresh")

    assert r.status_code == 200
    nuevo = cookie_refresh(cliente)
    assert nuevo != viejo
    anterior, siguiente = fila_de_token(session, viejo), fila_de_token(session, nuevo)
    assert anterior.revocada_en is not None and anterior.motivo_revocacion == "rotada"
    assert anterior.reemplazada_por == siguiente.id
    assert siguiente.revocada_en is None and siguiente.familia_id == anterior.familia_id
    assert siguiente.ultimo_uso >= anterior.ultimo_uso
    assert len(filas_de(session, usuario.usuario)) == 2


def test_AC_15_el_token_rotado_deja_de_servir_fuera_de_la_tolerancia(app, usuario_por_rol, session):
    cliente = entrar(app, usuario_por_rol("Almacenista"))
    viejo = cookie_refresh(cliente)
    cliente.post("/api/sesion/refresh")
    envejecer_rotacion(session, viejo)

    r = cliente_con(app, refresh=viejo).post("/api/sesion/refresh")

    assert r.status_code == 401 and r.json()["codigo"] == "SESION_VENCIDA"


def test_AC_15_se_puede_renovar_muchas_veces_seguidas_con_el_token_nuevo(app, usuario_por_rol):
    cliente = entrar(app, usuario_por_rol("Almacenista"))

    for _ in range(4):
        assert cliente.post("/api/sesion/refresh").status_code == 200
        assert cliente.get("/api/sesion").status_code == 200


# ------------------------------------------------------------------------------------- AC-16


def test_AC_16_el_token_viejo_dentro_de_la_tolerancia_da_acceso_sin_rotar_ni_revocar(
    app, usuario_por_rol, session
):
    usuario = usuario_por_rol("Almacenista")
    pestana_1 = entrar(app, usuario)
    viejo = cookie_refresh(pestana_1)
    pestana_2 = cliente_con(app, refresh=viejo)  # la otra pestaña sale con el token ya rotado

    primera = pestana_1.post("/api/sesion/refresh")
    segunda = pestana_2.post("/api/sesion/refresh")

    assert primera.status_code == 200 and _renueva_la_cookie_de_renovacion(primera)
    assert segunda.status_code == 200
    assert segunda.json() == primera.json()  # la misma sesión
    assert not _renueva_la_cookie_de_renovacion(segunda)  # no pisa el token nuevo de la primera
    assert pestana_2.get("/api/sesion").status_code == 200  # tiene su token de acceso
    # No hubo una segunda rotación: sigue habiendo una sola fila vigente y una rotada.
    filas = filas_de(session, usuario.usuario)
    assert len(filas) == 2 and len([f for f in filas if f.revocada_en is None]) == 1
    # El token nuevo de la primera sigue sirviendo (nada se revocó).
    assert pestana_1.post("/api/sesion/refresh").status_code == 200


def test_AC_16_la_tolerancia_se_agota(app, usuario_por_rol, session):
    cliente = entrar(app, usuario_por_rol("Almacenista"))
    viejo = cookie_refresh(cliente)
    cliente.post("/api/sesion/refresh")
    tolerancia = get_settings().refresh_tolerancia_segundos
    assert tolerancia == 10

    envejecer_rotacion(session, viejo, segundos=tolerancia - 3)  # hace 7 s: todavía vale
    assert cliente_con(app, refresh=viejo).post("/api/sesion/refresh").status_code == 200

    envejecer_rotacion(session, viejo, segundos=tolerancia + 3)  # hace 13 s: ya no
    assert cliente_con(app, refresh=viejo).post("/api/sesion/refresh").status_code == 401


def test_AC_16_con_tolerancia_cero_cualquier_reutilizacion_revoca(
    app, usuario_por_rol, session, monkeypatch
):
    monkeypatch.setattr(get_settings(), "refresh_tolerancia_segundos", 0)
    cliente = entrar(app, usuario_por_rol("Almacenista"))
    viejo = cookie_refresh(cliente)
    cliente.post("/api/sesion/refresh")
    envejecer_rotacion(session, viejo, segundos=1)

    assert cliente_con(app, refresh=viejo).post("/api/sesion/refresh").status_code == 401
    assert cliente.get("/api/sesion").status_code == 401


def test_AC_16_la_tolerancia_no_sirve_si_la_sesion_ya_se_cerro(app, usuario_por_rol):
    cliente = entrar(app, usuario_por_rol("Almacenista"))
    viejo = cookie_refresh(cliente)
    cliente.post("/api/sesion/refresh")
    cliente.delete("/api/sesion")  # salir, y de inmediato alguien usa el token viejo

    assert cliente_con(app, refresh=viejo).post("/api/sesion/refresh").status_code == 401


def test_AC_16_la_tolerancia_no_sirve_si_la_version_del_usuario_cambio(
    app, cliente_como, crear_usuario, session
):
    from app.modulos.acceso.repository import UsuarioRepository

    objetivo = crear_usuario({P.VALES_VER}, almacen="KEP")
    cliente = entrar(app, objetivo)
    viejo = cookie_refresh(cliente)
    cliente.post("/api/sesion/refresh")
    usuario_id = UsuarioRepository(session).get_by_usuario(objetivo.usuario).id
    cliente_como("Administrador").post(
        f"/api/usuarios/{usuario_id}/contrasena", json={"contrasena": "Clave-nueva-123"}
    )

    assert cliente_con(app, refresh=viejo).post("/api/sesion/refresh").status_code == 401


def test_AC_16_dos_renovaciones_simultaneas_con_el_mismo_token_no_se_pisan(
    engine, usuario_confirmado
):
    usuario = usuario_confirmado({P.VALES_VER})
    app = create_app()
    with TestClient(app) as cliente:
        r = cliente.post(
            "/api/sesion", json={"usuario": usuario.usuario, "contrasena": usuario.contrasena}
        )
        assert r.status_code == 200, r.text
        viejo = cookie_refresh(cliente)

    def renovar():
        with TestClient(app) as pestana:
            pestana.cookies.set(get_settings().cookie_refresh_nombre, viejo, path="/api/sesion")
            r = pestana.post("/api/sesion/refresh")
            return r.status_code, _renueva_la_cookie_de_renovacion(r)

    resultados = en_paralelo([renovar] * 6)

    assert not [r for r in resultados if not isinstance(r, tuple)], resultados
    assert Counter(r[0] for r in resultados) == {200: 6}, resultados  # ninguno se toma por robo
    assert sum(1 for _, rota in resultados if rota) == 1, resultados  # solo una rotó de verdad


# ------------------------------------------------------------------------------------- AC-17


def test_AC_17_reutilizar_un_token_rotado_fuera_de_la_tolerancia_revoca_toda_la_familia(
    app, usuario_por_rol, session
):
    usuario = usuario_por_rol("Almacenista")
    legitimo = entrar(app, usuario)
    viejo = cookie_refresh(legitimo)
    legitimo.post("/api/sesion/refresh")  # el dueño ya lo cambió por uno nuevo
    envejecer_rotacion(session, viejo)
    ladron = cliente_con(app, refresh=viejo)  # alguien presenta el token viejo, copiado antes

    r = ladron.post("/api/sesion/refresh")

    assert r.status_code == 401 and r.json()["codigo"] == "SESION_VENCIDA"
    # Toda la familia queda revocada: el token nuevo del dueño y su acceso, ya no sirven.
    assert legitimo.post("/api/sesion/refresh").status_code == 401
    assert legitimo.get("/api/sesion").status_code == 401
    vigentes = [f for f in filas_de(session, usuario.usuario) if f.revocada_en is None]
    assert vigentes == []
    ultima = max(filas_de(session, usuario.usuario), key=lambda f: f.creado_en)
    assert ultima.motivo_revocacion == "reutilizacion"
    acciones = list(
        session.scalars(select(Auditoria.accion).where(Auditoria.accion.like("sesion.%")))
    )
    assert "sesion.reutilizacion" in acciones


def test_AC_17_la_reutilizacion_solo_revoca_el_dispositivo_afectado(app, usuario_por_rol, session):
    usuario = usuario_por_rol("Almacenista")
    afectado = entrar(app, usuario)
    otro = entrar(app, usuario)
    viejo = cookie_refresh(afectado)
    afectado.post("/api/sesion/refresh")
    envejecer_rotacion(session, viejo)

    assert cliente_con(app, refresh=viejo).post("/api/sesion/refresh").status_code == 401

    assert afectado.get("/api/sesion").status_code == 401
    assert otro.get("/api/sesion").status_code == 200
    assert otro.post("/api/sesion/refresh").status_code == 200


def test_AC_17_la_persona_vuelve_a_entrar_con_su_contrasena_despues_de_una_reutilizacion(
    app, usuario_por_rol, session
):
    usuario = usuario_por_rol("Almacenista")
    cliente = entrar(app, usuario)
    viejo = cookie_refresh(cliente)
    cliente.post("/api/sesion/refresh")
    envejecer_rotacion(session, viejo)
    cliente_con(app, refresh=viejo).post("/api/sesion/refresh")

    nuevo = entrar(app, usuario)

    assert nuevo.get("/api/sesion").status_code == 200


def test_AC_17_un_token_cerrado_por_salir_no_se_toma_por_robo(app, usuario_por_rol, session):
    usuario = usuario_por_rol("Almacenista")
    cliente = entrar(app, usuario)
    token = cookie_refresh(cliente)
    cliente.delete("/api/sesion")
    antes = len(
        list(session.scalars(select(Auditoria).where(Auditoria.accion == "sesion.reutilizacion")))
    )

    r = cliente_con(app, refresh=token).post("/api/sesion/refresh")

    assert r.status_code == 401 and r.json()["codigo"] == "SESION_VENCIDA"
    despues = len(
        list(session.scalars(select(Auditoria).where(Auditoria.accion == "sesion.reutilizacion")))
    )
    assert despues == antes
    assert fila_de_token(session, token).motivo_revocacion == "salida"


def test_AC_17_un_token_inventado_no_cambia_nada(app, usuario_por_rol, session):
    usuario = usuario_por_rol("Almacenista")
    cliente = entrar(app, usuario)
    antes = [(f.id, f.revocada_en) for f in filas_de(session, usuario.usuario)]

    r = cliente_con(app, refresh="a" * 64).post("/api/sesion/refresh")

    assert r.status_code == 401
    assert [(f.id, f.revocada_en) for f in filas_de(session, usuario.usuario)] == antes
    assert cliente.get("/api/sesion").status_code == 200
