"""Endurecimiento (H2/H12): un interbloqueo (1213) o una espera vencida (1205) se reintenta de forma
acotada y nunca llega como 500."""

import pytest
from sqlalchemy.exc import OperationalError

from app.core.excepciones import ServicioOcupado
from app.core.reintento import reintentar_si_interbloqueo
from app.modulos.acceso.service import AccesoService


class SesionFalsa:
    def __init__(self) -> None:
        self.reversiones = 0

    def rollback(self) -> None:
        self.reversiones += 1


def _error_bd(errno: int) -> OperationalError:
    return OperationalError("UPDATE usuario ...", {}, Exception(errno, "error de MySQL"))


@pytest.mark.parametrize("errno", [1213, 1205])
def test_US_ACC_001_H2_un_interbloqueo_se_reintenta_y_luego_funciona(errno):
    sesion, llamadas = SesionFalsa(), []

    def operacion():
        llamadas.append(1)
        if len(llamadas) < 3:
            raise _error_bd(errno)
        return "ok"

    assert reintentar_si_interbloqueo(sesion, operacion, pausa=0) == "ok"
    assert len(llamadas) == 3 and sesion.reversiones == 2


def test_US_ACC_001_H2_si_el_interbloqueo_persiste_se_responde_servicio_ocupado():
    sesion, llamadas = SesionFalsa(), []

    def operacion():
        llamadas.append(1)
        raise _error_bd(1213)

    with pytest.raises(ServicioOcupado):
        reintentar_si_interbloqueo(sesion, operacion, pausa=0)
    assert len(llamadas) == 3  # acotado


def test_US_ACC_001_H2_otro_error_de_la_base_no_se_reintenta():
    sesion, llamadas = SesionFalsa(), []

    def operacion():
        llamadas.append(1)
        raise _error_bd(1062)

    with pytest.raises(OperationalError):
        reintentar_si_interbloqueo(sesion, operacion, pausa=0)
    assert len(llamadas) == 1 and sesion.reversiones == 0


def test_US_ACC_001_H2_el_login_con_un_interbloqueo_pasajero_sigue_funcionando(
    client, usuario_por_rol, monkeypatch
):
    original = AccesoService._autenticar
    fallos = []

    def con_un_choque(self, nombre, contrasena):
        if not fallos:
            fallos.append(1)
            raise _error_bd(1213)
        return original(self, nombre, contrasena)

    monkeypatch.setattr(AccesoService, "_autenticar", con_un_choque)
    monkeypatch.setattr("app.core.reintento.time.sleep", lambda s: None)
    usuario = usuario_por_rol("Almacenista")

    r = client.post(
        "/api/sesion", json={"usuario": usuario.usuario, "contrasena": usuario.contrasena}
    )

    assert r.status_code == 200, r.text


def test_US_ACC_001_H2_el_login_con_un_interbloqueo_permanente_es_503_no_500(
    client, usuario_por_rol, monkeypatch
):
    def siempre(self, nombre, contrasena):
        raise _error_bd(1213)

    monkeypatch.setattr(AccesoService, "_autenticar", siempre)
    monkeypatch.setattr("app.core.reintento.time.sleep", lambda s: None)

    r = client.post("/api/sesion", json={"usuario": "almacenista", "contrasena": "x"})

    assert r.status_code == 503
    assert r.json()["codigo"] == "SERVICIO_NO_DISPONIBLE"


def test_US_ACC_001_H2_un_interbloqueo_en_cualquier_endpoint_tampoco_es_500(app, monkeypatch):
    from fastapi.testclient import TestClient

    @app.get("/api/_prueba_interbloqueo")
    def _choque():
        raise _error_bd(1213)

    with TestClient(app, raise_server_exceptions=False) as cliente:
        r = cliente.get("/api/_prueba_interbloqueo")

    assert r.status_code == 503 and r.json()["codigo"] == "SERVICIO_NO_DISPONIBLE"
