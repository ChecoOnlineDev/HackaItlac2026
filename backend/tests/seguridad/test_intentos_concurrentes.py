"""Endurecimiento (H2): el límite de intentos de contraseña y de PIN resiste ráfagas (US-ACC-001).

Antes del arreglo, el contador de fallos se leía y se escribía sin control de concurrencia: con
peticiones simultáneas se podían probar muchas más de cinco claves y MySQL resolvía algunos
choques como interbloqueo (error 1213), que salía como 500. Aquí cada hilo tiene su propia
conexión y los datos están confirmados, como en producción.
"""

from collections import Counter

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from app.core.excepciones import DemasiadosIntentos
from app.main import create_app
from app.modulos.acceso.exceptions import CredencialesIncorrectas, PinIncorrecto
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.acceso.service import AccesoService
from tests.seguridad.conftest import en_paralelo

INTENTOS = 40
INTENTOS_CONTRASENA = 120


def test_US_ACC_001_H2_contrasenas_malas_simultaneas_dejan_como_maximo_cinco_respuestas_401(
    engine, usuario_confirmado
):
    usuario = usuario_confirmado({P.VALES_VER})
    app = create_app()

    def intento():
        with TestClient(app) as cliente:
            return cliente.post(
                "/api/sesion", json={"usuario": usuario.usuario, "contrasena": "mala-contrasena"}
            ).status_code

    estados = Counter(en_paralelo([intento] * INTENTOS_CONTRASENA))

    assert not [e for e in estados if not isinstance(e, int)], estados
    assert estados.get(500, 0) == 0, estados  # ningún interbloqueo llega como error interno
    assert estados[401] <= 5, estados  # a lo más cinco intentos reales por ventana
    assert estados[401] + estados[429] == INTENTOS_CONTRASENA, estados


def test_US_ACC_001_H2_pines_malos_simultaneos_dejan_como_maximo_cinco_respuestas_incorrecto(
    engine, usuario_confirmado, sesion_independiente
):
    supervisor = usuario_confirmado({P.AUTORIZACIONES_RESOLVER})

    def intento():
        s = sesion_independiente()
        usuario = s.scalar(select(Usuario).where(Usuario.id == supervisor.id))
        try:
            AccesoService(s).verificar_pin(usuario, "0000")
        except PinIncorrecto:
            return "incorrecto"
        except DemasiadosIntentos:
            return "bloqueado"
        except DBAPIError as exc:
            return f"bd:{exc.orig.args[0]}"
        finally:
            s.close()
        return "acepto"

    resultados = Counter(en_paralelo([intento] * INTENTOS))

    assert set(resultados) <= {"incorrecto", "bloqueado"}, resultados  # ni 1213 ni excepciones
    assert resultados["incorrecto"] <= 5, resultados
    assert resultados["incorrecto"] + resultados["bloqueado"] == INTENTOS, resultados


def test_US_ACC_001_H2_autenticar_con_sesiones_propias_cuenta_como_maximo_cinco_fallos(
    engine, usuario_confirmado, sesion_independiente
):
    usuario = usuario_confirmado({P.VALES_VER})

    def intento():
        s = sesion_independiente()
        try:
            AccesoService(s).autenticar(usuario.usuario, "mala-contrasena")
        except CredencialesIncorrectas:
            return "incorrecta"
        except DemasiadosIntentos:
            return "bloqueado"
        except DBAPIError as exc:
            return f"bd:{exc.orig.args[0]}"
        finally:
            s.close()
        return "acepto"

    resultados = Counter(en_paralelo([intento] * INTENTOS))

    assert set(resultados) <= {"incorrecta", "bloqueado"}, resultados
    assert resultados["incorrecta"] <= 5, resultados


def test_US_ACC_001_H2_la_contrasena_buena_no_entra_mientras_dura_el_bloqueo(
    engine, usuario_confirmado, sesion_independiente
):
    usuario = usuario_confirmado({P.VALES_VER})
    app = create_app()
    with TestClient(app) as cliente:
        for _ in range(5):
            cliente.post("/api/sesion", json={"usuario": usuario.usuario, "contrasena": "x"})
        r = cliente.post(
            "/api/sesion", json={"usuario": usuario.usuario, "contrasena": usuario.contrasena}
        )
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) > 0
    assert r.json()["detalles"]["segundos_espera"] > 0


def test_US_ACC_001_H2_una_entrada_buena_reinicia_el_contador(engine, usuario_confirmado):
    usuario = usuario_confirmado({P.VALES_VER})
    app = create_app()
    with TestClient(app) as cliente:
        for _ in range(4):
            r = cliente.post("/api/sesion", json={"usuario": usuario.usuario, "contrasena": "x"})
            assert r.status_code == 401
        ok = cliente.post(
            "/api/sesion", json={"usuario": usuario.usuario, "contrasena": usuario.contrasena}
        )
        assert ok.status_code == 200
        # El contador volvió a cero: otros cuatro fallos siguen sin bloquear.
        for _ in range(4):
            r = cliente.post("/api/sesion", json={"usuario": usuario.usuario, "contrasena": "x"})
            assert r.status_code == 401
