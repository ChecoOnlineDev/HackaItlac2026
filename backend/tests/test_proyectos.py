"""Reglas PR y alcance de proyectos contra MySQL real."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.tiempo import hoy_mx
from app.modulos.almacenes.models import Almacen
from app.modulos.trabajadores.models import Trabajador


@pytest.fixture
def admin(cliente_como):
    return cliente_como("Administrador")


@pytest.fixture
def trabajador(session):
    t = Trabajador(numero_empleado="PR-TEST", nombre="Trabajador de proyecto")
    session.add(t)
    session.commit()
    return t


def datos(session, clave="PR-UNO", almacen="MID", **cambios):
    a = session.scalar(select(Almacen).where(Almacen.clave == almacen))
    return {
        "clave": clave,
        "nombre": "Mantenimiento",
        "almacen_id": str(a.id),
        "inicio": hoy_mx().isoformat(),
        "fin_estimado": (hoy_mx() + timedelta(days=30)).isoformat(),
        **cambios,
    }


def crear(admin, session, **cambios):
    r = admin.post("/api/proyectos", json=datos(session, **cambios))
    assert r.status_code == 201, r.text
    return r.json()


def asignar(admin, t, p, **cambios):
    return admin.post(
        f"/api/trabajadores/{t.id}/proyectos", json={"proyecto_id": p["id"], **cambios}
    )


def test_pr_01_normaliza_clave_y_rechaza_duplicada(admin, session):
    p = crear(admin, session, clave="pr-uno")
    assert p["clave"] == "PR-UNO"
    assert admin.post("/api/proyectos", json=datos(session)).status_code == 409


def test_pr_01_no_crea_en_almacen_cerrado(admin, session):
    a = session.scalar(select(Almacen).where(Almacen.clave == "MID"))
    a.estado = "CERRADO"
    session.flush()
    r = admin.post("/api/proyectos", json=datos(session))
    assert r.status_code == 409 and r.json()["codigo"] == "ALMACEN_CERRADO"


def test_pr_01_permiso_obligatorio(cliente_como, session):
    r = cliente_como("Supervisor").post("/api/proyectos", json=datos(session))
    assert r.status_code == 403


def test_pr_01_proyecto_general_trae_aviso(admin, session):
    assert "personal general" in crear(admin, session, almacen="CON")["aviso"]


def test_pr_02_fechas_invalidas_no_guardan(admin, session):
    r = admin.post(
        "/api/proyectos",
        json=datos(session, fin_estimado=(hoy_mx() - timedelta(days=1)).isoformat()),
    )
    assert r.status_code == 422
    assert r.json()["detalles"][0]["regla"] == "PR-02"


def test_pr_03_editar_cerrado_exige_reapertura(admin, session):
    p = crear(admin, session)
    assert (
        admin.post(f"/api/proyectos/{p['id']}/cierre", json={"motivo": "Terminado"}).status_code
        == 200
    )
    r = admin.patch(f"/api/proyectos/{p['id']}", json={"nombre": "Otro"})
    assert r.status_code == 409 and r.json()["codigo"] == "PROYECTO_CERRADO"


def test_pr_04_cierre_termina_asignaciones_sin_cambiar_trabajador(admin, session, trabajador):
    p = crear(admin, session)
    assert asignar(admin, trabajador, p).status_code == 201
    r = admin.post(f"/api/proyectos/{p['id']}/cierre", json={"motivo": "Terminado"})
    assert r.status_code == 200, r.text
    assert r.json()["asignaciones_terminadas"] == 1
    assert r.json()["trabajadores_sin_proyecto"] == 1
    session.refresh(trabajador)
    assert trabajador.estado == "ACTIVO"
    assert admin.get(f"/api/trabajadores/{trabajador.id}/proyectos").json()[0]["terminada_en"]


def test_pr_04_cierre_antes_de_inicio_conserva_fecha_real(admin, session, trabajador):
    p = crear(admin, session)
    assert (
        asignar(admin, trabajador, p, inicio=(hoy_mx() + timedelta(days=7)).isoformat()).status_code
        == 201
    )
    r = admin.post(
        f"/api/proyectos/{p['id']}/cierre", json={"motivo": "Cancelado antes del inicio"}
    )
    assert r.status_code == 200, r.text
    a = admin.get(f"/api/trabajadores/{trabajador.id}/proyectos").json()[0]
    assert a["fin"] == hoy_mx().isoformat()


def test_pr_05_reabre_vencido_solo_con_fin_nuevo_sin_restaurar(admin, session, trabajador):
    p = crear(admin, session)
    assert asignar(admin, trabajador, p).status_code == 201
    admin.patch(
        f"/api/proyectos/{p['id']}",
        json={
            "inicio": (hoy_mx() - timedelta(days=5)).isoformat(),
            "fin_estimado": (hoy_mx() - timedelta(days=1)).isoformat(),
        },
    )
    admin.post(f"/api/proyectos/{p['id']}/cierre", json={"motivo": "Terminado"})
    assert admin.post(f"/api/proyectos/{p['id']}/reapertura", json={}).status_code == 422
    r = admin.post(
        f"/api/proyectos/{p['id']}/reapertura",
        json={"fin_estimado": (hoy_mx() + timedelta(days=5)).isoformat()},
    )
    assert r.status_code == 200 and r.json()["trabajadores_asignados"] == 0


def test_pr_06_vencido_sigue_activo_pero_no_asignable(admin, session, trabajador):
    p = crear(
        admin,
        session,
        inicio=(hoy_mx() - timedelta(days=5)).isoformat(),
        fin_estimado=(hoy_mx() - timedelta(days=1)).isoformat(),
    )
    assert p["estado"] == "ACTIVO" and p["situacion"] == "FIN_VENCIDO"
    assert asignar(admin, trabajador, p).status_code == 422
    assert admin.get("/api/proyectos?asignables=true").json()["total"] == 0


def test_pr_07_rh_sin_almacen_ve_generales(admin, session, cliente_como):
    p = crear(admin, session)
    r = cliente_como("Recursos Humanos").get(f"/api/proyectos/{p['id']}")
    assert r.status_code == 200, r.text
    assert "valor" not in r.json() and "consumo" not in r.json()


def test_pr_13_cambio_conserva_historial_y_principal(admin, session, trabajador):
    p = crear(admin, session)
    p2 = crear(admin, session, clave="PR-DOS")
    r = asignar(admin, trabajador, p)
    assert r.status_code == 201, r.text
    vieja = r.json()[0]
    r = asignar(admin, trabajador, p2, reemplaza_asignacion_id=vieja["id"])
    assert r.status_code == 201, r.text
    actual = [a for a in r.json() if a["terminada_en"] is None]
    assert len(actual) == 1 and actual[0]["principal"]
    assert len(r.json()) == 2


def test_pr_13_duplicado_y_segundo_proyecto_un_solo_principal(admin, session, trabajador):
    p = crear(admin, session)
    p2 = crear(admin, session, clave="PR-DOS")
    assert asignar(admin, trabajador, p).status_code == 201
    assert asignar(admin, trabajador, p).status_code == 409
    r = asignar(admin, trabajador, p2)
    assert r.status_code == 201 and sum(a["principal"] for a in r.json()) == 1


def test_pr_13_terminar_ultima_deja_sin_proyecto(admin, session, trabajador):
    p = crear(admin, session)
    a = asignar(admin, trabajador, p).json()[0]
    r = admin.post(f"/api/trabajadores/{trabajador.id}/proyectos/{a['id']}/termino")
    assert r.status_code == 200, r.text
    assert r.json()["queda_sin_proyecto"]
    assert (
        admin.post(f"/api/trabajadores/{trabajador.id}/proyectos/{a['id']}/termino").status_code
        == 409
    )


def test_ac_37_proyectos_de_dos_almacenes_y_detalle_ajeno_404(
    admin, session, crear_usuario, app, iniciar_sesion
):
    from fastapi.testclient import TestClient

    from app.modulos.acceso.models import Usuario, UsuarioAlmacen

    p = crear(admin, session)
    p2 = crear(admin, session, clave="HYL-UNO", almacen="HYL")
    p3 = crear(admin, session, clave="LAM-UNO", almacen="LAM")
    cred = crear_usuario({"proyectos.ver"}, almacen="MID")
    usuario = session.scalar(select(Usuario).where(Usuario.usuario == cred.usuario))
    hyl = session.scalar(select(Almacen).where(Almacen.clave == "HYL"))
    session.add(UsuarioAlmacen(usuario_id=usuario.id, almacen_id=hyl.id))
    session.commit()
    with TestClient(app) as cliente:
        assert iniciar_sesion(cliente, cred).status_code == 200
        r = cliente.get("/api/proyectos")
        assert r.status_code == 200, r.text
        assert {p["id"], p2["id"]} <= {a["id"] for a in r.json()["elementos"]}
        assert p3["id"] not in {a["id"] for a in r.json()["elementos"]}
        assert cliente.get(f"/api/proyectos/{p2['id']}").status_code == 200
        assert cliente.get(f"/api/proyectos/{p3['id']}").status_code == 404
        assert cliente.get(f"/api/proyectos?almacen_id={p3['almacen']['id']}").json()["total"] == 0


@pytest.mark.parametrize("mismo", [True, False])
def test_pr_13_asignaciones_concurrentes_mysql(engine, mismo):
    import uuid
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy import delete
    from sqlalchemy.orm import Session

    from app.modulos.acceso.models import Usuario
    from app.modulos.proyectos.exceptions import AsignacionRepetida
    from app.modulos.proyectos.models import AsignacionProyecto, Proyecto
    from app.modulos.proyectos.schemas import AsignacionIn, ProyectoCreate
    from app.modulos.proyectos.service import ProyectoService

    barrera = Barrier(2)
    tids = []
    pids = []
    try:
        with Session(engine, expire_on_commit=False) as db:
            actor = db.scalar(select(Usuario).where(Usuario.usuario == "admin"))
            # El usuario inicial puede variar; se resuelve por permiso protegido.
            if actor is None:
                from app.modulos.acceso.models import Rol

                actor = db.scalar(select(Usuario).join(Rol).where(Rol.protegido.is_(True)))
            actor_id = actor.id
            t = Trabajador(numero_empleado=f"PR-{uuid.uuid4().hex[:15]}", nombre="Concurrente")
            db.add(t)
            db.commit()
            tids.append(t.id)
            a = db.scalar(select(Almacen).where(Almacen.clave == "MID"))
            for _ in range(2):
                p = ProyectoService(db).crear(
                    ProyectoCreate(
                        clave=f"PR-{uuid.uuid4().hex[:12]}",
                        nombre="Prueba concurrente",
                        almacen_id=a.id,
                        inicio=hoy_mx(),
                        fin_estimado=hoy_mx() + timedelta(days=30),
                    ),
                    actor,
                )
                pids.append(p.id)

        def guardar(numero):
            with Session(engine, expire_on_commit=False) as db:
                actor = db.get(Usuario, actor_id)
                barrera.wait(timeout=10)
                try:
                    ProyectoService(db).asignar(
                        tids[0], AsignacionIn(proyecto_id=pids[0 if mismo else numero]), actor
                    )
                    return "guardado"
                except AsignacionRepetida:
                    return "repetido"

        with ThreadPoolExecutor(max_workers=2) as pool:
            resultados = list(pool.map(guardar, (0, 1)))
        assert resultados.count("guardado") == (1 if mismo else 2)
        if mismo:
            assert resultados.count("repetido") == 1
        with Session(engine) as db:
            activas = db.scalars(
                select(AsignacionProyecto).where(
                    AsignacionProyecto.trabajador_id == tids[0],
                    AsignacionProyecto.terminada_en.is_(None),
                )
            ).all()
            assert sum(a.principal for a in activas) == 1
    finally:
        with engine.begin() as conn:
            conn.execute(
                delete(AsignacionProyecto).where(AsignacionProyecto.trabajador_id.in_(tids))
            )
            conn.execute(delete(Proyecto).where(Proyecto.id.in_(pids)))
            conn.execute(delete(Trabajador).where(Trabajador.id.in_(tids)))


def cuerpo_trabajador(**cambios):
    return {
        "nombre": "Alta con proyecto",
        "puesto": "Ayudante",
        "inicio": hoy_mx().isoformat(),
        "fin": (hoy_mx() + timedelta(days=30)).isoformat(),
        **cambios,
    }


def test_pr_11_alta_obliga_proyecto_y_deriva_area(admin, session):
    r = admin.post("/api/trabajadores", json=cuerpo_trabajador())
    assert r.status_code == 422 and r.json()["codigo"] == "PROYECTO_REQUERIDO"
    p = crear(admin, session)
    r = admin.post(
        "/api/trabajadores", json=cuerpo_trabajador(proyecto_id=p["id"], area_obra="Texto ignorado")
    )
    assert r.status_code == 201, r.text
    assert r.json()["periodo"]["area_obra"] == p["nombre"]
    assert r.json()["proyectos"][0]["principal"]
    assert r.json()["proyectos"][0]["proyecto"]["id"] == p["id"]


def test_pr_11_proyecto_inexistente_vencido_rechazados(admin, session):
    import uuid

    p = crear(
        admin,
        session,
        inicio=(hoy_mx() - timedelta(days=5)).isoformat(),
        fin_estimado=(hoy_mx() - timedelta(days=1)).isoformat(),
    )
    for id in (str(uuid.uuid4()), p["id"]):
        r = admin.post("/api/trabajadores", json=cuerpo_trabajador(proyecto_id=id))
        assert r.status_code == 422 and r.json()["codigo"] == "PROYECTO_INVALIDO"


def test_pr_11_alta_exige_permiso_asignar(admin, session, crear_usuario, app, iniciar_sesion):
    from fastapi.testclient import TestClient

    p = crear(admin, session)
    cred = crear_usuario({"trabajadores.administrar"})
    with TestClient(app) as cliente:
        assert iniciar_sesion(cliente, cred).status_code == 200
        assert (
            cliente.post(
                "/api/trabajadores", json=cuerpo_trabajador(proyecto_id=p["id"])
            ).status_code
            == 403
        )


def test_pr_11_fallo_asignacion_revierte_alta_completa(admin, session, monkeypatch):
    from app.core.excepciones import DatosInvalidos
    from app.modulos.proyectos.service import ProyectoService
    from app.modulos.trabajadores.models import SerieEmpleado

    p = crear(admin, session)
    contador = session.get(SerieEmpleado, 1).ultimo

    def falla(*args, **kwargs):
        raise DatosInvalidos("No se pudo asignar al proyecto.")

    monkeypatch.setattr(ProyectoService, "asignar_en_transaccion", falla)
    r = admin.post(
        "/api/trabajadores", json=cuerpo_trabajador(proyecto_id=p["id"], nombre="Alta a revertir")
    )
    assert r.status_code == 422, r.text
    assert session.scalar(select(Trabajador).where(Trabajador.nombre == "Alta a revertir")) is None
    session.expire_all()
    assert session.get(SerieEmpleado, 1).ultimo == contador


def test_pr_11_reingreso_pide_proyecto_y_conserva_si_asignable(admin, session, trabajador):
    cuerpo = {"inicio": hoy_mx().isoformat(), "fin": (hoy_mx() + timedelta(days=50)).isoformat()}
    r = admin.post(f"/api/trabajadores/{trabajador.id}/periodos", json=cuerpo)
    assert r.status_code == 422 and r.json()["codigo"] == "PROYECTO_REQUERIDO"
    p = crear(admin, session)
    r = admin.post(
        f"/api/trabajadores/{trabajador.id}/periodos", json={**cuerpo, "proyecto_id": p["id"]}
    )
    assert r.status_code == 201, r.text
    assert r.json()["periodo"]["area_obra"] == p["nombre"]
    r = admin.post(f"/api/trabajadores/{trabajador.id}/periodos", json=cuerpo)
    assert r.status_code == 201 and len(r.json()["proyectos"]) == 1


def test_pr_13_principal_explicita_no_reescribe_historial(admin, session, trabajador):
    p = crear(admin, session)
    p2 = crear(admin, session, clave="PR-DOS")
    assert asignar(admin, trabajador, p).status_code == 201
    r = asignar(admin, trabajador, p2, principal=True)
    assert r.status_code == 409, r.text
    assert r.json()["detalles"][0]["regla"] == "PR-13"


def test_pr_03_clave_y_almacen_con_vales_no_cambian(admin, session):
    import uuid

    from app.modulos.movimientos.models import Vale
    from app.modulos.proyectos.models import Proyecto

    p = crear(admin, session)
    proyecto = session.get(Proyecto, uuid.UUID(p["id"]))
    # Fixture de lectura: la ruta de edición no escribe ningún vale.
    session.add(
        Vale(
            id_cliente=uuid.uuid4(),
            tipo="ENTREGA",
            folio="MID-ENT-PR03",
            almacen_id=proyecto.almacen_id,
            proyecto_id=proyecto.id,
            responsable_id=proyecto.creado_por,
            token=uuid.uuid4().hex,
        )
    )
    session.commit()
    r = admin.patch(f"/api/proyectos/{p['id']}", json={"clave": "OTRA-CLAVE"})
    assert r.status_code == 409 and r.json()["codigo"] == "PROYECTO_CON_VALES"
    assert (
        admin.patch(f"/api/proyectos/{p['id']}", json={"nombre": "Nombre editable"}).status_code
        == 200
    )
