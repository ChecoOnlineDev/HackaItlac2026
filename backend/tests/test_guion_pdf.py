"""El guion del PDF (p. 2) de punta a punta, SOLO por la API HTTP (TestClient con sesiones reales).

Es el «Flujo principal» de `docs/product/mvp-scope.md` en un solo escenario encadenado, con una
aserción fuerte en cada paso (existencias exactas antes y después, folios, estados, responsable,
ausencia de costos). Al final corre el verificador de invariantes y compara los reportes con lo
operado.

  1. RH registra a un trabajador.
  2. El almacenista le surte EPP y una herramienta por escaneo.
  3. Intenta entregar un arnés no apto: el sistema lo impide (y uno con la inspección vencida).
  4. Intenta una entrega que excede el límite: se bloquea hasta que el supervisor autoriza.
  5. Registra un traspaso entre almacenes y el destino lo recibe.
  6. Al procesar la baja, el sistema muestra los pendientes; tras devolverlos, emite el vale de
     no adeudo.

Usa las piezas de los datos de prueba (`app/datos_prueba_piezas.py`): ALT-001..008 y HER-001..005.
Cada paso es una función con el ID de las reglas que comprueba en su nombre.
"""

import re
from dataclasses import dataclass, field
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.core.tiempo import hoy_mx
from app.modulos.acceso.permisos import P
from tests.ayudas_guion import (
    FIRMA,
    alta_trabajador,
    buscar_trabajador_en_lista,
    cantidad_en,
    confirmar,
    disponible_en,
    en_ubicacion_virtual,
    entregar,
    evaluar,
    ids_de_almacen,
    nuevo_cliente,
    pieza_id,
    reglas_de,
    siguiente_folio,
    sin_costos,
    ubicacion_de_pieza,
)
from tests.conftest import iniciar_sesion_en
from tests.invariantes import tomar_huella, verificar_invariantes
from tests.movimientos.ayudas_traspasos import (  # noqa: F401  (fixtures)
    cliente_almacen,
    cliente_almacenista,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
VALES = "/api/vales"
AUT = "/api/autorizaciones"


@pytest.fixture(autouse=True)
def _archivos_tmp(tmp_path, monkeypatch):
    """Las fotos y firmas van a una carpeta temporal."""
    monkeypatch.setattr(get_settings(), "archivos_dir", tmp_path)


@dataclass
class Guion:
    """Lo que se va operando: los clientes, el trabajador y lo que cada paso deja anotado."""

    session: object
    rh: TestClient
    sup: TestClient
    admin: TestClient  # el único que ve todos los almacenes (AC-06)
    compras: TestClient
    kep: TestClient
    con: TestClient
    mid: TestClient
    hyl: TestClient
    pin_supervisor: str
    almacen: dict
    trabajador: dict = field(default_factory=dict)
    # Renglones de movimiento que cada vale dejó a nombre del trabajador (para el reporte).
    movimientos_del_trabajador: int = 0
    vales: dict = field(default_factory=dict)
    guantes_consumidos: int = 0


def _nivel_de(evaluacion: dict, renglon: int) -> str:
    return evaluacion["renglones"][renglon - 1]["nivel"]


def _solicitud(evaluacion: dict, trabajador_id: str, motivo: str) -> dict:
    """Lo que la interfaz manda a `POST /api/autorizaciones`: sale de la evaluación."""
    renglones = [
        {
            "codigo": r["codigo"],
            "articulo_id": r["articulo"]["id"],
            "articulo": r["articulo"]["nombre"],
            "cantidad": r["cantidad"],
            "regla": r["motivos"][0]["regla"],
            "mensaje": r["motivos"][0]["mensaje"],
            "autorizable": r["autorizable"],
        }
        for r in evaluacion["renglones"]
        if r["nivel"] == "NARANJA"
    ]
    return {"trabajador_id": trabajador_id, "renglones": renglones, "motivo": motivo}


# ============================================================ 1. RH registra al trabajador


def paso_1_rh_registra_al_trabajador(g: Guion) -> None:
    hoy = hoy_mx()
    ficha = alta_trabajador(
        g.rh,
        nombre="Pedro Gutiérrez Luna",
        numero="EMP-PDF-001",
        credencial="CRED-PDF-001",
        curp="GULP900101HCLTNR09",
        nss="12345678901",
        inicio_dias=-5,
        fin_dias=200,
    )
    # Queda Activo y vigente (T-03, T-06, T-07).
    assert ficha["estado"] == "ACTIVO" and ficha["estado_texto"] == "Activo"
    assert ficha["vigencia"]["vigente"] is True
    assert ficha["periodo"]["inicio"] == str(hoy - timedelta(days=5))
    assert ficha["periodo"]["fin"] == str(hoy + timedelta(days=200))
    assert ficha["situacion"] == "SIN_PENDIENTES" and ficha["resguardo"] == []
    # RH tiene el permiso de datos personales: ve CURP y NSS (RG-13).
    assert (ficha["curp"], ficha["nss"]) == ("GULP900101HCLTNR09", "12345678901")
    g.trabajador = ficha

    # Foto de prueba (T-09, opcional).
    assert g.rh.get(f"/api/trabajadores/{ficha['id']}/foto").status_code == 404
    r = g.rh.post(
        f"/api/trabajadores/{ficha['id']}/foto", files={"archivo": ("foto.png", PNG, "image/png")}
    )
    assert r.status_code == 200 and r.json()["tiene_foto"] is True
    de_rh = g.rh.get(f"/api/trabajadores/{ficha['id']}").json()
    assert de_rh["tiene_foto"] is True and de_rh["codigos"] == ["CRED-PDF-001"]

    # Un número de empleado repetido es reingreso, no alta (T-02): no crea a otra persona.
    repetido = g.rh.post(
        "/api/trabajadores",
        json={
            "nombre": "Otro",
            "numero_empleado": "EMP-PDF-001",
            "puesto": "Soldador",
            "area_obra": "Midrex",
            "inicio": str(hoy),
            "fin": str(hoy + timedelta(days=10)),
        },
    )
    assert repetido.status_code == 409 and repetido.json()["codigo"] == "TRABAJADOR_EXISTE"
    assert repetido.json()["detalles"]["trabajador"]["id"] == ficha["id"]

    # Su credencial lo identifica en CUALQUIER almacén (C-01), sin CURP ni NSS (RG-13).
    for sesion in (g.kep, g.con, g.mid, g.hyl):
        r = sesion.get("/api/escaneo/CRED-PDF-001")
        assert r.status_code == 200, r.text
        cuerpo = r.json()
        assert cuerpo["tipo"] == "TRABAJADOR" and cuerpo["id"] == ficha["id"]
        resumen = cuerpo["resumen"]
        assert resumen["nombre"] == "Pedro Gutiérrez Luna" and resumen["vigente"] is True
        assert resumen["numero_empleado"] == "EMP-PDF-001" and resumen["pendientes"] == 0
        assert "curp" not in resumen and "nss" not in resumen
    # También por el número tecleado (E-18).
    assert g.kep.get("/api/escaneo/EMP-PDF-001").json()["id"] == ficha["id"]
    # La ficha del almacenista trae foto y vigencia, pero no CURP ni NSS.
    de_almacen = g.kep.get(f"/api/trabajadores/{ficha['id']}").json()
    assert de_almacen["tiene_foto"] is True and de_almacen["vigencia"]["vigente"] is True
    assert "curp" not in de_almacen and "nss" not in de_almacen
    # RH lo ve en su lista sin pendientes (T-08).
    fila = buscar_trabajador_en_lista(g.rh, ficha["id"])
    assert fila["situacion"] == "SIN_PENDIENTES"


# ===================================== 2. El almacenista surte EPP y una herramienta


def paso_2_surtir_epp_y_herramienta_por_escaneo(g: Guion) -> None:
    kep, session, tid = g.kep, g.session, g.trabajador["id"]
    kep_id = g.almacen["KEP"]
    codigos = ("LENTE-CL", "GUANTE-CAR", "RESP-6200", "MINIPUL")
    antes = {c: cantidad_en(kep, kep_id, c) for c in codigos}
    assert antes == {"LENTE-CL": 200, "GUANTE-CAR": 120, "RESP-6200": 40, "MINIPUL": 2}
    consumido_antes = {
        c: en_ubicacion_virtual(session, "CONSUMIDO", c) for c in ("LENTE-CL", "GUANTE-CAR")
    }

    # Cada código se escanea y el sistema lo reconoce (artículo o pieza).
    assert kep.get("/api/escaneo/LENTE-CL").json()["tipo"] == "ARTICULO"
    assert kep.get("/api/escaneo/HER-001").json()["tipo"] == "PIEZA"

    renglones = [
        {"codigo": "LENTE-CL", "cantidad": 1},
        {"codigo": "GUANTE-CAR", "cantidad": 2},
        {"codigo": "RESP-6200", "cantidad": 1},
        {"codigo": "HER-001"},  # el minipulidor, una pieza por serie
    ]
    cuerpo = {"tipo": "ENTREGA", "trabajador_id": tid, "renglones": renglones}
    ev = evaluar(kep, cuerpo)
    assert ev["nivel"] == "VERDE" and ev["puede_confirmar"] is True
    assert [r["nivel"] for r in ev["renglones"]] == ["VERDE"] * 4
    assert ev["trabajador"]["tiene_foto"] is True and ev["trabajador"]["resguardo"] == []
    assert cantidad_en(kep, kep_id, "GUANTE-CAR") == 120  # evaluar no escribe (E-28)

    esperado_folio = siguiente_folio(session, "KEP", "ENT")
    antes_de_confirmar = tomar_huella(session)
    vale = entregar(kep, tid, renglones)
    # Folio KEP-ENT-… consecutivo, token del QR, un renglón por escaneo.
    assert vale["folio"] == esperado_folio and re.fullmatch(r"KEP-ENT-\d{6}", vale["folio"])
    assert vale["token"] and len(vale["renglones"]) == 4
    assert [r["codigo"] for r in vale["renglones"]] == [r["codigo"] for r in renglones]
    sin_costos(vale)
    g.vales["entrega_1"] = vale
    g.movimientos_del_trabajador += 4

    # Existencias exactas después.
    assert cantidad_en(kep, kep_id, "LENTE-CL") == 199
    assert cantidad_en(kep, kep_id, "GUANTE-CAR") == 118
    assert cantidad_en(kep, kep_id, "RESP-6200") == 39
    assert cantidad_en(kep, kep_id, "MINIPUL") == 1 and disponible_en(kep, kep_id, "MINIPUL") == 1
    # Los consumibles van a CONSUMIDO (con el trabajador anotado); los retornables, a su resguardo.
    assert en_ubicacion_virtual(session, "CONSUMIDO", "LENTE-CL") == consumido_antes["LENTE-CL"] + 1
    assert (
        en_ubicacion_virtual(session, "CONSUMIDO", "GUANTE-CAR")
        == consumido_antes["GUANTE-CAR"] + 2
    )
    g.guantes_consumidos += 2

    # El vale abre por su QR (token) y dice quién lo hizo, quién lo firmó y qué movió.
    r = kep.get(f"{VALES}/por-token/{vale['token']}")
    assert r.status_code == 200, r.text
    detalle = r.json()
    assert detalle["id"] == vale["id"] and detalle["folio"] == vale["folio"]
    assert detalle["tipo"] == "ENTREGA" and detalle["estado"] == "EMITIDO"
    assert detalle["responsable"]["nombre"] == "Almacenista Kepler"
    assert detalle["almacen"]["clave"] == "KEP" and detalle["trabajador"]["id"] == tid
    assert detalle["firma_modo"] == "PANTALLA" and detalle["tiene_firma"] is True
    assert detalle["valido"] is None  # sin autorización no hay «Validó»
    sin_costos(detalle)
    reng = {x["codigo_articulo"]: x for x in detalle["renglones"]}
    assert reng["GUANTE-CAR"]["destino"]["tipo"] == "CONSUMIDO"
    assert reng["GUANTE-CAR"]["saldo_origen"] == 118
    assert reng["RESP-6200"]["destino"]["tipo"] == "TRABAJADOR"
    assert reng["MINIPUL"]["codigo_pieza"] == "HER-001"
    assert reng["MINIPUL"]["numero_serie"] == "SN-MIN-0001"
    assert all(x["condicion"] == "BUENO" for x in detalle["renglones"])  # E-22
    # El QR y el folio se escanean como cualquier código (RG-10); la firma se descarga.
    assert kep.get(f"/api/escaneo/{vale['token']}").json()["tipo"] == "VALE"
    assert kep.get(f"/api/escaneo/{vale['folio']}").json()["id"] == vale["id"]
    firma = kep.get(f"{VALES}/{vale['id']}/firma")
    assert firma.status_code == 200 and firma.headers["content-type"] == "image/png"
    # Otro almacén no ve el vale de Kepler (AC-06).
    assert g.con.get(f"{VALES}/{vale['id']}").status_code == 404

    # El trabajador aparece con su resguardo: lo retornable, no lo consumido (B-03).
    ficha = kep.get(f"/api/trabajadores/{tid}").json()
    en_resguardo = {x["codigo"]: x for x in ficha["resguardo"]}
    assert set(en_resguardo) == {"RESP-6200", "HER-001"}
    assert en_resguardo["HER-001"]["folio"] == vale["folio"]
    assert en_resguardo["HER-001"]["almacen_clave"] == "KEP"
    assert ficha["pendientes"]["total"] == 2 and ficha["situacion"] == "CON_PENDIENTES"
    assert "Pedro" in ubicacion_de_pieza(kep, "HER-001")

    # Nada cambió de lo ya guardado salvo lo nuevo (invariantes 5 y 10).
    verificar_invariantes(session, antes_de_confirmar)
    g.huella = tomar_huella(session)


# ============================== 3. Un arnés no apto: el sistema lo impide (E-05, E-06)


def paso_3_arnes_no_apto_o_vencido_no_se_entrega(g: Guion) -> None:
    kep, tid = g.kep, g.trabajador["id"]
    kep_id = g.almacen["KEP"]
    vales_antes = kep.get(VALES, params={"tamano": 100}).json()["total"]

    # --- Arnés NO APTO (ALT-003): rojo por E-05 y E-06, sin salida por autorización.
    cuerpo = {"tipo": "ENTREGA", "trabajador_id": tid, "renglones": [{"codigo": "ALT-003"}]}
    ev = evaluar(kep, cuerpo)
    assert ev["nivel"] == "ROJO" and ev["puede_confirmar"] is False
    renglon = ev["renglones"][0]
    assert renglon["nivel"] == "ROJO" and renglon["autorizable"] is False
    assert {"E-05", "E-06"} <= set(reglas_de(ev, 1))  # SM-04
    assert renglon["pieza"]["estado"] == "NO_APTO"
    # El rojo de seguridad no se manda a autorizar (A-06): aunque la interfaz lo marque
    # «autorizable», el servidor lo evalúa de verdad y lo rechaza.
    pedida = {
        "trabajador_id": tid,
        "motivo": "Lo necesita ya",
        "renglones": [
            {
                "codigo": "ALT-003",
                "articulo_id": renglon["articulo"]["id"],
                "articulo": "Arnés Kevlar",
                "cantidad": 1,
                "regla": "E-05",
                "mensaje": "x",
                "autorizable": True,
            }
        ],
    }
    r = kep.post(AUT, json=pedida)
    assert r.status_code == 422 and r.json()["codigo"] == "RENGLON_NO_AUTORIZABLE"
    # Confirmar es 409 VALE_CAMBIO: no se guarda nada y la pieza sigue en Kepler.
    r = kep.post(VALES, json={**cuerpo, "id_cliente": nuevo_cliente(), "firma": FIRMA})
    assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO"
    assert r.json()["detalles"]["nivel"] == "ROJO"
    assert kep.get(VALES, params={"tamano": 100}).json()["total"] == vales_antes
    assert "Kepler" in ubicacion_de_pieza(kep, "ALT-003")

    # --- Arnés con la inspección VENCIDA (ALT-005): rojo E-06 con su fecha.
    hace_20 = hoy_mx() - timedelta(days=20)
    ev = evaluar(kep, {**cuerpo, "renglones": [{"codigo": "ALT-005"}]})
    assert ev["nivel"] == "ROJO" and ev["renglones"][0]["autorizable"] is False
    assert reglas_de(ev, 1) == ["E-06"]
    assert hace_20.strftime("%d/%m/%Y") in ev["renglones"][0]["motivos"][0]["mensaje"]
    r = kep.post(
        VALES,
        json={
            **cuerpo,
            "renglones": [{"codigo": "ALT-005"}],
            "id_cliente": nuevo_cliente(),
            "firma": FIRMA,
        },
    )
    assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO"

    # --- Se inspecciona (Apto) y entonces sí se entrega (P-01, SM-04).
    arnes = pieza_id(kep, "ALT-005")
    r = kep.post(
        f"/api/piezas/{arnes}/inspecciones",
        json={
            "resultado": "APTO",
            "puntos": {
                "etiquetas": True,
                "costuras": True,
                "cintas": True,
                "herrajes": True,
                "conectores": True,
            },
            "observacion": "Revisión completa en el mostrador",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["pieza"]["estado"] == "APTO"
    assert r.json()["pieza"]["inspeccion_vigente_hasta"] == str(hoy_mx() + timedelta(days=180))
    renglones = [{"codigo": "ALT-005"}, {"codigo": "ALT-007"}]  # arnés y gancho doble
    ev = evaluar(kep, {**cuerpo, "renglones": renglones})
    assert ev["nivel"] == "VERDE" and ev["puede_confirmar"] is True
    antes = (cantidad_en(kep, kep_id, "ARN-POL"), cantidad_en(kep, kep_id, "GAN-DOB"))
    assert antes == (2, 1)
    vale = entregar(kep, tid, renglones)
    g.vales["entrega_alturas"] = vale
    g.movimientos_del_trabajador += 2
    sin_costos(vale)
    assert cantidad_en(kep, kep_id, "ARN-POL") == 1 and cantidad_en(kep, kep_id, "GAN-DOB") == 0
    assert "Pedro" in ubicacion_de_pieza(kep, "ALT-005")
    # El arnés no apto sigue apartado, aunque se inspeccionó el otro.
    assert evaluar(kep, {**cuerpo, "renglones": [{"codigo": "ALT-003"}]})["nivel"] == "ROJO"
    # Y el historial de la pieza dejó la inspección y la entrega.
    historial = kep.get(f"/api/piezas/{arnes}").json()["historial"]
    tipos = [h["tipo"] for h in historial]
    assert tipos[:2] == ["MOVIMIENTO", "INSPECCION"] and historial[0]["folio"] == vale["folio"]


# ============ 4. Una entrega que excede el límite: bloqueada hasta que el supervisor autoriza


def paso_4_limite_excedido_requiere_autorizacion(g: Guion, app, crear_usuario) -> None:
    kep, tid = g.kep, g.trabajador["id"]
    kep_id = g.almacen["KEP"]
    cuerpo = {
        "tipo": "ENTREGA",
        "trabajador_id": tid,
        "renglones": [{"codigo": "GUANTE-CAR", "cantidad": 2}],
    }
    antes = cantidad_en(kep, kep_id, "GUANTE-CAR")
    assert antes == 118

    # Límite de la categoría: 3 por semana. Lleva 2 y pide 2: naranja L-03 (L-04, E-07).
    ev = evaluar(kep, cuerpo)
    assert ev["nivel"] == "NARANJA" and ev["puede_confirmar"] is False
    assert reglas_de(ev, 1) == ["L-03"] and ev["renglones"][0]["autorizable"] is True
    assert "límite 3, tiene 2" in ev["renglones"][0]["motivos"][0]["mensaje"]
    assert "pide 2" in ev["renglones"][0]["motivos"][0]["mensaje"]
    # Sin autorización el servidor no lo guarda (SM-03, RG-08).
    r = kep.post(VALES, json={**cuerpo, "id_cliente": nuevo_cliente(), "firma": FIRMA})
    assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO"
    assert cantidad_en(kep, kep_id, "GUANTE-CAR") == antes

    # El almacenista pide autorización con su motivo (A-02): queda PENDIENTE y vence en 15 min.
    r = kep.post(AUT, json=_solicitud(ev, tid, "Se le llenaron de grasa"))
    assert r.status_code == 201, r.text
    aut_pin = r.json()["id"]
    assert r.json()["estado"] == "PENDIENTE" and r.json()["vence_en"]
    # Pendiente no sirve; el almacenista no puede autorizar (no tiene el permiso), ni con PIN malo.
    r = kep.post(
        VALES,
        json={**cuerpo, "id_cliente": nuevo_cliente(), "firma": FIRMA, "autorizacion_id": aut_pin},
    )
    assert r.status_code == 409 and r.json()["codigo"] == "AUTORIZACION_INVALIDA"
    r = kep.post(f"{AUT}/{aut_pin}/resolucion", json={"decision": "APROBAR"})
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"
    r = kep.post(
        f"{AUT}/{aut_pin}/resolucion",
        json={"decision": "APROBAR", "usuario": "supervisor", "pin": "0000"},
    )
    assert r.status_code == 403 and r.json()["codigo"] == "PIN_INCORRECTO"
    assert kep.get(f"{AUT}/{aut_pin}").json()["estado"] == "PENDIENTE"
    # Un almacenista de otro almacén no ve la solicitud (AC-06).
    assert g.con.get(f"{AUT}/{aut_pin}").status_code == 404

    # El supervisor autoriza POR PIN en el dispositivo del almacenista (A-01, medio PIN).
    r = kep.post(
        f"{AUT}/{aut_pin}/resolucion",
        json={"decision": "APROBAR", "usuario": "supervisor", "pin": g.pin_supervisor},
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "APROBADA" and r.json()["medio"] == "PIN"
    assert r.json()["resuelta_por"]["nombre"] == "Supervisor Kepler"
    vale = entregar(kep, tid, cuerpo["renglones"], autorizacion_id=aut_pin)
    g.vales["entrega_pin"] = vale
    g.movimientos_del_trabajador += 1
    g.guantes_consumidos += 2
    assert vale["renglones"][0]["nivel"] == "NARANJA" and vale["renglones"][0]["reglas"] == ["L-03"]
    assert cantidad_en(kep, kep_id, "GUANTE-CAR") == antes - 2
    # El vale lleva «Validó» (A-04): quién pidió, quién autorizó, por qué medio y por qué.
    valido = kep.get(f"{VALES}/{vale['id']}").json()["valido"]
    assert valido["autorizacion_id"] == aut_pin and valido["medio"] == "PIN"
    assert valido["solicito"]["nombre"] == "Almacenista Kepler"
    assert valido["autorizo"]["nombre"] == "Supervisor Kepler"
    assert valido["motivo"] == "Se le llenaron de grasa"
    # La autorización es de UN SOLO USO (A-03): queda USADA y no vuelve a servir.
    assert kep.get(f"{AUT}/{aut_pin}").json()["estado"] == "USADA"
    r = kep.post(
        VALES,
        json={**cuerpo, "id_cliente": nuevo_cliente(), "firma": FIRMA, "autorizacion_id": aut_pin},
    )
    assert r.status_code == 409 and r.json()["codigo"] == "AUTORIZACION_INVALIDA"
    assert "ya se usó" in r.json()["mensaje"]
    assert cantidad_en(kep, kep_id, "GUANTE-CAR") == antes - 2

    # Quien captura NO se autoriza a sí mismo (A-05): ni remoto ni con su PIN.
    ambos = crear_usuario(
        {
            P.ENTREGAS_CREAR,
            P.AUTORIZACIONES_RESOLVER,
            P.TRABAJADORES_VER,
            P.CATALOGO_VER,
            P.INVENTARIO_VER,
        },
        almacen="KEP",
        pin="4321",
    )
    propio = TestClient(app)
    assert iniciar_sesion_en(propio, ambos).status_code == 200
    uno = {**cuerpo, "renglones": [{"codigo": "GUANTE-CAR", "cantidad": 1}]}
    ev_uno = evaluar(propio, uno)
    assert reglas_de(ev_uno, 1) == ["L-03"]
    aut_propia = propio.post(AUT, json=_solicitud(ev_uno, tid, "Para mí mismo")).json()["id"]
    r = propio.post(f"{AUT}/{aut_propia}/resolucion", json={"decision": "APROBAR"})
    assert r.status_code == 403 and r.json()["codigo"] == "AUTORIZACION_PROPIA"
    r = propio.post(
        f"{AUT}/{aut_propia}/resolucion",
        json={"decision": "APROBAR", "usuario": ambos.usuario, "pin": "4321"},
    )
    assert r.status_code == 403 and r.json()["codigo"] == "AUTORIZACION_PROPIA"
    assert propio.get(f"{AUT}/{aut_propia}").json()["estado"] == "PENDIENTE"
    propio.close()

    # Variante A DISTANCIA: el supervisor ve la solicitud en su celular y la aprueba (medio REMOTA).
    aut_remota = kep.post(AUT, json=_solicitud(ev_uno, tid, "Cubre a un compañero")).json()["id"]
    pendientes = g.sup.get(AUT).json()
    fila = next(x for x in pendientes["elementos"] if x["id"] == aut_remota)
    assert fila["estado"] == "PENDIENTE" and fila["motivo"] == "Cubre a un compañero"
    assert fila["trabajador"]["nombre"] == "Pedro Gutiérrez Luna"
    assert fila["solicitada_por"]["nombre"] == "Almacenista Kepler"
    r = g.sup.post(f"{AUT}/{aut_remota}/resolucion", json={"decision": "APROBAR"})
    assert r.status_code == 200 and r.json()["medio"] == "REMOTA"
    # La pantalla del almacenista se entera consultando (cada tres segundos en la interfaz).
    assert kep.get(f"{AUT}/{aut_remota}").json()["estado"] == "APROBADA"
    vale = entregar(kep, tid, uno["renglones"], autorizacion_id=aut_remota)
    g.vales["entrega_remota"] = vale
    g.movimientos_del_trabajador += 1
    g.guantes_consumidos += 1
    valido = kep.get(f"{VALES}/{vale['id']}").json()["valido"]
    assert valido["medio"] == "REMOTA" and valido["autorizo"]["nombre"] == "Supervisor Kepler"
    assert cantidad_en(kep, kep_id, "GUANTE-CAR") == antes - 3

    # Variante RECHAZADA: el supervisor dice que no y el vale no se puede guardar.
    aut_no = kep.post(AUT, json=_solicitud(ev_uno, tid, "Quiere más")).json()["id"]
    r = g.sup.post(f"{AUT}/{aut_no}/resolucion", json={"decision": "RECHAZAR"})
    assert r.status_code == 200 and r.json()["estado"] == "RECHAZADA"
    r = kep.post(
        VALES,
        json={**uno, "id_cliente": nuevo_cliente(), "firma": FIRMA, "autorizacion_id": aut_no},
    )
    assert r.status_code == 409 and r.json()["codigo"] == "AUTORIZACION_INVALIDA"
    assert cantidad_en(kep, kep_id, "GUANTE-CAR") == antes - 3

    # A mitad del guion el reporte de adeudos (RH ve completo) lista lo que el trabajador tiene.
    adeudos = [
        a["codigo"]
        for a in g.rh.get("/api/reportes/adeudos", params={"tamano": 200}).json()["elementos"]
        if a["trabajador_id"] == tid
    ]
    assert sorted(adeudos) == ["ALT-005", "ALT-007", "HER-001", "RESP-6200"]


# ================================ 5. Traspaso entre almacenes y el destino lo recibe


def _traspaso_cuerpo(g: Guion, destino: str, renglones: list[dict]) -> dict:
    return {
        "tipo": "TRASPASO",
        "destino_almacen_id": str(g.almacen[destino]),
        "renglones": renglones,
    }


def _suma_cincel(g: Guion) -> dict:
    """Cincel en cada lugar: tres almacenes y En tránsito (suman siempre 35)."""
    session = g.session
    return {
        "KEP": cantidad_en(g.kep, g.almacen["KEP"], "CINCEL"),
        "CON": cantidad_en(g.con, g.almacen["CON"], "CINCEL"),
        "MID": cantidad_en(g.mid, g.almacen["MID"], "CINCEL"),
        "TRANSITO": en_ubicacion_virtual(session, "EN_TRANSITO", "CINCEL"),
    }


def paso_5_traspasos_y_recepciones(g: Guion) -> None:
    session = g.session
    assert _suma_cincel(g) == {"KEP": 25, "CON": 10, "MID": 0, "TRANSITO": 0}
    pieza_arnes = pieza_id(g.kep, "ALT-001")
    assert cantidad_en(g.kep, g.almacen["KEP"], "ARN-KEV") == 3
    assert disponible_en(g.kep, g.almacen["KEP"], "ARN-KEV") == 2  # ALT-003 no cuenta (I-05)

    # --- Kepler -> Contratistas: sale una pieza y 5 cinceles (X-01..X-07).
    cuerpo = _traspaso_cuerpo(
        g, "CON", [{"codigo": "ALT-001"}, {"codigo": "CINCEL", "cantidad": 5}]
    )
    # El traspaso entre almacenes lo envía el supervisor del origen y lo recibe el del destino
    # (`traspasos.operar` es del Supervisor; el almacenista no lo opera).
    ev = evaluar(g.sup, cuerpo)
    assert ev["puede_confirmar"] is True and ev["nivel"] in ("VERDE", "AMARILLO")
    folio = siguiente_folio(session, "KEP", "TRS")
    trs1 = confirmar(g.sup, cuerpo)
    assert trs1["folio"] == folio and re.fullmatch(r"KEP-TRS-\d{6}", folio)
    g.vales["trs1"] = trs1
    sin_costos(trs1)
    d = g.kep.get(f"{VALES}/{trs1['id']}").json()
    assert d["estado"] == "EN_TRANSITO" and d["destino_almacen"]["clave"] == "CON"
    assert d["responsable"]["nombre"] == "Supervisor Kepler"
    assert _suma_cincel(g) == {"KEP": 20, "CON": 10, "MID": 0, "TRANSITO": 5}
    assert cantidad_en(g.kep, g.almacen["KEP"], "ARN-KEV") == 2
    assert ubicacion_de_pieza(g.kep, "ALT-001") == "En tránsito"

    # Solo el destino recibe (X-10): otro almacén y el mismo origen salen en rojo.
    for intruso in (g.hyl, g.sup):
        ev = evaluar(
            intruso,
            {
                "tipo": "RECEPCION",
                "vale_origen_id": trs1["id"],
                "renglones": [{"codigo": "CINCEL", "cantidad": 5}],
            },
        )
        assert ev["nivel"] == "ROJO" and "X-10" in reglas_de(ev)
    # El destino ve el traspaso por recibir con lo pendiente (el contador del inicio).
    assert g.con.get("/api/traspasos/por-recibir", params={"solo_contar": "true"}).json() == {
        "total": 1
    }
    por_recibir = g.con.get("/api/traspasos/por-recibir").json()["elementos"][0]
    assert por_recibir["folio"] == trs1["folio"] and por_recibir["pendiente_total"] == 6
    assert por_recibir["estado"] == "EN_TRANSITO" and por_recibir["origen"]["clave"] == "KEP"

    # Recepción TOTAL (X-11): todo lo pendiente de una vez.
    rec1 = confirmar(
        g.con,
        {
            "tipo": "RECEPCION",
            "vale_origen_id": trs1["id"],
            "renglones": [
                {"codigo": r["codigo"], "cantidad": r["cantidad_pendiente"]}
                for r in por_recibir["renglones"]
            ],
        },
    )
    assert re.fullmatch(r"CON-REC-\d{6}", rec1["folio"])
    assert g.con.get(f"{VALES}/{trs1['id']}").json()["estado"] == "RECIBIDO"
    assert g.con.get(f"{VALES}/{rec1['id']}").json()["responsable"]["nombre"] == (
        "Supervisor Contratistas"  # X-08
    )
    assert _suma_cincel(g) == {"KEP": 20, "CON": 15, "MID": 0, "TRANSITO": 0}
    assert "Contratistas" in ubicacion_de_pieza(g.con, "ALT-001")
    assert g.con.get("/api/traspasos/por-recibir", params={"solo_contar": "true"}).json() == {
        "total": 0
    }

    # --- Contratistas -> Midrex: 1 pieza y 4 cinceles; Midrex recibe CON DIFERENCIAS (X-13).
    cuerpo2 = _traspaso_cuerpo(
        g, "MID", [{"codigo": "ALT-001"}, {"codigo": "CINCEL", "cantidad": 4}]
    )
    trs2 = confirmar(g.con, cuerpo2)
    g.vales["trs2"] = trs2
    assert re.fullmatch(r"CON-TRS-\d{6}", trs2["folio"])
    assert _suma_cincel(g) == {"KEP": 20, "CON": 11, "MID": 0, "TRANSITO": 4}
    rec2 = confirmar(
        g.mid,
        {
            "tipo": "RECEPCION",
            "vale_origen_id": trs2["id"],
            "renglones": [{"codigo": "ALT-001"}, {"codigo": "CINCEL", "cantidad": 3}],
            "observacion": "Llegaron tres cinceles; falta uno en la caja.",  # RG-14
        },
    )
    assert re.fullmatch(r"MID-REC-\d{6}", rec2["folio"])
    assert g.mid.get(f"{VALES}/{trs2['id']}").json()["estado"] == "RECIBIDO_CON_DIFERENCIAS"
    # Lo que falta sigue En tránsito y las existencias cuadran en origen, tránsito y destino.
    assert _suma_cincel(g) == {"KEP": 20, "CON": 11, "MID": 3, "TRANSITO": 1}
    assert sum(_suma_cincel(g).values()) == 35
    pendiente = g.mid.get("/api/traspasos/por-recibir").json()["elementos"][0]
    assert pendiente["folio"] == trs2["folio"] and pendiente["pendiente_total"] == 1
    assert pendiente["estado"] == "RECIBIDO_CON_DIFERENCIAS"
    assert [r["codigo"] for r in pendiente["renglones"] if r["cantidad_pendiente"]] == ["CINCEL"]
    assert pendiente["recepciones"][0]["folio"] == rec2["folio"]
    # Recibir más de lo enviado es rojo (X-12).
    ev = evaluar(
        g.mid,
        {
            "tipo": "RECEPCION",
            "vale_origen_id": trs2["id"],
            "renglones": [{"codigo": "CINCEL", "cantidad": 2}],
        },
    )
    assert ev["nivel"] == "ROJO"
    # La que faltaba llega después y el traspaso se completa.
    rec3 = confirmar(
        g.mid,
        {
            "tipo": "RECEPCION",
            "vale_origen_id": trs2["id"],
            "renglones": [{"codigo": "CINCEL", "cantidad": 1}],
        },
    )
    assert g.mid.get(f"{VALES}/{trs2['id']}").json()["estado"] == "RECIBIDO"
    assert _suma_cincel(g) == {"KEP": 20, "CON": 11, "MID": 4, "TRANSITO": 0}
    assert g.mid.get("/api/traspasos/por-recibir", params={"solo_contar": "true"}).json() == {
        "total": 0
    }

    # El historial de la pieza muestra su recorrido completo (C-02, X-07).
    ficha = g.kep.get(f"/api/piezas/{pieza_arnes}").json()
    assert "Midrex" in ficha["ubicacion"]["texto"]
    recorrido = [h["folio"] for h in reversed(ficha["historial"]) if h["tipo"] == "MOVIMIENTO"]
    assert recorrido[1:] == [trs1["folio"], rec1["folio"], trs2["folio"], rec2["folio"]]
    assert recorrido[0].startswith("KEP-ING-")
    assert [h["tipo"] for h in ficha["historial"]].count("INSPECCION") == 1
    g.vales["rec1"], g.vales["rec2"], g.vales["rec3"] = rec1, rec2, rec3


# ======================= 6. La baja: pendientes, devolución y vale de no adeudo


def paso_6_baja_pendientes_devolucion_y_no_adeudo(g: Guion) -> None:
    kep, session, tid = g.kep, g.session, g.trabajador["id"]
    kep_id = g.almacen["KEP"]
    pendientes_esperados = {"HER-001", "RESP-6200", "ALT-005", "ALT-007"}

    # El almacenista inicia la baja cuando el trabajador pide su vale (B-01): Baja en proceso.
    r = kep.post(f"/api/trabajadores/{tid}/baja")
    assert r.status_code == 200, r.text
    baja = r.json()
    assert baja["estado"] == "BAJA_EN_PROCESO" and baja["puede_emitir_no_adeudo"] is False
    assert {p["codigo"] for p in baja["pendientes"]} == pendientes_esperados  # B-02
    assert all(p["almacen_clave"] == "KEP" and p["folio"] for p in baja["pendientes"])
    sin_costos(baja)
    # Ya no recibe entregas (E-02), pero SÍ puede devolver (SM-05).
    ev = evaluar(
        kep,
        {
            "tipo": "ENTREGA",
            "trabajador_id": tid,
            "renglones": [{"codigo": "LENTE-CL", "cantidad": 1}],
        },
    )
    assert ev["nivel"] == "ROJO" and "E-02" in reglas_de(ev, 1)
    # Sin devolver nada, el no adeudo se rechaza con la lista de pendientes (B-04).
    nad_cuerpo = {"id_cliente": nuevo_cliente()}
    r = kep.post(f"/api/trabajadores/{tid}/no-adeudo", json=nad_cuerpo)
    assert r.status_code == 409 and r.json()["codigo"] == "CON_PENDIENTES"
    assert r.json()["detalles"]["regla"] == "B-04"
    assert {p["codigo"] for p in r.json()["detalles"]["pendientes"]} == pendientes_esperados
    assert kep.get(f"/api/trabajadores/{tid}").json()["estado"] == "BAJA_EN_PROCESO"
    # RH ve «Con pendientes» (B-09).
    assert buscar_trabajador_en_lista(g.rh, tid)["situacion"] == "CON_PENDIENTES"

    # --- Devolución por PIEZA (se escanea la pieza y se abona a su titular, V-01) ---
    antes = {
        "MINIPUL": cantidad_en(kep, kep_id, "MINIPUL"),
        "ARN-POL": cantidad_en(kep, kep_id, "ARN-POL"),
        "GAN-DOB": cantidad_en(kep, kep_id, "GAN-DOB"),
    }
    assert antes == {"MINIPUL": 1, "ARN-POL": 1, "GAN-DOB": 0}
    piezas = [
        {"codigo": "HER-001", "condicion": "BUENO"},
        {"codigo": "ALT-005", "condicion": "DESGASTE"},
        {"codigo": "ALT-007", "condicion": "BUENO"},
    ]
    folio = siguiente_folio(session, "KEP", "DEV")
    dev1 = confirmar(kep, {"tipo": "DEVOLUCION", "renglones": piezas})
    assert dev1["folio"] == folio and re.fullmatch(r"KEP-DEV-\d{6}", folio)
    g.vales["dev_piezas"] = dev1
    g.movimientos_del_trabajador += 3
    sin_costos(dev1)
    d = kep.get(f"{VALES}/{dev1['id']}").json()
    assert d["tipo"] == "DEVOLUCION" and d["firma_modo"] == "SESION"  # F-08
    assert d["responsable"]["nombre"] == "Almacenista Kepler" and d["trabajador"]["id"] == tid
    assert [x["destino"]["clave"] for x in d["renglones"]] == ["KEP"] * 3
    assert cantidad_en(kep, kep_id, "MINIPUL") == 2
    assert cantidad_en(kep, kep_id, "ARN-POL") == 2 and cantidad_en(kep, kep_id, "GAN-DOB") == 1
    assert "Kepler" in ubicacion_de_pieza(kep, "HER-001")
    # Falta el respirador: el no adeudo sigue rechazado, ahora con un solo pendiente.
    r = kep.post(f"/api/trabajadores/{tid}/no-adeudo", json={"id_cliente": nuevo_cliente()})
    assert r.status_code == 409
    assert [p["codigo"] for p in r.json()["detalles"]["pendientes"]] == ["RESP-6200"]

    # --- Devolución por CANTIDAD, dañada: exige observación (V-05) y va a Baja, sin cargo ---
    resp = {"codigo": "RESP-6200", "cantidad": 1, "condicion": "DANADO"}
    sin_obs = evaluar(kep, {"tipo": "DEVOLUCION", "trabajador_id": tid, "renglones": [resp]})
    assert sin_obs["nivel"] == "ROJO" and "V-05" in reglas_de(sin_obs, 1)
    con_obs = {**resp, "observacion": "Mica rota y banda vencida"}
    ev = evaluar(kep, {"tipo": "DEVOLUCION", "trabajador_id": tid, "renglones": [con_obs]})
    assert ev["puede_confirmar"] is True and "V-05" in reglas_de(ev, 1)
    baja_antes = en_ubicacion_virtual(session, "BAJA", "RESP-6200")
    dev2 = confirmar(kep, {"tipo": "DEVOLUCION", "trabajador_id": tid, "renglones": [con_obs]})
    g.vales["dev_cantidad"] = dev2
    g.movimientos_del_trabajador += 1
    d = kep.get(f"{VALES}/{dev2['id']}").json()
    assert (
        d["renglones"][0]["condicion"] == "DANADO"
        and d["renglones"][0]["destino"]["tipo"] == "BAJA"
    )
    assert d["renglones"][0]["observacion"] == "Mica rota y banda vencida"
    assert cantidad_en(kep, kep_id, "RESP-6200") == 39  # lo dañado NO regresa a existencias
    assert en_ubicacion_virtual(session, "BAJA", "RESP-6200") == baja_antes + 1

    # --- Con todo en cero se emite el vale de no adeudo (B-04, B-08) ---
    folio = siguiente_folio(session, "KEP", "NAD")
    r = kep.post(f"/api/trabajadores/{tid}/no-adeudo", json=nad_cuerpo)
    assert r.status_code == 201, r.text
    nad = r.json()
    assert nad["folio"] == folio and re.fullmatch(r"KEP-NAD-\d{6}", folio)
    assert nad["renglones"] == [] and nad["trabajador"]["estado"] == "INACTIVO"
    g.vales["nad"] = nad
    # Reintento con el mismo id_cliente: el mismo vale, sin duplicar (RG-08).
    r = kep.post(f"/api/trabajadores/{tid}/no-adeudo", json=nad_cuerpo)
    assert r.status_code == 200 and r.json()["id"] == nad["id"]
    detalle = kep.get(f"{VALES}/{nad['id']}").json()
    assert detalle["tipo"] == "NO_ADEUDO" and detalle["renglones"] == []
    assert detalle["responsable"]["nombre"] == "Almacenista Kepler"
    sin_costos(detalle)
    # El trabajador queda Inactivo y RH ve «No adeudo emitido» (B-08, B-09).
    ficha = g.rh.get(f"/api/trabajadores/{tid}").json()
    assert ficha["estado"] == "INACTIVO" and ficha["situacion"] == "NO_ADEUDO_EMITIDO"
    assert buscar_trabajador_en_lista(g.rh, tid)["situacion"] == "NO_ADEUDO_EMITIDO"
    assert buscar_trabajador_en_lista(g.rh, tid, situacion="CON_PENDIENTES") is None
    adeudos = g.rh.get("/api/reportes/adeudos", params={"tamano": 200}).json()["elementos"]
    assert all(a["trabajador_id"] != tid for a in adeudos)
    # Inactivo: ya no se le entrega nada.
    ev = evaluar(
        kep,
        {
            "tipo": "ENTREGA",
            "trabajador_id": tid,
            "renglones": [{"codigo": "LENTE-CL", "cantidad": 1}],
        },
    )
    assert ev["nivel"] == "ROJO" and "E-02" in reglas_de(ev, 1)


# ================================== Cierre: invariantes y reportes contra lo operado


def cierre_invariantes_y_reportes(g: Guion) -> None:
    session, tid = g.session, g.trabajador["id"]
    verificar_invariantes(session, g.huella)  # los vales y movimientos no cambiaron (salvo estado)

    sup = g.sup
    # --- Movimientos: un renglón por cada movimiento del trabajador, sin costos ---
    r = sup.get("/api/reportes/movimientos", params={"trabajador_id": tid, "tamano": 200})
    assert r.status_code == 200
    filas = r.json()["elementos"]
    assert len(filas) == g.movimientos_del_trabajador == r.json()["total"]
    sin_costos(r.json())
    folios = {f["folio"] for f in filas}
    assert folios == {
        g.vales[k]["folio"]
        for k in (
            "entrega_1",
            "entrega_alturas",
            "entrega_pin",
            "entrega_remota",
            "dev_piezas",
            "dev_cantidad",
        )
    }
    assert all(f["responsable"] == "Almacenista Kepler" for f in filas)
    # El detector de la bitácora cuadra con el saldo de cada renglón.
    entrega = next(
        f
        for f in filas
        if f["folio"] == g.vales["entrega_1"]["folio"] and f["codigo_articulo"] == "GUANTE-CAR"
    )
    assert (entrega["saldo_origen"], entrega["destino"]) == (118, "Consumido")
    # Los traspasos cruzan almacenes: solo quien ve todos (Administrador) los ve juntos. El
    # supervisor de Kepler ve el que salió de su almacén y no el de Contratistas (AC-06).
    r = sup.get("/api/reportes/movimientos", params={"tipo": "TRASPASO", "tamano": 200})
    assert {f["folio"] for f in r.json()["elementos"]} == {g.vales["trs1"]["folio"]}
    r = g.admin.get("/api/reportes/movimientos", params={"tipo": "TRASPASO", "tamano": 200})
    assert {f["folio"] for f in r.json()["elementos"]} >= {
        g.vales["trs1"]["folio"],
        g.vales["trs2"]["folio"],
    }
    # --- Existencias: el reporte coincide con la consulta por almacén y con lo operado ---
    kep_id = g.almacen["KEP"]
    reporte = sup.get(
        "/api/reportes/existencias", params={"almacen_id": str(kep_id), "tamano": 200}
    ).json()["elementos"]
    por_codigo = {f["codigo"]: f for f in reporte}
    esperado = {
        "GUANTE-CAR": 115,
        "LENTE-CL": 199,
        "RESP-6200": 39,
        "CINCEL": 20,
        "MINIPUL": 2,
        "ARN-POL": 2,
        "GAN-DOB": 1,
        "ARN-KEV": 2,
    }
    for codigo, cantidad in esperado.items():
        assert por_codigo[codigo]["cantidad"] == cantidad, codigo
        assert cantidad_en(g.kep, kep_id, codigo) == cantidad, codigo
    assert por_codigo["ARN-KEV"]["disponible"] == 1  # ALT-002; ALT-003 no apta, ALT-001 se fue
    assert por_codigo["MINIPUL"]["disponible"] == 2
    sin_costos(reporte)
    # --- Consumo: los guantes y el lente del trabajador, y nada más suyo ---
    consumo = sup.get("/api/reportes/consumo", params={"trabajador_id": tid}).json()["elementos"]
    totales = {c["codigo"]: c["total"] for c in consumo}
    assert g.guantes_consumidos == 5
    assert totales == {"GUANTE-CAR": 5, "LENTE-CL": 1}
    guantes = next(c for c in consumo if c["codigo"] == "GUANTE-CAR")
    assert [(t["trabajador_id"], t["cantidad"]) for t in guantes["trabajadores"]] == [(tid, 5)]
    # --- Adeudos: ya no debe nada ---
    adeudos = g.admin.get("/api/reportes/adeudos", params={"tamano": 200}).json()["elementos"]
    assert all(a["trabajador_id"] != tid for a in adeudos)
    # --- CSV: mismos filtros, con BOM y sin costos ---
    csv = sup.get("/api/reportes/movimientos", params={"trabajador_id": tid, "formato": "csv"})
    assert csv.status_code == 200 and csv.headers["content-type"].startswith("text/csv")
    assert csv.content.startswith(b"\xef\xbb\xbf") and g.vales["entrega_1"]["folio"] in csv.text
    assert csv.text.count("\n") >= g.movimientos_del_trabajador + 1
    sin_costos({"csv": csv.text})


# ----------------------------------------------------------------------------- el guion


def test_guion_del_pdf_de_los_seis_pasos_de_punta_a_punta(
    cliente_como,
    cliente_almacen,  # noqa: F811
    cliente_almacenista,  # noqa: F811
    usuario_por_rol,
    session,
    app,
    crear_usuario,  # noqa: F811
):
    g = Guion(
        session=session,
        rh=cliente_como("Recursos Humanos"),
        sup=cliente_como("Supervisor"),
        admin=cliente_como("Administrador"),
        compras=cliente_como("Compras"),
        kep=cliente_almacenista("KEP"),  # entrega y devuelve; los traspasos son del supervisor
        con=cliente_almacen("CON"),  # sup_con: recibe en Contratistas y envía a Midrex
        mid=cliente_almacen("MID"),  # sup_mid: recibe en Midrex
        hyl=cliente_almacen("HYL"),
        pin_supervisor=usuario_por_rol("Supervisor").pin,
        almacen=ids_de_almacen(session),
    )
    paso_1_rh_registra_al_trabajador(g)
    paso_2_surtir_epp_y_herramienta_por_escaneo(g)
    paso_3_arnes_no_apto_o_vencido_no_se_entrega(g)
    paso_4_limite_excedido_requiere_autorizacion(g, app, crear_usuario)
    paso_5_traspasos_y_recepciones(g)
    paso_6_baja_pendientes_devolucion_y_no_adeudo(g)
    cierre_invariantes_y_reportes(g)
