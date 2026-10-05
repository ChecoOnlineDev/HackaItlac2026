"""Pruebas del comando de mantenimiento (TASK-F7-05): verificar y reconstruir existencias.

La base de pruebas trae la línea base de `app.datos_prueba` (entradas, piezas, vales); cada prueba
corre en una transacción que se revierte, así que estropear datos aquí no afecta a las demás.
"""

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.mantenimiento import FRASE_CONFIRMACION, main, verificar
from app.modulos.almacenes.models import Ubicacion
from app.modulos.auditoria.models import Auditoria
from app.modulos.catalogo.models import Articulo, Pieza
from app.modulos.movimientos.models import EstadoVale, Existencia, SerieFolio, Vale


def correr(session: Session, *args: str, **kw) -> tuple[int, str]:
    lineas: list[str] = []
    codigo = main(list(args), session=session, salida=lineas.append, **kw)
    return codigo, "\n".join(lineas)


def una_existencia(session: Session) -> Existencia:
    fila = session.execute(select(Existencia).where(Existencia.cantidad > 0)).scalars().first()
    assert fila is not None, "los datos de prueba deben traer existencias"
    return fila


def test_estado_sano_sale_con_cero(session: Session) -> None:
    assert verificar(session) == []
    codigo, texto = correr(session, "verificar")
    assert codigo == 0
    assert "Todo cuadra" in texto


def test_existencia_distinta_de_la_bitacora_sale_con_uno_y_da_el_detalle(session: Session) -> None:
    fila = una_existencia(session)
    guardada = fila.cantidad
    fila.cantidad = guardada + 3
    session.flush()

    codigo, texto = correr(session, "verificar")

    assert codigo == 1
    assert "Invariante 1" in texto
    assert (
        f"la existencia guardada es {guardada + 3} pero los movimientos suman {guardada}" in texto
    )


def test_pieza_fuera_de_su_ultimo_destino_es_invariante_4(session: Session) -> None:
    articulo = (
        session.execute(select(Articulo).where(Articulo.control == "PIEZA")).scalars().first()
    )
    ubicacion = session.execute(select(Ubicacion)).scalars().first()
    assert articulo is not None and ubicacion is not None
    # Una pieza sin movimientos no debe estar en ningún lugar.
    pieza = Pieza(articulo_id=articulo.id, codigo="PRUEBA-MANT-001", ubicacion_id=ubicacion.id)
    session.add(pieza)
    session.flush()

    codigo, texto = correr(session, "verificar")

    assert codigo == 1
    assert "Invariante 4" in texto and pieza.codigo in texto


def test_vale_cancelado_sin_cancelacion_es_invariante_5(session: Session) -> None:
    vale = session.execute(select(Vale)).scalars().first()
    assert vale is not None
    session.execute(update(Vale).where(Vale.id == vale.id).values(estado=EstadoVale.CANCELADO))
    session.flush()

    codigo, texto = correr(session, "verificar")

    assert codigo == 1
    assert "Invariante 5" in texto and "sin vale de cancelación" in texto


def test_contador_desfasado_en_folios_es_rg_06(session: Session) -> None:
    serie = session.execute(select(SerieFolio)).scalars().first()
    assert serie is not None
    serie.ultimo += 1
    session.flush()

    codigo, texto = correr(session, "verificar")

    assert codigo == 1
    assert "RG-06" in texto and "contador" in texto


def test_simular_no_escribe(session: Session) -> None:
    fila = una_existencia(session)
    guardada = fila.cantidad
    fila.cantidad = guardada + 5
    session.flush()
    llave = (fila.ubicacion_id, fila.articulo_id)
    auditorias = session.scalar(select(func.count()).select_from(Auditoria))

    codigo, texto = correr(session, "reconstruir-existencias", "--simular")

    assert codigo == 1
    assert "Simulación: no se escribió nada" in texto
    session.expire_all()
    assert session.get(Existencia, llave).cantidad == guardada + 5
    assert session.scalar(select(func.count()).select_from(Auditoria)) == auditorias


def test_simular_con_todo_cuadrado_no_hay_cambios(session: Session) -> None:
    codigo, texto = correr(session, "reconstruir-existencias", "--simular")
    assert codigo == 0
    assert "nada que cambiar" in texto


def test_aplicar_sin_confirmacion_correcta_no_escribe(session: Session) -> None:
    fila = una_existencia(session)
    fila.cantidad += 2
    session.flush()
    cambiada = fila.cantidad
    llave = (fila.ubicacion_id, fila.articulo_id)

    codigo, texto = correr(
        session,
        "reconstruir-existencias",
        "--aplicar",
        pedir=lambda _p: "sí",
        interactivo=True,
    )

    assert codigo == 2
    assert "Confirmación incorrecta" in texto
    assert session.get(Existencia, llave).cantidad == cambiada


def test_aplicar_sin_terminal_interactiva_se_niega(session: Session) -> None:
    una_existencia(session).cantidad += 2
    session.flush()
    codigo, texto = correr(session, "reconstruir-existencias", "--aplicar", interactivo=False)
    assert codigo == 2
    assert "terminal interactiva" in texto


def test_aplicar_con_confirmacion_corrige_y_deja_auditoria(session: Session) -> None:
    fila = una_existencia(session)
    correcta = fila.cantidad
    fila.cantidad = correcta + 7
    session.flush()
    llave = (fila.ubicacion_id, fila.articulo_id)

    codigo, _ = correr(
        session,
        "reconstruir-existencias",
        "--aplicar",
        pedir=lambda _p: FRASE_CONFIRMACION,
        interactivo=True,
    )

    assert codigo == 0
    session.expire_all()
    assert session.get(Existencia, llave).cantidad == correcta
    registro = (
        session.execute(
            select(Auditoria).where(Auditoria.accion == "mantenimiento.reconstruir_existencias")
        )
        .scalars()
        .one()
    )
    assert registro.despues["cambios"][0]["antes"] == correcta + 7
    assert correr(session, "verificar")[0] == 0


def test_verificar_no_modifica_nada(session: Session) -> None:
    def foto():
        return tuple(
            session.execute(
                select(func.count(), func.coalesce(func.sum(Existencia.cantidad), 0)).select_from(
                    Existencia
                )
            ).one()
        )

    antes = foto()
    correr(session, "verificar")
    assert foto() == antes


def test_reconstruir_exige_simular_o_aplicar() -> None:
    with pytest.raises(SystemExit):
        main(["reconstruir-existencias"])
