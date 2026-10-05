"""DEVOLUCION (US-DEV-001, fase 4): V-01 a V-07, V-11, V-12, V-14, F-08, F-12, SM-05, CF-11."""

import json
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.core.tiempo import hoy_mx
from app.modulos.acceso.permisos import P
from app.modulos.almacenes.models import Ubicacion
from app.modulos.almacenes.service import AlmacenService
from app.modulos.archivos.models import Adjunto
from app.modulos.catalogo.models import EstadoPieza
from app.modulos.inspecciones.models import EventoPieza
from app.modulos.movimientos.models import Existencia, Movimiento, Vale
from app.modulos.trabajadores.models import EstadoTrabajador, PeriodoContrato
from tests.conftest import iniciar_sesion_en
from tests.movimientos.ayudas import (
    abastecer,
    almacen,
    crear_articulo,
    crear_trabajador,
    existencia,
    existencia_de_trabajador,
    total_movimientos,
    total_vales,
)
from tests.movimientos.ayudas_devolucion import (
    EVALUAR,
    FOTO,
    VALES,
    cantidad_entregada,
    cuerpo_devolucion,
    entregar,
    evaluar_devolucion,
    motivos,
    pieza_entregada,
    renglon,
)
from tests.movimientos.test_invariantes import revisar_folios, revisar_invariantes


@pytest.fixture
def trabajador(session):
    return crear_trabajador(session)


def existencia_virtual(session, virtual: str, articulo) -> int:
    ubicacion = session.scalar(select(Ubicacion.id).where(Ubicacion.virtual == virtual))
    return (
        session.scalar(
            select(Existencia.cantidad).where(
                Existencia.ubicacion_id == ubicacion, Existencia.articulo_id == articulo.id
            )
        )
        or 0
    )


def movimientos_de(session, vale_id: str) -> list[Movimiento]:
    return list(
        session.scalars(
            select(Movimiento)
            .where(Movimiento.vale_id == uuid.UUID(vale_id))
            .order_by(Movimiento.renglon)
        )
    )


def ubicacion_kep(session) -> uuid.UUID:
    return AlmacenService(session).ubicacion_de_almacen(almacen(session, "KEP").id).id


def cliente_de(app, crear_usuario, permisos, clave_almacen: str | None) -> TestClient:
    usuario = crear_usuario(permisos, almacen=clave_almacen)
    cliente = TestClient(app)
    assert iniciar_sesion_en(cliente, usuario).status_code == 200
    return cliente


# ------------------------------------------------------------------------- V-01, V-11


def test_V_01_una_pieza_escaneada_se_abona_a_su_titular_sin_pedir_credencial(
    almacenista, compras, session, trabajador
):
    art, pieza = pieza_entregada(compras, almacenista, session, trabajador)
    ev = evaluar_devolucion(almacenista, [renglon(pieza.codigo)])  # sin trabajador_id
    r = ev["renglones"][0]
    assert r["nivel"] == "VERDE" and motivos(ev) == ["V-01"] and ev["puede_confirmar"] is True
    assert r["titular"]["id"] == str(trabajador.id) and r["titular"]["tipo"] == "TRABAJADOR"
    assert ev["trabajador"]["id"] == str(trabajador.id)  # la ficha del titular

    antes = existencia(session, "KEP", art)
    r = almacenista.post(VALES, json=cuerpo_devolucion([renglon(pieza.codigo)]))
    assert r.status_code == 201, r.text
    assert r.json()["renglones"][0]["reglas"] == ["V-01"]
    session.refresh(pieza)
    assert pieza.ubicacion_id == ubicacion_kep(session)
    assert existencia(session, "KEP", art) == antes + 1
    assert existencia_de_trabajador(session, trabajador, art) == 0
    (mov,) = movimientos_de(session, r.json()["id"])
    assert mov.trabajador_id == trabajador.id and mov.condicion == "BUENO"
    assert mov.destino_id == ubicacion_kep(session) and mov.pieza_id == pieza.id


def test_V_01_la_pieza_de_otro_titular_se_abona_a_su_titular_aunque_se_indique_otro(
    almacenista, compras, session
):
    dueno, quien_la_trae = crear_trabajador(session), crear_trabajador(session)
    _, pieza = pieza_entregada(compras, almacenista, session, dueno)
    # La trae otra persona y se identifica a esa persona: la pieza se abona a su titular.
    r = almacenista.post(
        VALES, json=cuerpo_devolucion([renglon(pieza.codigo)], trabajador=quien_la_trae)
    )
    assert r.status_code == 201, r.text
    (mov,) = movimientos_de(session, r.json()["id"])
    assert mov.trabajador_id == dueno.id
    detalle = almacenista.get(f"{VALES}/{r.json()['id']}").json()
    assert detalle["trabajador"]["id"] == str(dueno.id)


def test_V_01_piezas_de_dos_titulares_en_una_devolucion_cada_renglon_al_suyo(
    almacenista, compras, session
):
    t1, t2 = crear_trabajador(session), crear_trabajador(session)
    _, p1 = pieza_entregada(compras, almacenista, session, t1)
    _, p2 = pieza_entregada(compras, almacenista, session, t2)
    r = almacenista.post(VALES, json=cuerpo_devolucion([renglon(p1.codigo), renglon(p2.codigo)]))
    assert r.status_code == 201, r.text
    movs = movimientos_de(session, r.json()["id"])
    assert [m.trabajador_id for m in movs] == [t1.id, t2.id]
    assert [m.origen_id for m in movs] == [
        AlmacenService(session).ubicacion_de_trabajador(t.id).id for t in (t1, t2)
    ]
    detalle = almacenista.get(f"{VALES}/{r.json()['id']}").json()
    assert detalle["trabajador"] is None  # el vale no es de uno solo; cada renglón anota el suyo
    revisar_invariantes(session)


def test_V_01_una_pieza_repetida_en_el_vale_se_ignora(almacenista, compras, session, trabajador):
    _, pieza = pieza_entregada(compras, almacenista, session, trabajador)
    ev = evaluar_devolucion(almacenista, [renglon(pieza.codigo), renglon(pieza.codigo)])
    assert len(ev["renglones"]) == 1 and ev["puede_confirmar"] is True


def test_V_11_el_vale_de_devolucion_lleva_folio_dev_y_es_el_comprobante(
    almacenista, compras, session, trabajador
):
    art, pieza = pieza_entregada(compras, almacenista, session, trabajador)
    r = almacenista.post(VALES, json=cuerpo_devolucion([renglon(pieza.codigo)]))
    assert r.status_code == 201
    vale = r.json()
    assert vale["folio"].startswith("KEP-DEV-") and vale["token"]
    por_token = almacenista.get(f"{VALES}/por-token/{vale['token']}").json()
    assert por_token["tipo"] == "DEVOLUCION" and por_token["folio"] == vale["folio"]
    assert por_token["trabajador"]["id"] == str(trabajador.id)
    renglon_vale = por_token["renglones"][0]
    assert renglon_vale["origen"]["tipo"] == "TRABAJADOR"
    assert (
        renglon_vale["destino"]["tipo"] == "ALMACEN" and renglon_vale["destino"]["clave"] == "KEP"
    )
    assert renglon_vale["codigo_pieza"] == pieza.codigo and renglon_vale["condicion"] == "BUENO"
    # El folio también se puede teclear (RG-10).
    assert almacenista.get(f"/api/escaneo/{vale['folio']}").json()["tipo"] == "VALE"
    revisar_folios(session)


def test_F_08_firma_el_almacenista_con_su_sesion_sin_firma_en_pantalla(
    almacenista, compras, session, trabajador
):
    _, pieza = pieza_entregada(compras, almacenista, session, trabajador)
    cuerpo = cuerpo_devolucion([renglon(pieza.codigo)])
    assert "firma" not in cuerpo
    r = almacenista.post(VALES, json=cuerpo)
    assert r.status_code == 201, r.text
    detalle = almacenista.get(f"{VALES}/{r.json()['id']}").json()
    yo = almacenista.get("/api/sesion").json()["usuario"]["id"]
    assert detalle["firma_modo"] == "SESION" and detalle["tiene_firma"] is False
    assert detalle["responsable"]["id"] == yo


def test_F_12_el_vale_y_la_evaluacion_de_una_devolucion_no_muestran_costos(
    almacenista, compras, supervisor, session, trabajador
):
    art, pieza = pieza_entregada(
        compras, almacenista, session, trabajador, costo_unitario=Decimal("987.65")
    )
    ev = evaluar_devolucion(almacenista, [renglon(pieza.codigo)])
    assert "costo" not in json.dumps(ev).lower() and "987.65" not in json.dumps(ev)
    r = almacenista.post(VALES, json=cuerpo_devolucion([renglon(pieza.codigo)]))
    assert "costo" not in r.text.lower() and "987.65" not in r.text
    for cliente in (almacenista, supervisor, compras):
        detalle = cliente.get(f"{VALES}/{r.json()['id']}")
        assert "costo" not in detalle.text.lower() and "987.65" not in detalle.text


# ----------------------------------------------------------------------------- V-02


def test_V_02_una_pieza_que_no_esta_con_nadie_es_amarillo_y_dice_donde_esta(
    almacenista, compras, session
):
    from tests.movimientos.ayudas import crear_articulo as nuevo_articulo
    from tests.movimientos.ayudas import entrar_pieza

    art = nuevo_articulo(session, control="PIEZA", requiere_inspeccion=False)
    r, codigo = entrar_pieza(compras, art)  # está en Kepler, no con un trabajador
    assert r.status_code == 201
    ev = evaluar_devolucion(almacenista, [renglon(codigo)])
    rg = ev["renglones"][0]
    assert rg["nivel"] == "AMARILLO" and motivos(ev) == ["V-02"]
    assert (
        "almacén KEP" in rg["motivos"][0]["mensaje"]
        and "nada que devolver" in rg["motivos"][0]["mensaje"]
    )
    assert rg["titular"]["tipo"] == "ALMACEN"
    # Sin nada que recibir el vale no se puede confirmar y no genera movimiento.
    assert ev["puede_confirmar"] is False
    vales, movs = total_vales(session), total_movimientos(session)
    r = almacenista.post(VALES, json=cuerpo_devolucion([renglon(codigo)]))
    assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO"
    assert (total_vales(session), total_movimientos(session)) == (vales, movs)


def test_V_02_en_un_vale_mixto_el_renglon_sin_resguardo_no_genera_movimiento(
    almacenista, compras, session, trabajador
):
    _, suya = pieza_entregada(compras, almacenista, session, trabajador)
    art = crear_articulo(session, control="PIEZA", requiere_inspeccion=False)
    from tests.movimientos.ayudas import entrar_pieza

    _, en_kep = entrar_pieza(compras, art)
    ev = evaluar_devolucion(almacenista, [renglon(suya.codigo), renglon(en_kep)])
    assert ev["nivel"] == "AMARILLO" and ev["puede_confirmar"] is True
    r = almacenista.post(VALES, json=cuerpo_devolucion([renglon(suya.codigo), renglon(en_kep)]))
    assert r.status_code == 201, r.text
    assert [x["codigo"] for x in r.json()["renglones"]] == [suya.codigo]
    assert len(movimientos_de(session, r.json()["id"])) == 1


# ----------------------------------------------------------------------------- V-03


def test_V_03_por_cantidad_se_devuelve_de_lo_que_tiene_y_baja_su_resguardo(
    almacenista, compras, session, trabajador
):
    art = cantidad_entregada(compras, almacenista, session, trabajador, cantidad=10, entregado=4)
    assert existencia(session, "KEP", art) == 6
    ev = evaluar_devolucion(almacenista, [renglon(art.codigo, 3)], trabajador)
    assert ev["renglones"][0]["nivel"] == "VERDE" and ev["renglones"][0]["disponible"] == 4
    r = almacenista.post(VALES, json=cuerpo_devolucion([renglon(art.codigo, 3)], trabajador))
    assert r.status_code == 201, r.text
    assert existencia(session, "KEP", art) == 9
    assert existencia_de_trabajador(session, trabajador, art) == 1
    (mov,) = movimientos_de(session, r.json()["id"])
    assert mov.cantidad == 3 and mov.trabajador_id == trabajador.id and mov.saldo_destino == 9
    revisar_invariantes(session)


def test_V_03_no_se_acepta_mas_de_lo_que_tiene_es_rojo_en_ese_renglon(
    almacenista, compras, session, trabajador
):
    art = cantidad_entregada(compras, almacenista, session, trabajador, entregado=2)
    ev = evaluar_devolucion(almacenista, [renglon(art.codigo, 3)], trabajador)
    assert ev["renglones"][0]["nivel"] == "ROJO" and motivos(ev) == ["V-03"]
    assert "tiene 2" in ev["renglones"][0]["motivos"][0]["mensaje"]
    assert ev["puede_confirmar"] is False
    antes = existencia(session, "KEP", art)
    r = almacenista.post(VALES, json=cuerpo_devolucion([renglon(art.codigo, 3)], trabajador))
    assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO"
    assert existencia(session, "KEP", art) == antes
    assert existencia_de_trabajador(session, trabajador, art) == 2


def test_V_03_dos_renglones_del_mismo_articulo_suman_contra_lo_que_tiene(
    almacenista, compras, session, trabajador
):
    art = cantidad_entregada(compras, almacenista, session, trabajador, entregado=3)
    # Buena y dañada del mismo artículo son dos renglones: juntos no pasan de lo que tiene.
    renglones = [
        renglon(art.codigo, 2, "BUENO"),
        renglon(art.codigo, 2, "DANADO", observacion="Roto"),
    ]
    ev = evaluar_devolucion(almacenista, renglones, trabajador)
    assert [r["nivel"] for r in ev["renglones"]] == ["VERDE", "ROJO"]
    assert motivos(ev, 1) == ["V-03", "V-05"]


def test_V_03_por_cantidad_sin_identificar_al_trabajador_es_rojo(
    almacenista, compras, session, trabajador
):
    art = cantidad_entregada(compras, almacenista, session, trabajador)
    ev = evaluar_devolucion(almacenista, [renglon(art.codigo)])
    assert motivos(ev) == ["V-03"] and ev["renglones"][0]["nivel"] == "ROJO"


def test_V_03_un_consumible_no_se_devuelve_el_trabajador_no_tiene_nada(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    entregar(almacenista, trabajador, [{"codigo": guantes.codigo, "cantidad": 2}])
    ev = evaluar_devolucion(almacenista, [renglon(guantes.codigo)], trabajador)
    assert motivos(ev) == ["V-03"] and "tiene 0" in ev["renglones"][0]["motivos"][0]["mensaje"]


# ----------------------------------------------------------------------------- V-04


def test_V_04_la_condicion_es_obligatoria(almacenista, compras, session, trabajador):
    _, pieza = pieza_entregada(compras, almacenista, session, trabajador)
    ev = evaluar_devolucion(almacenista, [renglon(pieza.codigo, condicion=None)])
    assert motivos(ev) == ["V-04", "V-01"] and ev["puede_confirmar"] is False
    r = almacenista.post(VALES, json=cuerpo_devolucion([renglon(pieza.codigo, condicion=None)]))
    assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO"
    session.refresh(pieza)
    assert pieza.ubicacion_id == AlmacenService(session).ubicacion_de_trabajador(trabajador.id).id


def test_V_04_una_condicion_que_no_existe_se_rechaza(almacenista, compras, session, trabajador):
    _, pieza = pieza_entregada(compras, almacenista, session, trabajador)
    r = almacenista.post(VALES, json=cuerpo_devolucion([renglon(pieza.codigo, condicion="ROTO")]))
    assert r.status_code == 422


# ----------------------------------------------------------------------------- V-05


def test_V_05_danado_sin_observacion_se_rechaza(almacenista, compras, session, trabajador):
    _, pieza = pieza_entregada(compras, almacenista, session, trabajador)
    ev = evaluar_devolucion(almacenista, [renglon(pieza.codigo, condicion="DANADO")])
    assert motivos(ev) == ["V-05", "V-01"] and ev["renglones"][0]["nivel"] == "ROJO"
    assert ev["renglones"][0]["pide_observacion"] is True and ev["puede_confirmar"] is False
    r = almacenista.post(VALES, json=cuerpo_devolucion([renglon(pieza.codigo, condicion="DANADO")]))
    assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO"
    r = almacenista.post(
        VALES,
        json=cuerpo_devolucion([renglon(pieza.codigo, condicion="DANADO", observacion="   ")]),
    )
    assert r.status_code == 409


def test_V_05_una_pieza_danada_entra_al_almacen_como_no_apta_con_su_evento(
    almacenista, compras, session, trabajador
):
    art, pieza = pieza_entregada(compras, almacenista, session, trabajador)
    renglones = [renglon(pieza.codigo, condicion="DANADO", observacion="Se rompió la correa")]
    ev = evaluar_devolucion(almacenista, renglones)
    assert ev["renglones"][0]["nivel"] == "AMARILLO" and ev["puede_confirmar"] is True
    r = almacenista.post(VALES, json=cuerpo_devolucion(renglones))
    assert r.status_code == 201, r.text
    session.refresh(pieza)
    assert pieza.estado == EstadoPieza.NO_APTO
    assert pieza.ubicacion_id == ubicacion_kep(session)  # entra al almacén
    assert existencia(session, "KEP", art) == 1
    assert existencia_de_trabajador(session, trabajador, art) == 0
    eventos = session.scalars(select(EventoPieza).where(EventoPieza.pieza_id == pieza.id)).all()
    assert len(eventos) == 1
    assert eventos[0].estado_anterior == "APTO" and eventos[0].estado_nuevo == "NO_APTO"
    assert "Se rompió la correa" in eventos[0].observacion
    assert eventos[0].usuario_id is not None
    (mov,) = movimientos_de(session, r.json()["id"])
    assert mov.condicion == "DANADO" and mov.observacion == "Se rompió la correa"
    assert mov.reglas == ["V-05", "V-01"] and mov.nivel == "AMARILLO"
    # No apta: no se vuelve a entregar (E-05) y no cuenta como disponible.
    ev = almacenista.post(
        EVALUAR,
        json={
            "tipo": "ENTREGA",
            "trabajador_id": str(trabajador.id),
            "renglones": [{"codigo": pieza.codigo}],
        },
    ).json()
    assert [m["regla"] for m in ev["renglones"][0]["motivos"]] == ["E-05"]
    revisar_invariantes(session)


def test_V_05_en_ningun_caso_hay_cargo_al_trabajador(almacenista, compras, session, trabajador):
    art, pieza = pieza_entregada(compras, almacenista, session, trabajador)
    ev = evaluar_devolucion(
        almacenista, [renglon(pieza.codigo, condicion="DANADO", observacion="Roto")]
    )
    mensaje = ev["renglones"][0]["motivos"][0]["mensaje"]
    assert "No se cobra" in mensaje
    texto = json.dumps(ev).lower()
    assert "cargo" not in texto.replace("no se cobra", "") and "descuento" not in texto


def test_V_05_por_cantidad_danado_va_a_baja_y_no_suma_existencias(
    almacenista, compras, session, trabajador
):
    art = cantidad_entregada(compras, almacenista, session, trabajador, cantidad=10, entregado=4)
    assert existencia(session, "KEP", art) == 6
    renglones = [renglon(art.codigo, 2, "DANADO", observacion="Partido")]
    r = almacenista.post(VALES, json=cuerpo_devolucion(renglones, trabajador))
    assert r.status_code == 201, r.text
    assert existencia(session, "KEP", art) == 6  # NO regresa a existencias
    assert existencia_virtual(session, "BAJA", art) == 2
    assert existencia_de_trabajador(session, trabajador, art) == 2
    (mov,) = movimientos_de(session, r.json()["id"])
    baja = session.scalar(select(Ubicacion.id).where(Ubicacion.virtual == "BAJA"))
    assert mov.destino_id == baja and mov.motivo_baja and mov.condicion == "DANADO"
    revisar_invariantes(session)


def test_V_05_una_parte_buena_y_una_danada_del_mismo_articulo(
    almacenista, compras, session, trabajador
):
    art = cantidad_entregada(compras, almacenista, session, trabajador, cantidad=10, entregado=5)
    renglones = [
        renglon(art.codigo, 2, "BUENO"),
        renglon(art.codigo, 1, "DANADO", observacion="Quebrado"),
        renglon(art.codigo, 1, "DESGASTE"),
        renglon(art.codigo, 1, "BUENO"),  # suma con el primero
    ]
    r = almacenista.post(VALES, json=cuerpo_devolucion(renglones, trabajador))
    assert r.status_code == 201, r.text
    assert existencia(session, "KEP", art) == 5 + 3 + 1  # buenas y de desgaste vuelven
    assert existencia_virtual(session, "BAJA", art) == 1
    assert existencia_de_trabajador(session, trabajador, art) == 0
    assert len(movimientos_de(session, r.json()["id"])) == 3
    revisar_invariantes(session)


def test_V_05_la_foto_del_dano_se_guarda_ligada_al_movimiento(
    almacenista, compras, session, trabajador
):
    _, pieza = pieza_entregada(compras, almacenista, session, trabajador)
    renglones = [renglon(pieza.codigo, condicion="DANADO", observacion="Golpe", foto=FOTO)]
    r = almacenista.post(VALES, json=cuerpo_devolucion(renglones))
    assert r.status_code == 201, r.text
    (mov,) = movimientos_de(session, r.json()["id"])
    (adjunto,) = session.scalars(select(Adjunto).where(Adjunto.movimiento_id == mov.id)).all()
    assert adjunto.tipo == "FOTO_DANO" and adjunto.vale_id == uuid.UUID(r.json()["id"])


def test_V_05_la_foto_es_solo_de_lo_danado_y_debe_ser_una_imagen(
    almacenista, compras, session, trabajador
):
    _, pieza = pieza_entregada(compras, almacenista, session, trabajador)
    r = almacenista.post(VALES, json=cuerpo_devolucion([renglon(pieza.codigo, foto=FOTO)]))
    assert r.status_code == 422 and "renglones.0.foto" in json.dumps(r.json()["detalles"])
    mala = "data:image/png;base64,AAAA"
    renglones = [renglon(pieza.codigo, condicion="DANADO", observacion="x", foto=mala)]
    r = almacenista.post(VALES, json=cuerpo_devolucion(renglones))
    assert r.status_code == 422
    # Nada quedó: la pieza sigue con el trabajador.
    session.refresh(pieza)
    assert pieza.estado == EstadoPieza.APTO
    assert not session.scalars(select(EventoPieza).where(EventoPieza.pieza_id == pieza.id)).all()


# ----------------------------------------------------------------------------- V-06


def test_V_06_desgaste_por_uso_no_pide_observacion_ni_deja_la_pieza_no_apta(
    almacenista, compras, session, trabajador
):
    _, pieza = pieza_entregada(compras, almacenista, session, trabajador)
    ev = evaluar_devolucion(almacenista, [renglon(pieza.codigo, condicion="DESGASTE")])
    rg = ev["renglones"][0]
    assert rg["nivel"] == "VERDE" and rg["pide_observacion"] is False
    assert motivos(ev) == ["V-06", "V-01"]
    r = almacenista.post(
        VALES, json=cuerpo_devolucion([renglon(pieza.codigo, condicion="DESGASTE")])
    )
    assert r.status_code == 201, r.text
    session.refresh(pieza)
    assert pieza.estado == EstadoPieza.APTO and pieza.ubicacion_id == ubicacion_kep(session)
    (mov,) = movimientos_de(session, r.json()["id"])
    assert mov.condicion == "DESGASTE" and mov.observacion is None


# ----------------------------------------------------------------------------- V-07


def test_V_07_en_otro_almacen_se_recibe_con_aviso_y_entra_al_que_recibe(
    app, almacenista, compras, crear_usuario, session, trabajador
):
    art, pieza = pieza_entregada(compras, almacenista, session, trabajador)
    cantidad = cantidad_entregada(compras, almacenista, session, trabajador, entregado=2)
    de_con = cliente_de(app, crear_usuario, {P.DEVOLUCIONES_CREAR}, "CON")
    renglones = [renglon(pieza.codigo), renglon(cantidad.codigo, 2)]
    ev = evaluar_devolucion(de_con, renglones, trabajador)
    assert ev["almacen"]["clave"] == "CON" and ev["nivel"] == "AMARILLO"
    assert "V-07" in motivos(ev, 0) and "V-07" in motivos(ev, 1)
    assert ev["puede_confirmar"] is True

    kep_antes = (existencia(session, "KEP", art), existencia(session, "KEP", cantidad))
    r = de_con.post(VALES, json=cuerpo_devolucion(renglones, trabajador))
    assert r.status_code == 201, r.text
    assert r.json()["folio"].startswith("CON-DEV-")
    assert existencia(session, "CON", art) == 1 and existencia(session, "CON", cantidad) == 2
    assert (existencia(session, "KEP", art), existencia(session, "KEP", cantidad)) == kep_antes
    session.refresh(pieza)
    con = AlmacenService(session).ubicacion_de_almacen(almacen(session, "CON").id)
    assert pieza.ubicacion_id == con.id
    revisar_invariantes(session)


def test_V_07_en_el_mismo_almacen_no_hay_aviso(almacenista, compras, session, trabajador):
    _, pieza = pieza_entregada(compras, almacenista, session, trabajador)
    assert "V-07" not in motivos(evaluar_devolucion(almacenista, [renglon(pieza.codigo)]))


# ----------------------------------------------------------------------------- V-12, V-14


def test_V_12_un_codigo_que_no_existe_se_rechaza_y_el_pendiente_sigue_abierto(
    almacenista, compras, session, trabajador
):
    art, pieza = pieza_entregada(compras, almacenista, session, trabajador)
    ev = evaluar_devolucion(almacenista, [renglon("EQUIPO-DE-OTRA-EMPRESA")], trabajador)
    rg = ev["renglones"][0]
    assert rg["nivel"] == "ROJO" and motivos(ev) == ["V-12"] and rg["articulo"] is None
    assert "No es de la empresa" in rg["motivos"][0]["mensaje"]
    assert rg["autorizable"] is False and ev["puede_confirmar"] is False
    vales, movs = total_vales(session), total_movimientos(session)
    r = almacenista.post(
        VALES, json=cuerpo_devolucion([renglon("EQUIPO-DE-OTRA-EMPRESA")], trabajador)
    )
    assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO"
    assert (total_vales(session), total_movimientos(session)) == (vales, movs)
    ficha = almacenista.get(f"/api/trabajadores/{trabajador.id}").json()
    assert [p["codigo"] for p in ficha["resguardo"]] == [pieza.codigo]  # el pendiente sigue


def test_V_12_la_credencial_de_un_trabajador_no_es_un_equipo(almacenista, session, trabajador):
    ev = evaluar_devolucion(almacenista, [renglon(f"CRED-{trabajador.numero_empleado}")])
    assert motivos(ev) == ["V-12"] and ev["renglones"][0]["nivel"] == "ROJO"


def test_V_14_el_codigo_de_un_articulo_por_pieza_no_sirve_hay_que_elegir_la_pieza(
    almacenista, compras, session, trabajador
):
    art, pieza = pieza_entregada(compras, almacenista, session, trabajador)
    ev = evaluar_devolucion(almacenista, [renglon(art.codigo)], trabajador)
    assert motivos(ev) == ["V-14"] and ev["renglones"][0]["nivel"] == "ROJO"
    assert "número de serie" in ev["renglones"][0]["motivos"][0]["mensaje"]


def test_V_14_una_pieza_con_etiqueta_ilegible_se_busca_por_serie_y_se_devuelve(
    almacenista, compras, session, trabajador
):
    art, pieza = pieza_entregada(compras, almacenista, session, trabajador)
    busqueda = almacenista.get(f"/api/busqueda?q={pieza.numero_serie}").json()
    (encontrada,) = busqueda["piezas"]["elementos"]
    assert trabajador.nombre in encontrada["ubicacion"]  # quién la tiene
    # La interfaz manda el código que la búsqueda le devolvió, aunque la etiqueta no se lea.
    r = almacenista.post(VALES, json=cuerpo_devolucion([renglon(encontrada["codigo"])]))
    assert r.status_code == 201, r.text
    session.refresh(pieza)
    assert pieza.ubicacion_id == ubicacion_kep(session)


# ----------------------------------------------------------------------------- SM-05


def _vencer_contrato(session, trabajador) -> None:
    session.execute(
        update(PeriodoContrato)
        .where(PeriodoContrato.trabajador_id == trabajador.id)
        .values(fin=hoy_mx() - timedelta(days=2))
    )
    session.flush()


@pytest.mark.parametrize(
    "preparar",
    [
        lambda s, t: _vencer_contrato(s, t),
        lambda s, t: setattr(t, "estado", EstadoTrabajador.BAJA_EN_PROCESO),
        lambda s, t: setattr(t, "estado", EstadoTrabajador.INACTIVO),
    ],
    ids=["contrato_vencido", "baja_en_proceso", "inactivo"],
)
def test_SM_05_un_trabajador_no_vigente_tambien_puede_devolver(
    almacenista, compras, session, preparar
):
    t = crear_trabajador(session)
    art, pieza = pieza_entregada(compras, almacenista, session, t)
    cantidad = cantidad_entregada(compras, almacenista, session, t, entregado=2)
    preparar(session, t)
    session.flush()
    renglones = [renglon(pieza.codigo), renglon(cantidad.codigo, 2)]
    ev = evaluar_devolucion(almacenista, renglones, t)
    assert ev["trabajador"]["vigencia"]["vigente"] is False or t.estado != "ACTIVO"
    assert ev["nivel"] != "ROJO" and ev["puede_confirmar"] is True
    assert "E-02" not in motivos(ev, 0) + motivos(ev, 1) and ev["motivos"] == []
    r = almacenista.post(VALES, json=cuerpo_devolucion(renglones, t))
    assert r.status_code == 201, r.text
    assert existencia_de_trabajador(session, t, cantidad) == 0
    session.refresh(pieza)
    assert pieza.ubicacion_id == ubicacion_kep(session)


def test_SM_05_CF_11_un_articulo_inactivo_se_recibe_normal(
    almacenista, compras, session, trabajador
):
    art, pieza = pieza_entregada(compras, almacenista, session, trabajador)
    cantidad = cantidad_entregada(compras, almacenista, session, trabajador, entregado=2)
    for articulo in (art, cantidad):
        articulo.activo = False
        articulo.motivo_inactivacion = "Ya no se usa"
    session.flush()
    renglones = [renglon(pieza.codigo), renglon(cantidad.codigo, 2)]
    ev = evaluar_devolucion(almacenista, renglones, trabajador)
    assert ev["nivel"] == "VERDE" and ev["puede_confirmar"] is True
    r = almacenista.post(VALES, json=cuerpo_devolucion(renglones, trabajador))
    assert r.status_code == 201, r.text
    assert existencia(session, "KEP", cantidad) == 5 and existencia(session, "KEP", art) == 1


def test_SM_05_ni_el_limite_ni_la_autorizacion_ni_la_inspeccion_vencida_bloquean(
    almacenista, compras, session, trabajador
):
    """Un artículo con límite, autorización especial e inspección vencida se devuelve sin trabas."""
    art, pieza = pieza_entregada(
        compras,
        almacenista,
        session,
        trabajador,
        limite_cantidad=1,
    )
    art.requiere_autorizacion = True
    art.requiere_inspeccion = True
    pieza.inspeccion_vigente_hasta = hoy_mx() - timedelta(days=30)
    session.flush()
    ev = evaluar_devolucion(almacenista, [renglon(pieza.codigo)])
    assert ev["nivel"] == "VERDE" and ev["renglones"][0]["autorizable"] is False
    r = almacenista.post(VALES, json=cuerpo_devolucion([renglon(pieza.codigo)]))
    assert r.status_code == 201, r.text


# ------------------------------------------------------------------ ciclo y transacción


def test_ciclo_completo_entrega_devolucion_deja_el_resguardo_en_cero(
    almacenista, compras, session, trabajador
):
    art, pieza = pieza_entregada(compras, almacenista, session, trabajador)
    cantidad = cantidad_entregada(
        compras, almacenista, session, trabajador, cantidad=8, entregado=3
    )
    antes = almacenista.get(f"/api/trabajadores/{trabajador.id}").json()
    assert antes["pendientes"]["total"] == 2 and antes["situacion"] == "CON_PENDIENTES"

    r = almacenista.post(
        VALES,
        json=cuerpo_devolucion([renglon(pieza.codigo), renglon(cantidad.codigo, 3)], trabajador),
    )
    assert r.status_code == 201, r.text
    despues = almacenista.get(f"/api/trabajadores/{trabajador.id}").json()
    assert despues["resguardo"] == [] and despues["situacion"] == "SIN_PENDIENTES"
    assert existencia(session, "KEP", cantidad) == 8 and existencia(session, "KEP", art) == 1
    assert existencia_de_trabajador(session, trabajador, cantidad) == 0
    # El almacén ve las existencias al día y el trabajador ya no tiene nada.
    r = almacenista.get(
        f"/api/almacenes/{almacen(session, 'KEP').id}/existencias?q={cantidad.codigo}"
    )
    assert r.json()["elementos"][0]["cantidad"] == 8
    revisar_invariantes(session)
    revisar_folios(session)


def test_idempotencia_el_mismo_id_cliente_no_duplica_la_devolucion(
    almacenista, compras, session, trabajador
):
    art = cantidad_entregada(compras, almacenista, session, trabajador, entregado=3)
    cuerpo = cuerpo_devolucion([renglon(art.codigo, 2)], trabajador)
    r1 = almacenista.post(VALES, json=cuerpo)
    r2 = almacenista.post(VALES, json=cuerpo)
    assert (r1.status_code, r2.status_code) == (201, 200)
    assert r1.json() == r2.json()
    assert existencia_de_trabajador(session, trabajador, art) == 1  # solo una vez
    assert (
        len(
            session.scalars(
                select(Vale.id).where(Vale.id_cliente == uuid.UUID(cuerpo["id_cliente"]))
            ).all()
        )
        == 1
    )


def test_atomicidad_un_rojo_en_el_ultimo_renglon_no_deja_nada(
    almacenista, compras, session, trabajador
):
    art, pieza = pieza_entregada(compras, almacenista, session, trabajador)
    cantidad = cantidad_entregada(compras, almacenista, session, trabajador, entregado=2)
    vales, movs = total_vales(session), total_movimientos(session)
    renglones = [renglon(pieza.codigo), renglon(cantidad.codigo, 1), renglon("NO-ES-DE-LA-EMPRESA")]
    r = almacenista.post(VALES, json=cuerpo_devolucion(renglones, trabajador))
    assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO"
    detalles = r.json()["detalles"]
    assert [x["nivel"] for x in detalles["renglones"]] == ["VERDE", "VERDE", "ROJO"]
    assert (total_vales(session), total_movimientos(session)) == (vales, movs)
    session.refresh(pieza)
    assert pieza.ubicacion_id == AlmacenService(session).ubicacion_de_trabajador(trabajador.id).id
    assert existencia_de_trabajador(session, trabajador, cantidad) == 2
    # El folio no se quemó: la siguiente devolución usa el consecutivo que sigue.
    revisar_folios(session)


def test_la_devolucion_exige_al_menos_un_renglon(almacenista):
    r = almacenista.post(VALES, json=cuerpo_devolucion([]))
    assert r.status_code == 422


def test_los_datos_de_pieza_son_solo_de_las_entradas(almacenista, compras, session, trabajador):
    _, pieza = pieza_entregada(compras, almacenista, session, trabajador)
    cuerpo = cuerpo_devolucion([renglon(pieza.codigo) | {"pieza": {"codigo": "X"}}])
    assert almacenista.post(VALES, json=cuerpo).status_code == 422


def test_AC_13_si_el_almacenista_cambio_de_almacen_no_se_guarda(
    almacenista, compras, session, trabajador
):
    _, pieza = pieza_entregada(compras, almacenista, session, trabajador)
    cuerpo = cuerpo_devolucion([renglon(pieza.codigo)], almacen_id=str(almacen(session, "CON").id))
    r = almacenista.post(VALES, json=cuerpo)
    assert r.status_code == 409 and r.json()["codigo"] == "ALMACEN_CAMBIO"


# ------------------------------------------------------------------------- permisos


def test_permisos_devolver_exige_devoluciones_crear(
    app, almacenista, compras, session, crear_usuario, trabajador, cliente_como
):
    _, pieza = pieza_entregada(compras, almacenista, session, trabajador)
    cuerpo = cuerpo_devolucion([renglon(pieza.codigo)])
    sin = cliente_de(app, crear_usuario, {P.VALES_VER, P.ENTREGAS_CREAR}, "KEP")
    for ruta, c in (
        (EVALUAR, {k: v for k, v in cuerpo.items() if k != "id_cliente"}),
        (VALES, cuerpo),
    ):
        r = sin.post(ruta, json=c)
        assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"
    for rol in ("Compras", "Recursos Humanos"):
        assert cliente_como(rol).post(VALES, json=cuerpo).status_code == 403
    # Nada se movió.
    session.refresh(pieza)
    assert pieza.ubicacion_id == AlmacenService(session).ubicacion_de_trabajador(trabajador.id).id
    con = cliente_de(app, crear_usuario, {P.DEVOLUCIONES_CREAR}, "KEP")
    assert con.post(VALES, json=cuerpo).status_code == 201


def test_permisos_sin_sesion_es_401(client):
    assert client.post(VALES, json=cuerpo_devolucion([renglon("X")])).status_code == 401
