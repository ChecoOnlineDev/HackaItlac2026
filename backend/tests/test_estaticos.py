"""Entrega de la interfaz construida y cabeceras de seguridad (TASK-F0-04, ADR-002)."""

import base64
import hashlib

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from app.core.handlers import registrar_handlers
from app.estaticos import configurar_interfaz

SCRIPT = "window.__reactRouterContext = {};"
INDEX = (
    '<!DOCTYPE html><html><head><title>IMHOTEP</title></head><body><div id="r"></div>'
    f"<script>{SCRIPT}</script>"
    '<script type="module" src="/assets/app-abc123.js"></script></body></html>'
)


def _app(directorio, cookie_segura=False) -> FastAPI:
    app = FastAPI()
    registrar_handlers(app)
    api = APIRouter(prefix="/api")

    @api.get("/salud")
    def salud():
        return {"estado": "ok"}

    app.include_router(api)
    configurar_interfaz(app, directorio, cookie_segura=cookie_segura)
    return app


@pytest.fixture
def interfaz(tmp_path):
    carpeta = tmp_path / "interfaz"
    (carpeta / "assets").mkdir(parents=True)
    (carpeta / "index.html").write_text(INDEX, encoding="utf-8")
    (carpeta / "assets" / "app-abc123.js").write_text("console.log(1)", encoding="utf-8")
    (carpeta / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (tmp_path / "secreto.txt").write_text("secreto", encoding="utf-8")
    return carpeta


@pytest.fixture
def web(interfaz):
    return TestClient(_app(interfaz))


@pytest.mark.parametrize("ruta", ["/", "/entrar", "/vales/xyz", "/v/tok_abc", "/a/b/c"])
def test_rutas_de_pantalla_entregan_index(web, ruta):
    r = web.get(ruta)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert r.headers["cache-control"] == "no-cache"
    assert "IMHOTEP" in r.text


def test_api_desconocida_es_404_json_y_no_index(web):
    r = web.get("/api/inexistente")
    assert r.status_code == 404
    assert r.json()["codigo"] == "NO_ENCONTRADO"
    assert "html" not in r.headers["content-type"]
    assert web.get("/api").status_code == 404


def test_la_api_real_sigue_respondiendo(web):
    assert web.get("/api/salud").json() == {"estado": "ok"}


def test_asset_con_huella_se_guarda_un_anio(web):
    r = web.get("/assets/app-abc123.js")
    assert r.status_code == 200
    assert "javascript" in r.headers["content-type"]
    assert r.headers["cache-control"] == "public, max-age=31536000, immutable"


def test_asset_inexistente_es_404_no_index(web):
    r = web.get("/assets/no-existe.js")
    assert r.status_code == 404
    assert "html" not in r.headers["content-type"]


def test_archivo_de_la_raiz_se_entrega_con_su_tipo(web):
    r = web.get("/logo.png")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.headers["cache-control"] == "public, max-age=3600"


@pytest.mark.parametrize("ruta", ["/..%2Fsecreto.txt", "/../secreto.txt", "/%2e%2e/secreto.txt"])
def test_no_sale_de_la_carpeta(web, ruta):
    r = web.get(ruta)
    assert "secreto" not in r.text.replace("IMHOTEP", "")


def test_cabeceras_de_seguridad_y_csp_con_hash_del_script_en_linea(web):
    r = web.get("/entrar")
    h = r.headers
    assert h["x-content-type-options"] == "nosniff"
    assert h["x-frame-options"] == "DENY"
    assert h["referrer-policy"] == "same-origin"
    assert "camera=(self)" in h["permissions-policy"]
    huella = base64.b64encode(hashlib.sha256(SCRIPT.encode()).digest()).decode()
    csp = h["content-security-policy"]
    assert f"'sha256-{huella}'" in csp
    assert "unsafe-eval" not in csp
    assert "img-src 'self' data: blob:" in csp
    assert "strict-transport-security" not in h


def test_la_api_no_lleva_csp_pero_si_las_demas_cabeceras(web):
    r = web.get("/api/salud")
    assert "content-security-policy" not in r.headers
    assert r.headers["x-content-type-options"] == "nosniff"


def test_hsts_solo_con_cookie_segura(interfaz):
    r = TestClient(_app(interfaz, cookie_segura=True)).get("/")
    assert "max-age" in r.headers["strict-transport-security"]


def test_consulta_de_solo_cabeceras_tambien_responde(web):
    assert web.request("HEAD", "/entrar").status_code == 200
    assert web.request("HEAD", "/assets/app-abc123.js").status_code == 200


def test_sin_carpeta_de_interfaz_solo_hay_api(tmp_path):
    web = TestClient(_app(tmp_path / "no-existe"))
    assert web.get("/api/salud").status_code == 200
    r = web.get("/entrar")
    assert r.status_code == 404
    assert r.json()["codigo"] == "NO_ENCONTRADO"
