"""CP-01 a CP-05: faltantes y cierre histórico contra MySQL y la API real."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.config import get_settings
from app.core.tiempo import hoy_mx
from app.modulos.almacenes.models import EstadoAlmacen, Ubicacion
from app.modulos.catalogo.models import Pieza
from app.modulos.movimientos.models import Movimiento, TipoVale, Vale
from tests.movimientos.ayudas import (
    abastecer,
    abastecer_en,
    almacen,
    crear_articulo,
    crear_trabajador,
    cuerpo_entrega,
    entrar_pieza,
    existencia,
)


@pytest.fixture
def datos(session, cliente_como, monkeypatch, tmp_path):
    monkeypatch.setattr(get_settings(), "archivos_dir", tmp_path)
    supervisor = cliente_como("Supervisor")
    compras = cliente_como("Compras")
    articulo = crear_articulo(session)
    abastecer(compras, articulo, 20)
    return supervisor, compras, articulo


def ajuste(articulo, cantidad=2, **extra):
    return {
        "tipo": "AJUSTE",
        "id_cliente": str(uuid.uuid4()),
        "observacion": "Faltante detectado al revisar el contenedor",
        "renglones": [{"codigo": articulo.codigo, "cantidad": cantidad}],
        **extra,
    }


def reporte(cliente, a, **extra):
    return cliente.get(
        f"/api/almacenes/{a.id}/reporte-cierre",
        params={
            "desde": str(hoy_mx()),
            "hasta": str(hoy_mx()),
            **extra,
        },
    )


def articulo_del_reporte(respuesta, articulo):
    assert respuesta.status_code == 200, respuesta.text
    return next(a for a in respuesta.json()["articulos"] if a["articulo_id"] == str(articulo.id))


def test_CP_03_faltante_observacion_responsable_idempotencia(datos, session):
    sup, _, articulo = datos
    cuerpo = ajuste(articulo)
    evaluada = sup.post("/api/vales/evaluar", json=cuerpo)
    assert evaluada.status_code == 200, evaluada.text
    assert evaluada.json()["renglones"][0]["nivel"] == "VERDE"
    assert "CP-03" in {m["regla"] for m in evaluada.json()["renglones"][0]["motivos"]}
    assert existencia(session, "KEP", articulo) == 20
    respuesta = sup.post("/api/vales", json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    assert "-AJU-" in respuesta.json()["folio"]
    assert existencia(session, "KEP", articulo) == 18
    vale = session.get(Vale, uuid.UUID(respuesta.json()["id"]))
    assert vale.tipo == TipoVale.AJUSTE and vale.trabajador_id is None
    assert vale.observacion == cuerpo["observacion"] and vale.responsable_id
    assert vale.firma_modo == "SESION"
    movimiento = session.scalar(select(Movimiento).where(Movimiento.vale_id == vale.id))
    assert "CP-03" in movimiento.reglas and movimiento.motivo_baja == "Faltante de almacén"
    assert movimiento.trabajador_id is None
    repetida = sup.post("/api/vales", json=cuerpo)
    assert repetida.status_code == 200 and existencia(session, "KEP", articulo) == 18


@pytest.mark.parametrize("extra", [{"observacion": " "}, {"trabajador_id": str(uuid.uuid4())}])
def test_CP_03_rechaza_sin_observacion_o_adjudicar_perdida_al_trabajador(datos, session, extra):
    sup, _, articulo = datos
    antes = session.scalar(select(func.count()).select_from(Movimiento))
    respuesta = sup.post("/api/vales", json=ajuste(articulo, **extra))
    assert respuesta.status_code == 422, respuesta.text
    assert session.scalar(select(func.count()).select_from(Movimiento)) == antes
    assert existencia(session, "KEP", articulo) == 20


def test_CP_03_RG_04_no_saldo_negativo(datos, session):
    sup, _, articulo = datos
    respuesta = sup.post("/api/vales", json=ajuste(articulo, cantidad=21))
    assert respuesta.status_code == 409, respuesta.text
    assert existencia(session, "KEP", articulo) == 20


def test_CP_03_normalizar_observaciones_repetidas_respeta_limite(datos, session):
    sup, _, articulo = datos
    cuerpo = ajuste(
        articulo,
        renglones=[
            {"codigo": articulo.codigo, "observacion": "a" * 600},
            {"codigo": articulo.codigo, "observacion": "b" * 600},
        ],
    )
    respuesta = sup.post("/api/vales", json=cuerpo)
    assert respuesta.status_code == 422, respuesta.text
    assert existencia(session, "KEP", articulo) == 20


def test_CP_04_igualdad_entregado_devuelto_resguardo_consumido_faltante(datos, session):
    sup, compras, articulo = datos
    trabajador = crear_trabajador(session)
    respuesta = sup.post(
        "/api/vales",
        json=cuerpo_entrega(
            trabajador,
            [{"codigo": articulo.codigo, "cantidad": 5}],
            observacion="Entrega sin proyecto",
        ),
    )
    assert respuesta.status_code == 201, respuesta.text
    respuesta = sup.post(
        "/api/vales",
        json={
            "tipo": "DEVOLUCION",
            "id_cliente": str(uuid.uuid4()),
            "trabajador_id": str(trabajador.id),
            "renglones": [{"codigo": articulo.codigo, "cantidad": 2, "condicion": "BUENO"}],
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    assert sup.post("/api/vales", json=ajuste(articulo, 1)).status_code == 201
    r = articulo_del_reporte(reporte(sup, almacen(session)), articulo)
    assert r["otras_entradas"] == 20 and r["devuelto_a_almacen"] == 2
    assert r["entregado_trabajadores"] == 5 and r["devuelto_por_trabajadores"] == 2
    assert r["en_resguardo"] == 3 and r["faltantes"] == 1 and r["saldo_final"] == 16
    assert r["trabajadores"] == [
        {
            "id": str(trabajador.id),
            "nombre": trabajador.nombre,
            "numero_empleado": trabajador.numero_empleado,
            "cantidad": 3,
        }
    ]
    assert r["cuadra"] and r["diferencia"] == 0
    assert not any("costo" in clave for clave in r)
    consumible = crear_articulo(session, retornable=False)
    abastecer(compras, consumible, 4)
    respuesta = sup.post(
        "/api/vales",
        json=cuerpo_entrega(
            trabajador,
            [{"codigo": consumible.codigo, "cantidad": 3}],
            observacion="Entrega sin proyecto",
        ),
    )
    assert respuesta.status_code == 201, respuesta.text
    r = articulo_del_reporte(reporte(sup, almacen(session)), consumible)
    assert r["consumido"] == 3 and r["saldo_final"] == 1 and r["cuadra"]


def test_CP_04_rango_obligatorio_orden_y_lectura_de_cerrado(datos, session):
    sup, _, articulo = datos
    a = almacen(session)
    assert sup.get(f"/api/almacenes/{a.id}/reporte-cierre").status_code == 422
    assert reporte(sup, a, desde=str(hoy_mx() + timedelta(days=1))).status_code == 422
    a.estado = EstadoAlmacen.CERRADO
    session.flush()
    assert articulo_del_reporte(reporte(sup, a), articulo)["cuadra"]


def test_CP_04_permiso_y_alcance_C09_alias_valor(datos, session, cliente_como):
    sup, compras, _ = datos
    a = almacen(session)
    assert reporte(compras, a).status_code == 403
    assert reporte(sup, almacen(session, "CON")).status_code == 404
    almacenista = cliente_como("Almacenista")
    assert almacenista.post("/api/vales", json=ajuste(datos[2])).status_code == 403
    assert compras.get("/api/reportes/valor-inventario").status_code == 200
    assert almacenista.get("/api/reportes/valor-inventario").status_code == 403


def test_CP_04_recibido_traspasos_y_regresado(datos, session, cliente_como):
    _, _, articulo = datos
    abastecer_en(session, articulo, 4, "CON")
    admin = cliente_como("Administrador")
    r = articulo_del_reporte(reporte(admin, almacen(session, "CON")), articulo)
    assert r["recibido_traspasos"] == 4 and r["saldo_final"] == 4 and r["cuadra"]
    r = articulo_del_reporte(reporte(admin, almacen(session)), articulo)
    assert r["regresado"] == 4 and r["cuadra"]


def test_CP_04_saldo_inicial_historico_y_cancelacion_faltante(datos, session):
    from app.modulos.consulta.service_cierre import _inicio_utc

    sup, _, articulo = datos
    movimientos = session.scalars(
        select(Movimiento).where(Movimiento.articulo_id == articulo.id)
    ).all()
    for movimiento in movimientos:
        movimiento.creado_en = _inicio_utc(hoy_mx()) - timedelta(hours=1)
    session.flush()
    respuesta = sup.post("/api/vales", json=ajuste(articulo, 3))
    assert respuesta.status_code == 201, respuesta.text
    id_vale = respuesta.json()["id"]
    r = articulo_del_reporte(reporte(sup, almacen(session)), articulo)
    assert (
        r["saldo_inicial"] == 20
        and r["otras_entradas"] == 0
        and r["faltantes"] == 3
        and r["saldo_final"] == 17
        and r["cuadra"]
    )
    cancelada = sup.post(
        f"/api/vales/{id_vale}/cancelacion",
        json={"id_cliente": str(uuid.uuid4()), "motivo": "El equipo apareció en otro estante"},
    )
    assert cancelada.status_code == 201, cancelada.text
    r = articulo_del_reporte(reporte(sup, almacen(session)), articulo)
    assert r["faltantes"] == 0 and r["saldo_final"] == 20 and r["cuadra"]


def test_CP_01_CP_05_cierre_real_con_resguardo_sin_existencias(datos, session, cliente_como):
    admin = cliente_como("Administrador")
    clave = "T" + uuid.uuid4().hex[:7].upper()
    respuesta = admin.post(
        "/api/almacenes",
        json={
            "clave": clave,
            "nombre": f"Almacén cierre {clave}",
            "tipo": "PROYECTO",
            "padre_id": str(almacen(session, "CON").id),
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    a = almacen(session, clave)
    articulo = datos[2]
    abastecer_en(session, articulo, 3, clave)
    trabajador = crear_trabajador(session)
    respuesta = admin.post(
        "/api/vales",
        json=cuerpo_entrega(
            trabajador,
            [{"codigo": articulo.codigo, "cantidad": 3}],
            almacen_id=str(a.id),
            observacion="Entrega sin proyecto",
        ),
    )
    assert respuesta.status_code == 201, respuesta.text
    cerrada = admin.post(f"/api/almacenes/{a.id}/cierre")
    assert cerrada.status_code == 200, cerrada.text
    r = articulo_del_reporte(reporte(admin, a), articulo)
    assert r["en_resguardo"] == 3 and r["saldo_final"] == 0 and r["cuadra"]


def test_CP_04_retorno_otro_almacen_atribuye_fifo_cantidades(datos, session, cliente_como):
    admin = cliente_como("Administrador")
    articulo = datos[2]
    trabajador = crear_trabajador(session)
    abastecer_en(session, articulo, 3, "CON")
    for clave, cantidad in (("KEP", 2), ("CON", 3)):
        respuesta = admin.post(
            "/api/vales",
            json=cuerpo_entrega(
                trabajador,
                [{"codigo": articulo.codigo, "cantidad": cantidad}],
                almacen_id=str(almacen(session, clave).id),
                observacion="Entrega sin proyecto",
            ),
        )
        assert respuesta.status_code == 201, respuesta.text
    respuesta = admin.post(
        "/api/vales",
        json={
            "tipo": "DEVOLUCION",
            "id_cliente": str(uuid.uuid4()),
            "almacen_id": str(almacen(session, "CON").id),
            "trabajador_id": str(trabajador.id),
            "renglones": [{"codigo": articulo.codigo, "cantidad": 1, "condicion": "BUENO"}],
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    kep = articulo_del_reporte(reporte(admin, almacen(session)), articulo)
    con = articulo_del_reporte(reporte(admin, almacen(session, "CON")), articulo)
    assert kep["en_resguardo"] == 1 and kep["devuelto_por_trabajadores"] == 1
    assert con["en_resguardo"] == 3 and con["devuelto_por_trabajadores"] == 0
    assert kep["cuadra"] and con["cuadra"]


def test_CP_03_pieza_en_almacen_a_baja_sin_afectar_trabajador(datos, session):
    sup, compras, _ = datos
    articulo = crear_articulo(session, control="PIEZA")
    respuesta, codigo = entrar_pieza(compras, articulo)
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = ajuste(articulo, 1, renglones=[{"codigo": codigo, "cantidad": 1}])
    respuesta = sup.post("/api/vales", json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    pieza = session.scalar(select(Pieza).where(Pieza.codigo == codigo))
    assert session.get(Ubicacion, pieza.ubicacion_id).virtual == "BAJA"
    assert existencia(session, "KEP", articulo) == 0
    r = articulo_del_reporte(reporte(sup, almacen(session)), articulo)
    assert r["faltantes"] == 1 and r["en_resguardo"] == 0 and r["cuadra"]


def test_CP_03_pieza_con_trabajador_no_es_faltante_de_almacen(datos, session):
    sup, compras, _ = datos
    articulo = crear_articulo(session, control="PIEZA")
    respuesta, codigo = entrar_pieza(compras, articulo)
    assert respuesta.status_code == 201, respuesta.text
    trabajador = crear_trabajador(session)
    respuesta = sup.post(
        "/api/vales",
        json=cuerpo_entrega(trabajador, [{"codigo": codigo}], observacion="Entrega sin proyecto"),
    )
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = ajuste(articulo, 1, renglones=[{"codigo": codigo}])
    antes = session.scalar(select(func.count()).select_from(Movimiento))
    respuesta = sup.post("/api/vales", json=cuerpo)
    assert respuesta.status_code == 409, respuesta.text
    assert session.scalar(select(func.count()).select_from(Movimiento)) == antes


def test_CP_04_cancelar_entrega_usa_lote_original_no_fifo(datos, session, cliente_como):
    admin = cliente_como("Administrador")
    articulo = datos[2]
    trabajador = crear_trabajador(session)
    abastecer_en(session, articulo, 2, "CON")
    for clave, cantidad in (("KEP", 5), ("CON", 2)):
        respuesta = admin.post(
            "/api/vales",
            json=cuerpo_entrega(
                trabajador,
                [{"codigo": articulo.codigo, "cantidad": cantidad}],
                almacen_id=str(almacen(session, clave).id),
                observacion="Entrega sin proyecto",
            ),
        )
        assert respuesta.status_code == 201, respuesta.text
    id_vale = respuesta.json()["id"]
    respuesta = admin.post(
        f"/api/vales/{id_vale}/cancelacion",
        json={"id_cliente": str(uuid.uuid4()), "motivo": "Entrega duplicada"},
    )
    assert respuesta.status_code == 201, respuesta.text
    kep = articulo_del_reporte(reporte(admin, almacen(session)), articulo)
    con = articulo_del_reporte(reporte(admin, almacen(session, "CON")), articulo)
    assert kep["en_resguardo"] == 5 and kep["devuelto_por_trabajadores"] == 0
    assert con["en_resguardo"] == 0 and con["entregado_trabajadores"] == 0
    assert con["devuelto_por_trabajadores"] == 0 and con["cuadra"] and kep["cuadra"]


def test_CP_04_cancelar_devolucion_restaura_procedencia_original(datos, session, cliente_como):
    admin = cliente_como("Administrador")
    articulo = datos[2]
    trabajador = crear_trabajador(session)
    respuesta = admin.post(
        "/api/vales",
        json=cuerpo_entrega(
            trabajador,
            [{"codigo": articulo.codigo, "cantidad": 3}],
            almacen_id=str(almacen(session).id),
            observacion="Entrega sin proyecto",
        ),
    )
    assert respuesta.status_code == 201, respuesta.text
    respuesta = admin.post(
        "/api/vales",
        json={
            "tipo": "DEVOLUCION",
            "id_cliente": str(uuid.uuid4()),
            "almacen_id": str(almacen(session, "CON").id),
            "trabajador_id": str(trabajador.id),
            "renglones": [{"codigo": articulo.codigo, "cantidad": 2, "condicion": "BUENO"}],
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    id_vale = respuesta.json()["id"]
    respuesta = admin.post(
        f"/api/vales/{id_vale}/cancelacion",
        json={"id_cliente": str(uuid.uuid4()), "motivo": "Devolución duplicada"},
    )
    assert respuesta.status_code == 201, respuesta.text
    kep = articulo_del_reporte(reporte(admin, almacen(session)), articulo)
    con = articulo_del_reporte(reporte(admin, almacen(session, "CON")), articulo)
    assert kep["en_resguardo"] == 3 and kep["devuelto_por_trabajadores"] == 0 and kep["cuadra"]
    assert con["en_resguardo"] == 0 and con["entregado_trabajadores"] == 0
    assert con["devuelto_a_almacen"] == 0 and con["cuadra"]
