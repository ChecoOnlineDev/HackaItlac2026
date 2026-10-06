"""Concurrencia real entre dos lotes de importación (hilos, conexiones propias, datos
confirmados que se borran al final): no se duplican artículos ni piezas y las existencias
coinciden con la suma de los movimientos."""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import delete, func, select

from app.modulos.auditoria.models import Auditoria
from app.modulos.catalogo.models import Articulo, Pieza
from app.modulos.movimientos.models import Existencia, Movimiento
from tests.importacion.ayudas import ELECTRICA, IMPORTACION, MANUAL, cuerpo, fila


def test_I_10_dos_lotes_simultaneos_con_los_mismos_articulos_no_duplican_nada(
    cliente_independiente, sesion_independiente, limpieza
):
    marca = uuid.uuid4().hex[:6]
    codigo_a, codigo_b, taladro = f"CA-{marca}", f"CB-{marca}", f"TAL-{marca}"
    nombre_sin_codigo = f"Cinta {marca}"
    filas = [
        fila(codigo_a, nombre=f"A {marca}", cantidad=5),
        fila(codigo_b, nombre=f"B {marca}", cantidad=3),
        fila("", nombre=nombre_sin_codigo, marca="X", categoria=MANUAL, cantidad=2),
        fila(
            taladro,
            nombre=f"T {marca}",
            categoria=ELECTRICA,
            serie="S-1",
            codigo_pieza=f"P1-{marca}",
        ),
        fila(
            taladro,
            nombre=f"T {marca}",
            categoria=ELECTRICA,
            serie="S-2",
            codigo_pieza=f"P2-{marca}",
        ),
    ]
    lotes = [str(uuid.uuid4()), str(uuid.uuid4())]
    clientes = [cliente_independiente("Compras"), cliente_independiente("Compras")]
    barrera = threading.Barrier(2)

    def correr(i):
        barrera.wait(timeout=30)
        # Mismo contenido: se confirma de forma expresa para probar la carrera, no el aviso I-12.
        return clientes[i].post(
            IMPORTACION, json=cuerpo(filas, id_lote=lotes[i], confirmar_repetido=True)
        )

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            respuestas = list(pool.map(correr, range(2)))
        estados = sorted(r.status_code for r in respuestas)
        assert estados[0] == 201 and estados[1] in (201, 409, 422), [r.text for r in respuestas]

        s = sesion_independiente()
        codigos = [codigo_a, codigo_b, taladro]
        articulos = list(s.scalars(select(Articulo).where(Articulo.codigo.in_(codigos))))
        por_nombre = list(s.scalars(select(Articulo).where(Articulo.nombre == nombre_sin_codigo)))
        assert sorted(a.codigo for a in articulos) == sorted(codigos)  # ninguno duplicado
        assert len(por_nombre) == 1
        piezas = list(
            s.scalars(select(Pieza).where(Pieza.codigo.in_([f"P1-{marca}", f"P2-{marca}"])))
        )
        assert len(piezas) == 2
        ids = [a.id for a in articulos] + [por_nombre[0].id]
        limpieza.articulos.extend(ids)
        # Existencias == suma de movimientos (entradas) por artículo y almacén.
        for articulo_id in ids:
            esperado = s.scalar(
                select(func.coalesce(func.sum(Movimiento.cantidad), 0)).where(
                    Movimiento.articulo_id == articulo_id
                )
            )
            real = s.scalar(
                select(func.coalesce(func.sum(Existencia.cantidad), 0)).where(
                    Existencia.articulo_id == articulo_id
                )
            )
            assert real == esperado
    finally:
        s = sesion_independiente()
        s.execute(delete(Auditoria).where(Auditoria.entidad_id.in_(lotes)))
        s.commit()
