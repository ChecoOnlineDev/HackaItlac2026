"""Trazabilidad de la entrega: pruebas que anclan reglas y criterios con su ID en el nombre.

Cubre L-04 (detalle exacto del naranja), A-07 (autorización que no llega), F-04 (el supervisor
firma solo cuando autoriza), F-07 (el vale por su QR), F-11 (foto en la ficha breve), E-18
(búsqueda por serie y número de empleado tecleado), E-19 (artículo inactivado a medio capturar),
P-02 / CF-06 (solo se exige inspección donde el catálogo la pide) y RG-11 (hora del servidor).
"""

import re
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.tiempo import ahora_utc, hoy_mx
from app.modulos.acceso.permisos import P
from app.modulos.almacenes.service import AlmacenService
from app.modulos.autorizaciones.models import Autorizacion
from app.modulos.movimientos.models import Movimiento, Vale
from tests.conftest import iniciar_sesion_en
from tests.movimientos.ayudas import (
    abastecer,
    crear_articulo,
    crear_trabajador,
    cuerpo_entrega,
    existencia,
    existencia_de_trabajador,
    total_movimientos,
    total_vales,
)
from tests.movimientos.test_autorizacion_integracion import AUT, aprobar, solicitar
from tests.movimientos.test_entrega import evaluar, motivos, pieza_en_kep, renglon

VALES = "/api/vales"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


@pytest.fixture
def trabajador(session):
    return crear_trabajador(session)


def entregar(cliente, trabajador, articulo, cantidad=1):
    codigo = articulo if isinstance(articulo, str) else articulo.codigo
    r = cliente.post(VALES, json=cuerpo_entrega(trabajador, [renglon(codigo, cantidad)]))
    assert r.status_code == 201, r.text
    return r.json()


def detalle_del_limite(mensaje: str) -> str:
    """Lo que va entre paréntesis en el motivo: «límite N, tiene T, pide P»."""
    encontrado = re.search(r"\((límite[^)]*)\)", mensaje)
    assert encontrado, mensaje
    return encontrado.group(1)


# ------------------------------------------------------------------------------------ L-04


def test_L_04_retornable_el_naranja_dice_limite_tiene_y_pide(
    almacenista, compras, session, trabajador
):
    arnes = crear_articulo(session, retornable=True, limite_cantidad=2)
    abastecer(compras, arnes, 10)
    entregar(almacenista, trabajador, arnes, 2)

    ev = evaluar(almacenista, trabajador, [renglon(arnes.codigo, 1)])

    r = ev["renglones"][0]
    assert r["nivel"] == "NARANJA" and motivos(ev) == ["L-02"]
    assert r["motivos"][0]["nivel"] == "NARANJA"
    assert detalle_del_limite(r["motivos"][0]["mensaje"]) == "límite 2, tiene 2, pide 1"


def test_L_04_retornable_con_lo_que_pide_el_detalle_cambia_en_cada_cuenta(
    almacenista, compras, session, trabajador
):
    arnes = crear_articulo(session, retornable=True, limite_cantidad=3)
    abastecer(compras, arnes, 10)
    entregar(almacenista, trabajador, arnes, 1)
    for pide, esperado in ((3, "límite 3, tiene 1, pide 3"), (5, "límite 3, tiene 1, pide 5")):
        ev = evaluar(almacenista, trabajador, [renglon(arnes.codigo, pide)])
        assert ev["renglones"][0]["nivel"] == "NARANJA"
        assert detalle_del_limite(ev["renglones"][0]["motivos"][0]["mensaje"]) == esperado
    # Lo que justo llega al límite no es naranja y, por tanto, no trae detalle.
    ev = evaluar(almacenista, trabajador, [renglon(arnes.codigo, 2)])
    assert ev["renglones"][0]["nivel"] == "VERDE" and ev["renglones"][0]["motivos"] == []


def test_L_04_consumible_por_periodo_el_detalle_incluye_los_dias(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False, limite_cantidad=3, limite_periodo_dias=7)
    abastecer(compras, guantes, 20)
    entregar(almacenista, trabajador, guantes, 3)

    ev = evaluar(almacenista, trabajador, [renglon(guantes.codigo, 1)])

    r = ev["renglones"][0]
    assert r["nivel"] == "NARANJA" and motivos(ev) == ["L-03"]
    assert (
        detalle_del_limite(r["motivos"][0]["mensaje"])
        == "límite 3, tiene 3 en los últimos 7 días, pide 1"
    )


def test_L_04_el_mismo_detalle_llega_cuando_el_servidor_rechaza_la_confirmacion(
    almacenista, compras, session, trabajador
):
    arnes = crear_articulo(session, retornable=True, limite_cantidad=1)
    abastecer(compras, arnes, 5)
    entregar(almacenista, trabajador, arnes, 1)
    r = almacenista.post(VALES, json=cuerpo_entrega(trabajador, [renglon(arnes.codigo)]))
    assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO"
    motivo = r.json()["detalles"]["renglones"][0]["motivos"][0]
    assert motivo["regla"] == "L-02"
    assert detalle_del_limite(motivo["mensaje"]) == "límite 1, tiene 1, pide 1"


# ------------------------------------------------------------------------------------ A-07


@pytest.fixture
def excedente(almacenista, compras, session, trabajador):
    """Un retornable con límite 1 que el trabajador ya tiene: pedir otro es naranja."""
    arnes = crear_articulo(session, retornable=True, limite_cantidad=1)
    abastecer(compras, arnes, 10)
    entregar(almacenista, trabajador, arnes, 1)
    return arnes


@pytest.mark.parametrize("como_no_llega", ["rechazada", "vencida"])
def test_A_07_si_la_autorizacion_no_llega_se_quita_el_renglon_y_se_entrega_lo_demas(
    almacenista, supervisor, compras, session, trabajador, excedente, como_no_llega
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 10)
    ambos = [renglon(excedente.codigo), renglon(guantes.codigo, 2)]
    ev = evaluar(almacenista, trabajador, ambos)
    assert [r["nivel"] for r in ev["renglones"]] == ["NARANJA", "VERDE"]
    autorizacion_id = solicitar(almacenista, trabajador, ev)
    if como_no_llega == "rechazada":
        r = supervisor.post(f"{AUT}/{autorizacion_id}/resolucion", json={"decision": "RECHAZAR"})
        assert r.status_code == 200 and r.json()["estado"] == "RECHAZADA"
    else:
        fila = session.get(Autorizacion, uuid.UUID(autorizacion_id))
        fila.vence_en = ahora_utc() - timedelta(minutes=1)  # nadie respondió en 15 minutos
        session.flush()
        assert almacenista.get(f"{AUT}/{autorizacion_id}").json()["estado"] == "VENCIDA"

    # Con la autorización que no llegó, el vale completo no se confirma y no se escribe nada.
    vales, movs = total_vales(session), total_movimientos(session)
    r = almacenista.post(
        VALES, json=cuerpo_entrega(trabajador, ambos, autorizacion_id=autorizacion_id)
    )
    assert r.status_code == 409
    assert (total_vales(session), total_movimientos(session)) == (vales, movs)

    # El almacenista quita el renglón excedente y confirma el resto.
    resto = almacenista.post(VALES, json=cuerpo_entrega(trabajador, [renglon(guantes.codigo, 2)]))
    assert resto.status_code == 201, resto.text
    assert [r["codigo"] for r in resto.json()["renglones"]] == [guantes.codigo]
    assert existencia(session, "KEP", guantes) == 8
    assert existencia(session, "KEP", excedente) == 9  # el excedente no salió
    assert existencia_de_trabajador(session, trabajador, excedente) == 1
    # El vale sale sin autorización y la que no llegó nunca se usó.
    emitido = session.get(Vale, uuid.UUID(resto.json()["id"]))
    assert emitido.autorizacion_id is None
    assert almacenista.get(f"{AUT}/{autorizacion_id}").json()["estado"] == (
        "RECHAZADA" if como_no_llega == "rechazada" else "VENCIDA"
    )


# ------------------------------------------------------------------------------------ F-04


def test_F_04_el_supervisor_firma_solo_cuando_autoriza_y_no_valida_cada_vale(
    almacenista, supervisor, compras, session, trabajador, excedente
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 10)

    normal = entregar(almacenista, trabajador, guantes, 1)
    detalle = almacenista.get(f"{VALES}/{normal['id']}").json()
    assert detalle["valido"] is None  # ninguna entrega normal lleva «Validó»
    assert session.get(Vale, uuid.UUID(normal["id"])).autorizacion_id is None

    ev = evaluar(almacenista, trabajador, [renglon(excedente.codigo)])
    autorizacion_id = solicitar(almacenista, trabajador, ev, motivo="Cubre a un compañero")
    aprobar(supervisor, autorizacion_id)
    r = almacenista.post(
        VALES,
        json=cuerpo_entrega(
            trabajador, [renglon(excedente.codigo)], autorizacion_id=autorizacion_id
        ),
    )
    assert r.status_code == 201, r.text
    autorizada = almacenista.get(f"{VALES}/{r.json()['id']}").json()
    assert autorizada["valido"]["autorizo"]["nombre"] == "Supervisor de prueba"
    assert autorizada["valido"]["solicito"]["nombre"] == "Almacenista Kepler"
    assert autorizada["valido"]["motivo"] == "Cubre a un compañero"
    # Quien firma el vale (F-03) sigue siendo el almacenista: el supervisor no lo captura.
    assert autorizada["responsable"]["nombre"] == "Almacenista Kepler"

    # Después de autorizar, la siguiente entrega normal vuelve a salir sin «Validó».
    otra = entregar(almacenista, trabajador, guantes, 1)
    assert almacenista.get(f"{VALES}/{otra['id']}").json()["valido"] is None


# ------------------------------------------------------------------------------------ F-07


def test_F_07_el_qr_del_vale_abre_su_detalle_completo_con_sesion(
    client, almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False, marca="3M")
    abastecer(compras, guantes, 10)
    vale = entregar(almacenista, trabajador, guantes, 2)

    r = almacenista.get(f"{VALES}/por-token/{vale['token']}")

    assert r.status_code == 200, r.text
    d = r.json()
    assert d == almacenista.get(f"{VALES}/{vale['id']}").json()  # el mismo vale, completo
    assert d["id"] == vale["id"] and d["folio"] == vale["folio"] and d["token"] == vale["token"]
    assert d["tipo"] == "ENTREGA" and d["estado"] == "EMITIDO"
    assert d["almacen"]["clave"] == "KEP"
    assert d["trabajador"]["numero_empleado"] == trabajador.numero_empleado
    assert d["responsable"]["nombre"] == "Almacenista Kepler"
    assert d["tiene_firma"] is True and d["firma_modo"] == "PANTALLA"
    assert d["creado_en"].endswith("Z")
    (renglon_vale,) = d["renglones"]
    assert renglon_vale["codigo_articulo"] == guantes.codigo and renglon_vale["cantidad"] == 2
    assert renglon_vale["marca"] == "3M"
    assert renglon_vale["origen"]["clave"] == "KEP"
    assert renglon_vale["destino"]["tipo"] == "CONSUMIDO"  # consumible (E-21)

    # Sin sesión, ni el QR abre el vale.
    assert client.get(f"{VALES}/por-token/{vale['token']}").status_code == 401


def test_F_07_un_token_inventado_da_404(almacenista):
    r = almacenista.get(f"{VALES}/por-token/{uuid.uuid4().hex}")
    assert r.status_code == 404 and r.json()["codigo"] == "NO_ENCONTRADO"


def test_F_07_fuera_del_almacen_del_usuario_el_qr_no_abre_el_vale(
    app, almacenista, cliente_como, compras, session, trabajador, crear_usuario
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    vale = entregar(almacenista, trabajador, guantes)
    de_con = TestClient(app)
    assert iniciar_sesion_en(de_con, crear_usuario({P.VALES_VER}, almacen="CON")).status_code == 200
    r = de_con.get(f"{VALES}/por-token/{vale['token']}")
    assert r.status_code == 404 and r.json()["codigo"] == "NO_ENCONTRADO"
    # Quien opera todos los almacenes sí lo abre.
    assert cliente_como("Supervisor").get(f"{VALES}/por-token/{vale['token']}").status_code == 200


# ------------------------------------------------------------------------------------ F-11


def test_F_11_la_ficha_breve_trae_la_foto_si_la_tiene_y_dice_que_no_si_no(
    almacenista, cliente_como, compras, session, trabajador
):
    con_foto = crear_trabajador(session)
    rh = cliente_como("Recursos Humanos")
    subida = rh.post(
        f"/api/trabajadores/{con_foto.id}/foto", files={"archivo": ("foto.png", PNG, "image/png")}
    )
    assert subida.status_code == 200, subida.text
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)

    ev_con = evaluar(almacenista, con_foto, [renglon(guantes.codigo)])["trabajador"]
    ev_sin = evaluar(almacenista, trabajador, [renglon(guantes.codigo)])["trabajador"]

    assert ev_con["tiene_foto"] is True
    assert ev_con["foto_url"] == f"/api/trabajadores/{con_foto.id}/foto"
    assert almacenista.get(ev_con["foto_url"]).status_code == 200  # la foto se puede pintar
    assert ev_sin["tiene_foto"] is False and ev_sin["foto_url"] is None
    # Sin foto la entrega continúa: el aviso lo pinta la interfaz.
    assert evaluar(almacenista, trabajador, [renglon(guantes.codigo)])["puede_confirmar"] is True
    # La misma ficha por su endpoint propio.
    ficha_sin = almacenista.get(f"/api/trabajadores/{trabajador.id}").json()
    assert ficha_sin["tiene_foto"] is False and ficha_sin["foto_url"] is None
    ficha_con = almacenista.get(f"/api/trabajadores/{con_foto.id}").json()
    assert ficha_con["tiene_foto"] is True and ficha_con["foto_url"] == ev_con["foto_url"]


# ------------------------------------------------------------------------------------ E-18


def test_E_18_US_ENT_001_una_pieza_con_etiqueta_ilegible_se_halla_por_su_serie_y_se_entrega(
    almacenista, compras, session, trabajador
):
    _, pieza = pieza_en_kep(compras, session, vigente_hasta=hoy_mx() + timedelta(days=60))
    vales, movs = total_vales(session), total_movimientos(session)

    r = almacenista.get("/api/busqueda", params={"q": pieza.numero_serie})

    assert r.status_code == 200
    (hallada,) = r.json()["piezas"]["elementos"]
    assert hallada["id"] == str(pieza.id) and hallada["numero_serie"] == pieza.numero_serie
    assert "KEP" in hallada["ubicacion"]
    assert (total_vales(session), total_movimientos(session)) == (vales, movs)  # buscar no escribe

    # Con el código que devolvió la búsqueda se agrega el renglón y se entrega.
    ev = evaluar(almacenista, trabajador, [renglon(hallada["codigo"])])
    assert ev["renglones"][0]["nivel"] == "VERDE" and ev["puede_confirmar"] is True
    vale = entregar(almacenista, trabajador, hallada["codigo"])
    session.refresh(pieza)
    assert pieza.ubicacion_id == AlmacenService(session).ubicacion_de_trabajador(trabajador.id).id
    detalle = almacenista.get(f"{VALES}/{vale['id']}").json()
    assert detalle["renglones"][0]["numero_serie"] == pieza.numero_serie


def test_E_18_US_ENT_001_con_la_credencial_ilegible_se_teclea_el_numero_de_empleado(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)

    r = almacenista.get(f"/api/escaneo/{trabajador.numero_empleado}")

    assert r.status_code == 200
    escaneo = r.json()
    assert escaneo["tipo"] == "TRABAJADOR" and escaneo["id"] == str(trabajador.id)
    assert escaneo["resumen"]["numero_empleado"] == trabajador.numero_empleado
    assert escaneo["resumen"]["vigente"] is True
    # Con el trabajador identificado así, la entrega sale normal.
    cuerpo = cuerpo_entrega(trabajador, [renglon(guantes.codigo, 2)]) | {
        "trabajador_id": escaneo["id"]
    }
    ok = almacenista.post(VALES, json=cuerpo)
    assert ok.status_code == 201, ok.text
    detalle = almacenista.get(f"{VALES}/{ok.json()['id']}").json()
    assert detalle["trabajador"]["numero_empleado"] == trabajador.numero_empleado
    assert existencia(session, "KEP", guantes) == 3


# ------------------------------------------------------------------------------------ E-19


def test_E_19_un_articulo_inactivado_a_medio_capturar_se_rechaza_al_confirmar_sin_escribir(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    cuerpo = cuerpo_entrega(trabajador, [renglon(guantes.codigo, 2)])
    ev = almacenista.post(
        f"{VALES}/evaluar", json={k: v for k, v in cuerpo.items() if k != "id_cliente"}
    ).json()
    assert ev["nivel"] == "VERDE" and ev["puede_confirmar"] is True

    # Mientras el almacenista captura, Compras inactiva el modelo.
    inactivar = compras.post(
        f"/api/articulos/{guantes.id}/inactivacion", json={"motivo": "Descontinuado"}
    )
    assert inactivar.status_code == 200 and inactivar.json()["activo"] is False
    vales, movs = total_vales(session), total_movimientos(session)

    r = almacenista.post(VALES, json=cuerpo)

    assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO"
    nueva = r.json()["detalles"]
    assert nueva["nivel"] == "ROJO" and nueva["puede_confirmar"] is False
    renglon_rojo = nueva["renglones"][0]
    assert renglon_rojo["codigo"] == guantes.codigo and renglon_rojo["nivel"] == "ROJO"
    assert [m["regla"] for m in renglon_rojo["motivos"]] == ["E-19"]
    assert "Descontinuado" in renglon_rojo["motivos"][0]["mensaje"]
    assert renglon_rojo["autorizable"] is False
    # No se escribió nada: ni vale, ni movimientos, ni existencias.
    assert (total_vales(session), total_movimientos(session)) == (vales, movs)
    assert existencia(session, "KEP", guantes) == 5
    assert existencia_de_trabajador(session, trabajador, guantes) == 0


# ------------------------------------------------------------------------------ P-02 / CF-06


def test_P_02_CF_06_solo_los_articulos_que_requieren_inspeccion_la_exigen_al_entregar(
    almacenista, compras, session, trabajador
):
    _, exige = pieza_en_kep(compras, session, requiere_inspeccion=True)
    _, no_exige = pieza_en_kep(compras, session, requiere_inspeccion=False)
    # Las dos piezas están aptas y ninguna tiene inspección vigente.

    ev = evaluar(almacenista, trabajador, [renglon(exige.codigo), renglon(no_exige.codigo)])

    con, sin = ev["renglones"]
    assert con["nivel"] == "ROJO" and [m["regla"] for m in con["motivos"]] == ["E-06"]
    assert con["autorizable"] is False and "Sin inspección" in con["motivos"][0]["mensaje"]
    assert sin["nivel"] == "VERDE" and sin["motivos"] == []
    # El que no la exige se entrega; el que sí, no.
    assert (
        almacenista.post(
            VALES, json=cuerpo_entrega(trabajador, [renglon(exige.codigo)])
        ).status_code
        == 409
    )
    assert entregar(almacenista, trabajador, no_exige.codigo)["folio"]


def test_P_02_CF_06_el_requisito_se_define_en_el_catalogo_y_aplica_desde_ese_momento(
    almacenista, compras, session, trabajador
):
    articulo, pieza = pieza_en_kep(
        compras, session, requiere_inspeccion=False, vigencia_inspeccion_dias=30
    )
    assert evaluar(almacenista, trabajador, [renglon(pieza.codigo)])["nivel"] == "VERDE"

    activar = compras.patch(
        f"/api/articulos/{articulo.id}",
        json={"requiere_inspeccion": True, "vigencia_inspeccion_dias": 30},
    )
    assert activar.status_code == 200, activar.text
    ev = evaluar(almacenista, trabajador, [renglon(pieza.codigo)])
    assert ev["renglones"][0]["nivel"] == "ROJO" and motivos(ev) == ["E-06"]

    quitar = compras.patch(f"/api/articulos/{articulo.id}", json={"requiere_inspeccion": False})
    assert quitar.status_code == 200, quitar.text
    assert evaluar(almacenista, trabajador, [renglon(pieza.codigo)])["nivel"] == "VERDE"


# ----------------------------------------------------------------------------------- RG-11


def test_RG_11_un_cuerpo_con_fecha_propia_se_rechaza_y_no_escribe(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    vales, movs = total_vales(session), total_movimientos(session)
    for campo in ("creado_en", "fecha", "fecha_hora"):
        cuerpo = cuerpo_entrega(trabajador, [renglon(guantes.codigo)]) | {
            campo: "2020-01-01T00:00:00Z"
        }
        r = almacenista.post(VALES, json=cuerpo)
        assert r.status_code == 422, (campo, r.text)
    assert (total_vales(session), total_movimientos(session)) == (vales, movs)


def test_RG_11_la_fecha_y_hora_del_vale_son_las_del_servidor(
    almacenista, compras, session, trabajador, monkeypatch
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    instante = ahora_utc().replace(microsecond=0) - timedelta(days=3)  # el reloj del servidor
    monkeypatch.setattr("app.modulos.movimientos.service.ahora_utc", lambda: instante)

    vale = entregar(almacenista, trabajador, guantes, 1)

    assert vale["creado_en"] == instante.isoformat().replace("+00:00", "") + "Z"
    fila = session.get(Vale, uuid.UUID(vale["id"]))
    assert fila.creado_en == instante
    movimientos = session.scalars(select(Movimiento).where(Movimiento.vale_id == fila.id)).all()
    assert movimientos and all(m.creado_en == instante for m in movimientos)
