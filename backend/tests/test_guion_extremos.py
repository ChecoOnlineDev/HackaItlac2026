"""Los escenarios más delicados de `docs/product/escenarios.md`, de punta a punta por la API.

Cada prueba lleva el ID del escenario (ES-05, ES-09...). Todo se opera por HTTP con sesiones
reales (RH registra a los trabajadores, Compras abastece, el almacenista opera); la base solo se
lee para comprobar y al final de cada prueba corre el verificador de invariantes. Usan las piezas
de los datos de prueba (`app/datos_prueba_piezas.py`).

Cuando un escenario necesita que «pase el tiempo» se simula SIN dormir: el reloj del servicio de
autorizaciones se adelanta con `monkeypatch` y el fin de un contrato se mueve en la base.
"""

import uuid
from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select, update

from app.config import get_settings
from app.core.tiempo import ahora_utc, hoy_mx
from app.modulos.acceso.datos_prueba import PERMISOS_INICIALES
from app.modulos.archivos.models import Adjunto
from app.modulos.trabajadores.models import PeriodoContrato
from tests.ayudas_guion import (
    FIRMA,
    alta_trabajador,
    cantidad_en,
    confirmar,
    en_ubicacion_virtual,
    entregar,
    evaluar,
    ids_de_almacen,
    nuevo_cliente,
    pieza_id,
    reglas_de,
    sin_costos,
    ubicacion_de_pieza,
)
from tests.conftest import iniciar_sesion_en
from tests.invariantes import verificar_invariantes
from tests.movimientos.ayudas import PNG_B64
from tests.movimientos.ayudas_traspasos import (  # noqa: F401  (fixtures)
    cliente_almacen,
    cliente_almacenista,
)

VALES = "/api/vales"
AUT = "/api/autorizaciones"


@pytest.fixture(autouse=True)
def _archivos_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "archivos_dir", tmp_path)


@pytest.fixture
def mundo(cliente_como, cliente_almacen, cliente_almacenista, session):  # noqa: F811
    """Los clientes de cada rol y almacén, y los ids de los almacenes.

    `kep`, `con`, `mid` y `hyl` son los ALMACENISTAS (entregan y devuelven); `sup_kep`, `sup_con`,
    `sup_mid` y `sup_hyl` los supervisores de cada almacén, que son quienes operan traspasos.
    """
    return SimpleNamespace(
        session=session,
        rh=cliente_como("Recursos Humanos"),
        sup=cliente_como("Supervisor"),
        compras=cliente_como("Compras"),
        admin=cliente_como("Administrador"),
        kep=cliente_almacenista("KEP"),
        con=cliente_almacenista("CON"),
        mid=cliente_almacenista("MID"),
        hyl=cliente_almacenista("HYL"),
        sup_kep=cliente_almacen("KEP"),
        sup_con=cliente_almacen("CON"),
        sup_mid=cliente_almacen("MID"),
        sup_hyl=cliente_almacen("HYL"),
        almacen=ids_de_almacen(session),
    )


def _solicitud(evaluacion: dict, trabajador_id: str, motivo: str) -> dict:
    return {
        "trabajador_id": trabajador_id,
        "motivo": motivo,
        "renglones": [
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
        ],
    }


def _articulo_sin_limite(m, codigo: str, nombre: str, existencias: int) -> None:
    """Un consumible sin límite, creado y abastecido por la API (Compras)."""
    categorias = m.compras.get("/api/categorias", params={"tamano": 100}).json()["elementos"]
    categoria = next(c for c in categorias if c["nombre"] == "EPP de dotación")
    r = m.compras.post(
        "/api/articulos",
        json={
            "codigo": codigo,
            "nombre": nombre,
            "categoria_id": categoria["id"],
            "limite_cantidad": None,
            "limite_periodo_dias": None,
        },
    )
    assert r.status_code == 201, r.text
    confirmar(
        m.compras,
        {"tipo": "ENTRADA", "renglones": [{"codigo": codigo, "cantidad": existencias}]},
    )


# ============================================================================== ES-05


def test_ES_05_el_cuarto_par_de_guantes_de_la_semana_pide_autorizacion_y_vence_a_los_15_minutos(
    mundo, monkeypatch
):
    m = mundo
    kep_id = m.almacen["KEP"]
    juan = alta_trabajador(m.rh, nombre="Juan Pérez")
    entregar(m.kep, juan["id"], [{"codigo": "GUANTE-CAR", "cantidad": 3}])  # el límite: 3 en 7 días
    cuerpo = {
        "tipo": "ENTREGA",
        "trabajador_id": juan["id"],
        "renglones": [{"codigo": "GUANTE-CAR"}, {"codigo": "LENTE-CL"}],
    }
    ev = evaluar(m.kep, cuerpo)
    # 1. El renglón de los guantes queda naranja con el detalle; el lente va verde.
    guantes = ev["renglones"][0]
    assert ev["nivel"] == "NARANJA" and ev["puede_confirmar"] is False
    assert reglas_de(ev, 1) == ["L-03"] and reglas_de(ev, 2) == []
    assert "límite 3, tiene 3 en los últimos 7 días, pide 1" in guantes["motivos"][0]["mensaje"]
    assert guantes["autorizable"] is True

    # 2. Marta escribe el motivo y envía la solicitud. 3. El supervisor la ve y autoriza.
    aut = m.kep.post(AUT, json=_solicitud(ev, juan["id"], "Se le llenaron de grasa")).json()["id"]
    assert m.sup.post(f"{AUT}/{aut}/resolucion", json={"decision": "APROBAR"}).status_code == 200
    vale = entregar(m.kep, juan["id"], cuerpo["renglones"], autorizacion_id=aut)
    # 4. El vale guarda quién autorizó y por qué (A-04); el excedente es solo el renglón naranja.
    detalle = m.kep.get(f"{VALES}/{vale['id']}").json()
    assert detalle["valido"]["autorizo"]["nombre"] == "Supervisor Kepler"
    assert detalle["valido"]["motivo"] == "Se le llenaron de grasa"
    assert [r["nivel"] for r in detalle["renglones"]] == ["NARANJA", "VERDE"]
    assert cantidad_en(m.kep, kep_id, "GUANTE-CAR") == 120 - 4

    # Si nadie responde en quince minutos la solicitud vence (A-07, ES-05): se quita el renglón
    # y se entrega lo demás.
    ev2 = evaluar(m.kep, cuerpo)
    pendiente = m.kep.post(AUT, json=_solicitud(ev2, juan["id"], "Otra vez")).json()["id"]
    en_16_minutos = ahora_utc() + timedelta(minutes=16)
    monkeypatch.setattr("app.modulos.autorizaciones.service.ahora_utc", lambda: en_16_minutos)
    assert m.kep.get(f"{AUT}/{pendiente}").json()["estado"] == "VENCIDA"
    r = m.sup.post(f"{AUT}/{pendiente}/resolucion", json={"decision": "APROBAR"})
    assert r.status_code == 409 and r.json()["codigo"] == "AUTORIZACION_RESUELTA"
    monkeypatch.undo()
    sin_el_excedente = entregar(m.kep, juan["id"], [{"codigo": "LENTE-CL"}])
    assert sin_el_excedente["renglones"][0]["nivel"] == "VERDE"
    assert cantidad_en(m.kep, kep_id, "GUANTE-CAR") == 120 - 4
    verificar_invariantes(m.session)


# ============================================================================== ES-09


def test_ES_09_con_el_contrato_vencido_no_se_entrega_pero_si_se_recibe_lo_que_trae(mundo):
    m = mundo
    session = m.session
    pedro = alta_trabajador(m.rh, nombre="Pedro de otra contratista", fin_dias=30)
    entregar(m.kep, pedro["id"], [{"codigo": "HER-002"}, {"codigo": "RESP-6200"}])
    assert m.kep.get(f"/api/escaneo/{pedro['credencial']}").json()["resumen"]["vigente"] is True

    # «Pasa el tiempo»: el contrato terminó el viernes (se mueve el fin del periodo en la base).
    ayer = hoy_mx() - timedelta(days=1)
    session.execute(
        update(PeriodoContrato)
        .where(PeriodoContrato.trabajador_id == uuid.UUID(pedro["id"]))
        .values(fin=ayer)
    )
    # 1. La ficha sale no vigente, con el motivo y la fecha en que terminó.
    resumen = m.kep.get(f"/api/escaneo/{pedro['credencial']}").json()["resumen"]
    assert resumen["vigente"] is False and "plantilla" in resumen["motivo_no_vigente"]
    assert resumen["vigente_hasta"] == str(ayer)
    # 2. No se le puede agregar ningún artículo: todo el vale en rojo por E-02 (SM-05).
    cuerpo = {
        "tipo": "ENTREGA",
        "trabajador_id": pedro["id"],
        "renglones": [{"codigo": "LENTE-CL"}, {"codigo": "HER-001"}],
    }
    ev = evaluar(m.kep, cuerpo)
    assert ev["nivel"] == "ROJO" and ev["puede_confirmar"] is False
    assert [r["nivel"] for r in ev["renglones"]] == ["ROJO", "ROJO"]
    assert all("E-02" in reglas_de(ev, i) for i in (1, 2))
    r = m.kep.post(VALES, json={**cuerpo, "id_cliente": nuevo_cliente(), "firma": FIRMA})
    assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO"
    assert cantidad_en(m.kep, m.almacen["KEP"], "LENTE-CL") == 200
    # 3. Si trae algo que devolver, SÍ se le recibe (SM-05).
    ev = evaluar(
        m.kep, {"tipo": "DEVOLUCION", "renglones": [{"codigo": "HER-002", "condicion": "BUENO"}]}
    )
    assert ev["puede_confirmar"] is True and "E-02" not in reglas_de(ev, 1)
    confirmar(
        m.kep, {"tipo": "DEVOLUCION", "renglones": [{"codigo": "HER-002", "condicion": "BUENO"}]}
    )
    confirmar(
        m.kep,
        {
            "tipo": "DEVOLUCION",
            "trabajador_id": pedro["id"],
            "renglones": [{"codigo": "RESP-6200", "cantidad": 1, "condicion": "BUENO"}],
        },
    )
    ficha = m.rh.get(f"/api/trabajadores/{pedro['id']}").json()
    assert ficha["resguardo"] == [] and ficha["pendientes"]["total"] == 0
    assert cantidad_en(m.kep, m.almacen["KEP"], "MINIPUL") == 2
    verificar_invariantes(m.session)


# ============================================================================== ES-10


def test_ES_10_el_reintento_tras_una_caida_no_duplica_el_vale(mundo, usuario_por_rol):
    m = mundo
    kep_id = m.almacen["KEP"]
    juan = alta_trabajador(m.rh)
    cuerpo = {
        "tipo": "ENTREGA",
        "trabajador_id": juan["id"],
        "id_cliente": nuevo_cliente(),
        "firma": FIRMA,
        "renglones": [
            {"codigo": "LENTE-CL", "cantidad": 2},
            {"codigo": "HER-001"},
            {"codigo": "RESP-6200"},
            {"codigo": "CINCEL"},
            {"codigo": "FLEXOM"},
        ],
    }
    total_vales = m.kep.get(VALES, params={"tamano": 1}).json()["total"]
    # El primer intento sí llegó al servidor (aunque el celular no vio la respuesta)...
    primero = m.kep.post(VALES, json=cuerpo)
    assert primero.status_code == 201, primero.text
    # ...«Reintentar»: mismo id_cliente, misma respuesta, sin duplicar nada (RG-08, RG-09).
    segundo = m.kep.post(VALES, json=cuerpo)
    assert segundo.status_code == 200 and segundo.json() == primero.json()
    assert m.kep.get(VALES, params={"tamano": 1}).json()["total"] == total_vales + 1
    assert cantidad_en(m.kep, kep_id, "LENTE-CL") == 198
    assert cantidad_en(m.kep, kep_id, "MINIPUL") == 1  # la pieza salió una sola vez
    ficha = m.kep.get(f"/api/trabajadores/{juan['id']}").json()
    assert {x["codigo"] for x in ficha["resguardo"]} == {"HER-001", "RESP-6200", "CINCEL", "FLEXOM"}
    # El mismo id_cliente de otra persona es un conflicto (409), no el vale de otro.
    otro = m.sup.post(VALES, json=cuerpo | {"almacen_id": str(kep_id)})
    assert otro.status_code == 409 and otro.json()["codigo"] == "CONFLICTO"
    assert usuario_por_rol("Supervisor").usuario == "supervisor"
    verificar_invariantes(m.session)


# ============================================================================== ES-11


def test_ES_11_diez_pares_en_lugar_de_uno_se_cancela_y_se_rehace(mundo):
    m = mundo
    kep_id = m.almacen["KEP"]
    _articulo_sin_limite(m, "GUANTE-NIT", "Guantes de nitrilo", 50)
    juan = alta_trabajador(m.rh, nombre="Juan")
    equivocado = entregar(m.kep, juan["id"], [{"codigo": "GUANTE-NIT", "cantidad": 10}])
    assert cantidad_en(m.kep, kep_id, "GUANTE-NIT") == 40
    assert en_ubicacion_virtual(m.session, "CONSUMIDO", "GUANTE-NIT") == 10
    consumo = m.sup.get("/api/reportes/consumo", params={"trabajador_id": juan["id"]}).json()
    assert [(c["codigo"], c["total"]) for c in consumo["elementos"]] == [("GUANTE-NIT", 10)]

    # Se abre el vale y se cancela, con motivo, pidiendo rehacer (K-01, K-05).
    sin_motivo = m.kep.post(
        f"{VALES}/{equivocado['id']}/cancelacion",
        json={"motivo": "", "id_cliente": nuevo_cliente()},
    )
    assert sin_motivo.status_code == 422
    r = m.kep.post(
        f"{VALES}/{equivocado['id']}/cancelacion",
        json={"motivo": "error de captura", "id_cliente": nuevo_cliente(), "rehacer": True},
    )
    assert r.status_code == 201, r.text
    cancelacion = r.json()
    assert (
        cancelacion["folio"].startswith("KEP-CAN-") and cancelacion["motivo"] == "error de captura"
    )
    assert cancelacion["vale_cancelado"] == {
        "id": equivocado["id"],
        "folio": equivocado["folio"],
        "estado": "CANCELADO",
    }
    # Los diez pares regresan a existencias y el consumo de Juan vuelve a como estaba (K-02).
    assert cantidad_en(m.kep, kep_id, "GUANTE-NIT") == 50
    assert en_ubicacion_virtual(m.session, "CONSUMIDO", "GUANTE-NIT") == 0
    consumo = m.sup.get("/api/reportes/consumo", params={"trabajador_id": juan["id"]}).json()
    assert consumo["elementos"] == [] and consumo["sin_registros"] is True
    original = m.kep.get(f"{VALES}/{equivocado['id']}").json()
    assert (
        original["estado"] == "CANCELADO"
        and original["cancelacion"]["folio"] == cancelacion["folio"]
    )
    # No se cancela dos veces (K-03).
    r = m.kep.post(
        f"{VALES}/{equivocado['id']}/cancelacion",
        json={"motivo": "otra vez", "id_cliente": nuevo_cliente()},
    )
    assert r.status_code == 409 and r.json()["codigo"] == "NO_CANCELABLE"

    # «Cancelar y rehacer»: el borrador trae los mismos renglones; solo se corrige la cantidad.
    borrador = cancelacion["borrador"]
    assert borrador["tipo"] == "ENTREGA" and borrador["trabajador_id"] == juan["id"]
    assert [(r["codigo"], r["cantidad"]) for r in borrador["renglones"]] == [("GUANTE-NIT", 10)]
    assert "firma" not in borrador and "autorizacion_id" not in borrador  # K-05
    renglones = [{**borrador["renglones"][0], "cantidad": 1}]
    correcto = confirmar(
        m.kep,
        {
            "tipo": "ENTREGA",
            "trabajador_id": borrador["trabajador_id"],
            "renglones": renglones,
            "firma": FIRMA,
        },
    )
    assert cantidad_en(m.kep, kep_id, "GUANTE-NIT") == 49
    consumo = m.sup.get("/api/reportes/consumo", params={"trabajador_id": juan["id"]}).json()
    assert [(c["codigo"], c["total"]) for c in consumo["elementos"]] == [("GUANTE-NIT", 1)]
    # Los tres vales quedan en el historial (RG-02) y en «Mis movimientos de hoy» (C-12).
    yo = m.kep.get("/api/sesion").json()["usuario"]["id"]
    hoy = str(hoy_mx())
    mios = m.kep.get(VALES, params={"usuario_id": yo, "desde": hoy, "hasta": hoy, "tamano": 100})
    folios = {v["folio"] for v in mios.json()["elementos"]}
    assert {equivocado["folio"], cancelacion["folio"], correcto["folio"]} <= folios
    sin_costos(cancelacion)
    verificar_invariantes(m.session)


# ============================================================================== ES-12


def test_ES_12_dos_almacenistas_del_mismo_almacen_con_su_propia_cuenta(mundo, app, crear_usuario):
    m = mundo
    from fastapi.testclient import TestClient

    raul = crear_usuario(PERMISOS_INICIALES["Almacenista"], almacen="KEP")
    noche = TestClient(app)
    assert iniciar_sesion_en(noche, raul).status_code == 200
    juan = alta_trabajador(m.rh, nombre="Juan")
    # Marta cubre el día; Raúl, la noche. Cada vale lleva a quien lo hizo (RG-03, RG-07).
    de_marta = entregar(m.kep, juan["id"], [{"codigo": "LENTE-CL"}])
    de_raul = entregar(noche, juan["id"], [{"codigo": "CACHUCHA"}])
    ids = {
        "marta": m.kep.get("/api/sesion").json()["usuario"],
        "raul": noche.get("/api/sesion").json()["usuario"],
    }
    assert ids["marta"]["usuario"] == "almacenista" and ids["raul"]["usuario"] == raul.usuario
    assert m.kep.get(f"{VALES}/{de_marta['id']}").json()["responsable"]["id"] == ids["marta"]["id"]
    assert m.kep.get(f"{VALES}/{de_raul['id']}").json()["responsable"]["id"] == ids["raul"]["id"]
    # Los dos ven los vales del almacén; ninguno puede cancelar el del otro (K-01).
    assert noche.get(f"{VALES}/{de_marta['id']}").status_code == 200
    r = noche.post(
        f"{VALES}/{de_marta['id']}/cancelacion",
        json={"motivo": "no es mío", "id_cliente": nuevo_cliente()},
    )
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"
    # El reporte de movimientos, filtrado por almacén, fechas y usuario, dice qué hizo cada uno
    # (C-11).
    hoy = str(hoy_mx())
    for quien, vale, otro in (("marta", de_marta, de_raul), ("raul", de_raul, de_marta)):
        r = m.sup.get(
            "/api/reportes/movimientos",
            params={
                "usuario_id": ids[quien]["id"],
                "almacen_id": str(m.almacen["KEP"]),
                "desde": hoy,
                "hasta": hoy,
                "tamano": 100,
            },
        )
        folios = {f["folio"] for f in r.json()["elementos"]}
        assert vale["folio"] in folios and otro["folio"] not in folios
    # El filtro «quién lo hizo» ofrece a los dos de Kepler; el de Midrex ve solo a los suyos.
    # (el almacenista no tiene reportes: lo consultan los supervisores de cada almacén)
    kepler = {u["usuario"] for u in m.sup_kep.get("/api/reportes/usuarios").json()["elementos"]}
    assert {"almacenista", raul.usuario} <= kepler and "alm_mid" not in kepler
    # Nadie ha hecho vales en Midrex: su almacenista no ve a los de Kepler (AC-06).
    midrex = {u["usuario"] for u in m.sup_mid.get("/api/reportes/usuarios").json()["elementos"]}
    assert midrex == set()
    todos = {u["usuario"] for u in m.admin.get("/api/reportes/usuarios").json()["elementos"]}
    assert {"almacenista", raul.usuario} <= todos
    noche.close()
    verificar_invariantes(m.session)


# ============================================================================== ES-13


def test_ES_13_quien_tiene_el_detector_busqueda_y_ficha_de_pieza(mundo):
    m = mundo
    pedro = alta_trabajador(m.rh, nombre="Pedro Torres")
    entregar(m.kep, pedro["id"], [{"codigo": "HER-003"}])  # un detector con Pedro
    # El otro detector se aparta como No apto (P-03).
    r = m.kep.post(
        f"/api/piezas/{pieza_id(m.kep, 'HER-004')}/estado",
        json={"estado": "NO_APTO", "observacion": "Sensor sin respuesta"},
    )
    assert r.status_code == 200, r.text

    # Escribe «detector» en la búsqueda y ve cada uno con su serie y dónde está (C-03, C-06).
    r = m.sup.get("/api/busqueda", params={"q": "detector"})
    piezas = {p["codigo"]: p for p in r.json()["piezas"]["elementos"]}
    assert {"HER-003", "HER-004"} <= set(piezas)
    assert piezas["HER-003"]["numero_serie"] == "SN-DET-0001"
    assert (
        "Pedro Torres" in piezas["HER-003"]["ubicacion"] and piezas["HER-003"]["estado"] == "APTO"
    )
    assert "Kepler" in piezas["HER-004"]["ubicacion"] and piezas["HER-004"]["estado"] == "NO_APTO"
    assert any(a["codigo"] == "DET-GAS" for a in r.json()["articulos"]["elementos"])
    # La ficha de la pieza trae su titular y su historial completo (C-02).
    ficha = m.sup.get(f"/api/piezas/{piezas['HER-003']['id']}").json()
    assert (
        ficha["ubicacion"]["tipo"] == "TRABAJADOR"
        and ficha["ubicacion"]["trabajador_id"] == pedro["id"]
    )
    assert [h["titulo"] for h in ficha["historial"]][:2] == ["Entrega", "Entrada"]
    # La ficha del artículo dice quién lo tiene y cuántos hay en cada almacén (C-03).
    articulo_id = piezas["HER-003"]["articulo_id"]
    art = m.sup.get(f"/api/articulos/{articulo_id}").json()
    assert [
        (x["trabajador"] if "trabajador" in x else x.get("nombre")) for x in art["en_posesion"]
    ] == ["Pedro Torres"]
    # Si Juan lo devuelve sin pasar por Pedro, se abona a Pedro (V-01): el titular sigue siendo él.
    dev = confirmar(
        m.kep, {"tipo": "DEVOLUCION", "renglones": [{"codigo": "HER-003", "condicion": "BUENO"}]}
    )
    detalle = m.kep.get(f"{VALES}/{dev['id']}").json()
    assert detalle["trabajador"]["id"] == pedro["id"]
    assert "Kepler" in ubicacion_de_pieza(m.kep, "HER-003")
    verificar_invariantes(m.session)


# ============================================================================== ES-14


def test_ES_14_devolver_un_detector_que_no_es_de_la_empresa_no_se_recibe(mundo):
    m = mundo
    pedro = alta_trabajador(m.rh, nombre="Pedro Torres")
    entregar(m.kep, pedro["id"], [{"codigo": "HER-003"}])
    ajeno = {
        "tipo": "DEVOLUCION",
        "trabajador_id": pedro["id"],
        "renglones": [{"codigo": "DET-DE-OTRA-COMPANIA-77", "condicion": "BUENO"}],
    }
    # 1. El código no existe: rojo «No es de la empresa». No se recibe.
    ev = evaluar(m.kep, ajeno)
    assert ev["nivel"] == "ROJO" and ev["puede_confirmar"] is False
    assert (
        reglas_de(ev, 1) == ["V-12"]
        and "No es de la empresa" in ev["renglones"][0]["motivos"][0]["mensaje"]
    )
    r = m.kep.post(VALES, json={**ajeno, "id_cliente": nuevo_cliente()})
    assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO"
    # El código del ARTÍCULO por pieza tampoco sirve: hay que escanear la pieza (V-14).
    por_articulo = ajeno | {"renglones": [{"codigo": "DET-GAS", "condicion": "BUENO"}]}
    assert reglas_de(evaluar(m.kep, por_articulo), 1) == ["V-14"]
    # 2. Para comparar la serie grabada, la pantalla muestra la del detector que tiene Pedro.
    propio = evaluar(m.kep, ajeno | {"renglones": [{"codigo": "HER-003", "condicion": "BUENO"}]})
    assert propio["renglones"][0]["pieza"]["numero_serie"] == "SN-DET-0001"
    # 3. El detector de Pedro sigue pendiente a su nombre.
    ficha = m.kep.get(f"/api/trabajadores/{pedro['id']}").json()
    assert [x["codigo"] for x in ficha["resguardo"]] == ["HER-003"]
    assert ficha["pendientes"]["total"] == 1
    assert "Pedro" in ubicacion_de_pieza(m.kep, "HER-003")
    verificar_invariantes(m.session)


# ============================================================================== ES-15


def test_ES_15_el_minipulidor_regresa_danado_entra_no_apto_y_sin_cargo(mundo):
    m = mundo
    juan = alta_trabajador(m.rh, nombre="Juan")
    entregar(m.kep, juan["id"], [{"codigo": "HER-001"}])
    danado = {"codigo": "HER-001", "condicion": "DANADO"}
    # 1. «Dañado» pide una observación (V-05)...
    ev = evaluar(m.kep, {"tipo": "DEVOLUCION", "renglones": [danado]})
    assert ev["nivel"] == "ROJO" and ev["renglones"][0]["pide_observacion"] is True
    assert "V-05" in reglas_de(ev, 1)
    # ...y deja tomar una foto (adjunto FOTO_DANO).
    con_obs = danado | {"observacion": "Cable pelado", "foto": f"data:image/png;base64,{PNG_B64}"}
    ev = evaluar(m.kep, {"tipo": "DEVOLUCION", "renglones": [con_obs]})
    assert ev["puede_confirmar"] is True and ev["nivel"] == "AMARILLO"
    dev = confirmar(m.kep, {"tipo": "DEVOLUCION", "renglones": [con_obs]})
    fotos = m.session.scalars(select(Adjunto).where(Adjunto.tipo == "FOTO_DANO")).all()
    assert len(fotos) == 1 and fotos[0].vale_id is not None
    sin_costos(dev)
    # 2. Entra al almacén como No apto: ya no se puede entregar.
    pieza = m.kep.get(f"/api/piezas/{pieza_id(m.kep, 'HER-001')}").json()
    assert pieza["estado"] == "NO_APTO" and "Kepler" in pieza["ubicacion"]["texto"]
    assert cantidad_en(m.kep, m.almacen["KEP"], "MINIPUL") == 2  # sigue contando en el almacén
    ev = evaluar(
        m.kep,
        {"tipo": "ENTREGA", "trabajador_id": juan["id"], "renglones": [{"codigo": "HER-001"}]},
    )
    assert ev["nivel"] == "ROJO" and "E-05" in reglas_de(ev, 1)
    # 3. A Juan no se le carga nada: queda sin pendientes y la observación en el historial.
    ficha = m.rh.get(f"/api/trabajadores/{juan['id']}").json()
    assert ficha["resguardo"] == [] and ficha["situacion"] == "SIN_PENDIENTES"
    historial = m.kep.get(f"/api/piezas/{pieza['id']}").json()["historial"]
    assert any(h["tipo"] == "MOVIMIENTO" and h["condicion"] == "DANADO" for h in historial)
    assert any(
        h["tipo"] == "CAMBIO_ESTADO"
        and h["estado_nuevo"] == "NO_APTO"
        and "Cable pelado" in h["observacion"]
        and dev["folio"] in h["observacion"]
        for h in historial
    )
    # 4. De regreso de reparación, una inspección Apto la vuelve a poner disponible (P-03).
    r = m.kep.post(
        f"/api/piezas/{pieza['id']}/inspecciones",
        json={"resultado": "APTO", "observacion": "Reparada"},
    )
    assert r.status_code == 201 and r.json()["pieza"]["estado"] == "APTO"
    ev = evaluar(
        m.kep,
        {"tipo": "ENTREGA", "trabajador_id": juan["id"], "renglones": [{"codigo": "HER-001"}]},
    )
    assert ev["nivel"] == "VERDE" and ev["puede_confirmar"] is True
    verificar_invariantes(m.session)


# ============================================================================== ES-19


def test_ES_19_baja_en_kepler_con_un_arnes_pendiente_en_midrex(mundo):
    m = mundo
    # El arnés llega a Midrex (ruta inusual: solo el Administrador, con observación; X-03).
    trs = confirmar(
        m.admin,  # Kepler -> Midrex no es padre-hijo: solo el Administrador, con observación (X-03)
        {
            "tipo": "TRASPASO",
            "almacen_id": str(m.almacen["KEP"]),
            "observacion": "Ruta fuera de lo habitual",
            "destino_almacen_id": str(m.almacen["MID"]),
            "renglones": [{"codigo": "ALT-004"}],
        },
    )
    confirmar(
        m.sup_mid,
        {"tipo": "RECEPCION", "vale_origen_id": trs["id"], "renglones": [{"codigo": "ALT-004"}]},
    )
    juan = alta_trabajador(m.rh, nombre="Juan")
    # Juan recibió casco y respirador en Kepler y el arnés en Midrex.
    entregar(m.kep, juan["id"], [{"codigo": "CACHUCHA"}, {"codigo": "RESP-6200"}])
    entregar(m.mid, juan["id"], [{"codigo": "ALT-004"}])

    # 1. Oscar abre su ficha y pide el vale de no adeudo: Juan pasa a Baja en proceso.
    r = m.kep.post(
        f"/api/trabajadores/{juan['id']}/no-adeudo", json={"id_cliente": nuevo_cliente()}
    )
    assert r.status_code == 409 and r.json()["codigo"] == "CON_PENDIENTES"
    assert m.kep.get(f"/api/trabajadores/{juan['id']}").json()["estado"] == "BAJA_EN_PROCESO"
    # 2. La lista muestra los pendientes de TODOS los almacenes (el casco es consumible: no cuenta).
    pendientes = {p["codigo"]: p["almacen_clave"] for p in r.json()["detalles"]["pendientes"]}
    assert pendientes == {"RESP-6200": "KEP", "ALT-004": "MID"}
    # 3. Oscar recibe el respirador. El arnés lo recibe ahí mismo si Juan lo trae, con el aviso de
    # que entra a Kepler (V-07).
    confirmar(
        m.kep,
        {
            "tipo": "DEVOLUCION",
            "trabajador_id": juan["id"],
            "renglones": [{"codigo": "RESP-6200", "cantidad": 1, "condicion": "BUENO"}],
        },
    )
    r = m.kep.post(
        f"/api/trabajadores/{juan['id']}/no-adeudo", json={"id_cliente": nuevo_cliente()}
    )
    assert [p["codigo"] for p in r.json()["detalles"]["pendientes"]] == ["ALT-004"]
    ev = evaluar(
        m.kep, {"tipo": "DEVOLUCION", "renglones": [{"codigo": "ALT-004", "condicion": "BUENO"}]}
    )
    assert ev["puede_confirmar"] is True and "V-07" in reglas_de(ev, 1)
    assert ev["renglones"][0]["nivel"] == "AMARILLO"
    confirmar(
        m.kep, {"tipo": "DEVOLUCION", "renglones": [{"codigo": "ALT-004", "condicion": "BUENO"}]}
    )
    assert "Kepler" in ubicacion_de_pieza(m.kep, "ALT-004")  # entró a Kepler, no a Midrex
    assert cantidad_en(m.mid, m.almacen["MID"], "ARN-POL") == 0
    # 4. Con todo en cero se emite el vale y Juan queda inactivo; Ana (RH) ve «No adeudo emitido».
    r = m.kep.post(
        f"/api/trabajadores/{juan['id']}/no-adeudo", json={"id_cliente": nuevo_cliente()}
    )
    assert r.status_code == 201 and r.json()["trabajador"]["estado"] == "INACTIVO"
    assert m.rh.get(f"/api/trabajadores/{juan['id']}").json()["situacion"] == "NO_ADEUDO_EMITIDO"
    verificar_invariantes(m.session)


# ============================================================================== ES-26


def test_ES_26_el_reporte_de_consumo_total_y_desglose_por_trabajador(mundo):
    m = mundo
    kep_id = m.almacen["KEP"]
    consumos = {"Luis": 3, "Ana": 2, "Rosa": 1}
    trabajadores = {}
    for nombre, pares in consumos.items():
        trabajadores[nombre] = alta_trabajador(m.rh, nombre=nombre)
        entregar(m.kep, trabajadores[nombre]["id"], [{"codigo": "GUANTE-CAR", "cantidad": pares}])
    assert cantidad_en(m.kep, kep_id, "GUANTE-CAR") == 120 - 6
    hoy = str(hoy_mx())
    # Filtra por el artículo y el periodo: el total y quiénes más consumieron, de mayor a menor.
    r = m.sup.get("/api/reportes/consumo", params={"desde": hoy, "hasta": hoy})
    guantes = next(c for c in r.json()["elementos"] if c["codigo"] == "GUANTE-CAR")
    assert guantes["total"] == 6 and guantes["unidad"] == "par"
    assert [(t["trabajador"], t["cantidad"]) for t in guantes["trabajadores"]] == [
        ("Luis", 3),
        ("Ana", 2),
        ("Rosa", 1),
    ]
    # Por trabajador, por almacén, por artículo, por periodo.
    por_ana = m.sup.get(
        "/api/reportes/consumo", params={"trabajador_id": trabajadores["Ana"]["id"]}
    )
    assert [(c["codigo"], c["total"]) for c in por_ana.json()["elementos"]] == [("GUANTE-CAR", 2)]
    otro_almacen = m.sup.get("/api/reportes/consumo", params={"almacen_id": str(m.almacen["CON"])})
    assert otro_almacen.json()["elementos"] == []
    assert otro_almacen.json()["mensaje"] == "No hay registros con esos filtros."
    manana = str(hoy_mx() + timedelta(days=1))
    assert (
        m.sup.get("/api/reportes/consumo", params={"desde": manana}).json()["sin_registros"] is True
    )
    rango_malo = m.sup.get("/api/reportes/consumo", params={"desde": manana, "hasta": hoy})
    assert rango_malo.status_code == 422 and rango_malo.json()["codigo"] == "DATOS_INVALIDOS"
    # El almacenista no tiene este reporte; Compras sí, y tampoco ve costos aquí (RG-12).
    assert m.kep.get("/api/reportes/consumo").status_code == 403
    de_compras = m.compras.get("/api/reportes/consumo", params={"tamano": 100})
    assert de_compras.status_code == 200
    sin_costos(de_compras.json())
    # Para el detalle, la bitácora muestra cada entrega: a quién, dónde y quién la hizo.
    r = m.sup.get("/api/reportes/movimientos", params={"tipo": "ENTREGA", "tamano": 100})
    filas = [f for f in r.json()["elementos"] if f["codigo_articulo"] == "GUANTE-CAR"]
    assert sorted((f["trabajador"], f["cantidad"], f["responsable"]) for f in filas) == [
        (f"{t['nombre']} ({t['numero_empleado']})", pares, "Almacenista Kepler")
        for t, pares in sorted(
            ((trabajadores[n], p) for n, p in consumos.items()), key=lambda x: x[0]["nombre"]
        )
    ]
    # CSV del consumo: un renglón por artículo y trabajador.
    csv = m.sup.get("/api/reportes/consumo", params={"formato": "csv"})
    assert csv.status_code == 200 and csv.content.startswith(b"\xef\xbb\xbf")
    assert csv.text.count("Luis") == 1 and csv.text.count("Rosa") == 1
    verificar_invariantes(m.session)


# ============================================================================== ES-28


def test_ES_28_rastreo_por_usuario_en_la_bitacora_y_alcance_del_almacen(mundo):
    m = mundo
    # El detector llega a Midrex (Kepler -> Midrex) y alguien de Midrex lo entrega.
    trs = confirmar(
        m.admin,  # Kepler -> Midrex no es padre-hijo: solo el Administrador, con observación (X-03)
        {
            "tipo": "TRASPASO",
            "almacen_id": str(m.almacen["KEP"]),
            "observacion": "Ruta fuera de lo habitual",
            "destino_almacen_id": str(m.almacen["MID"]),
            "renglones": [{"codigo": "HER-004"}, {"codigo": "CINCEL", "cantidad": 2}],
        },
    )
    rec = confirmar(
        m.sup_mid,
        {
            "tipo": "RECEPCION",
            "vale_origen_id": trs["id"],
            "renglones": [{"codigo": "HER-004"}, {"codigo": "CINCEL", "cantidad": 2}],
        },
    )
    luis = alta_trabajador(m.rh, nombre="Luis")
    entrega = entregar(m.mid, luis["id"], [{"codigo": "HER-004"}, {"codigo": "CINCEL"}])
    mid_user = m.mid.get("/api/sesion").json()["usuario"]
    articulo = m.mid.get("/api/busqueda", params={"q": "HER-004"}).json()["piezas"]["elementos"][0]

    # Quien ve todos los almacenes (el Administrador) filtra por el artículo: cada vale que movió
    # el detector, con su responsable (C-11).
    r = m.admin.get(
        "/api/reportes/movimientos", params={"articulo_id": articulo["articulo_id"], "tamano": 100}
    )
    de_la_pieza = [f for f in r.json()["elementos"] if f["pieza"] == "HER-004"]
    assert [f["folio"] for f in de_la_pieza][:3] == [entrega["folio"], rec["folio"], trs["folio"]]
    assert [f["responsable"] for f in de_la_pieza][:3] == [
        "Almacenista Midrex",
        "Supervisor Midrex",
        "Administrador de prueba",  # Kepler -> Midrex lo hizo el Administrador (X-03)
    ]
    # En la ficha de la pieza está su historial completo.
    ficha = m.admin.get(f"/api/piezas/{articulo['id']}").json()
    assert "Luis" in ficha["ubicacion"]["texto"]
    assert [h["folio"] for h in ficha["historial"] if h["tipo"] == "MOVIMIENTO"][:3] == [
        entrega["folio"],
        rec["folio"],
        trs["folio"],
    ]
    # Filtra por usuario: qué más hizo cada persona (el almacenista de Midrex: la recepción y la
    # entrega, nada de Kepler).
    r = m.admin.get(
        "/api/reportes/movimientos", params={"usuario_id": mid_user["id"], "tamano": 100}
    )
    folios = {f["folio"] for f in r.json()["elementos"]}
    assert entrega["folio"] in folios and trs["folio"] not in folios
    assert {f["responsable"] for f in r.json()["elementos"]} == {"Almacenista Midrex"}
    # El supervisor de Midrex usa el mismo filtro, pero solo sobre su almacén (AC-06).
    propios = m.sup_mid.get("/api/reportes/movimientos", params={"usuario_id": mid_user["id"]})
    assert entrega["folio"] in {f["folio"] for f in propios.json()["elementos"]}
    kep_user = m.kep.get("/api/sesion").json()["usuario"]
    ajeno = m.sup_mid.get("/api/reportes/movimientos", params={"usuario_id": kep_user["id"]})
    assert ajeno.status_code == 200 and ajeno.json()["elementos"] == []
    otro_almacen = m.sup_mid.get(
        "/api/reportes/movimientos", params={"almacen_id": str(m.almacen["KEP"])}
    )
    assert otro_almacen.json()["elementos"] == []
    verificar_invariantes(m.session)
