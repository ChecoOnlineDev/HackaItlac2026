"""Las pruebas de `autorizaciones` usan códigos inventados (por ejemplo `ALT-024`): aquí se
apaga el verificador real de `movimientos`, que rechazaría un código desconocido como rojo (A-06).

La integración con la evaluación real (un rojo no se envía a autorización) se prueba en
`tests/movimientos/test_autorizacion_integracion.py`.
"""

import pytest


@pytest.fixture(autouse=True)
def _sin_verificador_de_movimientos(monkeypatch):
    monkeypatch.setattr(
        "app.modulos.autorizaciones.router.crear_verificador",
        lambda session, usuario: lambda almacen_id, trabajador_id, renglones: None,
    )
