"""Los siete tipos de vale están registrados con su permiso y ninguno es un stub pendiente."""

import uuid

from app.modulos.acceso.permisos import P
from app.modulos.movimientos.models import TipoVale
from app.modulos.movimientos.tipos import TIPOS, manejador_de
from app.modulos.movimientos.tipos.base import TipoPendiente

PENDIENTES: list[TipoVale] = []  # ya no queda ninguno: los siete tipos del MVP están hechos


def test_todos_los_tipos_de_vale_estan_registrados_con_su_permiso():
    assert set(TIPOS) == set(TipoVale)
    permisos = {t: manejador_de(t).permiso for t in TipoVale}
    assert permisos[TipoVale.ENTRADA] == P.INVENTARIO_ENTRADAS
    assert permisos[TipoVale.ENTREGA] == P.ENTREGAS_CREAR
    assert permisos[TipoVale.DEVOLUCION] == P.DEVOLUCIONES_CREAR
    assert permisos[TipoVale.TRASPASO] == P.TRASPASOS_OPERAR
    assert permisos[TipoVale.RECEPCION] == P.TRASPASOS_RECIBIR
    assert permisos[TipoVale.NO_ADEUDO] == P.NO_ADEUDO_EMITIR
    assert permisos[TipoVale.CANCELACION] == P.VALES_CANCELAR
    assert {t for t, m in TIPOS.items() if isinstance(m, TipoPendiente)} == set(PENDIENTES)


def test_los_endpoints_de_traspasos_no_adeudo_y_cancelacion_exigen_permiso(cliente_como):
    rh = cliente_como("Recursos Humanos")
    assert rh.get("/api/traspasos/por-recibir").status_code == 403
    sin_permiso = rh.post(
        f"/api/trabajadores/{uuid.uuid4()}/no-adeudo", json={"id_cliente": str(uuid.uuid4())}
    )
    assert sin_permiso.status_code == 403
    cancelacion = {"motivo": "Error", "id_cliente": str(uuid.uuid4()), "rehacer": False}
    assert rh.post(f"/api/vales/{uuid.uuid4()}/cancelacion", json=cancelacion).status_code == 403


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
