# ruff: noqa: F811  (los fixtures importados se piden por nombre en cada prueba)
"""TRASPASO, la salida (US-TRS-001): X-01 a X-04, X-06, X-07, X-09, F-09 y las reglas generales.

Los almacenistas de prueba: KEP (`almacenista`), CON, MID, HYL. Las existencias nacen de ENTRADAS
reales por la API (Compras).
"""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.tiempo import hoy_mx
from app.modulos.almacenes.models import Almacen
from app.modulos.catalogo.models import EstadoPieza
from app.modulos.movimientos.models import Vale
from tests.movimientos.ayudas import (
    abastecer,
    crear_articulo,
    crear_trabajador,
    cuerpo_entrega,
    existencia,
    total_movimientos,
    total_vales,
)
from tests.movimientos.ayudas_traspasos import (
    VALES,
    almacen_id,
    cliente_almacen,  # noqa: F401  (fixture)
    cuerpo_traspaso,
    en_transito,
    enviar,
    evaluar_traspaso,
    movimientos_del_vale,
    pieza,
    reglas,
    renglon,
    total_en_almacenes,
    ubicacion_de_pieza,
    vale,
)
from tests.movimientos.test_entrega import pieza_en_kep
from tests.movimientos.test_invariantes import revisar_folios, revisar_invariantes


@pytest.fixture
def almacenista(cliente_como):
    """El que opera los traspasos de Kepler: su supervisor (`traspasos.operar` es del Supervisor,
    tabla 8.2; el almacenista no los opera). Se llama `almacenista` por las pruebas ya escritas."""
    return cliente_como("Supervisor")


def vigencia():
    return hoy_mx() + timedelta(days=60)


# ------------------------------------------------------------------------ X-01, X-06, X-07


def test_X_01_el_traspaso_saca_del_origen_y_la_existencia_queda_en_transito(
    almacenista, compras, cliente_almacen, session
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 10)
    antes = total_en_almacenes(session, guantes)

    traspaso = enviar(almacenista, session, "CON", [renglon(guantes.codigo, 4)])

    assert existencia(session, "KEP", guantes) == 6
    assert existencia(session, "CON", guantes) == 0  # todavía no llega
    assert en_transito(session, guantes) == 4
    # Lo que está En tránsito no cuenta para ningún almacén.
    assert total_en_almacenes(session, guantes) == antes - 4
    # Tampoco la consulta de existencias del almacén de destino lo cuenta.
    r = cliente_almacen("CON").get(f"/api/almacenes/{almacen_id(session, 'CON')}/existencias")
    assert all(
        e["articulo_id"] != str(guantes.id) or e["cantidad"] == 0 for e in r.json()["elementos"]
    )
    assert traspaso["renglones"][0]["reglas"][:2] == ["X-01", "X-07"]
    revisar_invariantes(session)
    revisar_folios(session)


def test_X_01_la_pieza_queda_en_transito_y_no_esta_en_ningun_almacen(almacenista, compras, session):
    articulo, p = pieza_en_kep(compras, session, vigente_hasta=vigencia())
    enviar(almacenista, session, "CON", [renglon(p.codigo)])
    assert ubicacion_de_pieza(session, p.codigo) == "EN_TRANSITO"
    assert existencia(session, "KEP", articulo) == 0
    assert existencia(session, "CON", articulo) == 0
    assert en_transito(session, articulo) == 1
    revisar_invariantes(session)


def test_X_03_la_pieza_en_transito_dice_hacia_donde_va_en_espanol(almacenista, compras, session):
    """El titular de una pieza en tránsito no es un código interno: dice a dónde va."""
    articulo, p = pieza_en_kep(compras, session, vigente_hasta=vigencia())
    enviar(almacenista, session, "CON", [renglon(p.codigo)])
    nombre_destino = session.scalar(select(Almacen.nombre).where(Almacen.clave == "CON"))

    r = evaluar_traspaso(almacenista, session, "MID", [renglon(p.codigo)])

    titular = r["renglones"][0]["titular"]
    assert titular["tipo"] == "VIRTUAL"
    assert titular["nombre"] == f"En tránsito a {nombre_destino}"
    assert "EN_TRANSITO" not in titular["nombre"] + titular["descripcion"]


def test_X_06_el_vale_lleva_folio_trs_qr_y_queda_en_transito(almacenista, compras, session):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    traspaso = enviar(almacenista, session, "CON", [renglon(guantes.codigo, 2)])
    assert traspaso["folio"] == "KEP-TRS-000001" or traspaso["folio"].startswith("KEP-TRS-")
    assert traspaso["token"]
    detalle = almacenista.get(f"/api/vales/por-token/{traspaso['token']}")  # el QR lo abre
    assert detalle.status_code == 200
    d = detalle.json()
    assert d["tipo"] == "TRASPASO" and d["estado"] == "EN_TRANSITO"
    assert d["almacen"]["clave"] == "KEP" and d["destino_almacen"]["clave"] == "CON"
    assert d["trabajador"] is None


def test_X_06_los_folios_de_traspaso_son_consecutivos_por_almacen(
    almacenista, cliente_almacen, compras, session
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    a = enviar(almacenista, session, "CON", [renglon(guantes.codigo)])
    b = enviar(almacenista, session, "CON", [renglon(guantes.codigo)])
    assert int(b["folio"].rsplit("-", 1)[1]) == int(a["folio"].rsplit("-", 1)[1]) + 1
    revisar_folios(session)


def test_X_07_cada_movimiento_conserva_origen_y_destino(almacenista, compras, session):
    guantes = crear_articulo(session, retornable=False)
    articulo, p = pieza_en_kep(compras, session, vigente_hasta=vigencia())
    abastecer(compras, guantes, 5)
    traspaso = enviar(almacenista, session, "CON", [renglon(guantes.codigo, 3), renglon(p.codigo)])
    d = almacenista.get(f"/api/vales/{traspaso['id']}").json()
    assert len(d["renglones"]) == 2
    for r in d["renglones"]:
        assert r["origen"]["tipo"] == "ALMACEN" and r["origen"]["clave"] == "KEP"
        assert r["destino"]["tipo"] == "EN_TRANSITO"
    # saldos: en el origen baja y En tránsito sube
    cantidad = next(r for r in d["renglones"] if r["codigo_articulo"] == guantes.codigo)
    assert cantidad["saldo_origen"] == 2 and cantidad["saldo_destino"] == 3
    assert [m.cantidad for m in movimientos_del_vale(session, traspaso["id"])] == [3, 1]


def test_el_vale_de_traspaso_no_trae_costos_RG_12(almacenista, compras, session):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    traspaso = enviar(almacenista, session, "CON", [renglon(guantes.codigo)])
    texto = almacenista.get(f"/api/vales/{traspaso['id']}").text.lower()
    assert "costo" not in texto and "precio" not in texto
    r = almacenista.post(
        VALES,
        json=cuerpo_traspaso(session, "CON", [renglon(guantes.codigo)], costo=10),
    )
    assert r.status_code == 422  # el cuerpo no acepta campos desconocidos como el costo


# --------------------------------------------------------------------------------- X-02


def test_X_02_una_pieza_que_no_esta_en_el_almacen_es_roja_y_dice_donde_esta(
    almacenista, cliente_almacen, compras, session
):
    articulo, p = pieza_en_kep(compras, session, vigente_hasta=vigencia())
    # Kepler la manda a Contratistas: ahora está En tránsito, y Contratistas no la tiene todavía.
    enviar(almacenista, session, "CON", [renglon(p.codigo)])
    ev = evaluar_traspaso(almacenista, session, "CON", [renglon(p.codigo)])
    assert ev["nivel"] == "ROJO" and ev["puede_confirmar"] is False
    assert reglas(ev, 0) == ["X-02"]
    assert ev["renglones"][0]["titular"]["tipo"] == "VIRTUAL"
    assert "tránsito" in ev["renglones"][0]["motivos"][0]["mensaje"]
    # Contratistas tampoco puede enviarla: no es suya.
    ev = evaluar_traspaso(cliente_almacen("CON"), session, "MID", [renglon(p.codigo)])
    assert reglas(ev, 0) == ["X-02"] and ev["nivel"] == "ROJO"


def test_X_02_una_pieza_que_tiene_un_trabajador_no_sale_del_almacen(almacenista, compras, session):
    articulo, p = pieza_en_kep(compras, session, vigente_hasta=vigencia())
    t = crear_trabajador(session)
    r = almacenista.post(VALES, json=cuerpo_entrega(t, [renglon(p.codigo)]))
    assert r.status_code == 201, r.text
    ev = evaluar_traspaso(almacenista, session, "CON", [renglon(p.codigo)])
    assert reglas(ev, 0) == ["X-02"]
    assert t.numero_empleado in ev["renglones"][0]["motivos"][0]["mensaje"]
    assert ev["renglones"][0]["titular"]["tipo"] == "TRABAJADOR"


def test_X_02_una_cantidad_mayor_a_la_existencia_es_roja_y_la_igual_es_verde(
    almacenista, compras, session
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    ev = evaluar_traspaso(almacenista, session, "CON", [renglon(guantes.codigo, 6)])
    assert ev["nivel"] == "ROJO" and reglas(ev, 0) == ["X-02"] and not ev["puede_confirmar"]
    assert ev["renglones"][0]["disponible"] == 5
    ev = evaluar_traspaso(almacenista, session, "CON", [renglon(guantes.codigo, 5)])
    assert ev["nivel"] == "VERDE" and ev["puede_confirmar"] is True


def test_X_02_confirmar_con_un_rojo_responde_409_y_no_escribe_nada(almacenista, compras, session):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    vales, movs = total_vales(session), total_movimientos(session)
    r = almacenista.post(VALES, json=cuerpo_traspaso(session, "CON", [renglon(guantes.codigo, 9)]))
    assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO"
    assert r.json()["detalles"]["renglones"][0]["motivos"][0]["regla"] == "X-02"
    assert total_vales(session) == vales and total_movimientos(session) == movs
    assert existencia(session, "KEP", guantes) == 5 and en_transito(session, guantes) == 0


def test_X_02_codigo_desconocido_y_articulo_por_pieza_escaneado_por_articulo(
    almacenista, compras, session
):
    articulo, p = pieza_en_kep(compras, session, vigente_hasta=vigencia())
    ev = evaluar_traspaso(
        almacenista, session, "CON", [renglon("NO-EXISTE-Z"), renglon(articulo.codigo)]
    )
    assert reglas(ev, 0) == ["X-02"] and reglas(ev, 1) == ["X-02"]
    assert "escanea el código de la pieza" in ev["renglones"][1]["motivos"][0]["mensaje"]
    assert ev["renglones"][0]["articulo"] is None


def test_RG_05_una_pieza_se_envia_de_una_en_una(almacenista, compras, session):
    articulo, p = pieza_en_kep(compras, session, vigente_hasta=vigencia())
    ev = evaluar_traspaso(almacenista, session, "CON", [renglon(p.codigo, 2)])
    assert reglas(ev, 0) == ["RG-05"] and ev["nivel"] == "ROJO"


def test_X_02_cada_almacen_solo_envia_lo_suyo(almacenista, cliente_almacen, compras, session):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    # Contratistas no tiene guantes: no puede enviar lo que hay en Kepler.
    ev = evaluar_traspaso(cliente_almacen("CON"), session, "MID", [renglon(guantes.codigo)])
    assert ev["nivel"] == "ROJO" and reglas(ev, 0) == ["X-02"]
    assert ev["renglones"][0]["disponible"] == 0


# --------------------------------------------------------------------------------- X-03


@pytest.mark.parametrize(
    ("origen", "destino"),
    [("KEP", "CON"), ("CON", "KEP"), ("CON", "MID"), ("MID", "CON"), ("CON", "HYL")],
)
def test_X_03_las_rutas_habituales_no_llevan_aviso(
    cliente_almacen, cliente_como, session, origen, destino
):
    guantes = crear_articulo(session, retornable=False)
    # Compras es de Kepler: los demás almacenes los abastece el Administrador.
    abastecer(
        cliente_como("Administrador"), guantes, 3, almacen_id=str(almacen_id(session, origen))
    )
    ev = evaluar_traspaso(cliente_almacen(origen), session, destino, [renglon(guantes.codigo)])
    assert ev["nivel"] == "VERDE" and ev["puede_confirmar"] is True
    assert [(m["regla"], m["nivel"]) for m in ev["motivos"]] == [("X-03", "VERDE")]
    assert "habitual" in ev["motivos"][0]["mensaje"]


@pytest.mark.parametrize(("origen", "destino"), [("KEP", "MID"), ("MID", "HYL"), ("HYL", "KEP")])
def test_X_03_otra_ruta_se_permite_con_aviso_amarillo(
    cliente_almacen, cliente_como, session, origen, destino
):
    guantes = crear_articulo(session, retornable=False)
    # Compras es de Kepler: los demás almacenes los abastece el Administrador.
    abastecer(
        cliente_como("Administrador"), guantes, 3, almacen_id=str(almacen_id(session, origen))
    )
    cliente = cliente_almacen(origen)
    ev = evaluar_traspaso(cliente, session, destino, [renglon(guantes.codigo)])
    assert ev["nivel"] == "AMARILLO" and ev["puede_confirmar"] is True
    assert [(m["regla"], m["nivel"]) for m in ev["motivos"]] == [("X-03", "AMARILLO")]
    # Con el aviso se confirma, y el movimiento guarda la regla.
    traspaso = enviar(cliente, session, destino, [renglon(guantes.codigo)])
    assert "X-03" in traspaso["renglones"][0]["reglas"]


def test_X_03_el_destino_igual_al_origen_es_rojo_y_no_se_confirma(almacenista, compras, session):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 3)
    ev = evaluar_traspaso(almacenista, session, "KEP", [renglon(guantes.codigo)])
    assert ev["nivel"] == "ROJO" and reglas(ev) == ["X-03"] and not ev["puede_confirmar"]
    vales = total_vales(session)
    r = almacenista.post(VALES, json=cuerpo_traspaso(session, "KEP", [renglon(guantes.codigo)]))
    assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO"
    assert total_vales(session) == vales and existencia(session, "KEP", guantes) == 3


def test_X_03_un_destino_inexistente_o_cerrado_es_rojo(almacenista, compras, session):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 3)
    cuerpo = cuerpo_traspaso(session, "CON", [renglon(guantes.codigo)])
    cuerpo["destino_almacen_id"] = str(uuid.uuid4())
    r = almacenista.post("/api/vales/evaluar", json=cuerpo)
    assert r.status_code == 200 and r.json()["nivel"] == "ROJO"
    assert reglas(r.json()) == ["X-03"]
    # Un almacén cerrado no recibe traspasos.
    hyl = session.scalar(select(Almacen).where(Almacen.clave == "HYL"))
    hyl.estado = "CERRADO"
    session.flush()
    ev = evaluar_traspaso(almacenista, session, "HYL", [renglon(guantes.codigo)])
    assert ev["nivel"] == "ROJO" and "cerrado" in ev["motivos"][0]["mensaje"]


# --------------------------------------------------------------------------- X-04 y X-09


def test_X_04_una_pieza_no_apta_se_traslada_con_aviso_y_conserva_su_estado(
    almacenista, compras, session
):
    articulo, p = pieza_en_kep(
        compras, session, estado=EstadoPieza.NO_APTO, vigente_hasta=vigencia()
    )
    ev = evaluar_traspaso(almacenista, session, "CON", [renglon(p.codigo)])
    assert ev["nivel"] == "AMARILLO" and ev["puede_confirmar"] is True
    assert reglas(ev, 0) == ["X-04"]
    assert "no es apta" in ev["renglones"][0]["motivos"][0]["mensaje"]
    traspaso = enviar(almacenista, session, "CON", [renglon(p.codigo)])
    assert "X-04" in traspaso["renglones"][0]["reglas"]
    assert pieza(session, p.codigo).estado == EstadoPieza.NO_APTO  # conserva su estado
    assert ubicacion_de_pieza(session, p.codigo) == "EN_TRANSITO"


def test_X_09_un_articulo_inactivo_si_se_puede_trasladar(almacenista, compras, session):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    guantes.activo = False
    guantes.motivo_inactivacion = "Ya no se compra"
    session.flush()
    ev = evaluar_traspaso(almacenista, session, "CON", [renglon(guantes.codigo, 2)])
    assert ev["nivel"] == "VERDE" and ev["puede_confirmar"] is True
    assert reglas(ev, 0) == ["X-09"]  # solo lo informa
    traspaso = enviar(almacenista, session, "CON", [renglon(guantes.codigo, 2)])
    assert "X-09" in traspaso["renglones"][0]["reglas"]
    assert en_transito(session, guantes) == 2


# ---------------------------------------------------------------------------------- F-09


def test_F_09_el_traspaso_se_firma_con_la_sesion_de_quien_envia(almacenista, compras, session):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    traspaso = enviar(almacenista, session, "CON", [renglon(guantes.codigo)])  # sin `firma`
    d = almacenista.get(f"/api/vales/{traspaso['id']}").json()
    assert d["firma_modo"] == "SESION" and d["tiene_firma"] is False
    assert d["responsable"]["nombre"] == "Supervisor Kepler"


# --------------------------------------------------------------------- cuerpo y alcance


def test_un_traspaso_sin_renglones_se_rechaza(almacenista, session):
    r = almacenista.post(VALES, json=cuerpo_traspaso(session, "CON", []))
    assert r.status_code == 422 and r.json()["detalles"][0]["campo"] == "renglones"
    ev = evaluar_traspaso(almacenista, session, "CON", [])
    assert ev["puede_confirmar"] is False


def test_el_traspaso_exige_destino_y_no_acepta_trabajador(almacenista, compras, session):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    sin_destino = cuerpo_traspaso(session, "CON", [renglon(guantes.codigo)])
    del sin_destino["destino_almacen_id"]
    r = almacenista.post(VALES, json=sin_destino)
    assert r.status_code == 422 and r.json()["detalles"][0]["campo"] == "destino_almacen_id"
    t = crear_trabajador(session)
    con_trabajador = cuerpo_traspaso(
        session, "CON", [renglon(guantes.codigo)], trabajador_id=str(t.id)
    )
    r = almacenista.post(VALES, json=con_trabajador)
    assert r.status_code == 422 and r.json()["detalles"][0]["campo"] == "trabajador_id"
    r = almacenista.post(
        VALES,
        json=cuerpo_traspaso(
            session, "CON", [renglon(guantes.codigo)], vale_origen_id=str(uuid.uuid4())
        ),
    )
    assert r.status_code == 422


def test_un_traspaso_pide_el_permiso_traspasos_operar(cliente_como, compras, session):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    cuerpo = cuerpo_traspaso(session, "CON", [renglon(guantes.codigo)])
    # Ninguno tiene `traspasos.operar` (tabla 8.2: es del Supervisor; el almacenista no).
    for rol in ("Recursos Humanos", "Compras", "Almacenista"):
        c = cliente_como(rol)
        assert c.post("/api/vales/evaluar", json=cuerpo).status_code == 403, rol
        assert c.post(VALES, json=cuerpo).status_code == 403, rol
    assert cliente_como("Supervisor").post("/api/vales/evaluar", json=cuerpo).status_code == 200
    # Quien tiene `almacenes.todos` (Administrador) debe indicar el almacén de origen.
    assert cliente_como("Administrador").post("/api/vales/evaluar", json=cuerpo).status_code == 422


def test_quien_opera_todos_los_almacenes_indica_el_almacen_de_origen(
    cliente_como, compras, session
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    supervisor = cliente_como("Administrador")  # el único con `almacenes.todos`
    cuerpo = cuerpo_traspaso(
        session, "CON", [renglon(guantes.codigo, 2)], almacen_id=str(almacen_id(session, "KEP"))
    )
    r = supervisor.post(VALES, json=cuerpo)
    assert r.status_code == 201 and r.json()["folio"].startswith("KEP-TRS-")
    assert existencia(session, "KEP", guantes) == 3


def test_un_almacenista_no_puede_enviar_desde_otro_almacen(almacenista, compras, session):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    cuerpo = cuerpo_traspaso(
        session, "CON", [renglon(guantes.codigo)], almacen_id=str(almacen_id(session, "MID"))
    )
    r = almacenista.post(VALES, json=cuerpo)
    assert r.status_code == 409 and r.json()["codigo"] == "ALMACEN_CAMBIO"


# --------------------------------------------------------------- normalización, atomicidad


def test_pieza_repetida_se_ignora_y_articulo_por_cantidad_repetido_suma(
    almacenista, compras, session
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 10)
    articulo, p = pieza_en_kep(compras, session, vigente_hasta=vigencia())
    traspaso = enviar(
        almacenista,
        session,
        "CON",
        [
            renglon(guantes.codigo, 2),
            renglon(p.codigo),
            renglon(guantes.codigo, 3),
            renglon(p.codigo),
        ],
    )
    assert [(r["codigo"], r["cantidad"]) for r in traspaso["renglones"]] == [
        (guantes.codigo, 5),
        (p.codigo, 1),
    ]
    assert en_transito(session, guantes) == 5


def test_RG_09_un_traspaso_con_un_renglon_en_rojo_no_mueve_los_demas(almacenista, compras, session):
    guantes = crear_articulo(session, retornable=False)
    casco = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 10)
    abastecer(compras, casco, 1)
    vales, movs = total_vales(session), total_movimientos(session)
    r = almacenista.post(
        VALES,
        json=cuerpo_traspaso(
            session, "CON", [renglon(guantes.codigo, 4), renglon(casco.codigo, 3)]
        ),
    )
    assert r.status_code == 409
    assert total_vales(session) == vales and total_movimientos(session) == movs
    assert existencia(session, "KEP", guantes) == 10 and en_transito(session, guantes) == 0
    revisar_invariantes(session)
    revisar_folios(session)  # el folio no se quemó


def test_RG_09_un_error_de_la_base_en_mitad_del_traspaso_no_deja_nada(
    almacenista, compras, session, monkeypatch
):
    """Atomicidad: si algo falla al escribir el segundo movimiento, no queda vale, ni
    movimientos, ni folio, ni cambio en las existencias."""
    from app.modulos.movimientos.repository import MovimientoRepository

    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 10)
    casco = crear_articulo(session, retornable=False)
    abastecer(compras, casco, 10)
    vales, movs = total_vales(session), total_movimientos(session)
    original = MovimientoRepository.add_movimiento
    llamadas = []

    def falla_en_el_segundo(self, movimiento):
        llamadas.append(movimiento.renglon)
        if len(llamadas) == 2:
            raise RuntimeError("falla simulada")
        return original(self, movimiento)

    monkeypatch.setattr(MovimientoRepository, "add_movimiento", falla_en_el_segundo)
    with pytest.raises(RuntimeError, match="falla simulada"):
        almacenista.post(
            VALES,
            json=cuerpo_traspaso(
                session, "CON", [renglon(guantes.codigo, 4), renglon(casco.codigo, 3)]
            ),
        )
    monkeypatch.undo()
    assert total_vales(session) == vales and total_movimientos(session) == movs
    assert existencia(session, "KEP", guantes) == 10 and existencia(session, "KEP", casco) == 10
    assert en_transito(session, guantes) == 0 and en_transito(session, casco) == 0
    revisar_folios(session)


def test_idempotencia_el_mismo_id_cliente_no_crea_dos_traspasos(almacenista, compras, session):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 10)
    cuerpo = cuerpo_traspaso(session, "CON", [renglon(guantes.codigo, 4)])
    primero = almacenista.post(VALES, json=cuerpo)
    segundo = almacenista.post(VALES, json=cuerpo)
    assert (primero.status_code, segundo.status_code) == (201, 200)
    assert primero.json() == segundo.json()
    assert existencia(session, "KEP", guantes) == 6 and en_transito(session, guantes) == 4
    n = session.scalars(select(Vale.id).where(Vale.id_cliente == uuid.UUID(cuerpo["id_cliente"])))
    assert len(n.all()) == 1
    assert vale(session, primero.json()["id"]).estado == "EN_TRANSITO"
    revisar_invariantes(session)
