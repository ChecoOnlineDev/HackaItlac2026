"""Concurrencia real: hilos con conexiones propias y datos CONFIRMADOS (RG-08, RG-09, RG-06).

El fixture normal usa una transacción externa; aquí cada petición abre su propia sesión y hace
commit de verdad. Todo lo que se crea queda registrado en `limpieza`, que lo borra al final y
devuelve el contador de folios a su valor.
"""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.core.tiempo import hoy_mx
from app.modulos.almacenes.models import Ubicacion
from app.modulos.catalogo.models import Pieza
from app.modulos.catalogo.service import CatalogoService
from app.modulos.movimientos.models import Existencia, Movimiento, Vale
from tests.movimientos.ayudas import (
    abastecer,
    crear_articulo,
    crear_trabajador,
    cuerpo_entrega,
    entrar_pieza,
)

VALES = "/api/vales"


class Escenario:
    """Crea datos confirmados y los registra para la limpieza."""

    def __init__(self, sesion_independiente, limpieza, cliente_independiente):
        self.nueva = sesion_independiente
        self.limpieza = limpieza
        self.compras = cliente_independiente("Compras")
        self.clientes = cliente_independiente

    def articulo(self, **kw):
        s = self.nueva()
        articulo = crear_articulo(s, **kw)
        s.commit()
        self.limpieza.articulos.append(articulo.id)
        return articulo

    def trabajador(self):
        s = self.nueva()
        trabajador = crear_trabajador(s)
        s.commit()
        self.limpieza.trabajadores.append(trabajador.id)
        return trabajador

    def pieza_en_kep(self, articulo):
        r, codigo = entrar_pieza(self.compras, articulo)
        assert r.status_code == 201, r.text
        s = self.nueva()
        pieza = s.scalar(select(Pieza).where(Pieza.codigo == codigo))
        CatalogoService(s).actualizar_estado_pieza(
            pieza.id, inspeccion_vigente_hasta=hoy_mx() + timedelta(days=30)
        )
        s.commit()
        return codigo


@pytest.fixture
def escenario(sesion_independiente, limpieza, cliente_independiente):
    return Escenario(sesion_independiente, limpieza, cliente_independiente)


def en_paralelo(llamadas):
    """Ejecuta las llamadas a la vez (todas esperan en una barrera) y devuelve sus resultados."""
    barrera = threading.Barrier(len(llamadas))

    def correr(llamada):
        barrera.wait(timeout=30)
        return llamada()

    with ThreadPoolExecutor(max_workers=len(llamadas)) as pool:
        futuros = [pool.submit(correr, c) for c in llamadas]
        return [f.result(timeout=120) for f in futuros]


def renglon(codigo, cantidad=1):
    return {"codigo": codigo, "cantidad": cantidad}


def test_RG_08_dos_confirmaciones_simultaneas_de_la_misma_pieza_solo_una_gana(
    escenario, sesion_independiente
):
    arnes = escenario.articulo(control="PIEZA", requiere_inspeccion=False)
    codigo = escenario.pieza_en_kep(arnes)
    t1, t2 = escenario.trabajador(), escenario.trabajador()
    c1, c2 = escenario.clientes("Almacenista"), escenario.clientes("Almacenista")

    r1, r2 = en_paralelo(
        [
            lambda: c1.post(VALES, json=cuerpo_entrega(t1, [renglon(codigo)])),
            lambda: c2.post(VALES, json=cuerpo_entrega(t2, [renglon(codigo)])),
        ]
    )
    estados = sorted([r1.status_code, r2.status_code])
    assert estados == [201, 409], (r1.text, r2.text)
    perdedor = r1 if r1.status_code == 409 else r2
    assert perdedor.json()["codigo"] == "VALE_CAMBIO"
    assert [m["regla"] for m in perdedor.json()["detalles"]["renglones"][0]["motivos"]] == ["E-03"]

    s = sesion_independiente()
    vales = s.scalars(
        select(Vale.id)
        .join(Movimiento, Movimiento.vale_id == Vale.id)
        .where(Movimiento.articulo_id == arnes.id, Vale.tipo == "ENTREGA")
    ).all()
    assert len(vales) == 1  # RG-09: el que perdió no dejó nada
    pieza = s.scalar(select(Pieza).where(Pieza.codigo == codigo))
    ganador = t1 if r1.status_code == 201 else t2
    ubicacion = s.scalar(select(Ubicacion.id).where(Ubicacion.trabajador_id == ganador.id))
    assert pieza.ubicacion_id == ubicacion
    kep_ub = s.scalar(
        select(Existencia.cantidad)
        .join(Ubicacion, Ubicacion.id == Existencia.ubicacion_id)
        .where(Existencia.articulo_id == arnes.id, Ubicacion.almacen_id.is_not(None))
    )
    assert kep_ub == 0


def test_idempotencia_dos_confirmaciones_simultaneas_con_el_mismo_id_cliente(
    escenario, sesion_independiente
):
    guantes = escenario.articulo(retornable=False)
    abastecer(escenario.compras, guantes, 10)
    t = escenario.trabajador()
    c1, c2 = escenario.clientes("Almacenista"), escenario.clientes("Almacenista")
    cuerpo = cuerpo_entrega(t, [renglon(guantes.codigo, 3)])

    r1, r2 = en_paralelo([lambda: c1.post(VALES, json=cuerpo), lambda: c2.post(VALES, json=cuerpo)])
    assert sorted([r1.status_code, r2.status_code]) == [200, 201], (r1.text, r2.text)
    assert r1.json() == r2.json()  # el mismo vale
    s = sesion_independiente()
    n = s.scalar(
        select(func.count())
        .select_from(Vale)
        .where(Vale.id_cliente == uuid.UUID(cuerpo["id_cliente"]))
    )
    assert n == 1
    cantidad = s.scalar(
        select(func.sum(Existencia.cantidad))
        .join(Ubicacion, Ubicacion.id == Existencia.ubicacion_id)
        .where(Existencia.articulo_id == guantes.id, Ubicacion.almacen_id.is_not(None))
    )
    assert cantidad == 7  # una sola salida


def test_RG_04_dos_entregas_simultaneas_no_dejan_la_existencia_negativa(
    escenario, sesion_independiente
):
    guantes = escenario.articulo(retornable=False)
    abastecer(escenario.compras, guantes, 5)
    t1, t2 = escenario.trabajador(), escenario.trabajador()
    c1, c2 = escenario.clientes("Almacenista"), escenario.clientes("Almacenista")
    r1, r2 = en_paralelo(
        [
            lambda: c1.post(VALES, json=cuerpo_entrega(t1, [renglon(guantes.codigo, 3)])),
            lambda: c2.post(VALES, json=cuerpo_entrega(t2, [renglon(guantes.codigo, 3)])),
        ]
    )
    assert sorted([r1.status_code, r2.status_code]) == [201, 409]
    perdedor = r1 if r1.status_code == 409 else r2
    assert perdedor.json()["detalles"]["renglones"][0]["motivos"][0]["regla"] == "E-04"
    s = sesion_independiente()
    cantidades = s.scalars(
        select(Existencia.cantidad).where(Existencia.articulo_id == guantes.id)
    ).all()
    assert min(cantidades) >= 0 and sorted(cantidades)[-1] == 3


def test_L_02_dos_entregas_simultaneas_al_mismo_trabajador_respetan_el_limite(
    escenario, sesion_independiente
):
    arnes = escenario.articulo(retornable=True, limite_cantidad=1)
    abastecer(escenario.compras, arnes, 5)
    t = escenario.trabajador()
    c1, c2 = escenario.clientes("Almacenista"), escenario.clientes("Almacenista")
    r1, r2 = en_paralelo(
        [
            lambda: c1.post(VALES, json=cuerpo_entrega(t, [renglon(arnes.codigo)])),
            lambda: c2.post(VALES, json=cuerpo_entrega(t, [renglon(arnes.codigo)])),
        ]
    )
    assert sorted([r1.status_code, r2.status_code]) == [201, 409], (r1.text, r2.text)
    perdedor = r1 if r1.status_code == 409 else r2
    assert perdedor.json()["detalles"]["renglones"][0]["motivos"][0]["regla"] == "L-02"


def test_RG_06_los_folios_de_confirmaciones_simultaneas_son_consecutivos_y_sin_huecos(
    escenario, sesion_independiente
):
    guantes = escenario.articulo(retornable=False)
    abastecer(escenario.compras, guantes, 20)
    trabajadores = [escenario.trabajador() for _ in range(5)]
    clientes = [escenario.clientes("Almacenista") for _ in trabajadores]
    resultados = en_paralelo(
        [
            (lambda c=c, t=t: c.post(VALES, json=cuerpo_entrega(t, [renglon(guantes.codigo)])))
            for c, t in zip(clientes, trabajadores, strict=True)
        ]
    )
    assert [r.status_code for r in resultados] == [201] * 5, [r.text for r in resultados]
    numeros = sorted(int(r.json()["folio"].rsplit("-", 1)[1]) for r in resultados)
    assert numeros == list(range(numeros[0], numeros[0] + 5))  # sin huecos ni repetidos
    assert len({r.json()["folio"] for r in resultados}) == 5
    s = sesion_independiente()
    existencia_final = s.scalar(
        select(Existencia.cantidad)
        .join(Ubicacion, Ubicacion.id == Existencia.ubicacion_id)
        .where(Existencia.articulo_id == guantes.id, Ubicacion.almacen_id.is_not(None))
    )
    assert existencia_final == 15


def test_RG_08_la_confirmacion_corre_en_read_committed(escenario, monkeypatch):
    """Tras esperar un bloqueo, las lecturas de la confirmación deben ver lo último confirmado:
    en REPEATABLE READ verían la foto vieja que dejó la autenticación."""
    from sqlalchemy import text

    from app.modulos.movimientos.repository import MovimientoRepository

    niveles = []
    original = MovimientoRepository.bloquear_serie

    def espiar(self, almacen_id, tipo):
        niveles.append(self.session.execute(text("SELECT @@transaction_isolation")).scalar())
        return original(self, almacen_id, tipo)

    monkeypatch.setattr(MovimientoRepository, "bloquear_serie", espiar)
    guantes = escenario.articulo(retornable=False)
    abastecer(escenario.compras, guantes, 2)
    assert niveles and set(niveles) == {"READ-COMMITTED"}
