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


# --- Aplicación instalable (PWA): sin modo sin conexión ---


@pytest.fixture
def web_pwa(interfaz):
    (interfaz / "manifest.webmanifest").write_text('{"name": "IMHOTEP"}', encoding="utf-8")
    (interfaz / "sw.js").write_text("self.addEventListener('fetch', () => {});", encoding="utf-8")
    (interfaz / "offline.html").write_text(
        "<!doctype html><title>Sin conexión</title>", encoding="utf-8"
    )
    (interfaz / "icono-192.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    return TestClient(_app(interfaz))


def test_pwa_manifiesto_con_su_tipo_y_sin_caer_en_index(web_pwa):
    r = web_pwa.get("/manifest.webmanifest")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/manifest+json")
    assert r.json()["name"] == "IMHOTEP"


def test_pwa_service_worker_con_tipo_alcance_y_sin_cache(web_pwa):
    r = web_pwa.get("/sw.js")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/javascript")
    assert r.headers["cache-control"] == "no-cache"
    assert r.headers["service-worker-allowed"] == "/"
    assert "addEventListener" in r.text


def test_pwa_pagina_sin_conexion_e_iconos_se_entregan_tal_cual(web_pwa):
    r = web_pwa.get("/offline.html")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "Sin conexión" in r.text
    r = web_pwa.get("/icono-192.png")
    assert r.headers["content-type"] == "image/png"


def test_pwa_csp_permite_manifiesto_y_worker_sin_relajar_lo_demas(web_pwa):
    csp = web_pwa.get("/entrar").headers["content-security-policy"]
    assert "manifest-src 'self'" in csp
    assert "worker-src 'self';" in csp  # S-04: sin `blob:`; ningún código usa workers en memoria
    assert "default-src 'self'" in csp
    assert "unsafe-eval" not in csp
    assert "script-src 'self' 'sha256-" in csp
    assert "connect-src 'self'" in csp


def test_S_07_la_api_responde_sin_guardar_en_cache(web_pwa):
    assert web_pwa.get("/api/salud").headers["cache-control"] == "no-store"


def test_pwa_la_api_no_recibe_cabeceras_del_service_worker(web_pwa):
    r = web_pwa.get("/api/salud")
    assert r.json() == {"estado": "ok"}
    assert "service-worker-allowed" not in r.headers
