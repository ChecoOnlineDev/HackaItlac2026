"""Endurecimiento (H6): en producción la aplicación se niega a arrancar con una configuración
insegura y no publica su documentación interactiva; en desarrollo solo avisa."""

import logging

import pytest
from fastapi.testclient import TestClient

from app.config import ConfiguracionInsegura, Settings
from app.main import create_app, verificar_configuracion

CLAVE_BUENA = "k3Yq9-zX2mP7vL4nB8tR1wC6dF0hJ5sA3gU9eY2oI7pQ"  # 44 caracteres


def ajustes(**cambios) -> Settings:
    base = {
        "entorno": "produccion",
        "clave_sesion": CLAVE_BUENA,
        "cookie_segura": True,
        "cargar_datos_prueba": False,
        "clave_datos_prueba": "",
    }
    return Settings(_env_file=None, **(base | cambios))


def test_H6_una_configuracion_segura_arranca_en_produccion():
    verificar_configuracion(ajustes())  # no lanza


@pytest.mark.parametrize(
    ("cambios", "texto"),
    [
        ({"clave_sesion": "cambia-esta-clave"}, "CLAVE_SESION"),
        ({"clave_sesion": "cambia-esta-clave-larga"}, "CLAVE_SESION"),
        ({"clave_sesion": "corta-pero-no-de-ejemplo"}, "menos de 32"),
        ({"cookie_segura": False}, "COOKIE_SEGURA"),
        ({"cargar_datos_prueba": True, "clave_datos_prueba": ""}, "CLAVE_DATOS_PRUEBA"),
        ({"cargar_datos_prueba": True, "clave_datos_prueba": "   "}, "CLAVE_DATOS_PRUEBA"),
    ],
)
def test_H6_produccion_se_niega_a_arrancar_con_una_configuracion_insegura(cambios, texto):
    with pytest.raises(ConfiguracionInsegura, match=texto):
        verificar_configuracion(ajustes(**cambios))


def test_H6_cargar_datos_de_prueba_con_clave_definida_si_arranca():
    verificar_configuracion(ajustes(cargar_datos_prueba=True, clave_datos_prueba="Otra-clave-9!"))


def test_H6_el_valor_por_defecto_de_la_clave_de_sesion_no_sirve_en_produccion():
    por_defecto = Settings(_env_file=None, entorno="produccion", cookie_segura=True)
    with pytest.raises(ConfiguracionInsegura):
        verificar_configuracion(por_defecto)


def test_H6_en_desarrollo_solo_avisa_en_el_registro(caplog):
    inseguro = ajustes(entorno="desarrollo", clave_sesion="cambia-esta-clave", cookie_segura=False)
    with caplog.at_level(logging.WARNING, logger="imhotep"):
        verificar_configuracion(inseguro)  # no lanza
    assert "CLAVE_SESION" in caplog.text and "COOKIE_SEGURA" in caplog.text


def test_H6_create_app_en_produccion_con_clave_debil_no_arranca(monkeypatch):
    monkeypatch.setattr("app.main.get_settings", lambda: ajustes(clave_sesion="cambia-esta-clave"))
    with pytest.raises(ConfiguracionInsegura):
        create_app()


def test_H6_el_entorno_solo_admite_desarrollo_o_produccion():
    with pytest.raises(ValueError):
        Settings(_env_file=None, entorno="staging")


def test_H6_en_produccion_no_hay_documentacion_interactiva(monkeypatch):
    monkeypatch.setattr("app.main.get_settings", lambda: ajustes())
    with TestClient(create_app()) as cliente:
        for ruta in ("/api/docs", "/api/redoc", "/api/openapi.json", "/docs", "/openapi.json"):
            r = cliente.get(ruta)
            assert r.status_code == 404, ruta


def test_H6_en_desarrollo_la_documentacion_sigue_disponible(monkeypatch):
    monkeypatch.setattr("app.main.get_settings", lambda: ajustes(entorno="desarrollo"))
    with TestClient(create_app()) as cliente:
        assert cliente.get("/api/docs").status_code == 200
        assert cliente.get("/api/redoc").status_code == 200
        assert cliente.get("/api/openapi.json").status_code == 200
