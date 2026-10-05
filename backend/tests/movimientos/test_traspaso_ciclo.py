# ruff: noqa: F811  (los fixtures importados se piden por nombre en cada prueba)
"""Paso 5 del guion (gate de la fase 5): Kepler -> Contratistas -> Midrex.

Las existencias cuadran en origen, tránsito y destino en cada momento y el historial de la pieza
muestra su recorrido completo.
"""

from datetime import timedelta

from app.core.tiempo import hoy_mx
from tests.movimientos.ayudas import abastecer, crear_articulo, existencia
from tests.movimientos.ayudas_traspasos import (
    POR_RECIBIR,
    cliente_almacen,  # noqa: F401  (fixture)
    en_transito,
    enviar,
    evaluar_traspaso,
    recibir,
    reglas,
    renglon,
    total_en_almacenes,
    ubicacion_de_pieza,
    vale,
)
from tests.movimientos.test_entrega import pieza_en_kep
from tests.movimientos.test_invariantes import revisar_folios, revisar_invariantes


def test_paso_5_del_guion_kepler_a_contratistas_y_de_contratistas_a_midrex(
    almacenista, cliente_almacen, compras, session
):
    kep, con, mid = almacenista, cliente_almacen("CON"), cliente_almacen("MID")
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 20)
    _, arnes = pieza_en_kep(compras, session, vigente_hasta=hoy_mx() + timedelta(days=90))

    def cuadro():
        """(Kepler, Contratistas, Midrex, En tránsito) de los guantes; el total no cambia."""
        t = (
            existencia(session, "KEP", guantes),
            existencia(session, "CON", guantes),
            existencia(session, "MID", guantes),
            en_transito(session, guantes),
        )
        assert sum(t) == 20 and total_en_almacenes(session, guantes) == 20 - t[3]
        return t

    assert cuadro() == (20, 0, 0, 0)

    # 1. Kepler envía a Contratistas (ruta habitual, sin aviso).
    ev = evaluar_traspaso(kep, session, "CON", [renglon(guantes.codigo, 8), renglon(arnes.codigo)])
    assert ev["nivel"] == "VERDE" and ev["puede_confirmar"] is True
    t1 = enviar(kep, session, "CON", [renglon(guantes.codigo, 8), renglon(arnes.codigo)])
    assert cuadro() == (12, 0, 0, 8)
    assert ubicacion_de_pieza(session, arnes.codigo) == "EN_TRANSITO"
    assert vale(session, t1["id"]).estado == "EN_TRANSITO"
    assert con.get(POR_RECIBIR, params={"solo_contar": "true"}).json() == {"total": 1}

    # 2. Contratistas lo abre desde su QR y lo recibe todo.
    abierto = con.get(f"/api/vales/por-token/{t1['token']}").json()
    assert abierto["estado"] == "EN_TRANSITO" and len(abierto["renglones"]) == 2
    r1 = recibir(con, t1, [renglon(guantes.codigo, 8), renglon(arnes.codigo)])
    assert cuadro() == (12, 8, 0, 0)
    assert vale(session, t1["id"]).estado == "RECIBIDO"
    assert ubicacion_de_pieza(session, arnes.codigo) == "CON"
    assert con.get(POR_RECIBIR, params={"solo_contar": "true"}).json() == {"total": 0}

    # 3. Contratistas envía a Midrex (ruta habitual) y Midrex recibe.
    t2 = enviar(con, session, "MID", [renglon(guantes.codigo, 5), renglon(arnes.codigo)])
    assert t2["folio"].startswith("CON-TRS-")
    assert cuadro() == (12, 3, 0, 5)
    assert mid.get(POR_RECIBIR, params={"solo_contar": "true"}).json() == {"total": 1}
    r2 = recibir(mid, t2, [renglon(guantes.codigo, 5), renglon(arnes.codigo)])
    assert r2["folio"].startswith("MID-REC-")
    assert cuadro() == (12, 3, 5, 0)
    assert ubicacion_de_pieza(session, arnes.codigo) == "MID"

    # 4. El historial de la pieza muestra su recorrido completo.
    ficha = con.get(f"/api/piezas/{arnes.id}").json()
    movimientos = [h for h in reversed(ficha["historial"]) if h["tipo"] == "MOVIMIENTO"]
    recorrido = [(h["tipo_vale"], h["origen"], h["destino"], h["folio"]) for h in movimientos]
    assert [r[0] for r in recorrido] == [
        "ENTRADA",
        "TRASPASO",
        "RECEPCION",
        "TRASPASO",
        "RECEPCION",
    ]
    assert [r[3] for r in recorrido[1:]] == [t1["folio"], r1["folio"], t2["folio"], r2["folio"]]
    # origen -> tránsito -> destino, dos veces
    assert recorrido[1][1] != recorrido[1][2] and "tránsito" in recorrido[1][2].lower()
    assert "tránsito" in recorrido[2][1].lower()
    assert "tránsito" in recorrido[3][2].lower() and "tránsito" in recorrido[4][1].lower()
    assert ficha["ubicacion"] is not None

    # 5. Una pieza que ya salió de Kepler no se vuelve a enviar desde ahí (X-02).
    ev = evaluar_traspaso(kep, session, "CON", [renglon(arnes.codigo)])
    assert ev["nivel"] == "ROJO" and reglas(ev, 0) == ["X-02"]
    revisar_invariantes(session)
    revisar_folios(session)
