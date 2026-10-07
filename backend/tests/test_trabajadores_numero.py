"""Número de empleado automático (T-10) y reingreso por CURP o por nombre (T-02)."""

import re
import uuid
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.tiempo import hoy_mx
from app.modulos.almacenes.models import Ubicacion
from app.modulos.auditoria.models import Auditoria
from app.modulos.trabajadores.models import PeriodoContrato, SerieEmpleado, Trabajador
from tests.conftest import iniciar_sesion_en
from tests.movimientos.test_concurrencia import en_paralelo

TRABAJADORES = "/api/trabajadores"


def cuerpo(**extra) -> dict:
    hoy = hoy_mx()
    base = {
        "nombre": f"Persona {uuid.uuid4().hex[:10]}",
        "puesto": "Soldador",
        "area_obra": "Midrex",
        "inicio": str(hoy - timedelta(days=1)),
        "fin": str(hoy + timedelta(days=100)),
    }
    return base | extra


def curp_nueva() -> str:
    return ("CURP" + uuid.uuid4().hex[:14]).upper()


def test_T_10_el_servidor_genera_el_numero_consecutivo(cliente_como):
    rh = cliente_como("Recursos Humanos")
    primero = rh.post(TRABAJADORES, json=cuerpo())
    segundo = rh.post(TRABAJADORES, json=cuerpo())
    assert primero.status_code == 201 and segundo.status_code == 201
    a, b = primero.json(), segundo.json()
    assert re.fullmatch(r"E-\d{6}", a["numero_empleado"]) and a["numero_externo"] is False
    assert int(b["numero_empleado"][2:]) == int(a["numero_empleado"][2:]) + 1


def test_T_10_rh_no_puede_escribir_el_numero(cliente_como):
    rh = cliente_como("Recursos Humanos")
    r = rh.post(TRABAJADORES, json=cuerpo(numero_empleado="EMP-9999"))
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"


def test_T_10_con_numero_externo_se_acepta_y_queda_marcado(cliente_como, session):
    admin = cliente_como("Administrador")
    r = admin.post(TRABAJADORES, json=cuerpo(numero_empleado="EXT-0001"))
    assert r.status_code == 201, r.text
    ficha = r.json()
    assert ficha["numero_empleado"] == "EXT-0001" and ficha["numero_externo"] is True
    lista = admin.get(TRABAJADORES, params={"q": "EXT-0001"}).json()["elementos"]
    assert lista[0]["numero_externo"] is True
    # Repetido: reingreso (409), nunca por confirmar_distinta.
    r = admin.post(TRABAJADORES, json=cuerpo(numero_empleado="EXT-0001", confirmar_distinta=True))
    assert r.status_code == 409 and r.json()["codigo"] == "TRABAJADOR_EXISTE"
    assert r.json()["detalles"]["coincide_por"] == "numero_empleado"
    assert r.json()["detalles"]["puede_confirmar_distinta"] is False
    # El contador no avanza con un número escrito a mano.
    ultimo = session.scalar(select(SerieEmpleado.ultimo))
    siguiente = admin.post(TRABAJADORES, json=cuerpo()).json()["numero_empleado"]
    assert siguiente == f"E-{ultimo + 1:06d}"


def test_T_10_se_salta_un_numero_externo_con_la_forma_del_consecutivo(cliente_como, session):
    admin = cliente_como("Administrador")
    ultimo = session.scalar(select(SerieEmpleado.ultimo))
    tomado = f"E-{ultimo + 1:06d}"
    assert admin.post(TRABAJADORES, json=cuerpo(numero_empleado=tomado)).status_code == 201
    r = admin.post(TRABAJADORES, json=cuerpo())
    assert r.status_code == 201 and r.json()["numero_empleado"] == f"E-{ultimo + 2:06d}"


def test_T_02_el_reingreso_se_detecta_por_curp(cliente_como):
    rh = cliente_como("Recursos Humanos")
    curp = curp_nueva()
    original = rh.post(TRABAJADORES, json=cuerpo(curp=curp)).json()
    r = rh.post(TRABAJADORES, json=cuerpo(curp=curp))
    assert r.status_code == 409 and r.json()["codigo"] == "TRABAJADOR_EXISTE"
    detalles = r.json()["detalles"]
    assert detalles["coincide_por"] == "curp" and detalles["trabajador"]["id"] == original["id"]
    assert detalles["puede_confirmar_distinta"] is False
    # Con la CURP no se confirma que es otra persona.
    r = rh.post(TRABAJADORES, json=cuerpo(curp=curp, confirmar_distinta=True))
    assert r.status_code == 409


def test_T_02_sin_curp_el_nombre_repetido_avisa_y_se_puede_confirmar(cliente_como):
    rh = cliente_como("Recursos Humanos")
    nombre = f"José Ángel {uuid.uuid4().hex[:8]}"
    original = rh.post(TRABAJADORES, json=cuerpo(nombre=nombre)).json()
    # Sin distinguir mayúsculas ni acentos.
    parecido = nombre.upper().replace("É", "E").replace("Á", "A")
    r = rh.post(TRABAJADORES, json=cuerpo(nombre=parecido))
    assert r.status_code == 409 and r.json()["codigo"] == "TRABAJADOR_EXISTE"
    detalles = r.json()["detalles"]
    assert detalles["coincide_por"] == "nombre" and detalles["puede_confirmar_distinta"] is True
    assert detalles["trabajador"]["numero_empleado"] == original["numero_empleado"]
    r = rh.post(TRABAJADORES, json=cuerpo(nombre=parecido, confirmar_distinta=True))
    assert r.status_code == 201 and r.json()["id"] != original["id"]


def test_T_02_con_curp_el_nombre_repetido_no_estorba(cliente_como):
    rh = cliente_como("Recursos Humanos")
    nombre = f"Mismo Nombre {uuid.uuid4().hex[:8]}"
    rh.post(TRABAJADORES, json=cuerpo(nombre=nombre))
    r = rh.post(TRABAJADORES, json=cuerpo(nombre=nombre, curp=curp_nueva()))
    assert r.status_code == 201


def test_T_10_altas_simultaneas_no_repiten_ni_saltan_numeros(engine, usuario_por_rol):
    from app.main import create_app

    app = create_app()  # motor real: commits de verdad
    clientes = [TestClient(app) for _ in range(6)]
    for c in clientes:
        assert iniciar_sesion_en(c, usuario_por_rol("Recursos Humanos")).status_code == 200
    with Session(bind=engine) as s:
        antes = s.scalar(select(SerieEmpleado.ultimo))
    marca = uuid.uuid4().hex[:8]
    try:
        respuestas = en_paralelo(
            [
                lambda c=c, i=i: c.post(TRABAJADORES, json=cuerpo(nombre=f"Conc {marca} {i}"))
                for i, c in enumerate(clientes)
            ]
        )
        assert [r.status_code for r in respuestas] == [201] * 6, [r.text for r in respuestas]
        numeros = sorted(r.json()["numero_empleado"] for r in respuestas)
        assert len(set(numeros)) == 6
        assert numeros == [f"E-{antes + i:06d}" for i in range(1, 7)]  # sin huecos
    finally:
        with Session(bind=engine) as s:
            ids = list(
                s.scalars(select(Trabajador.id).where(Trabajador.nombre.like(f"Conc {marca}%")))
            )
            s.execute(delete(Auditoria).where(Auditoria.entidad_id.in_([str(i) for i in ids])))
            s.execute(delete(PeriodoContrato).where(PeriodoContrato.trabajador_id.in_(ids)))
            s.execute(delete(Ubicacion).where(Ubicacion.trabajador_id.in_(ids)))
            s.execute(delete(Trabajador).where(Trabajador.id.in_(ids)))
            serie = s.scalar(select(SerieEmpleado))
            serie.ultimo = antes
            s.commit()
        for c in clientes:
            c.close()
