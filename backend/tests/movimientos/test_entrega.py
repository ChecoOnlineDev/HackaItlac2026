"""ENTREGA (US-ENT-001, 002 y 003): E-01 a E-07, E-12, E-15 a E-22, E-24, E-26 a E-28, SM-01 a 06"""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select, update

from app.core.tiempo import ahora_utc, hoy_mx
from app.modulos.catalogo.models import EstadoPieza, Pieza
from app.modulos.catalogo.service import CatalogoService
from app.modulos.movimientos.models import Movimiento
from app.modulos.trabajadores.models import EstadoTrabajador, PeriodoContrato
from tests.movimientos.ayudas import (
    abastecer,
    almacen,
    crear_articulo,
    crear_trabajador,
    cuerpo_entrega,
    entrar_pieza,
    existencia,
    existencia_de_trabajador,
    total_movimientos,
    total_vales,
    unico,
)

VALES = "/api/vales"
EVALUAR = "/api/vales/evaluar"


def evaluar(cliente, trabajador, renglones, **extra):
    r = cliente.post(
        EVALUAR,
        json={"tipo": "ENTREGA", "trabajador_id": str(trabajador.id), "renglones": renglones}
        | extra,
    )
    assert r.status_code == 200, r.text
    return r.json()


def renglon(codigo, cantidad=1, **extra):
    return {"codigo": codigo, "cantidad": cantidad} | extra


def motivos(evaluacion, indice=0):
    return [m["regla"] for m in evaluacion["renglones"][indice]["motivos"]]


def pieza_en_kep(compras, session, *, estado=EstadoPieza.APTO, vigente_hasta=None, **art):
    """Una pieza de un artículo nuevo, ya dentro de Kepler (ENTRADA real)."""
    articulo = crear_articulo(session, control="PIEZA", **art)
    r, codigo = entrar_pieza(compras, articulo)
    assert r.status_code == 201, r.text
    pieza = session.scalar(select(Pieza).where(Pieza.codigo == codigo))
    CatalogoService(session).actualizar_estado_pieza(
        pieza.id, estado=estado, inspeccion_vigente_hasta=vigente_hasta
    )
    return articulo, pieza


@pytest.fixture
def trabajador(session):
    return crear_trabajador(session)


# ----------------------------------------------------------------------------- código


def test_E_01_un_codigo_desconocido_es_rojo(almacenista, trabajador):
    ev = evaluar(almacenista, trabajador, [renglon("NO-EXISTE-X")])
    r = ev["renglones"][0]
    assert r["nivel"] == "ROJO" and motivos(ev) == ["E-01"] and r["articulo"] is None
    assert ev["nivel"] == "ROJO" and ev["puede_confirmar"] is False
    assert r["autorizable"] is False


def test_E_01_la_credencial_de_un_trabajador_no_es_un_articulo(almacenista, trabajador):
    ev = evaluar(almacenista, trabajador, [renglon(f"CRED-{trabajador.numero_empleado}")])
    assert motivos(ev) == ["E-01"]


def test_E_01_un_articulo_por_pieza_se_entrega_con_el_codigo_de_la_pieza(
    almacenista, compras, session, trabajador
):
    articulo, _ = pieza_en_kep(compras, session, vigente_hasta=hoy_mx() + timedelta(days=9))
    ev = evaluar(almacenista, trabajador, [renglon(articulo.codigo)])
    assert motivos(ev) == ["E-01"] and "pieza" in ev["renglones"][0]["motivos"][0]["mensaje"]


def test_E_19_un_articulo_inactivo_no_se_entrega(almacenista, compras, session, trabajador):
    articulo = crear_articulo(session)
    abastecer(compras, articulo, 5)
    articulo.activo = False
    articulo.motivo_inactivacion = "Ya no se usa"
    session.flush()
    ev = evaluar(almacenista, trabajador, [renglon(articulo.codigo)])
    assert motivos(ev) == ["E-19"] and ev["renglones"][0]["nivel"] == "ROJO"
    assert "Ya no se usa" in ev["renglones"][0]["motivos"][0]["mensaje"]


# -------------------------------------------------------------------------- trabajador


def test_E_02_trabajador_con_contrato_vencido_pone_todo_el_vale_en_rojo(
    almacenista, compras, session
):
    vencido = crear_trabajador(session, vigente=False)
    guantes = crear_articulo(session)
    abastecer(compras, guantes, 5)
    ev = evaluar(almacenista, vencido, [renglon(guantes.codigo)])
    assert ev["nivel"] == "ROJO" and ev["puede_confirmar"] is False
    assert ev["motivos"][0]["regla"] == "E-02"
    # Un renglón que en sí está bien también queda en rojo: es rojo todo el vale.
    assert ev["renglones"][0]["nivel"] == "ROJO" and motivos(ev) == ["E-02"]
    assert "plantilla" in ev["renglones"][0]["motivos"][0]["mensaje"]


def test_E_02_confirmar_con_un_trabajador_no_vigente_no_guarda_nada(almacenista, compras, session):
    vencido = crear_trabajador(session, vigente=False)
    guantes = crear_articulo(session)
    abastecer(compras, guantes, 5)
    vales, movs = total_vales(session), total_movimientos(session)
    r = almacenista.post(VALES, json=cuerpo_entrega(vencido, [renglon(guantes.codigo)]))
    assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO"
    assert r.json()["detalles"]["nivel"] == "ROJO"
    assert (total_vales(session), total_movimientos(session)) == (vales, movs)
    assert existencia(session, "KEP", guantes) == 5


@pytest.mark.parametrize("estado", [EstadoTrabajador.BAJA_EN_PROCESO, EstadoTrabajador.INACTIVO])
def test_E_02_trabajador_en_baja_no_recibe(almacenista, session, estado):
    t = crear_trabajador(session, estado=estado)
    ev = evaluar(almacenista, t, [])
    assert ev["nivel"] == "ROJO" and ev["motivos"][0]["regla"] == "E-02"


def test_E_02_el_ultimo_dia_del_contrato_todavia_es_vigente(almacenista, session, monkeypatch):
    t = crear_trabajador(session)
    fin = session.scalar(select(PeriodoContrato.fin).where(PeriodoContrato.trabajador_id == t.id))
    monkeypatch.setattr("app.modulos.trabajadores.service.hoy_mx", lambda: fin)
    ev = evaluar(almacenista, t, [])
    assert ev["motivos"] == [] and ev["nivel"] == "VERDE"
    monkeypatch.setattr("app.modulos.trabajadores.service.hoy_mx", lambda: fin + timedelta(days=1))
    assert evaluar(almacenista, t, [])["motivos"][0]["regla"] == "E-02"


def test_E_12_pendientes_de_un_periodo_anterior_es_aviso_amarillo(almacenista, compras, session):
    t = crear_trabajador(session)
    casco = crear_articulo(session, retornable=True)
    abastecer(compras, casco, 3)
    r = almacenista.post(VALES, json=cuerpo_entrega(t, [renglon(casco.codigo)]))
    assert r.status_code == 201, r.text
    # La entrega es de hace 90 días: antes de que empezara el periodo vigente (hace 30).
    session.execute(
        update(Movimiento)
        .where(Movimiento.vale_id == uuid.UUID(r.json()["id"]))
        .values(creado_en=ahora_utc() - timedelta(days=90))
    )
    otro = crear_articulo(session)
    abastecer(compras, otro, 3)
    ev = evaluar(almacenista, t, [renglon(otro.codigo)])
    assert [m["regla"] for m in ev["motivos"]] == ["E-12"]
    assert ev["nivel"] == "AMARILLO" and ev["puede_confirmar"] is True  # no bloquea
    assert ev["renglones"][0]["nivel"] == "VERDE"


def test_E_17_la_evaluacion_trae_la_ficha_del_trabajador_con_su_resguardo(
    almacenista, compras, session
):
    t = crear_trabajador(session)
    casco = crear_articulo(session, retornable=True)
    abastecer(compras, casco, 2)
    almacenista.post(VALES, json=cuerpo_entrega(t, [renglon(casco.codigo)]))
    ev = evaluar(almacenista, t, [])
    ficha = ev["trabajador"]
    assert ficha["nombre"] == t.nombre and ficha["vigencia"]["vigente"] is True
    assert ficha["resguardo"][0]["codigo"] == casco.codigo
    assert "curp" not in ficha and "nss" not in ficha  # RG-13


# ---------------------------------------------------------------- ubicación y existencias


def _pieza_en_otro_almacen(compras, session, clave="CON"):
    from app.modulos.almacenes.service import AlmacenService

    _, pieza = pieza_en_kep(compras, session, vigente_hasta=hoy_mx() + timedelta(days=30))
    pieza.ubicacion_id = AlmacenService(session).ubicacion_de_almacen(almacen(session, clave).id).id
    session.flush()
    return pieza


def test_E_03_una_pieza_en_otro_almacen_es_rojo_y_dice_donde_esta_al_administrador(
    cliente_como, compras, session, trabajador
):
    # AC-06: dónde está una pieza ajena al almacén solo lo ve quien tiene `almacenes.todos`.
    pieza = _pieza_en_otro_almacen(compras, session)
    admin = cliente_como("Administrador")
    ev = evaluar(
        admin, trabajador, [renglon(pieza.codigo)], almacen_id=str(almacen(session, "KEP").id)
    )
    r = ev["renglones"][0]
    assert r["nivel"] == "ROJO" and "E-03" in motivos(ev)
    assert r["titular"]["tipo"] == "ALMACEN" and "CON" in r["titular"]["descripcion"]
    assert "CON" in r["motivos"][0]["mensaje"]


def test_E_03_una_pieza_en_otro_almacen_es_rojo_sin_decir_donde_esta_al_almacenista(
    almacenista, compras, session, trabajador
):
    # AC-06: el almacenista sigue viendo el rojo, pero no se entera de qué hay en otro almacén.
    pieza = _pieza_en_otro_almacen(compras, session)
    ev = evaluar(almacenista, trabajador, [renglon(pieza.codigo)])
    r = ev["renglones"][0]
    assert r["nivel"] == "ROJO" and "E-03" in motivos(ev)
    assert r["motivos"][0]["mensaje"] == (
        "Esta pieza no está registrada en tu almacén. No se puede entregar."
    )
    assert r["titular"]["tipo"] is None and r["titular"]["id"] is None
    assert "CON" not in str(r["titular"]) and "Contratistas" not in str(ev)


def test_E_03_una_pieza_en_resguardo_de_otro_trabajador_dice_quien_la_tiene_al_administrador(
    cliente_como, almacenista, compras, session, trabajador
):
    _, pieza = pieza_en_kep(compras, session, vigente_hasta=hoy_mx() + timedelta(days=30))
    otro = crear_trabajador(session)
    r = almacenista.post(VALES, json=cuerpo_entrega(otro, [renglon(pieza.codigo)]))
    assert r.status_code == 201, r.text
    admin = cliente_como("Administrador")
    ev = evaluar(
        admin, trabajador, [renglon(pieza.codigo)], almacen_id=str(almacen(session, "KEP").id)
    )
    titular = ev["renglones"][0]["titular"]
    assert "E-03" in motivos(ev)
    assert titular["tipo"] == "TRABAJADOR" and titular["numero_empleado"] == otro.numero_empleado


def test_E_03_una_pieza_en_resguardo_de_otro_trabajador_no_dice_quien_la_tiene_al_almacenista(
    almacenista, compras, session, trabajador
):
    _, pieza = pieza_en_kep(compras, session, vigente_hasta=hoy_mx() + timedelta(days=30))
    otro = crear_trabajador(session)
    r = almacenista.post(VALES, json=cuerpo_entrega(otro, [renglon(pieza.codigo)]))
    assert r.status_code == 201, r.text
    ev = evaluar(almacenista, trabajador, [renglon(pieza.codigo)])
    assert "E-03" in motivos(ev)
    assert ev["renglones"][0]["titular"]["tipo"] is None
    assert otro.numero_empleado not in str(ev) and otro.nombre not in str(ev)


def test_E_03_una_pieza_que_nunca_entro_a_un_almacen_es_rojo(almacenista, session, trabajador):
    from tests.movimientos.ayudas import crear_pieza

    articulo = crear_articulo(session, control="PIEZA")
    pieza = crear_pieza(session, articulo)
    ev = evaluar(almacenista, trabajador, [renglon(pieza.codigo)])
    assert "E-03" in motivos(ev)
    assert "tu almacén" in ev["renglones"][0]["motivos"][0]["mensaje"]


def test_E_04_una_cantidad_mayor_a_la_existencia_es_rojo(almacenista, compras, session, trabajador):
    guantes = crear_articulo(session)
    abastecer(compras, guantes, 3)
    ev = evaluar(almacenista, trabajador, [renglon(guantes.codigo, 4)])
    r = ev["renglones"][0]
    assert r["nivel"] == "ROJO" and motivos(ev) == ["E-04"] and r["disponible"] == 3
    assert "hay 3" in r["motivos"][0]["mensaje"]
    exacta = evaluar(almacenista, trabajador, [renglon(guantes.codigo, 3)])
    assert exacta["renglones"][0]["nivel"] == "VERDE"


def test_E_04_sin_existencia_en_este_almacen_es_rojo(almacenista, session, trabajador):
    guantes = crear_articulo(session)
    ev = evaluar(almacenista, trabajador, [renglon(guantes.codigo)])
    assert motivos(ev) == ["E-04"] and ev["renglones"][0]["disponible"] == 0


def test_RG_05_una_pieza_se_entrega_de_una_en_una(almacenista, compras, session, trabajador):
    _, pieza = pieza_en_kep(compras, session, vigente_hasta=hoy_mx() + timedelta(days=30))
    ev = evaluar(almacenista, trabajador, [renglon(pieza.codigo, 2)])
    assert "RG-05" in motivos(ev) and ev["renglones"][0]["nivel"] == "ROJO"


# ------------------------------------------------------------------------- seguridad


def test_E_05_el_mensaje_de_una_pieza_no_apta_se_lee_natural(
    almacenista, compras, session, trabajador
):
    articulo, pieza = pieza_en_kep(
        compras, session, estado=EstadoPieza.NO_APTO, vigente_hasta=hoy_mx() + timedelta(days=30)
    )
    ev = evaluar(almacenista, trabajador, [renglon(pieza.codigo)])
    mensaje = ev["renglones"][0]["motivos"][0]["mensaje"]
    assert mensaje == "La pieza no es apta. No se puede entregar."


@pytest.mark.parametrize(
    "estado",
    [
        EstadoPieza.NO_APTO,
        EstadoPieza.EN_MANTENIMIENTO,
        EstadoPieza.EN_CALIBRACION,
        EstadoPieza.BAJA,
    ],
)
def test_E_05_una_pieza_que_no_esta_apta_es_rojo_y_no_se_autoriza(
    almacenista, compras, session, trabajador, estado
):
    articulo, pieza = pieza_en_kep(
        compras, session, estado=estado, vigente_hasta=hoy_mx() + timedelta(days=30)
    )
    ev = evaluar(almacenista, trabajador, [renglon(pieza.codigo)])
    r = ev["renglones"][0]
    assert r["nivel"] == "ROJO" and "E-05" in motivos(ev)
    assert r["autorizable"] is False  # SM-04, A-06
    assert r["pieza"]["estado"] == estado.value  # la pantalla muestra el estado
    assert ev["puede_confirmar"] is False


def test_E_06_una_pieza_sin_inspeccion_vigente_es_rojo(almacenista, compras, session, trabajador):
    _, pieza = pieza_en_kep(compras, session, requiere_inspeccion=True)
    ev = evaluar(almacenista, trabajador, [renglon(pieza.codigo)])
    r = ev["renglones"][0]
    assert motivos(ev) == ["E-06"] and "Sin inspección" in r["motivos"][0]["mensaje"]
    assert r["autorizable"] is False


def test_E_06_una_inspeccion_vencida_dice_la_fecha(almacenista, compras, session, trabajador):
    ayer = hoy_mx() - timedelta(days=1)
    _, pieza = pieza_en_kep(compras, session, requiere_inspeccion=True, vigente_hasta=ayer)
    ev = evaluar(almacenista, trabajador, [renglon(pieza.codigo)])
    assert motivos(ev) == ["E-06"]
    assert ayer.strftime("%d/%m/%Y") in ev["renglones"][0]["motivos"][0]["mensaje"]
    assert ev["renglones"][0]["pieza"]["inspeccion_vigente_hasta"] == ayer.isoformat()


@pytest.mark.parametrize("dias", [0, 1, 180])
def test_E_06_una_inspeccion_que_vence_hoy_todavia_es_vigente(
    almacenista, compras, session, trabajador, dias
):
    _, pieza = pieza_en_kep(
        compras, session, requiere_inspeccion=True, vigente_hasta=hoy_mx() + timedelta(days=dias)
    )
    ev = evaluar(almacenista, trabajador, [renglon(pieza.codigo)])
    # Vigente: no es E-06 y se puede confirmar. Si vence en 7 días o menos, avisa (E-11, amarillo).
    por_vencer = dias <= 7
    assert ev["renglones"][0]["nivel"] == ("AMARILLO" if por_vencer else "VERDE")
    assert "E-06" not in motivos(ev) and ev["puede_confirmar"] is True


def test_E_06_solo_aplica_si_el_articulo_requiere_inspeccion(
    almacenista, compras, session, trabajador
):
    _, pieza = pieza_en_kep(compras, session, requiere_inspeccion=False)
    ev = evaluar(almacenista, trabajador, [renglon(pieza.codigo)])
    assert ev["renglones"][0]["nivel"] == "VERDE"


def test_US_ENT_002_una_pieza_apta_con_inspeccion_vigente_es_verde(
    almacenista, compras, session, trabajador
):
    articulo, pieza = pieza_en_kep(
        compras, session, requiere_inspeccion=True, vigente_hasta=hoy_mx() + timedelta(days=60)
    )
    ev = evaluar(almacenista, trabajador, [renglon(pieza.codigo)])
    r = ev["renglones"][0]
    assert r["nivel"] == "VERDE" and r["motivos"] == []
    assert r["pieza"]["id"] == str(pieza.id) and r["articulo"]["nombre"] == articulo.nombre
    assert r["disponible"] == 1 and r["titular"] is None


def test_SM_01_se_muestra_el_nivel_mas_grave_y_todos_los_motivos(
    almacenista, compras, session, trabajador
):
    ayer = hoy_mx() - timedelta(days=1)
    _, pieza = pieza_en_kep(
        compras,
        session,
        estado=EstadoPieza.NO_APTO,
        requiere_inspeccion=True,
        vigente_hasta=ayer,
        limite_cantidad=1,
    )
    ev = evaluar(almacenista, trabajador, [renglon(pieza.codigo)])
    r = ev["renglones"][0]
    assert r["nivel"] == "ROJO"
    assert motivos(ev) == ["E-05", "E-06"]


def test_SM_06_el_orden_de_los_motivos_es_codigo_trabajador_ubicacion_seguridad_limites_avisos(
    almacenista, compras, session
):
    vencido = crear_trabajador(session, vigente=False)
    ayer = hoy_mx() - timedelta(days=1)
    _, pieza = pieza_en_kep(
        compras,
        session,
        estado=EstadoPieza.NO_APTO,
        requiere_inspeccion=True,
        vigente_hasta=ayer,
        requiere_autorizacion=True,
        cantidad_aviso=1,
    )
    from app.modulos.almacenes.service import AlmacenService

    pieza.ubicacion_id = AlmacenService(session).ubicacion_de_almacen(almacen(session, "CON").id).id
    session.flush()
    ev = evaluar(almacenista, vencido, [renglon(pieza.codigo)])
    assert motivos(ev) == ["E-02", "E-03", "E-05", "E-06", "E-26", "E-27"]


# ----------------------------------------------------------------- repetidos y cantidades


def test_E_15_una_pieza_repetida_en_el_vale_se_ignora(almacenista, compras, session, trabajador):
    _, pieza = pieza_en_kep(compras, session, vigente_hasta=hoy_mx() + timedelta(days=30))
    ev = evaluar(almacenista, trabajador, [renglon(pieza.codigo), renglon(pieza.codigo)])
    assert len(ev["renglones"]) == 1 and ev["renglones"][0]["cantidad"] == 1
    r = almacenista.post(
        VALES, json=cuerpo_entrega(trabajador, [renglon(pieza.codigo), renglon(pieza.codigo)])
    )
    assert r.status_code == 201 and len(r.json()["renglones"]) == 1


def test_E_16_un_articulo_por_cantidad_repetido_suma_uno(almacenista, compras, session, trabajador):
    guantes = crear_articulo(session)
    abastecer(compras, guantes, 10)
    ev = evaluar(almacenista, trabajador, [renglon(guantes.codigo), renglon(guantes.codigo)])
    assert len(ev["renglones"]) == 1 and ev["renglones"][0]["cantidad"] == 2
    r = almacenista.post(
        VALES,
        json=cuerpo_entrega(trabajador, [renglon(guantes.codigo), renglon(guantes.codigo)]),
    )
    assert r.status_code == 201
    assert existencia(session, "KEP", guantes) == 8


# --------------------------------------------------------------- retornable y consumible


def test_E_20_un_retornable_pasa_del_almacen_al_trabajador(
    almacenista, compras, session, trabajador
):
    casco = crear_articulo(session, retornable=True)
    abastecer(compras, casco, 5)
    r = almacenista.post(VALES, json=cuerpo_entrega(trabajador, [renglon(casco.codigo, 2)]))
    assert r.status_code == 201, r.text
    assert existencia(session, "KEP", casco) == 3
    assert existencia_de_trabajador(session, trabajador, casco) == 2
    mov = session.scalar(select(Movimiento).where(Movimiento.vale_id == uuid.UUID(r.json()["id"])))
    assert mov.saldo_origen == 3 and mov.saldo_destino == 2 and mov.trabajador_id == trabajador.id


def test_E_20_una_pieza_retornable_queda_en_la_ubicacion_del_trabajador(
    almacenista, compras, session, trabajador
):
    from app.modulos.almacenes.service import AlmacenService

    _, pieza = pieza_en_kep(compras, session, vigente_hasta=hoy_mx() + timedelta(days=30))
    r = almacenista.post(VALES, json=cuerpo_entrega(trabajador, [renglon(pieza.codigo)]))
    assert r.status_code == 201, r.text
    session.refresh(pieza)
    assert pieza.ubicacion_id == AlmacenService(session).ubicacion_de_trabajador(trabajador.id).id


def test_E_21_un_consumible_pasa_a_consumido_con_el_trabajador_anotado(
    almacenista, compras, session, trabajador
):
    from app.modulos.almacenes.models import UbicacionVirtual
    from app.modulos.almacenes.service import AlmacenService

    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 10)
    r = almacenista.post(VALES, json=cuerpo_entrega(trabajador, [renglon(guantes.codigo, 3)]))
    assert r.status_code == 201, r.text
    mov = session.scalar(select(Movimiento).where(Movimiento.vale_id == uuid.UUID(r.json()["id"])))
    consumido = AlmacenService(session).ubicacion_virtual(UbicacionVirtual.CONSUMIDO)
    assert mov.destino_id == consumido.id and mov.trabajador_id == trabajador.id
    assert existencia(session, "KEP", guantes) == 7
    assert existencia_de_trabajador(session, trabajador, guantes) == 0  # no genera pendiente


def test_E_22_se_registra_la_condicion_al_salir_de_cada_renglon(
    almacenista, compras, session, trabajador
):
    a, b = crear_articulo(session), crear_articulo(session)
    abastecer(compras, a, 2)
    abastecer(compras, b, 2)
    r = almacenista.post(
        VALES,
        json=cuerpo_entrega(
            trabajador,
            [renglon(a.codigo), renglon(b.codigo, condicion="DESGASTE", observacion="Usado")],
        ),
    )
    assert r.status_code == 201, r.text
    movs = session.scalars(
        select(Movimiento)
        .where(Movimiento.vale_id == uuid.UUID(r.json()["id"]))
        .order_by(Movimiento.renglon)
    ).all()
    assert [m.condicion for m in movs] == ["BUENO", "DESGASTE"]
    assert movs[1].observacion == "Usado"


def test_E_22_un_equipo_danado_no_se_entrega(almacenista, compras, session, trabajador):
    a = crear_articulo(session)
    abastecer(compras, a, 2)
    r = almacenista.post(
        VALES, json=cuerpo_entrega(trabajador, [renglon(a.codigo, condicion="DANADO")])
    )
    assert r.status_code == 422


# ------------------------------------------------------------------ avisos y autorización


def test_E_26_un_articulo_de_uso_especial_es_naranja_con_su_motivo(
    almacenista, compras, session, trabajador
):
    herramienta = crear_articulo(
        session, requiere_autorizacion=True, motivo_uso_especial="Uso restringido por seguridad"
    )
    abastecer(compras, herramienta, 2)
    ev = evaluar(almacenista, trabajador, [renglon(herramienta.codigo)])
    r = ev["renglones"][0]
    assert r["nivel"] == "NARANJA" and motivos(ev) == ["E-26"] and r["autorizable"] is True
    assert "Uso restringido por seguridad" in r["motivos"][0]["mensaje"]
    assert ev["puede_confirmar"] is False  # SM-03: falta la autorización


def test_E_26_quitar_el_requisito_deja_el_renglon_en_verde(
    almacenista, compras, session, trabajador
):
    herramienta = crear_articulo(session, requiere_autorizacion=True)
    abastecer(compras, herramienta, 2)
    assert evaluar(almacenista, trabajador, [renglon(herramienta.codigo)])["nivel"] == "NARANJA"
    herramienta.requiere_autorizacion = False
    session.flush()
    assert evaluar(almacenista, trabajador, [renglon(herramienta.codigo)])["nivel"] == "VERDE"


def test_SM_03_un_naranja_sin_autorizacion_no_se_confirma(
    almacenista, compras, session, trabajador
):
    herramienta = crear_articulo(session, requiere_autorizacion=True)
    abastecer(compras, herramienta, 2)
    vales = total_vales(session)
    r = almacenista.post(VALES, json=cuerpo_entrega(trabajador, [renglon(herramienta.codigo)]))
    assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO"
    assert r.json()["detalles"]["renglones"][0]["nivel"] == "NARANJA"
    assert total_vales(session) == vales


def test_E_27_una_cantidad_inusual_pide_confirmarla(almacenista, compras, session, trabajador):
    guantes = crear_articulo(session, retornable=False, cantidad_aviso=5)
    abastecer(compras, guantes, 20)
    normal = evaluar(almacenista, trabajador, [renglon(guantes.codigo, 4)])
    assert normal["renglones"][0]["requiere_confirmacion"] is False
    inusual = evaluar(almacenista, trabajador, [renglon(guantes.codigo, 5)])
    r = inusual["renglones"][0]
    assert r["requiere_confirmacion"] is True and motivos(inusual) == ["E-27"]
    assert r["nivel"] == "AMARILLO" and inusual["puede_confirmar"] is True  # el servidor no bloquea


def test_E_27_sin_aviso_configurado_no_aplica(almacenista, compras, session, trabajador):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 20)
    ev = evaluar(almacenista, trabajador, [renglon(guantes.codigo, 15)])
    assert ev["renglones"][0]["requiere_confirmacion"] is False


# ----------------------------------------------------------------------- borrador


def test_E_28_evaluar_no_escribe_nada_ni_cambia_las_existencias(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 10)
    vales, movs = total_vales(session), total_movimientos(session)
    ev = evaluar(almacenista, trabajador, [renglon(guantes.codigo, 4)])
    assert ev["puede_confirmar"] is True
    assert (total_vales(session), total_movimientos(session)) == (vales, movs)
    assert existencia(session, "KEP", guantes) == 10
    assert existencia_de_trabajador(session, trabajador, guantes) == 0


def test_E_28_un_vale_sin_renglones_todavia_se_evalua_pero_no_se_confirma(almacenista, trabajador):
    ev = evaluar(almacenista, trabajador, [])
    assert ev["renglones"] == [] and ev["puede_confirmar"] is False
    r = almacenista.post(VALES, json=cuerpo_entrega(trabajador, []))
    assert r.status_code == 422


# ----------------------------------------------------------------- el vale emitido


def test_E_24_el_vale_trae_folio_trabajador_area_descripcion_condicion_responsable_y_qr(
    almacenista, compras, session, trabajador
):
    articulo, pieza = pieza_en_kep(
        compras, session, vigente_hasta=hoy_mx() + timedelta(days=30), marca="Marca X"
    )
    guantes = crear_articulo(session, retornable=False, talla="M")
    abastecer(compras, guantes, 5)
    r = almacenista.post(
        VALES,
        json=cuerpo_entrega(trabajador, [renglon(pieza.codigo), renglon(guantes.codigo, 2)]),
    )
    assert r.status_code == 201, r.text
    vale = r.json()
    assert vale["folio"].startswith("KEP-ENT-") and vale["token"]
    d = almacenista.get(f"{VALES}/{vale['id']}").json()
    assert d["tipo"] == "ENTREGA" and d["estado"] == "EMITIDO" and d["creado_en"].endswith("Z")
    assert d["trabajador"]["numero_empleado"] == trabajador.numero_empleado
    assert d["trabajador"]["area_obra"] == "Midrex" and d["trabajador"]["puesto"] == "Soldador"
    assert d["responsable"]["nombre"] == "Almacenista Kepler"
    assert d["almacen"]["clave"] == "KEP" and d["firma_modo"] == "PANTALLA"
    assert d["tiene_firma"] is True and d["valido"] is None
    por_pieza, por_cantidad = d["renglones"]
    assert por_pieza["marca"] == "Marca X" and por_pieza["codigo_pieza"] == pieza.codigo
    assert por_pieza["numero_serie"] == pieza.numero_serie and por_pieza["condicion"] == "BUENO"
    assert por_cantidad["cantidad"] == 2 and por_cantidad["talla"] == "M"
    assert por_pieza["origen"]["clave"] == "KEP"
    assert por_pieza["destino"]["clave"] == trabajador.numero_empleado
    assert por_cantidad["destino"]["tipo"] == "CONSUMIDO"
    # El QR abre el vale.
    por_token = almacenista.get(f"{VALES}/por-token/{vale['token']}")
    assert por_token.status_code == 200 and por_token.json()["id"] == vale["id"]


def test_E_24_el_vale_aparece_en_la_ficha_del_trabajador(
    almacenista, supervisor, compras, session, trabajador
):
    casco = crear_articulo(session, retornable=True)
    abastecer(compras, casco, 2)
    r = almacenista.post(VALES, json=cuerpo_entrega(trabajador, [renglon(casco.codigo)]))
    ficha = supervisor.get(f"/api/trabajadores/{trabajador.id}").json()
    assert ficha["resguardo"][0]["folio"] == r.json()["folio"]


# ------------------------------------------------------------------ permisos y almacén


def test_AC_04_la_entrega_exige_entregas_crear(compras, cliente_como, session, trabajador):
    guantes = crear_articulo(session)
    cuerpo = cuerpo_entrega(trabajador, [renglon(guantes.codigo)])
    for cliente in (compras, cliente_como("Recursos Humanos")):
        assert cliente.post(VALES, json=cuerpo).status_code == 403
        assert cliente.post(EVALUAR, json=cuerpo).status_code == 403


def test_AC_01_sin_sesion_responde_401(client, trabajador):
    r = client.post(EVALUAR, json={"tipo": "ENTREGA", "trabajador_id": str(trabajador.id)})
    assert r.status_code == 401 and r.json()["codigo"] == "NO_AUTENTICADO"


def test_E_01_la_entrega_pide_trabajador_y_un_trabajador_inexistente_da_404(almacenista):
    r = almacenista.post(EVALUAR, json={"tipo": "ENTREGA", "renglones": []})
    assert r.status_code == 422 and r.json()["detalles"][0]["campo"] == "trabajador_id"
    r = almacenista.post(EVALUAR, json={"tipo": "ENTREGA", "trabajador_id": str(uuid.uuid4())})
    assert r.status_code == 404


def test_AC_13_si_el_usuario_cambio_de_almacen_el_vale_no_se_guarda(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session)
    abastecer(compras, guantes, 5)
    otro = almacen(session, "CON")
    vales = total_vales(session)
    r = almacenista.post(
        VALES, json=cuerpo_entrega(trabajador, [renglon(guantes.codigo)], almacen_id=str(otro.id))
    )
    assert r.status_code == 409 and r.json()["codigo"] == "ALMACEN_CAMBIO"
    assert r.json()["detalles"]["almacen"]["clave"] == "KEP"
    assert total_vales(session) == vales


def test_AC_13_almacen_cambio_trae_el_detalle_del_contrato_al_evaluar_y_al_confirmar(
    almacenista, session, trabajador
):
    """Contrato: `detalles = {almacen_captura_id, almacen: {id, clave, nombre}}`, en ambos."""
    guantes = crear_articulo(session)
    otro = almacen(session, "CON")
    propio = almacen(session, "KEP")
    cuerpo = cuerpo_entrega(trabajador, [renglon(guantes.codigo)], almacen_id=str(otro.id))
    for url, cuerpo_enviado in ((VALES, cuerpo), (EVALUAR, {**cuerpo, "tipo": "ENTREGA"})):
        r = almacenista.post(url, json=cuerpo_enviado)
        assert r.status_code == 409 and r.json()["codigo"] == "ALMACEN_CAMBIO"
        assert r.json()["detalles"] == {
            "almacen_captura_id": str(otro.id),
            "almacen": {"id": str(propio.id), "clave": "KEP", "nombre": propio.nombre},
        }


def test_AC_06_quien_opera_todos_los_almacenes_indica_cual(
    supervisor, compras, session, trabajador
):
    guantes = crear_articulo(session)
    abastecer(compras, guantes, 5)
    cuerpo = cuerpo_entrega(trabajador, [renglon(guantes.codigo)])
    r = supervisor.post(VALES, json=cuerpo)
    assert r.status_code == 422 and r.json()["detalles"][0]["campo"] == "almacen_id"
    kep = almacen(session, "KEP")
    r = supervisor.post(VALES, json=cuerpo | {"almacen_id": str(kep.id)})
    assert r.status_code == 201 and r.json()["folio"].startswith("KEP-ENT-")


def test_E_01_la_entrega_no_acepta_datos_de_pieza_de_entrada(almacenista, trabajador):
    r = almacenista.post(
        EVALUAR,
        json={
            "tipo": "ENTREGA",
            "trabajador_id": str(trabajador.id),
            "renglones": [{"codigo": "X", "pieza": {"codigo": unico("P")}}],
        },
    )
    assert r.status_code == 422


def test_TRD_11_evaluar_un_vale_de_cinco_renglones_tarda_menos_de_500_ms(
    almacenista, compras, session, trabajador
):
    import time

    articulos = [crear_articulo(session, retornable=bool(n % 2)) for n in range(5)]
    for articulo in articulos:
        abastecer(compras, articulo, 10)
    cuerpo = {
        "tipo": "ENTREGA",
        "trabajador_id": str(trabajador.id),
        "renglones": [renglon(a.codigo, 2) for a in articulos],
    }
    almacenista.post(EVALUAR, json=cuerpo)  # calienta
    tiempos = []
    for _ in range(3):
        inicio = time.perf_counter()
        r = almacenista.post(EVALUAR, json=cuerpo)
        tiempos.append(time.perf_counter() - inicio)
        assert r.status_code == 200 and len(r.json()["renglones"]) == 5
    assert min(tiempos) < 0.5, tiempos
