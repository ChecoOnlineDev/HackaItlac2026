"""Los tipos que otros agentes implementan están registrados, con sus endpoints, y responden 501.

Cuando un tipo se implemente, su prueba cambia aquí por las suyas (sin tocar `service.py` ni
`router.py`).
"""

import uuid

import pytest

from app.modulos.acceso.permisos import P
from app.modulos.movimientos.models import TipoVale
from app.modulos.movimientos.tipos import TIPOS, manejador_de
from app.modulos.movimientos.tipos.base import TipoPendiente

PENDIENTES = [
    TipoVale.TRASPASO,
    TipoVale.RECEPCION,
    TipoVale.CANCELACION,
]


def test_todos_los_tipos_de_vale_estan_registrados_con_su_permiso():
    assert set(TIPOS) == set(TipoVale)
    permisos = {t: manejador_de(t).permiso for t in TipoVale}
    assert permisos[TipoVale.ENTRADA] == P.INVENTARIO_ENTRADAS
    assert permisos[TipoVale.ENTREGA] == P.ENTREGAS_CREAR
    assert permisos[TipoVale.DEVOLUCION] == P.DEVOLUCIONES_CREAR
    assert permisos[TipoVale.TRASPASO] == P.TRASPASOS_OPERAR
    assert permisos[TipoVale.RECEPCION] == P.TRASPASOS_OPERAR
    assert permisos[TipoVale.NO_ADEUDO] == P.NO_ADEUDO_EMITIR
    assert permisos[TipoVale.CANCELACION] == P.VALES_CANCELAR
    assert {t for t, m in TIPOS.items() if isinstance(m, TipoPendiente)} == set(PENDIENTES)


@pytest.mark.parametrize("tipo", PENDIENTES)
def test_un_tipo_pendiente_responde_501_con_permiso_y_403_sin_el(almacenista, cliente_como, tipo):
    sin_permisos = cliente_como("Recursos Humanos")
    cuerpo = {"tipo": tipo.value, "id_cliente": str(uuid.uuid4()), "renglones": []}
    for ruta in ("/api/vales/evaluar", "/api/vales"):
        r = almacenista.post(ruta, json=cuerpo)
        assert r.status_code == 501, (tipo, ruta, r.text)
        assert (
            r.json()["codigo"] == "TIPO_NO_IMPLEMENTADO"
            and "todavía no está disponible" in (r.json()["mensaje"])
        )
        assert sin_permisos.post(ruta, json=cuerpo).status_code == 403  # sin el permiso del tipo


def test_los_endpoints_de_traspasos_y_cancelacion_existen(
    almacenista, compras, cliente_como, session
):
    rh = cliente_como("Recursos Humanos")
    assert almacenista.get("/api/traspasos/por-recibir").status_code == 501
    assert rh.get("/api/traspasos/por-recibir").status_code == 403
    cancelacion = {"motivo": "Error", "id_cliente": str(uuid.uuid4()), "rehacer": False}
    r = almacenista.post(f"/api/vales/{uuid.uuid4()}/cancelacion", json=cancelacion)
    assert r.status_code == 501
    assert rh.post(f"/api/vales/{uuid.uuid4()}/cancelacion", json=cancelacion).status_code == 403
    # Compras tiene `vales.cancelar`: el stub responde 501 y no 403.
    assert (
        compras.post(f"/api/vales/{uuid.uuid4()}/cancelacion", json=cancelacion).status_code == 501
    )


def test_un_tipo_nuevo_se_enchufa_sin_tocar_el_motor(almacenista, session, monkeypatch):
    """El ejemplo del README: se reemplaza una entrada de `TIPOS` por un manejador que hereda de
    `ManejadorTipo`; el router y el service ya lo usan."""
    from app.modulos.movimientos.contexto import DatosVale, Evaluacion, PlanBloqueo
    from app.modulos.movimientos.tipos.base import ManejadorTipo

    visto = {}

    class DevolucionDePrueba(ManejadorTipo):
        tipo = TipoVale.DEVOLUCION
        permiso = P.DEVOLUCIONES_CREAR

        def evaluar(self, ctx, cuerpo):
            visto["almacen"] = ctx.almacen.clave
            return Evaluacion()

        def bloqueos(self, ctx, cuerpo):
            return PlanBloqueo()

        def datos_vale(self, ctx, cuerpo, evaluacion):
            return DatosVale()

        def construir_movimientos(self, ctx, cuerpo, evaluacion):
            return []

    monkeypatch.setitem(TIPOS, TipoVale.DEVOLUCION, DevolucionDePrueba())
    r = almacenista.post("/api/vales/evaluar", json={"tipo": "DEVOLUCION", "renglones": []})
    assert r.status_code == 200 and visto["almacen"] == "KEP"
    assert r.json()["nivel"] == "VERDE" and r.json()["puede_confirmar"] is False


def test_un_tipo_que_admite_vale_sin_renglones_puede_confirmarse_sin_ellos(
    almacenista, monkeypatch
):
    """El vale de no adeudo no lleva renglones ni movimientos (`admite_sin_renglones`)."""
    from app.modulos.movimientos.contexto import DatosVale, Evaluacion, PlanBloqueo
    from app.modulos.movimientos.tipos.base import ManejadorTipo

    class SinRenglones(ManejadorTipo):
        tipo = TipoVale.NO_ADEUDO
        permiso = P.NO_ADEUDO_EMITIR
        admite_sin_renglones = True

        def evaluar(self, ctx, cuerpo):
            return Evaluacion()

        def bloqueos(self, ctx, cuerpo):
            return PlanBloqueo()

        def datos_vale(self, ctx, cuerpo, evaluacion):
            return DatosVale()

        def construir_movimientos(self, ctx, cuerpo, evaluacion):
            return []

    monkeypatch.setitem(TIPOS, TipoVale.NO_ADEUDO, SinRenglones())
    r = almacenista.post("/api/vales/evaluar", json={"tipo": "NO_ADEUDO"})
    assert r.status_code == 200 and r.json()["puede_confirmar"] is True
    ok = almacenista.post(
        "/api/vales", json={"tipo": "NO_ADEUDO", "id_cliente": str(uuid.uuid4()), "renglones": []}
    )
    assert ok.status_code == 201 and ok.json()["folio"].startswith("KEP-NAD-")
    assert ok.json()["renglones"] == []
