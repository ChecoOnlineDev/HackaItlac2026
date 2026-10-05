"""Ficha de pieza `GET /api/piezas/{id}` (C-02): estado, inspección, ubicación e historial."""

import uuid
from datetime import datetime, timedelta

from app.core.tiempo import ahora_utc, hoy_mx
from app.modulos.almacenes.models import UbicacionVirtual
from app.modulos.movimientos.models import TipoVale

RUTA = "/api/piezas"


def _instante(dias_atras: int) -> datetime:
    """Un instante UTC sin zona, `dias_atras` días antes de ahora (para fijar el orden)."""
    return ahora_utc().replace(microsecond=0) - timedelta(days=dias_atras)


def _armar_pieza_con_vida_completa(datos):
    """Entrada, inspección, cambio de estado, ajuste de vigencia y entrega, en ese orden."""
    juan = datos.trabajador("Juan Pérez")
    articulo = datos.articulo("Arnés de cuerpo completo", control="PIEZA")
    pieza = datos.pieza(articulo, None, serie="SN-HIST-1")

    entrada = datos.vale(TipoVale.ENTRADA, "KEP", responsable="compras", creado_en=_instante(10))
    datos.movimiento(
        entrada,
        articulo,
        datos.ub_virtual(UbicacionVirtual.PROVEEDOR),
        datos.ub_almacen("KEP"),
        pieza=pieza,
    )
    inspeccion = datos.inspeccion(
        pieza,
        vigente_hasta=hoy_mx() + timedelta(days=100),
        usuario="almacenista",
        creado_en=_instante(8),
        observacion="Costuras en buen estado",
    )
    datos.cambio_estado(
        pieza, "APTO", "NO_APTO", creado_en=_instante(6), observacion="Cinta deshilachada"
    )
    datos.ajuste_vigencia(
        pieza,
        inspeccion,
        anterior=hoy_mx() + timedelta(days=100),
        nuevo=hoy_mx() + timedelta(days=60),
        motivo="Uso intensivo",
        creado_en=_instante(4),
    )
    entrega = datos.vale(
        TipoVale.ENTREGA, "KEP", trabajador=juan, creado_en=_instante(2), responsable="almacenista"
    )
    datos.movimiento(
        entrega, articulo, datos.ub_almacen("KEP"), datos.ub_trabajador(juan), pieza=pieza
    )
    pieza.ubicacion_id = datos.ub_trabajador(juan).id
    pieza.inspeccion_vigente_hasta = hoy_mx() + timedelta(days=60)
    datos.session.flush()
    return pieza, entrada, entrega, juan


def test_C_02_la_ficha_trae_estado_inspeccion_ubicacion_y_articulo(cliente_como, datos):
    pieza, _, _, juan = _armar_pieza_con_vida_completa(datos)

    respuesta = cliente_como("Almacenista").get(f"{RUTA}/{pieza.id}")

    assert respuesta.status_code == 200, respuesta.text
    ficha = respuesta.json()
    assert ficha["id"] == str(pieza.id)
    assert ficha["codigo"] == pieza.codigo
    assert ficha["numero_serie"] == "SN-HIST-1"
    assert ficha["estado"] == "APTO"
    assert ficha["articulo"]["nombre"] == "Arnés de cuerpo completo"
    assert ficha["inspeccion_vigente_hasta"] == (hoy_mx() + timedelta(days=60)).isoformat()
    assert ficha["inspeccion_vigente"] is True
    assert ficha["ultima_inspeccion"]["resultado"] == "APTO"
    assert ficha["ultima_inspeccion"]["observacion"] == "Costuras en buen estado"
    assert ficha["ubicacion"]["tipo"] == "TRABAJADOR"
    assert ficha["ubicacion"]["trabajador_id"] == str(juan.id)


def test_C_02_el_historial_junta_movimientos_inspecciones_cambios_de_estado_y_ajustes(
    cliente_como, datos
):
    pieza, entrada, entrega, _ = _armar_pieza_con_vida_completa(datos)

    historial = cliente_como("Almacenista").get(f"{RUTA}/{pieza.id}").json()["historial"]

    assert [h["tipo"] for h in historial] == [
        "MOVIMIENTO",  # la entrega, la más reciente
        "AJUSTE_VIGENCIA",
        "CAMBIO_ESTADO",
        "INSPECCION",
        "MOVIMIENTO",  # la entrada, la más antigua
    ]
    fechas = [h["fecha"] for h in historial]
    assert fechas == sorted(fechas, reverse=True)

    mov_entrega, ajuste, cambio, inspeccion, mov_entrada = historial
    assert mov_entrega["folio"] == entrega.folio
    assert mov_entrega["tipo_vale"] == "ENTREGA"
    assert "KEP" in mov_entrega["origen"]
    assert "Juan Pérez" in mov_entrega["destino"]
    assert mov_entrega["responsable"]
    assert mov_entrada["folio"] == entrada.folio
    assert mov_entrada["tipo_vale"] == "ENTRADA"
    assert mov_entrada["origen"] == "Proveedor"
    assert "KEP" in mov_entrada["destino"]
    assert inspeccion["resultado"] == "APTO"
    assert inspeccion["vigente_hasta"] == (hoy_mx() + timedelta(days=100)).isoformat()
    assert cambio["estado_anterior"] == "APTO" and cambio["estado_nuevo"] == "NO_APTO"
    assert cambio["observacion"] == "Cinta deshilachada"
    assert ajuste["vigente_hasta_anterior"] == (hoy_mx() + timedelta(days=100)).isoformat()
    assert ajuste["vigente_hasta"] == (hoy_mx() + timedelta(days=60)).isoformat()
    assert ajuste["observacion"] == "Uso intensivo"


def test_C_02_el_historial_solo_trae_los_hechos_de_esa_pieza(cliente_como, datos):
    pieza, *_ = _armar_pieza_con_vida_completa(datos)
    otra_pieza, *_ = _armar_pieza_con_vida_completa(datos)

    historial = cliente_como("Almacenista").get(f"{RUTA}/{pieza.id}").json()["historial"]
    historial_otra = cliente_como("Almacenista").get(f"{RUTA}/{otra_pieza.id}").json()["historial"]

    assert len(historial) == 5
    assert len(historial_otra) == 5
    folios = {h["folio"] for h in historial if h["folio"]}
    folios_otra = {h["folio"] for h in historial_otra if h["folio"]}
    assert folios.isdisjoint(folios_otra)


def test_C_02_una_pieza_sin_movimientos_ni_inspecciones_tiene_historial_vacio(cliente_como, datos):
    articulo = datos.articulo("Casco nuevo", control="PIEZA")
    pieza = datos.pieza(articulo, None)

    ficha = cliente_como("Almacenista").get(f"{RUTA}/{pieza.id}").json()

    assert ficha["historial"] == []
    assert ficha["ubicacion"] is None
    assert ficha["ultima_inspeccion"] is None
    assert ficha["inspeccion_vigente"] is False
    assert ficha["inspeccion_vigente_hasta"] is None


def test_C_02_una_inspeccion_vencida_no_es_vigente_y_se_muestra_su_fecha(cliente_como, datos):
    articulo = datos.articulo("Línea de vida", control="PIEZA")
    ayer = hoy_mx() - timedelta(days=1)
    pieza = datos.pieza(articulo, datos.ub_almacen("KEP"), vigente_hasta=ayer)

    ficha = cliente_como("Almacenista").get(f"{RUTA}/{pieza.id}").json()

    assert ficha["inspeccion_vigente"] is False
    assert ficha["inspeccion_vigente_hasta"] == ayer.isoformat()


def test_C_02_la_pieza_en_un_almacen_dice_cual(cliente_como, datos):
    articulo = datos.articulo("Taladro", control="PIEZA")
    pieza = datos.pieza(articulo, datos.ub_almacen("CON"))

    ficha = cliente_como("Almacenista").get(f"{RUTA}/{pieza.id}").json()

    assert ficha["ubicacion"]["tipo"] == "ALMACEN"
    assert ficha["ubicacion"]["almacen_clave"] == "CON"


def test_C_02_la_ficha_de_una_pieza_que_no_existe_responde_404(cliente_como):
    respuesta = cliente_como("Almacenista").get(f"{RUTA}/{uuid.uuid4()}")

    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "NO_ENCONTRADO"


def test_C_02_sin_catalogo_ver_la_ficha_responde_403(cliente_como, datos):
    articulo = datos.articulo("Taladro", control="PIEZA")
    pieza = datos.pieza(articulo, datos.ub_almacen("KEP"))

    respuesta = cliente_como("Recursos Humanos").get(f"{RUTA}/{pieza.id}")

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "SIN_PERMISO"


def test_C_02_la_ficha_sin_sesion_responde_401(client):
    assert client.get(f"{RUTA}/{uuid.uuid4()}").status_code == 401


def test_RG_12_la_ficha_de_pieza_nunca_trae_costos(cliente_como, datos):
    articulo = datos.articulo("Detector caro", control="PIEZA", costo="55555.55")
    pieza = datos.pieza(articulo, datos.ub_almacen("KEP"))

    respuesta = cliente_como("Compras").get(f"{RUTA}/{pieza.id}")

    assert respuesta.status_code == 200
    assert "55555.55" not in respuesta.text
    assert "costo" not in respuesta.text.lower()
