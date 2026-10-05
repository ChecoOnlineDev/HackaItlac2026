"""Las pruebas de `autorizaciones` usan códigos inventados (por ejemplo `ALT-024`): aquí se
reemplaza el verificador real de `movimientos` por uno falso que arma los renglones como lo haría
la evaluación del servidor (artículo, límite 2, excedente, regla L-01). Los códigos que empiezan
con `ROJO` simulan un renglón en rojo (A-06) y `VERDE` uno que no necesita autorización.

La integración con la evaluación real (datos del servidor, un rojo o un verde no se envía a
autorización) se prueba en `tests/movimientos/test_autorizacion_integracion.py` y
`tests/movimientos/test_autorizacion_endurecimiento.py`.
"""

import pytest

from app.modulos.autorizaciones.exceptions import RenglonNoAutorizable
from app.modulos.autorizaciones.schemas import RenglonSolicitud


def verificador_falso(session, usuario):
    def verificar(almacen_id, trabajador_id, renglones):
        salida = []
        for r in renglones:
            if r.codigo.startswith("ROJO"):
                raise RenglonNoAutorizable(
                    f"El renglón {r.codigo} está en rojo (A-06).", {"codigo": r.codigo}
                )
            if r.codigo.startswith("VERDE"):
                raise RenglonNoAutorizable(f"El renglón {r.codigo} no necesita autorización.")
            salida.append(
                RenglonSolicitud(
                    codigo=r.codigo,
                    articulo="Guante de carnaza",
                    cantidad=r.cantidad,
                    limite=2,
                    tiene=0,
                    excedente=max(0, r.cantidad - 2),
                    regla="L-01",
                )
            )
        return salida

    return verificar


@pytest.fixture(autouse=True)
def _verificador_falso(monkeypatch):
    monkeypatch.setattr("app.modulos.autorizaciones.router.crear_verificador", verificador_falso)
