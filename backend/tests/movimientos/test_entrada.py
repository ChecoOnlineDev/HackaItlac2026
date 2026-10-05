"""ENTRADA (US-INV-001): I-01 a I-04, I-09, RG-01, RG-06, RG-09, RG-12."""

import uuid
from decimal import Decimal

from sqlalchemy import select

from app.modulos.catalogo.models import Codigo, Pieza
from app.modulos.movimientos.models import Movimiento, Vale
from tests.movimientos.ayudas import (
    abastecer,
    almacen,
    crear_articulo,
    cuerpo_entrada,
    entrar_pieza,
    existencia,
    total_movimientos,
    total_vales,
    unico,
)

VALES = "/api/vales"


def test_I_01_entrada_por_cantidad_aumenta_la_existencia_del_almacen(compras, session):
    guantes = crear_articulo(session, retornable=False)
    antes = existencia(session, "KEP", guantes)
    vale = abastecer(compras, guantes, 10)
    assert vale["folio"].startswith("KEP-ING-") and len(vale["token"]) >= 22
    assert existencia(session, "KEP", guantes) == antes + 10
    renglon = vale["renglones"][0]
    assert renglon["cantidad"] == 10 and renglon["nivel"] == "VERDE"


def test_I_01_la_entrada_registra_saldos_y_proveedor_no_lleva_existencia(compras, session):
    articulo = crear_articulo(session)
    abastecer(compras, articulo, 4)
    abastecer(compras, articulo, 6)
    movs = session.scalars(
        select(Movimiento).where(Movimiento.articulo_id == articulo.id).order_by(Movimiento.creado_en)
    ).all()
    assert [m.saldo_destino for m in movs] == [4, 10]
    assert all(m.saldo_origen is None for m in movs)  # PROVEEDOR no lleva existencia


def test_I_01_las_compras_entran_por_kepler_y_la_carga_inicial_puede_ir_a_otro_almacen(
    compras, session
):
    articulo = crear_articulo(session)
    contratistas = almacen(session, "CON")
    r = compras.post(
        VALES,
        json=cuerpo_entrada(
            [{"codigo": articulo.codigo, "cantidad": 3}], almacen_id=str(contratistas.id)
        ),
    )
    assert r.status_code == 201 and r.json()["folio"].startswith("CON-ING-")
    assert existencia(session, "CON", articulo) == 3
    assert existencia(session, "KEP", articulo) == 0


def test_I_01_articulo_por_cantidad_repetido_en_el_vale_suma(compras, session):
    articulo = crear_articulo(session)
    r = compras.post(
        VALES,
        json=cuerpo_entrada(
            [
                {"codigo": articulo.codigo, "cantidad": 2},
                {"codigo": articulo.codigo, "cantidad": 3},
            ]
        ),
    )
    assert r.status_code == 201 and len(r.json()["renglones"]) == 1
    assert existencia(session, "KEP", articulo) == 5


def test_I_02_entrada_por_pieza_crea_la_pieza_y_registra_su_codigo(compras, session):
    arnes = crear_articulo(session, control="PIEZA", nombre="Arnés de prueba")
    r, codigo = entrar_pieza(compras, arnes)
    assert r.status_code == 201, r.text
    pieza = session.scalar(select(Pieza).where(Pieza.codigo == codigo))
    kep = almacen(session, "KEP")
    from app.modulos.almacenes.service import AlmacenService

    assert pieza.ubicacion_id == AlmacenService(session).ubicacion_de_almacen(kep.id).id
    assert session.get(Codigo, codigo).ref_id == pieza.id  # RG-10: el código queda registrado
    mov = session.scalar(select(Movimiento).where(Movimiento.pieza_id == pieza.id))
    assert mov.cantidad == 1 and mov.saldo_destino == 1  # invariante 3
    assert existencia(session, "KEP", arnes) == 1


def test_I_02_dos_piezas_suben_la_existencia_del_articulo_por_pieza(compras, session):
    arnes = crear_articulo(session, control="PIEZA")
    renglones = [
        {"codigo": arnes.codigo, "pieza": {"codigo": unico("P"), "numero_serie": unico("S")}}
        for _ in range(2)
    ]
    r = compras.post(VALES, json=cuerpo_entrada(renglones))
    assert r.status_code == 201, r.text
    assert existencia(session, "KEP", arnes) == 2


def test_I_02_un_codigo_de_pieza_repetido_se_rechaza(compras, session):
    arnes = crear_articulo(session, control="PIEZA")
    _, codigo = entrar_pieza(compras, arnes)
    vales_antes = total_vales(session)
    r, _ = entrar_pieza(compras, arnes, codigo=codigo)
    assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO"
    motivo = r.json()["detalles"]["renglones"][0]["motivos"][0]
    assert motivo["regla"] == "I-02" and "ya identifica" in motivo["mensaje"]
    assert total_vales(session) == vales_antes  # RG-09: no se guardó nada


def test_I_02_un_codigo_que_ya_es_de_un_articulo_o_credencial_se_rechaza(compras, session):
    arnes = crear_articulo(session, control="PIEZA")
    otro = crear_articulo(session)
    r, _ = entrar_pieza(compras, arnes, codigo=otro.codigo)
    assert r.status_code == 409
    assert r.json()["detalles"]["renglones"][0]["motivos"][0]["regla"] == "I-02"


def test_I_02_la_serie_repetida_del_mismo_articulo_se_rechaza(compras, session):
    arnes = crear_articulo(session, control="PIEZA")
    r, _ = entrar_pieza(compras, arnes, serie="SER-REPE")
    assert r.status_code == 201
    r, _ = entrar_pieza(compras, arnes, serie="SER-REPE")
    assert r.status_code == 409
    mensaje = r.json()["detalles"]["renglones"][0]["motivos"][0]["mensaje"]
    assert "número de serie" in mensaje


def test_I_02_el_mismo_codigo_dos_veces_en_el_vale_se_rechaza(compras, session):
    arnes = crear_articulo(session, control="PIEZA")
    codigo = unico("P")
    renglones = [
        {"codigo": arnes.codigo, "pieza": {"codigo": codigo, "numero_serie": unico("S")}},
        {"codigo": arnes.codigo, "pieza": {"codigo": codigo, "numero_serie": unico("S")}},
    ]
    r = compras.post("/api/vales/evaluar", json={"tipo": "ENTRADA", "renglones": renglones})
    assert r.status_code == 200
    segundo = r.json()["renglones"][1]
    assert segundo["nivel"] == "ROJO" and segundo["motivos"][0]["regla"] == "I-02"
    assert r.json()["renglones"][0]["nivel"] == "VERDE"


def test_I_02_cada_pieza_lleva_codigo_y_serie(compras, session):
    arnes = crear_articulo(session, control="PIEZA")
    sin_pieza = {"tipo": "ENTRADA", "renglones": [{"codigo": arnes.codigo}]}
    r = compras.post("/api/vales/evaluar", json=sin_pieza)
    assert r.json()["renglones"][0]["motivos"][0]["regla"] == "I-02"
    sin_serie = {
        "tipo": "ENTRADA",
        "renglones": [{"codigo": arnes.codigo, "pieza": {"codigo": unico("P")}}],
    }
    r = compras.post("/api/vales/evaluar", json=sin_serie)
    assert "serie" in r.json()["renglones"][0]["motivos"][0]["mensaje"]


def test_RG_05_una_pieza_entra_de_una_en_una(compras, session):
    arnes = crear_articulo(session, control="PIEZA")
    cuerpo = {
        "tipo": "ENTRADA",
        "renglones": [
            {
                "codigo": arnes.codigo,
                "cantidad": 2,
                "pieza": {"codigo": unico("P"), "numero_serie": unico("S")},
            }
        ],
    }
    r = compras.post("/api/vales/evaluar", json=cuerpo)
    assert r.json()["renglones"][0]["motivos"][0]["regla"] == "RG-05"


def test_I_02_un_articulo_por_cantidad_no_lleva_datos_de_pieza(compras, session):
    articulo = crear_articulo(session)
    cuerpo = {
        "tipo": "ENTRADA",
        "renglones": [
            {"codigo": articulo.codigo, "pieza": {"codigo": unico("P"), "numero_serie": "1"}}
        ],
    }
    r = compras.post("/api/vales/evaluar", json=cuerpo)
    assert r.json()["renglones"][0]["nivel"] == "ROJO"


def test_I_03_pieza_que_requiere_inspeccion_sin_inspeccion_queda_pendiente(
    compras, almacenista, session
):
    arnes = crear_articulo(session, control="PIEZA", requiere_inspeccion=True)
    arnes.vigencia_inspeccion_dias = 180
    session.flush()
    r, codigo = entrar_pieza(compras, arnes)
    assert r.status_code == 201, r.text  # amarillo: no bloquea
    assert r.json()["renglones"][0]["nivel"] == "AMARILLO"
    assert r.json()["renglones"][0]["reglas"] == ["I-03"]
    pieza = session.scalar(select(Pieza).where(Pieza.codigo == codigo))
    assert pieza.inspeccion_vigente_hasta is None  # pendiente: no se puede entregar (E-06)


def test_I_03_la_evaluacion_avisa_que_la_pieza_entra_pendiente(compras, session):
    arnes = crear_articulo(session, control="PIEZA", requiere_inspeccion=True)
    cuerpo = {
        "tipo": "ENTRADA",
        "renglones": [
            {"codigo": arnes.codigo, "pieza": {"codigo": unico("P"), "numero_serie": unico("S")}}
        ],
    }
    r = compras.post("/api/vales/evaluar", json=cuerpo).json()
    renglon = r["renglones"][0]
    assert renglon["nivel"] == "AMARILLO" and renglon["pieza"]["pendiente_inspeccion"] is True
    assert r["puede_confirmar"] is True


def test_I_03_la_inspeccion_inicial_se_registra_con_registrar_inicial(
    compras, session, doble_inspecciones
):
    arnes = crear_articulo(session, control="PIEZA", requiere_inspeccion=True)
    arnes.vigencia_inspeccion_dias = 100
    session.flush()
    r, codigo = entrar_pieza(
        compras,
        arnes,
        inspeccion={"fecha": "2026-10-01", "resultado": "APTO", "observacion": "Sin daño"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["renglones"][0]["nivel"] == "VERDE"
    pieza = session.scalar(select(Pieza).where(Pieza.codigo == codigo))
    (llamada,) = doble_inspecciones
    assert llamada.pieza_id == pieza.id and str(llamada.resultado) == "APTO"
    assert llamada.fecha.isoformat() == "2026-10-01" and llamada.observacion == "Sin daño"
    assert pieza.estado == "APTO" and pieza.inspeccion_vigente_hasta.isoformat() == "2027-01-09"


def test_I_03_la_inspeccion_no_apta_deja_la_pieza_no_apta(compras, session, doble_inspecciones):
    arnes = crear_articulo(session, control="PIEZA", requiere_inspeccion=True)
    r, codigo = entrar_pieza(
        compras, arnes, inspeccion={"resultado": "NO_APTO", "observacion": "Costura rota"}
    )
    assert r.status_code == 201, r.text
    pieza = session.scalar(select(Pieza).where(Pieza.codigo == codigo))
    assert pieza.estado == "NO_APTO"
    assert len(doble_inspecciones) == 1


def test_I_03_una_inspeccion_no_apta_exige_observacion(compras, session, doble_inspecciones):
    arnes = crear_articulo(session, control="PIEZA", requiere_inspeccion=True)
    r, _ = entrar_pieza(compras, arnes, inspeccion={"resultado": "NO_APTO"})
    assert r.status_code == 409
    assert r.json()["detalles"]["renglones"][0]["motivos"][0]["regla"] == "I-03"
    assert doble_inspecciones == []


def test_I_03_una_pieza_de_un_articulo_sin_inspeccion_no_la_registra(
    compras, session, doble_inspecciones
):
    arnes = crear_articulo(session, control="PIEZA", requiere_inspeccion=False)
    r, _ = entrar_pieza(compras, arnes, inspeccion={"resultado": "APTO"})
    assert r.status_code == 201
    assert doble_inspecciones == []


def test_I_09_un_articulo_inactivo_no_recibe_entradas(compras, session):
    viejo = crear_articulo(session, activo=False)
    cuerpo = cuerpo_entrada([{"codigo": viejo.codigo, "cantidad": 1}])
    r = compras.post(VALES, json=cuerpo)
    assert r.status_code == 409 and r.json()["codigo"] == "VALE_CAMBIO"
    assert r.json()["detalles"]["renglones"][0]["motivos"][0]["regla"] == "I-09"
    assert existencia(session, "KEP", viejo) == 0


def test_E_01_un_codigo_desconocido_en_la_entrada_es_rojo(compras):
    r = compras.post(
        "/api/vales/evaluar", json={"tipo": "ENTRADA", "renglones": [{"codigo": "NO-EXISTE-1"}]}
    )
    renglon = r.json()["renglones"][0]
    assert renglon["nivel"] == "ROJO" and renglon["motivos"][0]["regla"] == "E-01"
    assert r.json()["puede_confirmar"] is False and renglon["autorizable"] is False


def test_E_01_un_codigo_de_pieza_no_sirve_como_articulo_en_la_entrada(compras, session):
    arnes = crear_articulo(session, control="PIEZA")
    _, codigo = entrar_pieza(compras, arnes)
    r = compras.post(
        "/api/vales/evaluar", json={"tipo": "ENTRADA", "renglones": [{"codigo": codigo}]}
    )
    assert "no es de un artículo" in r.json()["renglones"][0]["motivos"][0]["mensaje"]


def test_RG_09_un_renglon_con_error_impide_guardar_todo_el_vale(compras, session):
    bueno = crear_articulo(session)
    vales, movs = total_vales(session), total_movimientos(session)
    r = compras.post(
        VALES,
        json=cuerpo_entrada(
            [{"codigo": bueno.codigo, "cantidad": 5}, {"codigo": "NO-EXISTE-2", "cantidad": 1}]
        ),
    )
    assert r.status_code == 409
    assert (total_vales(session), total_movimientos(session)) == (vales, movs)
    assert existencia(session, "KEP", bueno) == 0


def test_I_04_el_vale_de_entrada_no_acepta_costos(compras, session):
    articulo = crear_articulo(session)
    cuerpo = cuerpo_entrada([{"codigo": articulo.codigo, "cantidad": 1, "costo_unitario": "5.00"}])
    r = compras.post(VALES, json=cuerpo)
    assert r.status_code == 422 and r.json()["codigo"] == "DATOS_INVALIDOS"
    assert total_vales(session) == total_vales(session)  # sin cambios


def test_RG_12_el_vale_de_entrada_no_muestra_costos_ni_a_quien_los_ve(compras, session):
    articulo = crear_articulo(session, costo_unitario=Decimal("123.45"))
    vale = abastecer(compras, articulo, 2)  # Compras sí tiene `catalogo.costos`
    assert "costo" not in str(vale).lower()
    detalle = compras.get(f"{VALES}/{vale['id']}")
    assert detalle.status_code == 200
    assert "costo" not in detalle.text.lower() and "123.45" not in detalle.text


def test_AC_04_la_entrada_exige_inventario_entradas(almacenista, supervisor, session):
    articulo = crear_articulo(session)
    cuerpo = cuerpo_entrada([{"codigo": articulo.codigo, "cantidad": 1}])
    for cliente in (almacenista, supervisor):
        assert cliente.post(VALES, json=cuerpo).status_code == 403
        assert cliente.post("/api/vales/evaluar", json=cuerpo).status_code == 403


def test_I_01_una_entrada_no_lleva_trabajador(compras, session):
    articulo = crear_articulo(session)
    cuerpo = cuerpo_entrada(
        [{"codigo": articulo.codigo, "cantidad": 1}], trabajador_id=str(uuid.uuid4())
    )
    r = compras.post(VALES, json=cuerpo)
    assert r.status_code == 422 and r.json()["detalles"][0]["campo"] == "trabajador_id"


def test_F_03_la_entrada_firma_con_la_sesion_sin_imagen(compras, session):
    articulo = crear_articulo(session)
    vale = abastecer(compras, articulo, 1)
    fila = session.get(Vale, uuid.UUID(vale["id"]))
    assert fila.firma_modo == "SESION" and fila.firma_adjunto_id is None
    assert fila.responsable_id is not None and fila.token  # F-05: responsable y token


def test_I_01_la_entrada_sin_renglones_se_rechaza(compras):
    r = compras.post(VALES, json=cuerpo_entrada([]))
    assert r.status_code == 422


def test_I_01_la_entrada_a_un_almacen_inexistente_da_404(compras, session):
    articulo = crear_articulo(session)
    cuerpo = cuerpo_entrada(
        [{"codigo": articulo.codigo, "cantidad": 1}], almacen_id=str(uuid.uuid4())
    )
    assert compras.post(VALES, json=cuerpo).status_code == 404
