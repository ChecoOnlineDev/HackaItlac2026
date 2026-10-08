"""AC-30 (FEAT-011): importar desde Excel pide `inventario.importar`, no `inventario.entradas`."""

import uuid

from app.modulos.acceso.permisos import P
from tests.importacion.ayudas import ARCHIVO, IMPORTACION, VISTA_PREVIA, cuerpo, fila

PLANTILLA = "/api/importacion/plantilla"


def test_AC_30_inventario_importar_abre_la_importacion_y_la_plantilla(cliente_con):
    cliente = cliente_con({P.INVENTARIO_IMPORTAR}, almacen="KEP")
    assert cliente.get(PLANTILLA).status_code == 200
    assert cliente.post(VISTA_PREVIA, json=cuerpo([fila("X", cantidad=1)])).status_code == 200


def test_AC_30_inventario_entradas_no_basta_para_importar(cliente_con):
    cliente = cliente_con({P.INVENTARIO_ENTRADAS}, almacen="KEP")
    assert cliente.get(PLANTILLA).status_code == 403
    assert cliente.post(VISTA_PREVIA, json=cuerpo([fila("X", cantidad=1)])).status_code == 403
    assert cliente.post(IMPORTACION, json=cuerpo([], id_lote=str(uuid.uuid4()))).status_code == 403
    assert cliente.post(ARCHIVO, files={"archivo": ("a.xlsx", b"x")}).status_code == 403


def test_AC_30_confirmar_pide_importar_y_tambien_entradas(cliente_con):
    """La carga escribe un vale de entrada (`movimientos`): sin `inventario.entradas`, 403."""
    solo_importar = cliente_con({P.INVENTARIO_IMPORTAR}, almacen="KEP")
    r = solo_importar.post(IMPORTACION, json=cuerpo([], id_lote=str(uuid.uuid4())))
    assert r.status_code == 403
