"""Confirmación (POST /api/vales): RG-01, RG-03, RG-04, RG-06, RG-08, RG-09, RG-11, F-02, F-03,
F-05, F-12, idempotencia y atomicidad."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.core import errores_bd
from app.core.tiempo import hoy_mx
from app.modulos.archivos.models import Adjunto
from app.modulos.catalogo.models import Codigo
from app.modulos.movimientos.models import Existencia, Movimiento, SerieFolio, Vale
from app.modulos.movimientos.repository import MovimientoRepository
from tests.movimientos.ayudas import (
    FIRMA,
    PNG_B64,
    abastecer,
    almacen,
    crear_articulo,
    crear_trabajador,
    cuerpo_entrega,
    existencia,
    existencia_de_trabajador,
    total_movimientos,
    total_vales,
)
from tests.movimientos.test_entrega import pieza_en_kep, renglon

VALES = "/api/vales"


@pytest.fixture
def trabajador(session):
    return crear_trabajador(session)


def serie(session, clave, tipo):
    return (
        session.scalar(
            select(SerieFolio.ultimo).where(
                SerieFolio.almacen_id == almacen(session, clave).id, SerieFolio.tipo == tipo
            )
        )
        or 0
    )


# ------------------------------------------------------------------------- firma


def test_F_02_una_entrega_sin_firma_se_rechaza(almacenista, compras, session, trabajador):
    guantes = crear_articulo(session)
    abastecer(compras, guantes, 5)
    cuerpo = cuerpo_entrega(trabajador, [renglon(guantes.codigo)])
    del cuerpo["firma"]
    vales = total_vales(session)
    r = almacenista.post(VALES, json=cuerpo)
    assert r.status_code == 422 and r.json()["detalles"][0]["campo"] == "firma"
    assert r.json()["detalles"][0]["regla"] == "F-02"
    assert total_vales(session) == vales and existencia(session, "KEP", guantes) == 5


@pytest.mark.parametrize(
    "firma",
    [
        {"modo": "PANTALLA"},
        {"modo": "PANTALLA", "imagen": ""},
        {"modo": "SESION", "imagen": f"data:image/png;base64,{PNG_B64}"},
    ],
)
def test_F_02_una_firma_vacia_o_de_otro_modo_se_rechaza(
    almacenista, compras, session, trabajador, firma
):
    guantes = crear_articulo(session)
    abastecer(compras, guantes, 5)
    r = almacenista.post(
        VALES, json=cuerpo_entrega(trabajador, [renglon(guantes.codigo)], firma=firma)
    )
    assert r.status_code == 422
    assert existencia(session, "KEP", guantes) == 5


def test_F_02_una_firma_que_no_es_imagen_se_rechaza_y_no_guarda_nada(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session)
    abastecer(compras, guantes, 5)
    malo = {"modo": "PANTALLA", "imagen": "data:image/png;base64,SG9sYSBtdW5kbw==", "trazo": []}
    vales = total_vales(session)
    r = almacenista.post(
        VALES, json=cuerpo_entrega(trabajador, [renglon(guantes.codigo)], firma=malo)
    )
    assert r.status_code == 422
    assert total_vales(session) == vales and existencia(session, "KEP", guantes) == 5


def test_F_02_la_firma_queda_guardada_y_ligada_al_vale(
    almacenista, compras, session, trabajador, _archivos_tmp
):
    guantes = crear_articulo(session)
    abastecer(compras, guantes, 5)
    r = almacenista.post(VALES, json=cuerpo_entrega(trabajador, [renglon(guantes.codigo)]))
    assert r.status_code == 201, r.text
    vale = session.get(Vale, uuid.UUID(r.json()["id"]))
    adjunto = session.get(Adjunto, vale.firma_adjunto_id)
    assert adjunto.tipo == "FIRMA" and adjunto.vale_id == vale.id and adjunto.mime == "image/png"
    assert adjunto.subido_por == vale.responsable_id
    assert (_archivos_tmp / adjunto.ruta).exists()  # el archivo vive en el volumen
    assert FIRMA["imagen"] not in r.text  # la firma no viaja de regreso en la respuesta


def test_F_03_F_05_el_vale_guarda_responsable_dispositivo_y_fecha_del_servidor(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session)
    abastecer(compras, guantes, 5)
    r = almacenista.post(
        VALES,
        json=cuerpo_entrega(trabajador, [renglon(guantes.codigo)]),
        headers={"User-Agent": "Zebra TC52 / Chrome 120"},
    )
    vale = session.get(Vale, uuid.UUID(r.json()["id"]))
    assert vale.dispositivo == "Zebra TC52 / Chrome 120"
    assert vale.responsable_id is not None and vale.estado == "EMITIDO"
    assert vale.firma_modo == "PANTALLA"
    ahora = datetime.now(UTC).replace(tzinfo=None)
    assert abs(vale.creado_en - ahora) < timedelta(minutes=1)  # RG-11: hora del servidor
    assert vale.periodo_contrato_id is not None


def test_F_05_el_dispositivo_se_recorta_a_200_caracteres(almacenista, compras, session, trabajador):
    guantes = crear_articulo(session)
    abastecer(compras, guantes, 5)
    r = almacenista.post(
        VALES,
        json=cuerpo_entrega(trabajador, [renglon(guantes.codigo)]),
        headers={"User-Agent": "X" * 500},
    )
    assert len(session.get(Vale, uuid.UUID(r.json()["id"])).dispositivo) == 200


# ------------------------------------------------------------------------- folios


def test_RG_06_los_folios_son_consecutivos_por_almacen_y_tipo(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session)
    abastecer(compras, guantes, 20)
    base = serie(session, "KEP", "ENTREGA")
    folios = []
    for _ in range(3):
        r = almacenista.post(VALES, json=cuerpo_entrega(trabajador, [renglon(guantes.codigo)]))
        folios.append(r.json()["folio"])
    assert folios == [f"KEP-ENT-{base + n:06d}" for n in (1, 2, 3)]


def test_RG_06_cada_almacen_y_cada_tipo_lleva_su_propio_consecutivo(
    compras, almacenista, cliente_como, session, trabajador
):
    articulo = crear_articulo(session)
    con = str(almacen(session, "CON").id)
    kep_ing = serie(session, "KEP", "ENTRADA")
    con_ing = serie(session, "CON", "ENTRADA")
    r1 = abastecer(compras, articulo, 1)
    # Compras es de Kepler; la carga de Contratistas la hace el Administrador (AC-06).
    r2 = abastecer(cliente_como("Administrador"), articulo, 1, almacen_id=con)
    r3 = abastecer(compras, articulo, 1)
    assert r1["folio"] == f"KEP-ING-{kep_ing + 1:06d}"
    assert r3["folio"] == f"KEP-ING-{kep_ing + 2:06d}"
    assert r2["folio"] == f"CON-ING-{con_ing + 1:06d}"
    # Un vale de otro tipo en el mismo almacén no avanza el contador de entradas.
    r4 = almacenista.post(VALES, json=cuerpo_entrega(trabajador, [renglon(articulo.codigo)]))
    assert r4.json()["folio"].startswith("KEP-ENT-")
    assert serie(session, "KEP", "ENTRADA") == kep_ing + 2


def test_RG_06_un_vale_rechazado_no_quema_folio(almacenista, compras, session, trabajador):
    guantes = crear_articulo(session)
    abastecer(compras, guantes, 1)
    base = serie(session, "KEP", "ENTREGA")
    malo = almacenista.post(VALES, json=cuerpo_entrega(trabajador, [renglon(guantes.codigo, 9)]))
    assert malo.status_code == 409
    assert serie(session, "KEP", "ENTREGA") == base
    bueno = almacenista.post(VALES, json=cuerpo_entrega(trabajador, [renglon(guantes.codigo)]))
    assert bueno.json()["folio"] == f"KEP-ENT-{base + 1:06d}"


def test_RG_06_el_folio_no_sale_del_id(almacenista, compras, session, trabajador):
    guantes = crear_articulo(session)
    abastecer(compras, guantes, 5)
    r = almacenista.post(VALES, json=cuerpo_entrega(trabajador, [renglon(guantes.codigo)]))
    assert r.json()["id"].replace("-", "")[:6] not in r.json()["folio"]
    assert len(r.json()["folio"].split("-")[-1]) == 6


# ----------------------------------------------------------------- idempotencia


def test_idempotencia_un_doble_toque_en_confirmar_no_crea_dos_vales(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session)
    abastecer(compras, guantes, 10)
    cuerpo = cuerpo_entrega(trabajador, [renglon(guantes.codigo, 2)])
    primero = almacenista.post(VALES, json=cuerpo)
    segundo = almacenista.post(VALES, json=cuerpo)
    assert primero.status_code == 201 and segundo.status_code == 200
    assert segundo.json() == primero.json()  # el mismo vale que se guardó la primera vez
    assert existencia(session, "KEP", guantes) == 8  # una sola salida
    n = session.scalars(select(Vale.id).where(Vale.id_cliente == uuid.UUID(cuerpo["id_cliente"])))
    assert len(n.all()) == 1


def test_idempotencia_repetir_la_entrada_no_duplica_las_existencias(compras, session):
    articulo = crear_articulo(session)
    cuerpo = {
        "tipo": "ENTRADA",
        "id_cliente": str(uuid.uuid4()),
        "renglones": [{"codigo": articulo.codigo, "cantidad": 4}],
    }
    assert compras.post(VALES, json=cuerpo).status_code == 201
    assert compras.post(VALES, json=cuerpo).status_code == 200
    assert existencia(session, "KEP", articulo) == 4


def test_idempotencia_el_reintento_devuelve_el_vale_aunque_el_inventario_ya_cambio(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session)
    abastecer(compras, guantes, 1)
    cuerpo = cuerpo_entrega(trabajador, [renglon(guantes.codigo)])
    assert almacenista.post(VALES, json=cuerpo).status_code == 201
    # Ya no queda existencia: sin idempotencia el reintento daría rojo.
    segundo = almacenista.post(VALES, json=cuerpo)
    assert segundo.status_code == 200 and segundo.json()["folio"].startswith("KEP-ENT-")


def test_idempotencia_el_id_cliente_de_otro_usuario_no_devuelve_su_vale(
    almacenista, supervisor, compras, session, trabajador
):
    guantes = crear_articulo(session)
    abastecer(compras, guantes, 5)
    cuerpo = cuerpo_entrega(trabajador, [renglon(guantes.codigo)])
    assert almacenista.post(VALES, json=cuerpo).status_code == 201
    kep = str(almacen(session, "KEP").id)
    r = supervisor.post(VALES, json=cuerpo | {"almacen_id": kep})
    assert r.status_code == 409 and r.json()["codigo"] == "CONFLICTO"


# ----------------------------------------------------------------- atomicidad y RG-08


def test_RG_09_si_falla_el_ultimo_renglon_no_queda_nada(
    almacenista, compras, session, trabajador, monkeypatch
):
    a, b, c = (crear_articulo(session) for _ in range(3))
    for articulo in (a, b, c):
        abastecer(compras, articulo, 5)
    vales, movs = total_vales(session), total_movimientos(session)
    folio = serie(session, "KEP", "ENTREGA")
    codigos = len(session.scalars(select(Codigo.codigo)).all())
    original = MovimientoRepository.add_movimiento
    llamadas = {"n": 0}

    def falla_en_el_tercero(self, movimiento):
        llamadas["n"] += 1
        if llamadas["n"] == 3:
            raise RuntimeError("falla simulada")
        return original(self, movimiento)

    monkeypatch.setattr(MovimientoRepository, "add_movimiento", falla_en_el_tercero)
    cuerpo = cuerpo_entrega(trabajador, [renglon(x.codigo) for x in (a, b, c)])
    with pytest.raises(RuntimeError):
        almacenista.post(VALES, json=cuerpo)
    monkeypatch.setattr(MovimientoRepository, "add_movimiento", original)
    session.rollback()
    assert (total_vales(session), total_movimientos(session)) == (vales, movs)
    assert [existencia(session, "KEP", x) for x in (a, b, c)] == [5, 5, 5]
    assert [existencia_de_trabajador(session, trabajador, x) for x in (a, b, c)] == [0, 0, 0]
    assert serie(session, "KEP", "ENTREGA") == folio  # el folio no se quemó
    assert len(session.scalars(select(Codigo.codigo)).all()) == codigos  # ni códigos del vale
    # Y el mismo `id_cliente` se puede volver a confirmar con éxito.
    assert almacenista.post(VALES, json=cuerpo).status_code == 201


def test_RG_08_si_otra_persona_entrego_la_pieza_al_confirmar_se_responde_con_el_cambio(
    almacenista, compras, session, trabajador
):
    _, pieza = pieza_en_kep(compras, session, vigente_hasta=hoy_mx() + timedelta(days=30))
    otro = crear_trabajador(session)
    primero = almacenista.post(VALES, json=cuerpo_entrega(otro, [renglon(pieza.codigo)]))
    assert primero.status_code == 201
    vales = total_vales(session)
    segundo = almacenista.post(VALES, json=cuerpo_entrega(trabajador, [renglon(pieza.codigo)]))
    assert segundo.status_code == 409 and segundo.json()["codigo"] == "VALE_CAMBIO"
    nueva = segundo.json()["detalles"]
    assert nueva["nivel"] == "ROJO" and nueva["puede_confirmar"] is False
    renglon_fallido = nueva["renglones"][0]  # se indica el renglón que falló
    assert renglon_fallido["codigo"] == pieza.codigo
    assert [m["regla"] for m in renglon_fallido["motivos"]] == ["E-03"]
    assert total_vales(session) == vales  # RG-09: el segundo no se guardó


def test_RG_08_si_cambio_la_existencia_entre_evaluar_y_confirmar_gana_el_primero(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session)
    abastecer(compras, guantes, 3)
    cuerpo = cuerpo_entrega(trabajador, [renglon(guantes.codigo, 3)])
    assert almacenista.post("/api/vales/evaluar", json=cuerpo).json()["puede_confirmar"] is True
    otro = crear_trabajador(session)
    assert (
        almacenista.post(VALES, json=cuerpo_entrega(otro, [renglon(guantes.codigo, 2)])).status_code
        == 201
    )
    r = almacenista.post(VALES, json=cuerpo)
    assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO"
    assert r.json()["detalles"]["renglones"][0]["motivos"][0]["regla"] == "E-04"
    assert existencia(session, "KEP", guantes) == 1


def test_RG_08_si_activan_el_requisito_de_autorizacion_a_medio_capturar_responde_con_el_cambio(
    almacenista, compras, session, trabajador
):
    herramienta = crear_articulo(session)
    abastecer(compras, herramienta, 3)
    cuerpo = cuerpo_entrega(trabajador, [renglon(herramienta.codigo)])
    assert almacenista.post("/api/vales/evaluar", json=cuerpo).json()["nivel"] == "VERDE"
    herramienta.requiere_autorizacion = True  # lo activa un supervisor desde el catálogo
    session.flush()
    r = almacenista.post(VALES, json=cuerpo)
    assert r.status_code == 409 and r.json()["detalles"]["renglones"][0]["nivel"] == "NARANJA"


# ----------------------------------------------------------------------- RG-04, RG-01


def test_RG_04_el_saldo_nunca_es_negativo_ni_con_una_entrega_mayor(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session)
    abastecer(compras, guantes, 2)
    r = almacenista.post(VALES, json=cuerpo_entrega(trabajador, [renglon(guantes.codigo, 3)]))
    assert r.status_code == 409
    assert existencia(session, "KEP", guantes) == 2


def test_RG_04_la_base_rechaza_una_existencia_negativa_con_su_check(session):
    guantes = crear_articulo(session)
    kep = almacen(session, "KEP")
    from app.modulos.almacenes.service import AlmacenService

    ubicacion = AlmacenService(session).ubicacion_de_almacen(kep.id)
    session.add(Existencia(ubicacion_id=ubicacion.id, articulo_id=guantes.id, cantidad=1))
    session.flush()
    with pytest.raises(DBAPIError) as exc:
        with session.begin_nested():
            session.execute(
                text("UPDATE existencia SET cantidad = -1 WHERE articulo_id = :a"),
                {"a": guantes.id.hex},
            )
    assert errores_bd.es_restriccion(exc.value, "ck_existencia_cantidad_no_negativa")


def test_RG_04_el_motor_rechaza_una_salida_sin_existencia_aunque_se_salte_la_evaluacion(
    almacenista, compras, session, trabajador, monkeypatch
):
    """Defensa en profundidad: si la evaluación dejara pasar una salida sin existencia, el motor
    la rechaza antes de escribir (y la base con su CHECK)."""
    from app.modulos.movimientos import service as modulo

    guantes = crear_articulo(session)
    abastecer(compras, guantes, 1)
    original = modulo.MovimientoService._escribir_movimientos

    def pide_de_mas(self, ctx, vale, nuevos):
        for m in nuevos:
            m.cantidad = 5
        return original(self, ctx, vale, nuevos)

    monkeypatch.setattr(modulo.MovimientoService, "_escribir_movimientos", pide_de_mas)
    r = almacenista.post(VALES, json=cuerpo_entrega(trabajador, [renglon(guantes.codigo)]))
    assert r.status_code == 409 and r.json()["codigo"] == "CONFLICTO"
    assert existencia(session, "KEP", guantes) == 1


def test_RG_01_la_existencia_cambia_junto_al_movimiento_y_el_saldo_queda_en_el_renglon(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=True)
    abastecer(compras, guantes, 10)
    r = almacenista.post(VALES, json=cuerpo_entrega(trabajador, [renglon(guantes.codigo, 4)]))
    mov = session.scalar(select(Movimiento).where(Movimiento.vale_id == uuid.UUID(r.json()["id"])))
    assert (mov.saldo_origen, mov.saldo_destino) == (6, 4)
    assert existencia(session, "KEP", guantes) == 6
    assert existencia_de_trabajador(session, trabajador, guantes) == 4


def test_RG_03_cada_movimiento_conserva_origen_destino_fecha_y_vale(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session)
    abastecer(compras, guantes, 10)
    r = almacenista.post(VALES, json=cuerpo_entrega(trabajador, [renglon(guantes.codigo, 4)]))
    vale = session.get(Vale, uuid.UUID(r.json()["id"]))
    mov = session.scalar(select(Movimiento).where(Movimiento.vale_id == vale.id))
    assert mov.origen_id != mov.destino_id and mov.creado_en == vale.creado_en
    assert mov.articulo_id == guantes.id and mov.cantidad == 4 and mov.renglon == 1


# -------------------------------------------------------------------- sin costos


def test_F_12_el_vale_no_muestra_costos_lo_vea_quien_lo_vea(
    almacenista, compras, supervisor, session, trabajador
):
    from decimal import Decimal

    guantes = crear_articulo(session, costo_unitario=Decimal("987.65"))
    abastecer(compras, guantes, 10)
    r = almacenista.post(VALES, json=cuerpo_entrega(trabajador, [renglon(guantes.codigo)]))
    assert "costo" not in r.text.lower() and "987.65" not in r.text
    for cliente in (almacenista, compras, supervisor):  # Compras sí ve costos en el catálogo
        detalle = cliente.get(f"{VALES}/{r.json()['id']}")
        assert detalle.status_code == 200
        assert "costo" not in detalle.text.lower() and "987.65" not in detalle.text
        assert "987.65" not in cliente.get(f"{VALES}/por-token/{r.json()['token']}").text
    ev = almacenista.post(
        "/api/vales/evaluar",
        json={
            "tipo": "ENTREGA",
            "trabajador_id": str(trabajador.id),
            "renglones": [renglon(guantes.codigo)],
        },
    )
    assert "987.65" not in ev.text and "costo" not in ev.text.lower()


# ---------------------------------------------------------------------- QR y códigos


def test_RG_10_el_token_del_vale_es_un_codigo_escaneable_unico(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session)
    abastecer(compras, guantes, 10)
    r = almacenista.post(VALES, json=cuerpo_entrega(trabajador, [renglon(guantes.codigo)]))
    vale = r.json()
    for codigo in (vale["token"], vale["folio"]):
        fila = session.get(Codigo, codigo)
        assert fila is not None and fila.tipo == "VALE" and str(fila.ref_id) == vale["id"]
    otro = abastecer(compras, guantes, 1)
    assert otro["token"] != vale["token"]


def test_F_07_un_token_desconocido_da_404(almacenista):
    assert almacenista.get(f"{VALES}/por-token/no-existe").status_code == 404


def test_E_01_el_codigo_de_un_vale_no_sirve_para_entregar(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session)
    vale = abastecer(compras, guantes, 10)
    r = almacenista.post(
        "/api/vales/evaluar",
        json={
            "tipo": "ENTREGA",
            "trabajador_id": str(trabajador.id),
            "renglones": [renglon(vale["token"])],
        },
    )
    assert r.json()["renglones"][0]["motivos"][0]["regla"] == "E-01"


def test_F_05_la_firma_guardada_se_puede_ver_en_el_detalle_del_vale(
    almacenista, compras, session, trabajador
):
    """El detalle solo dice `tiene_firma`; la imagen se pide aparte y respeta el alcance (AC-06)."""
    guantes = crear_articulo(session)
    abastecer(compras, guantes, 5)
    r = almacenista.post(VALES, json=cuerpo_entrega(trabajador, [renglon(guantes.codigo)]))
    assert r.status_code == 201, r.text
    vale_id = r.json()["id"]
    assert almacenista.get(f"{VALES}/{vale_id}").json()["tiene_firma"] is True

    firma = almacenista.get(f"{VALES}/{vale_id}/firma")

    assert firma.status_code == 200
    assert firma.headers["content-type"] == "image/png"
    assert firma.content.startswith(b"\x89PNG")
    # Una entrada no tiene firma de trabajador: no hay imagen que mostrar.
    entrada = abastecer(compras, guantes, 1)
    assert compras.get(f"{VALES}/{entrada['id']}/firma").status_code == 404
