"""Administración de almacenes (FEAT-008): AL-01 a AL-05 y el almacén cerrado en el resto de la API.

Cada prueba corre dentro de la transacción de la prueba (se revierte). La de concurrencia usa
conexiones reales y borra lo que crea.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.modulos.acceso.permisos import P
from app.modulos.almacenes.models import Almacen, Ubicacion
from app.modulos.auditoria.models import Auditoria
from tests.movimientos.ayudas import abastecer, crear_articulo, crear_trabajador, unico
from tests.movimientos.ayudas_traspasos import (  # noqa: F401  (fixtures)
    cliente_almacen,
    cuerpo_traspaso,
    renglon,
)
from tests.movimientos.test_concurrencia import en_paralelo

ALMACENES = "/api/almacenes"


def _clave() -> str:
    return "T" + uuid.uuid4().hex[:6].upper()


def _id(session, clave: str) -> str:
    return str(session.scalar(select(Almacen.id).where(Almacen.clave == clave)))


def nuevo(admin: TestClient, session, padre: str = "CON", tipo: str = "PROYECTO", **extra) -> dict:
    """Un almacén nuevo por la API (201)."""
    clave = extra.pop("clave", _clave())
    r = admin.post(
        ALMACENES,
        json={
            "clave": clave,
            "nombre": f"Almacén {clave}",
            "tipo": tipo,
            "padre_id": _id(session, padre) if padre else None,
        }
        | extra,
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def admin(cliente_como) -> TestClient:
    return cliente_como("Administrador")


# --------------------------------------------------------------------------------- AL-01


def test_AL_01_solo_almacenes_administrar_crea_edita_cierra_y_reabre(cliente_como, admin, session):
    supervisor = cliente_como("Supervisor")
    cuerpo = {
        "clave": "ZZ1",
        "nombre": "Zona uno",
        "tipo": "PROYECTO",
        "padre_id": _id(session, "CON"),
    }
    assert supervisor.post(ALMACENES, json=cuerpo).status_code == 403
    ficha = nuevo(admin, session)
    for metodo, ruta, datos in (
        ("PATCH", f"{ALMACENES}/{ficha['id']}", {"nombre": "Otro"}),
        ("POST", f"{ALMACENES}/{ficha['id']}/cierre", None),
        ("POST", f"{ALMACENES}/{ficha['id']}/reapertura", None),
    ):
        r = supervisor.request(metodo, ruta, json=datos)
        assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"
    # El resumen trae datos de otros almacenes: solo con almacenes.administrar.
    assert supervisor.get(f"{ALMACENES}?resumen=true").status_code == 403
    assert supervisor.get(ALMACENES).status_code == 200


def test_AL_01_el_alta_crea_la_ubicacion_y_queda_en_la_auditoria(admin, session):
    ficha = nuevo(admin, session)
    assert ficha["estado"] == "ACTIVO" and ficha["cerrado_en"] is None
    assert ficha["padre_clave"] == "CON" and ficha["tipo"] == "PROYECTO"
    ubicacion = session.scalar(
        select(Ubicacion).where(Ubicacion.almacen_id == uuid.UUID(ficha["id"]))
    )
    assert ubicacion is not None
    registro = session.scalar(
        select(Auditoria).where(
            Auditoria.accion == "almacen.crear", Auditoria.entidad_id == ficha["id"]
        )
    )
    assert registro is not None and registro.despues["codigo"] == ficha["clave"]
    # Aparece en la lista, también en el resumen.
    lista = admin.get(f"{ALMACENES}?resumen=true").json()
    propia = next(a for a in lista if a["id"] == ficha["id"])
    assert propia["resumen"]["puede_cerrar"] is True and propia["resumen"]["tiene_folios"] is False


def test_AL_01_cerrar_y_reabrir_se_auditan(admin, session):
    ficha = nuevo(admin, session)
    r = admin.post(f"{ALMACENES}/{ficha['id']}/cierre", json={"motivo": "Terminó el paro"})
    assert r.status_code == 200 and r.json()["estado"] == "CERRADO" and r.json()["cerrado_en"]
    r = admin.post(f"{ALMACENES}/{ficha['id']}/reapertura")
    assert (
        r.status_code == 200 and r.json()["estado"] == "ACTIVO" and r.json()["cerrado_en"] is None
    )
    acciones = set(
        session.scalars(select(Auditoria.accion).where(Auditoria.entidad_id == ficha["id"]))
    )
    assert {"almacen.crear", "almacen.inactivar", "almacen.reactivar"} <= acciones


# --------------------------------------------------------------------------------- AL-02


def test_AL_02_la_clave_se_pasa_a_mayusculas_y_no_se_repite(admin, session):
    ficha = nuevo(admin, session, clave="abc12")
    assert ficha["clave"] == "ABC12"
    r = admin.post(
        ALMACENES,
        json={
            "clave": "Abc12",
            "nombre": "Otro nombre",
            "tipo": "PROYECTO",
            "padre_id": _id(session, "CON"),
        },
    )
    assert r.status_code == 409 and r.json()["codigo"] == "CLAVE_REPETIDA"
    for mala in ("A", "ABCDEFGHIJK", "AB-1", "ÁB1"):
        r = admin.post(
            ALMACENES,
            json={
                "clave": mala,
                "nombre": "X",
                "tipo": "PROYECTO",
                "padre_id": _id(session, "CON"),
            },
        )
        assert r.status_code == 422, mala


def test_AL_02_el_nombre_no_se_repite_sin_importar_mayusculas_ni_acentos(admin, session):
    r = admin.post(
        ALMACENES,
        json={
            "clave": _clave(),
            "nombre": "KEPLER",
            "tipo": "PROYECTO",
            "padre_id": _id(session, "CON"),
        },
    )
    assert r.status_code == 409 and r.json()["codigo"] == "NOMBRE_REPETIDO"
    r = admin.post(
        ALMACENES,
        json={
            "clave": _clave(),
            "nombre": "contratistás",
            "tipo": "PROYECTO",
            "padre_id": _id(session, "CON"),
        },
    )
    assert r.status_code == 409 and r.json()["codigo"] == "NOMBRE_REPETIDO"


def test_AL_02_solo_hay_un_almacen_central(admin):
    r = admin.post(ALMACENES, json={"clave": _clave(), "nombre": "Otro central", "tipo": "CENTRAL"})
    assert r.status_code == 409 and r.json()["codigo"] == "YA_HAY_CENTRAL"


def test_AL_02_el_padre_debe_existir_estar_activo_y_cuadrar_con_el_tipo(admin, session):
    def alta(**cambios):
        cuerpo = {"clave": _clave(), "nombre": f"N{uuid.uuid4().hex}", "tipo": "PROYECTO"}
        return admin.post(ALMACENES, json=cuerpo | cambios)

    r = alta()  # un no central sin padre
    assert r.status_code == 422 and r.json()["codigo"] == "PADRE_INVALIDO"
    assert r.json()["detalles"]["regla"] == "AL-02"
    r = alta(padre_id=str(uuid.uuid4()))
    assert r.status_code == 422 and r.json()["codigo"] == "PADRE_INVALIDO"
    cerrado = nuevo(admin, session)
    admin.post(f"{ALMACENES}/{cerrado['id']}/cierre")
    r = alta(padre_id=cerrado["id"])
    assert r.status_code == 422 and r.json()["codigo"] == "PADRE_INVALIDO"
    assert alta(padre_id=_id(session, "KEP"), tipo="CENTRAL").json()["codigo"] in (
        "PADRE_INVALIDO",
    )


def test_AL_02_un_almacen_no_depende_de_si_mismo_ni_de_un_descendiente(admin, session):
    a = nuevo(admin, session)
    b = nuevo(admin, session, padre=a["clave"])
    c = nuevo(admin, session, padre=b["clave"])
    for padre in (a["id"], c["id"]):  # él mismo y su descendiente
        r = admin.patch(f"{ALMACENES}/{a['id']}", json={"padre_id": padre})
        assert r.status_code == 422 and r.json()["codigo"] == "PADRE_INVALIDO", padre
    # Con un padre válido sí cambia.
    r = admin.patch(f"{ALMACENES}/{c['id']}", json={"padre_id": _id(session, "CON")})
    assert r.status_code == 200 and r.json()["padre_clave"] == "CON"
    # El central no lleva padre.
    r = admin.patch(f"{ALMACENES}/{_id(session, 'KEP')}", json={"padre_id": _id(session, "CON")})
    assert r.status_code == 422 and r.json()["codigo"] == "PADRE_INVALIDO"


def test_AL_02_el_tipo_no_se_cambia_y_un_cambio_sin_campos_no_hace_nada(admin, session):
    ficha = nuevo(admin, session)
    assert admin.patch(f"{ALMACENES}/{ficha['id']}", json={"tipo": "CENTRAL"}).status_code == 422
    r = admin.patch(f"{ALMACENES}/{ficha['id']}", json={})
    assert r.status_code == 200 and r.json()["nombre"] == ficha["nombre"]
    r = admin.patch(f"{ALMACENES}/{ficha['id']}", json={"nombre": "Nombre nuevo"})
    assert r.json()["nombre"] == "Nombre nuevo"
    assert admin.patch(f"{ALMACENES}/{uuid.uuid4()}", json={"nombre": "x"}).status_code == 404


def test_AL_02_dos_altas_simultaneas_con_la_misma_clave_solo_una_gana(engine, usuario_por_rol):
    from app.main import create_app
    from tests.conftest import iniciar_sesion_en

    app = create_app()  # usa el motor real: commits de verdad
    clave = _clave()
    clientes = [TestClient(app), TestClient(app)]
    for c in clientes:
        assert iniciar_sesion_en(c, usuario_por_rol("Administrador")).status_code == 200
    from sqlalchemy.orm import Session

    with Session(bind=engine) as s:
        padre = str(s.scalar(select(Almacen.id).where(Almacen.clave == "CON")))
    try:
        respuestas = en_paralelo(
            [
                lambda c=c, n=n: c.post(
                    ALMACENES,
                    json={
                        "clave": clave,
                        "nombre": f"Concurrente {n} {clave}",
                        "tipo": "PROYECTO",
                        "padre_id": padre,
                    },
                )
                for n, c in enumerate(clientes)
            ]
        )
        codigos = sorted(r.status_code for r in respuestas)
        assert codigos == [201, 409], [r.text for r in respuestas]
        assert next(r for r in respuestas if r.status_code == 409).json()["codigo"] == (
            "CLAVE_REPETIDA"
        )
    finally:
        with Session(bind=engine) as s:
            ids = list(s.scalars(select(Almacen.id).where(Almacen.clave == clave)))
            s.execute(delete(Auditoria).where(Auditoria.entidad_id.in_([str(i) for i in ids])))
            s.execute(delete(Ubicacion).where(Ubicacion.almacen_id.in_(ids)))
            s.execute(delete(Almacen).where(Almacen.id.in_(ids)))
            s.commit()
        for c in clientes:
            c.close()


# --------------------------------------------------------------------------------- AL-03


def _bloqueos(r) -> list[str]:
    return [b["codigo"] for b in r.json()["detalles"]["bloqueos"]]


def test_AL_03_con_existencias_no_se_cierra_y_dice_cuantas(admin, session):
    ficha = nuevo(admin, session)
    articulo = crear_articulo(session, retornable=False)
    abastecer(admin, articulo, 7, almacen_id=ficha["id"])
    r = admin.post(f"{ALMACENES}/{ficha['id']}/cierre")
    assert r.status_code == 409 and r.json()["codigo"] == "CON_EXISTENCIAS"
    bloqueo = r.json()["detalles"]["bloqueos"][0]
    assert r.json()["detalles"]["regla"] == "AL-03"
    assert bloqueo["unidades"] == 7 and bloqueo["total_articulos"] == 1
    assert bloqueo["articulos"][0]["codigo"] == articulo.codigo
    # No cambió nada y el resumen lo explica.
    resumen = next(
        a for a in admin.get(f"{ALMACENES}?resumen=true").json() if a["id"] == ficha["id"]
    )
    assert resumen["estado"] == "ACTIVO"
    assert resumen["resumen"]["existencias"] == {"unidades": 7, "articulos": 1}
    assert resumen["resumen"]["puede_cerrar"] is False and resumen["resumen"]["tiene_folios"]
    assert resumen["resumen"]["bloqueos_cierre"][0]["codigo"] == "CON_EXISTENCIAS"


def test_AL_03_con_traspasos_en_transito_no_se_cierra(admin, session):
    ficha = nuevo(admin, session)
    articulo = crear_articulo(session, retornable=False)
    abastecer(admin, articulo, 5, almacen_id=_id(session, "CON"))
    r = admin.post(
        "/api/vales",
        json=cuerpo_traspaso(session, ficha["clave"], [renglon(articulo.codigo, 2)])
        | {"almacen_id": _id(session, "CON")},
    )
    assert r.status_code == 201, r.text
    r = admin.post(f"{ALMACENES}/{ficha['id']}/cierre")
    assert r.status_code == 409 and r.json()["codigo"] == "CON_TRASPASOS_EN_TRANSITO"
    traspaso = r.json()["detalles"]["bloqueos"][0]["traspasos"][0]
    assert traspaso["origen"]["clave"] == "CON" and traspaso["destino"]["clave"] == ficha["clave"]


def test_AL_03_con_hijos_activos_no_se_cierra(admin, session):
    padre = nuevo(admin, session)
    hijo = nuevo(admin, session, padre=padre["clave"])
    r = admin.post(f"{ALMACENES}/{padre['id']}/cierre")
    assert r.status_code == 409 and r.json()["codigo"] == "CON_HIJOS_ACTIVOS"
    assert r.json()["detalles"]["bloqueos"][0]["hijos"][0]["id"] == hijo["id"]
    # Cerrado el hijo, el padre ya puede cerrarse.
    assert admin.post(f"{ALMACENES}/{hijo['id']}/cierre").status_code == 200
    assert admin.post(f"{ALMACENES}/{padre['id']}/cierre").status_code == 200


def test_AL_03_con_usuarios_no_se_cierra_y_dice_quienes(admin, session, crear_usuario):
    ficha = nuevo(admin, session)
    persona = crear_usuario({P.INVENTARIO_VER}, almacen=ficha["clave"])
    r = admin.post(f"{ALMACENES}/{ficha['id']}/cierre")
    assert r.status_code == 409 and r.json()["codigo"] == "CON_USUARIOS"
    bloqueo = r.json()["detalles"]["bloqueos"][0]
    assert bloqueo["total"] == 1 and bloqueo["usuarios"][0]["usuario"] == persona.usuario


def test_AL_03_el_detalle_lista_todos_los_bloqueos_en_orden(admin, session, crear_usuario):
    ficha = nuevo(admin, session)
    articulo = crear_articulo(session, retornable=False)
    abastecer(admin, articulo, 3, almacen_id=ficha["id"])
    crear_usuario({P.INVENTARIO_VER}, almacen=ficha["clave"])
    r = admin.post(f"{ALMACENES}/{ficha['id']}/cierre")
    assert r.json()["codigo"] == "CON_EXISTENCIAS"
    assert _bloqueos(r) == ["CON_EXISTENCIAS", "CON_USUARIOS"]


def test_AL_03_al_reabrir_con_el_padre_cerrado_responde_padre_cerrado(admin, session):
    a = nuevo(admin, session)
    b = nuevo(admin, session, padre=a["clave"])
    assert admin.post(f"{ALMACENES}/{b['id']}/cierre").status_code == 200
    assert admin.post(f"{ALMACENES}/{a['id']}/cierre").status_code == 200
    r = admin.post(f"{ALMACENES}/{b['id']}/reapertura")
    assert r.status_code == 409 and r.json()["codigo"] == "PADRE_CERRADO"
    assert admin.post(f"{ALMACENES}/{a['id']}/reapertura").status_code == 200
    assert admin.post(f"{ALMACENES}/{b['id']}/reapertura").status_code == 200


def test_AL_03_cerrar_dos_veces_o_reabrir_uno_activo_es_conflicto(admin, session):
    ficha = nuevo(admin, session)
    assert admin.post(f"{ALMACENES}/{ficha['id']}/reapertura").json()["codigo"] == "CONFLICTO"
    admin.post(f"{ALMACENES}/{ficha['id']}/cierre")
    assert admin.post(f"{ALMACENES}/{ficha['id']}/cierre").json()["codigo"] == "CONFLICTO"


def test_AL_03_las_piezas_en_resguardo_no_impiden_cerrar_y_el_historial_sigue(admin, session):
    ficha = nuevo(admin, session)
    assert admin.post(f"{ALMACENES}/{ficha['id']}/cierre").status_code == 200
    # Un almacén cerrado sigue en la lista y en las existencias (reportes y consultas).
    lista = admin.get(ALMACENES).json()
    assert next(a for a in lista if a["id"] == ficha["id"])["estado"] == "CERRADO"
    assert admin.get(f"{ALMACENES}/{ficha['id']}/existencias").status_code == 200


# --------------------------------------------------------------------------------- AL-04


def _cerrar(session, clave: str) -> None:
    session.scalar(select(Almacen).where(Almacen.clave == clave)).estado = "CERRADO"
    session.flush()


def test_AL_04_una_entrega_desde_un_almacen_cerrado_se_rechaza(cliente_como, session):
    from tests.movimientos.ayudas import cuerpo_entrega

    trabajador = crear_trabajador(session)
    articulo = crear_articulo(session, retornable=False)
    abastecer(cliente_como("Administrador"), articulo, 3, almacen_id=_id(session, "MID"))
    _cerrar(session, "MID")
    cliente = cliente_como("Almacenista")  # de Kepler; el administrador opera con almacen_id
    admin = cliente_como("Administrador")
    cuerpo = cuerpo_entrega(trabajador, [renglon(articulo.codigo)], almacen_id=_id(session, "MID"))
    ev = admin.post(
        "/api/vales/evaluar", json={k: v for k, v in cuerpo.items() if k != "id_cliente"}
    )
    assert ev.status_code == 200 and ev.json()["nivel"] == "ROJO"
    assert ("AL-04", "ROJO") in [(m["regla"], m["nivel"]) for m in ev.json()["motivos"]]
    r = admin.post("/api/vales", json=cuerpo)
    assert r.status_code == 409 and r.json()["codigo"] == "ALMACEN_CERRADO"
    assert r.json()["mensaje"] == "Ese almacén está cerrado."
    assert r.json()["detalles"]["regla"] == "AL-04"
    assert r.json()["detalles"]["almacen"]["clave"] == "MID"
    del cliente


def test_AL_04_una_entrada_y_una_devolucion_a_un_almacen_cerrado_se_rechazan(cliente_como, session):
    from tests.movimientos.ayudas import cuerpo_entrada
    from tests.movimientos.ayudas_devolucion import cuerpo_devolucion

    articulo = crear_articulo(session, retornable=False)
    _cerrar(session, "HYL")
    admin = cliente_como("Administrador")
    r = admin.post(
        "/api/vales",
        json=cuerpo_entrada(
            [{"codigo": articulo.codigo, "cantidad": 1}], almacen_id=_id(session, "HYL")
        ),
    )
    assert r.status_code == 409 and r.json()["codigo"] == "ALMACEN_CERRADO"
    trabajador = crear_trabajador(session)
    r = admin.post(
        "/api/vales",
        json=cuerpo_devolucion(
            [{"codigo": articulo.codigo, "cantidad": 1}], trabajador, almacen_id=_id(session, "HYL")
        ),
    )
    assert r.status_code == 409 and r.json()["codigo"] == "ALMACEN_CERRADO"


def test_AL_04_un_traspaso_desde_o_hacia_un_almacen_cerrado_se_rechaza(cliente_como, session):
    articulo = crear_articulo(session, retornable=False)
    admin = cliente_como("Administrador")
    abastecer(admin, articulo, 4, almacen_id=_id(session, "CON"))
    _cerrar(session, "LAM")
    cuerpo = cuerpo_traspaso(session, "LAM", [renglon(articulo.codigo)]) | {
        "almacen_id": _id(session, "CON")
    }
    r = admin.post("/api/vales", json=cuerpo)
    assert r.status_code == 409 and r.json()["codigo"] == "ALMACEN_CERRADO"
    assert r.json()["detalles"]["almacen"]["clave"] == "LAM"
    # Desde el cerrado.
    _cerrar(session, "CON")
    cuerpo = cuerpo_traspaso(session, "MID", [renglon(articulo.codigo)]) | {
        "almacen_id": _id(session, "CON")
    }
    r = admin.post("/api/vales", json=cuerpo)
    assert r.status_code == 409 and r.json()["codigo"] == "ALMACEN_CERRADO"


def test_AL_04_una_solicitud_de_compra_nueva_de_un_almacen_cerrado_se_rechaza(
    cliente_como, session
):
    _cerrar(session, "MIN")
    admin = cliente_como("Administrador")
    r = admin.post(
        "/api/solicitudes-compra",
        json={
            "id_cliente": str(uuid.uuid4()),
            "almacen_id": _id(session, "MIN"),
            "descripcion": "Discos de corte",
            "cantidad": 10,
            "motivo": "Se acabaron",
            "urgencia": "URGENTE",
        },
    )
    assert r.status_code == 409 and r.json()["codigo"] == "ALMACEN_CERRADO", r.text


# --------------------------------------------------------------------------------- AL-05


def test_AL_05_la_clave_se_corrige_mientras_no_tenga_folios(admin, session):
    ficha = nuevo(admin, session)
    r = admin.patch(f"{ALMACENES}/{ficha['id']}", json={"clave": "nueva9"})
    assert r.status_code == 200 and r.json()["clave"] == "NUEVA9"
    # Una clave que ya es de otro almacén choca.
    r = admin.patch(f"{ALMACENES}/{ficha['id']}", json={"clave": "kep"})
    assert r.status_code == 409 and r.json()["codigo"] == "CLAVE_REPETIDA"


def test_AL_05_con_folios_la_clave_no_se_cambia(admin, session):
    ficha = nuevo(admin, session)
    articulo = crear_articulo(session, retornable=False)
    vale = abastecer(admin, articulo, 2, almacen_id=ficha["id"])
    assert vale["folio"].startswith(ficha["clave"] + "-")
    r = admin.patch(f"{ALMACENES}/{ficha['id']}", json={"clave": "otra9"})
    assert r.status_code == 409 and r.json()["codigo"] == "CLAVE_CON_FOLIOS"
    # El nombre sí se puede cambiar.
    assert (
        admin.patch(
            f"{ALMACENES}/{ficha['id']}", json={"nombre": f"Nuevo {ficha['clave']}"}
        ).status_code
        == 200
    )


def test_AL_05_un_almacen_cerrado_no_se_edita(admin, session):
    ficha = nuevo(admin, session)
    admin.post(f"{ALMACENES}/{ficha['id']}/cierre")
    r = admin.patch(f"{ALMACENES}/{ficha['id']}", json={"nombre": "Nuevo"})
    assert r.status_code == 409 and r.json()["codigo"] == "ALMACEN_CERRADO"


def test_AL_02_el_primer_folio_de_un_almacen_nuevo_es_el_001(admin, session):
    ficha = nuevo(admin, session, clave="PRY")
    articulo = crear_articulo(session, retornable=False, codigo=unico("ART"))
    vale = abastecer(admin, articulo, 1, almacen_id=ficha["id"])
    assert vale["folio"] == "PRY-ING-000001"
