"""P-08: `POST /api/piezas/{id}/serie` pone el número de serie a una pieza que no lo tiene."""

import pytest
from sqlalchemy import select

from app.modulos.acceso.permisos import P
from app.modulos.auditoria.models import Auditoria
from app.modulos.catalogo.models import Pieza


def _sin_serie(datos, articulo, ubicacion):
    pieza = datos.pieza(articulo, ubicacion)
    pieza.numero_serie = None
    datos.session.flush()
    return pieza


def _ruta(pieza) -> str:
    return f"/api/piezas/{pieza.id}/serie"


PERMISOS = (P.PIEZAS_REGISTRAR_SERIE, P.CATALOGO_VER, P.INVENTARIO_VER)


def test_P_08_pone_la_serie_deja_auditoria_y_responde_la_ficha(cliente_con, datos, session):
    cliente = cliente_con(*PERMISOS, P.ALMACENES_TODOS)
    arnes = datos.articulo("Arnés sin serie", control="PIEZA")
    pieza = _sin_serie(datos, arnes, datos.ub_almacen("KEP"))
    antes_vales = datos.session.execute(select(Pieza.ubicacion_id).where(Pieza.id == pieza.id))
    ubicacion_antes = antes_vales.scalar_one()

    r = cliente.post(_ruta(pieza), json={"numero_serie": "  SER-NUEVA-1  "})

    assert r.status_code == 200, r.text
    ficha = r.json()
    assert ficha["id"] == str(pieza.id)
    assert ficha["numero_serie"] == "SER-NUEVA-1" and ficha["serie_pendiente"] is False
    session.refresh(pieza)
    assert pieza.numero_serie == "SER-NUEVA-1" and pieza.ubicacion_id == ubicacion_antes
    fila = session.scalars(
        select(Auditoria).where(
            Auditoria.accion == "pieza.registrar_serie", Auditoria.entidad_id == str(pieza.id)
        )
    ).one()
    assert fila.antes == {"numero_serie": None}
    assert fila.despues == {"numero_serie": "SER-NUEVA-1"}


def test_P_08_si_la_pieza_ya_tiene_serie_responde_409_serie_ya_registrada(cliente_con, datos):
    cliente = cliente_con(*PERMISOS, P.ALMACENES_TODOS)
    arnes = datos.articulo("Arnés con serie", control="PIEZA")
    pieza = datos.pieza(arnes, datos.ub_almacen("KEP"), serie="SER-ORIGINAL")
    r = cliente.post(_ruta(pieza), json={"numero_serie": "OTRA"})
    assert r.status_code == 409 and r.json()["codigo"] == "SERIE_YA_REGISTRADA"
    assert r.json()["detalles"] == {"regla": "P-08"}
    # Con el 409 el servicio deshace su transacción, que en esta prueba es la misma sesión que armó
    # los datos: la pieza ya no se puede releer. Que la serie no cambió lo prueba el rechazo previo
    # a cualquier escritura: no hay renglón de auditoría de este intento.
    assert (
        datos.session.scalars(
            select(Auditoria).where(Auditoria.accion == "pieza.registrar_serie")
        ).all()
        == []
    )


def test_P_08_una_serie_repetida_en_el_articulo_responde_409_serie_repetida(cliente_con, datos):
    cliente = cliente_con(*PERMISOS, P.ALMACENES_TODOS)
    arnes = datos.articulo("Arnés con serie repetida", control="PIEZA")
    ub = datos.ub_almacen("KEP")
    existente = datos.pieza(arnes, ub, serie="SER-REPE-1")
    pieza = _sin_serie(datos, arnes, ub)
    r = cliente.post(_ruta(pieza), json={"numero_serie": "SER-REPE-1"})
    assert r.status_code == 409 and r.json()["codigo"] == "SERIE_REPETIDA"
    assert r.json()["detalles"]["pieza"] == {"id": str(existente.id), "codigo": existente.codigo}
    # La misma serie en otro artículo sí se acepta.
    otro = datos.articulo("Otro arnés", control="PIEZA")
    ajena = _sin_serie(datos, otro, ub)
    assert cliente.post(_ruta(ajena), json={"numero_serie": "SER-REPE-1"}).status_code == 200


def test_P_08_una_pieza_de_baja_responde_409_y_una_inexistente_404(cliente_con, datos):
    import uuid

    cliente = cliente_con(*PERMISOS, P.ALMACENES_TODOS)
    arnes = datos.articulo("Arnés de baja", control="PIEZA")
    pieza = _sin_serie(datos, arnes, datos.ub_almacen("KEP"))
    pieza.estado = "BAJA"
    datos.session.flush()
    assert cliente.post(_ruta(pieza), json={"numero_serie": "X-1"}).status_code == 409
    r = cliente.post(f"/api/piezas/{uuid.uuid4()}/serie", json={"numero_serie": "X-1"})
    assert r.status_code == 404


@pytest.mark.parametrize("cuerpo", [{}, {"numero_serie": ""}, {"numero_serie": "   "}])
def test_P_08_la_serie_vacia_o_ausente_es_422(cliente_con, datos, cuerpo):
    cliente = cliente_con(*PERMISOS, P.ALMACENES_TODOS)
    arnes = datos.articulo("Arnés para 422", control="PIEZA")
    pieza = _sin_serie(datos, arnes, datos.ub_almacen("KEP"))
    assert cliente.post(_ruta(pieza), json=cuerpo).status_code == 422


def test_P_08_AC_06_una_pieza_de_otro_almacen_responde_404(cliente_con, datos):
    en_con = cliente_con(*PERMISOS, almacen="CON")
    arnes = datos.articulo("Arnés de Kepler", control="PIEZA")
    pieza = _sin_serie(datos, arnes, datos.ub_almacen("KEP"))
    assert en_con.post(_ruta(pieza), json={"numero_serie": "X-2"}).status_code == 404
    en_kep = cliente_con(*PERMISOS, almacen="KEP")
    assert en_kep.post(_ruta(pieza), json={"numero_serie": "X-2"}).status_code == 200


def test_P_08_AC_01_sin_el_permiso_responde_403(cliente_con, datos):
    cliente = cliente_con(P.CATALOGO_VER, P.INVENTARIO_VER, P.ALMACENES_TODOS)
    arnes = datos.articulo("Arnés sin permiso", control="PIEZA")
    pieza = _sin_serie(datos, arnes, datos.ub_almacen("KEP"))
    r = cliente.post(_ruta(pieza), json={"numero_serie": "X-3"})
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"


def test_P_08_los_roles_iniciales_con_el_permiso_son_supervisor_compras_y_administrador(
    cliente_como,
):
    for rol, esperado in (
        ("Supervisor", True),
        ("Compras", True),
        ("Administrador", True),
        ("Almacenista", False),
        ("Recursos Humanos", False),
    ):
        permisos = set(cliente_como(rol).get("/api/sesion").json()["permisos"])
        assert (P.PIEZAS_REGISTRAR_SERIE in permisos) is esperado, rol
