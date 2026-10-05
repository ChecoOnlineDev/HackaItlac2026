"""Endurecimiento (H8): límite de tamaño del cuerpo de las peticiones.

413 `CUERPO_MUY_GRANDE` (JSON del contrato) cuando `Content-Length` pasa del límite de la ruta, y
también cuando no hay `Content-Length` (transferencia por trozos) y el flujo pasa del límite. Los
límites salen de `config.py`: 1 MB de JSON, 12 MB al crear o evaluar un vale, 3 MB la foto de un
trabajador y 6 MB la importación.
"""

import pytest

from app.config import get_settings
from app.limite_cuerpo import limite_para
from tests.movimientos.ayudas import (
    abastecer,
    crear_articulo,
    crear_trabajador,
    cuerpo_entrega,
)

MB = 1024 * 1024
JSON = {"content-type": "application/json"}
ZIP = "application/zip"


def _trozos(total: int, tamano: int = 64 * 1024):
    """Un cuerpo de `total` bytes enviado por trozos (httpx lo manda `chunked`, sin
    `Content-Length`)."""
    restante = total
    while restante > 0:
        n = min(tamano, restante)
        yield b"x" * n
        restante -= n


def _es_413(r) -> None:
    assert r.status_code == 413, r.text
    cuerpo = r.json()
    assert cuerpo["codigo"] == "CUERPO_MUY_GRANDE"
    assert cuerpo["mensaje"] and cuerpo["detalles"]["limite_bytes"] > 0


# -------------------------------------------------------------- por Content-Length


def test_H8_un_cuerpo_de_2_mb_en_el_login_sin_sesion_da_413(client):
    r = client.post("/api/sesion", content=b"x" * (2 * MB), headers=JSON)

    _es_413(r)
    assert r.json()["detalles"]["limite_bytes"] == 1 * MB


def test_H8_el_login_normal_sigue_funcionando(client, usuario_por_rol):
    usuario = usuario_por_rol("Almacenista")

    r = client.post(
        "/api/sesion", json={"usuario": usuario.usuario, "contrasena": usuario.contrasena}
    )

    assert r.status_code == 200


def test_H8_un_vale_de_13_mb_da_413_y_uno_de_cuerpo_razonable_no(almacenista):
    grande = almacenista.post("/api/vales", content=b"x" * (13 * MB), headers=JSON)
    _es_413(grande)
    assert grande.json()["detalles"]["limite_bytes"] == 12 * MB

    evaluar = almacenista.post("/api/vales/evaluar", content=b"x" * (13 * MB), headers=JSON)
    _es_413(evaluar)

    # Un cuerpo de 2 MB (más que el de JSON general) llega a la validación: 422, no 413.
    r = almacenista.post("/api/vales", content=b"{" + b" " * (2 * MB) + b"}", headers=JSON)
    assert r.status_code == 422, r.text


def test_H8_la_foto_de_un_trabajador_pasa_hasta_3_mb(cliente_como, session):
    rh = cliente_como("Recursos Humanos")
    trabajador = crear_trabajador(session)
    ruta = f"/api/trabajadores/{trabajador.id}/foto"

    grande = rh.post(ruta, files={"archivo": ("f.png", b"x" * (4 * MB), "image/png")})
    _es_413(grande)
    assert grande.json()["detalles"]["limite_bytes"] == 3 * MB

    # Una de 1 MB llega al servicio (que la rechaza por no ser imagen: 422, no 413).
    mediana = rh.post(ruta, files={"archivo": ("f.png", b"x" * (1 * MB), "image/png")})
    assert mediana.status_code != 413


def test_H8_la_importacion_pasa_hasta_6_mb(cliente_como):
    compras = cliente_como("Compras")

    grande = compras.post(
        "/api/importacion/archivo", files={"archivo": ("a.xlsx", b"x" * (7 * MB), ZIP)}
    )
    _es_413(grande)
    assert grande.json()["detalles"]["limite_bytes"] == 6 * MB

    mediano = compras.post(
        "/api/importacion/archivo", files={"archivo": ("a.xlsx", b"x" * (2 * MB), ZIP)}
    )
    assert mediano.status_code != 413


def test_H8_los_limites_por_ruta_salen_de_la_configuracion():
    ajustes = get_settings()
    assert limite_para(ajustes, "/api/sesion") == ajustes.limite_cuerpo_json
    assert limite_para(ajustes, "/api/vales") == ajustes.limite_cuerpo_vale
    assert limite_para(ajustes, "/api/vales/evaluar") == ajustes.limite_cuerpo_vale
    assert limite_para(ajustes, "/api/vales/abc/cancelacion") == ajustes.limite_cuerpo_json
    foto = limite_para(ajustes, "/api/trabajadores/abc/foto")
    assert foto == ajustes.limite_cuerpo_foto_trabajador
    assert limite_para(ajustes, "/api/importacion") == ajustes.limite_cuerpo_importacion
    assert limite_para(ajustes, "/api/importacion/archivo") == ajustes.limite_cuerpo_importacion


def test_H8_el_limite_es_configurable(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "limite_cuerpo_json", 1000)

    r = client.post("/api/sesion", content=b"x" * 2000, headers=JSON)

    _es_413(r)
    assert r.json()["detalles"]["limite_bytes"] == 1000


# ------------------------------------------------------------ sin Content-Length


def test_H8_un_cuerpo_por_trozos_sin_content_length_que_pasa_del_limite_da_413(client):
    peticion = client.build_request("POST", "/api/sesion", content=_trozos(3 * MB), headers=JSON)
    assert "content-length" not in peticion.headers  # se envía por trozos
    assert peticion.headers.get("transfer-encoding") == "chunked"

    r = client.send(peticion)

    _es_413(r)


def test_H8_un_cuerpo_por_trozos_dentro_del_limite_si_se_procesa(client, usuario_por_rol):
    import json

    usuario = usuario_por_rol("Almacenista")
    cuerpo = json.dumps({"usuario": usuario.usuario, "contrasena": usuario.contrasena}).encode()

    def trozos():
        yield cuerpo[:10]
        yield cuerpo[10:]

    r = client.post("/api/sesion", content=trozos(), headers=JSON)

    assert r.status_code == 200, r.text


def test_H8_por_trozos_en_un_vale_el_limite_es_el_del_vale(almacenista):
    dentro = almacenista.build_request("POST", "/api/vales", content=_trozos(8 * MB), headers=JSON)
    assert almacenista.send(dentro).status_code != 413  # 8 MB caben en un vale (y no es JSON: 422)

    fuera = almacenista.build_request("POST", "/api/vales", content=_trozos(13 * MB), headers=JSON)
    _es_413(almacenista.send(fuera))


# -------------------------------------------------------------- topes por campo


@pytest.fixture
def entrega_con_fotos(almacenista, compras, session):
    articulo = crear_articulo(session)
    abastecer(compras, articulo, 5)
    trabajador = crear_trabajador(session)

    def _armar(*fotos: str) -> dict:
        renglones = [{"codigo": articulo.codigo, "cantidad": 1, "foto": f} for f in fotos]
        return cuerpo_entrega(trabajador, renglones)

    return _armar


def test_H8_una_foto_de_mas_de_3_mb_en_un_renglon_se_rechaza(almacenista, entrega_con_fotos):
    foto = "data:image/png;base64," + "A" * 4_000_000  # pasa de los 4 millones de caracteres

    r = almacenista.post("/api/vales", json=entrega_con_fotos(foto))

    assert r.status_code == 422, r.text
    assert "foto" in r.text


def test_H8_las_fotos_de_un_vale_tienen_un_tope_en_total(almacenista, entrega_con_fotos):
    # Cada una cabe sola (3.6 millones de caracteres), pero tres suman más de 10 MB.
    foto = "data:image/png;base64," + "A" * 3_600_000

    r = almacenista.post("/api/vales", json=entrega_con_fotos(foto, foto, foto))

    assert r.status_code == 422, r.text
    assert "fotos del vale" in r.text
