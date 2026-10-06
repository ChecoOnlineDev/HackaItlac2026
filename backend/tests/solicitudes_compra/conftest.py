"""Fixtures de las pruebas de `solicitudes_compra`.

- `como("alm_mid")`: cliente con la sesión de un usuario de los datos de prueba.
- `con_permisos({P.X}, almacen="KEP")`: cliente de un usuario nuevo con un rol de esos permisos.
- `pedir(cliente, ...)`: levanta una solicitud por la API y devuelve su JSON.
"""

from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from tests.conftest import UsuarioPrueba, iniciar_sesion_en


@pytest.fixture(autouse=True)
def _archivos_tmp(tmp_path, monkeypatch):
    """Las firmas de los vales de las pruebas se guardan en una carpeta temporal."""
    monkeypatch.setattr(get_settings(), "archivos_dir", tmp_path)
    return tmp_path


@pytest.fixture
def como(app) -> Iterator[Callable[[str], TestClient]]:
    """`como("alm_mid")` -> cliente con la sesión iniciada de ese usuario de prueba."""
    clientes: list[TestClient] = []

    def _cliente(usuario: str) -> TestClient:
        cliente = TestClient(app)
        ajustes = get_settings()
        r = iniciar_sesion_en(cliente, UsuarioPrueba(usuario, ajustes.clave_datos_prueba))
        assert r.status_code == 200, r.text
        clientes.append(cliente)
        return cliente

    yield _cliente
    for c in clientes:
        c.close()


@pytest.fixture
def con_permisos(app, crear_usuario) -> Iterator[Callable[..., TestClient]]:
    """Cliente de un usuario nuevo con exactamente esos permisos y ese almacén."""
    clientes: list[TestClient] = []

    def _cliente(permisos, *, almacen: str | None = "KEP") -> TestClient:
        usuario = crear_usuario(set(permisos), almacen=almacen)
        cliente = TestClient(app)
        assert iniciar_sesion_en(cliente, usuario).status_code == 200
        clientes.append(cliente)
        return cliente

    yield _cliente
    for c in clientes:
        c.close()
