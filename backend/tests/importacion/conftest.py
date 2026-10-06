"""Fixtures de las pruebas de `importacion`.

- `compras`: sesión de quien importa a cualquier almacén: el Administrador (`inventario.entradas`,
  `catalogo.costos`, `almacenes.todos`). Compras es de Kepler y ya no carga otros almacenes (AC-06);
  esa regla se prueba con `cliente_con` y con `compras_de_kepler`.
- `compras_de_kepler`: sesión de Compras (almacén asignado: Kepler).
- `almacenista`: sesión del almacenista de Kepler (sin `inventario.entradas`).
- `cliente_con`: sesión de un rol nuevo con exactamente esos permisos y ese almacén.
"""

from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient

from tests.conftest import iniciar_sesion_en


@pytest.fixture
def compras(cliente_como) -> TestClient:
    return cliente_como("Administrador")


@pytest.fixture
def compras_de_kepler(cliente_como) -> TestClient:
    return cliente_como("Compras")


@pytest.fixture
def almacenista(cliente_como) -> TestClient:
    return cliente_como("Almacenista")


@pytest.fixture
def cliente_con(app, crear_usuario) -> Iterator[Callable[..., TestClient]]:
    clientes: list[TestClient] = []

    def _cliente(permisos, almacen: str | None = None) -> TestClient:
        usuario = crear_usuario(set(permisos), almacen=almacen)
        cliente = TestClient(app)
        respuesta = iniciar_sesion_en(cliente, usuario)
        assert respuesta.status_code == 200, respuesta.text
        clientes.append(cliente)
        return cliente

    yield _cliente
    for c in clientes:
        c.close()
