"""OF-02: control de versión sin cambiar las cookies ni atrapar colas antiguas."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.version_app import VersionAppMiddleware


def cliente() -> TestClient:
    app = FastAPI()
    app.add_middleware(VersionAppMiddleware, version_minima="1.10.0")

    @app.api_route("/api/{ruta:path}", methods=["GET", "POST"])
    def responder(ruta: str):
        return {"ok": True}

    return TestClient(app)


@pytest.mark.parametrize("version", [None, "1.10.0", "1.11.0", "2.0.0"])
def test_OF_02_web_y_apk_vigente_siguen_operando(version):
    headers = {"X-App-Version": version} if version is not None else {}
    assert cliente().get("/api/sesion", headers=headers).status_code == 200


@pytest.mark.parametrize("version", ["1.9.0", "0.1.0", "incorrecta", "", "1.10.0-beta"])
def test_OF_02_apk_antiguo_o_version_invalida_pide_actualizar(version):
    respuesta = cliente().get("/api/sesion", headers={"X-App-Version": version})
    assert respuesta.status_code == 426
    assert respuesta.json()["codigo"] == "APP_DESACTUALIZADA"


def test_OF_02_lotes_antiguos_se_aceptan_solo_en_post():
    client = cliente()
    headers = {"X-App-Version": "0.1.0"}
    assert client.post("/api/sincronizacion/lotes", headers=headers).status_code == 200
    assert client.get("/api/sincronizacion/lotes", headers=headers).status_code == 426
    assert client.post("/api/sincronizacion/lotes/otra", headers=headers).status_code == 426


def test_OF_02_configuracion_rechaza_version_invalida():
    with pytest.raises(ValueError):
        Settings(_env_file=None, app_version_minima="1.2")
