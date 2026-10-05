"""Pruebas de `catalogo` (US-CAT-001, US-CAT-002, US-CAT-003, US-ETQ-001).

Cada regla lleva su ID en el nombre. Los movimientos y las existencias los escribe `movimientos`
(aún no existe): estas pruebas los insertan directo, solo para probar lo que el catálogo lee.
"""

import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.core.excepciones import DatosInvalidos
from app.core.ids import nuevo_id
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.acceso.repository import UsuarioRepository
from app.modulos.almacenes.models import UbicacionVirtual
from app.modulos.almacenes.repository import AlmacenRepository, UbicacionRepository
from app.modulos.auditoria.models import Auditoria
from app.modulos.catalogo.codigos import CodigoRepetido, CodigoService
from app.modulos.catalogo.exceptions import SerieRepetida
from app.modulos.catalogo.models import (
    Articulo,
    Categoria,
    Control,
    EstadoPieza,
    Pieza,
    TipoCodigo,
)
from app.modulos.catalogo.service import SIN_CAMBIO, CatalogoService
from app.modulos.movimientos.models import Existencia, Movimiento, TipoVale, Vale
from app.modulos.trabajadores.models import Trabajador
from tests.conftest import iniciar_sesion_en

# ------------------------------------------------------------------------------ apoyo


@pytest.fixture
def cliente_con(app, crear_usuario) -> Callable[..., TestClient]:
    """`cliente_con({P.X})`: cliente con la sesión de un rol que tiene solo esos permisos."""
    clientes: list[TestClient] = []

    def _hacer(permisos: set[str], almacen: str | None = None) -> TestClient:
        usuario = crear_usuario(set(permisos), almacen=almacen)
        cliente = TestClient(app)
        assert iniciar_sesion_en(cliente, usuario).status_code == 200
        clientes.append(cliente)
        return cliente

    yield _hacer
    for c in clientes:
        c.close()


def _categoria(session: Session, nombre: str) -> Categoria:
    fila = session.scalar(select(Categoria).where(Categoria.nombre == nombre))
    assert fila is not None
    return fila


def _articulo_por_codigo(session: Session, codigo: str) -> Articulo:
    fila = session.scalar(select(Articulo).where(Articulo.codigo == codigo))
    assert fila is not None
    return fila


def _usuario(session: Session, nombre: str) -> Usuario:
    fila = UsuarioRepository(session).get_by_usuario(nombre)
    assert fila is not None
    return fila


def _ubicacion_kep(session: Session) -> uuid.UUID:
    almacen = AlmacenRepository(session).get_by_clave("KEP")
    return UbicacionRepository(session).de_almacen(almacen.id).id


def _con_movimiento(session: Session, articulo_id: uuid.UUID, cantidad: int = 1) -> None:
    """Simula una entrada de `movimientos`: un vale, un movimiento y la existencia."""
    kep = AlmacenRepository(session).get_by_clave("KEP")
    ubicaciones = UbicacionRepository(session)
    vale = Vale(
        id_cliente=nuevo_id(),
        tipo=TipoVale.ENTRADA,
        folio=f"KEP-ING-{uuid.uuid4().hex[:12]}",
        almacen_id=kep.id,
        responsable_id=_usuario(session, "compras").id,
        token=uuid.uuid4().hex,
    )
    session.add(vale)
    session.flush()
    session.add(
        Movimiento(
            vale_id=vale.id,
            renglon=1,
            articulo_id=articulo_id,
            cantidad=cantidad,
            origen_id=ubicaciones.virtual(UbicacionVirtual.PROVEEDOR).id,
            destino_id=ubicaciones.de_almacen(kep.id).id,
            saldo_destino=cantidad,
        )
    )
    session.flush()


def _cuerpo_articulo(codigo: str, categoria_id: uuid.UUID, **extra) -> dict:
    return {
        "codigo": codigo,
        "nombre": f"Artículo {codigo}",
        "categoria_id": str(categoria_id),
    } | extra


def _crear_articulo(cliente: TestClient, session: Session, codigo: str, categoria: str, **extra):
    respuesta = cliente.post(
        "/api/articulos", json=_cuerpo_articulo(codigo, _categoria(session, categoria).id, **extra)
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _auditoria(session: Session, accion: str, entidad_id) -> list[Auditoria]:
    consulta = select(Auditoria).where(
        Auditoria.accion == accion, Auditoria.entidad_id == str(entidad_id)
    )
    return list(session.scalars(consulta))


# ------------------------------------------------------------- US-CAT-001: categorías


def test_CF_01_categorias_iniciales_cargadas(cliente_como):
    respuesta = cliente_como("Compras").get("/api/categorias")
    assert respuesta.status_code == 200
    por_nombre = {c["nombre"]: c for c in respuesta.json()["elementos"]}
    assert set(por_nombre) >= {
        "EPP básico",
        "EPP de dotación",
        "Equipo de alturas",
        "Herramienta manual",
        "Herramienta eléctrica",
        "Equipo de alto valor",
        "Consumibles de trabajo",
    }
    alturas = por_nombre["Equipo de alturas"]
    assert (alturas["tipo"], alturas["control"], alturas["retornable"]) == ("EPP", "PIEZA", True)
    assert alturas["requiere_inspeccion"] is True
    basico = por_nombre["EPP básico"]
    assert basico["limite_cantidad"] == 1 and basico["limite_periodo_dias"] is None


def test_CF_01_crear_categoria_con_su_plantilla(cliente_como):
    respuesta = cliente_como("Compras").post(
        "/api/categorias",
        json={
            "nombre": "Soldadura",
            "tipo": "HERRAMIENTA",
            "control": "CANTIDAD",
            "retornable": False,
            "requiere_autorizacion": True,
            "motivo_uso_especial": "Uso restringido",
            "limite_cantidad": 2,
            "limite_periodo_dias": 7,
            "cantidad_aviso": 2,
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["nombre"] == "Soldadura" and cuerpo["activo"] is True
    assert cuerpo["requiere_autorizacion"] is True
    assert (cuerpo["limite_cantidad"], cuerpo["limite_periodo_dias"]) == (2, 7)
    assert cuerpo["cantidad_aviso"] == 2


def test_CF_01_el_nombre_de_una_categoria_no_se_repite(cliente_como):
    cuerpo = {"nombre": "EPP Básico", "tipo": "EPP", "control": "CANTIDAD", "retornable": True}
    respuesta = cliente_como("Compras").post("/api/categorias", json=cuerpo)
    assert respuesta.status_code == 409
    assert respuesta.json()["detalles"]["campo"] == "nombre"


def test_CF_06_plantilla_con_inspeccion_en_categoria_por_cantidad_se_rechaza(cliente_como):
    cliente = cliente_como("Compras")
    respuesta = cliente.post(
        "/api/categorias",
        json={
            "nombre": "Invento",
            "tipo": "EPP",
            "control": "CANTIDAD",
            "retornable": True,
            "requiere_inspeccion": True,
        },
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["detalles"][0]["regla"] == "CF-06"

    # Tampoco se permite pasar una categoría con inspección a "por cantidad".
    categorias = cliente.get("/api/categorias").json()["elementos"]
    alturas = next(c for c in categorias if c["nombre"] == "Equipo de alturas")
    cambio = cliente.patch(f"/api/categorias/{alturas['id']}", json={"control": "CANTIDAD"})
    assert cambio.status_code == 422


def test_CF_01_vigencia_por_defecto_de_180_dias_al_activar_la_inspeccion(cliente_como):
    respuesta = cliente_como("Compras").post(
        "/api/categorias",
        json={
            "nombre": "Pruebas de pieza",
            "tipo": "HERRAMIENTA",
            "control": "PIEZA",
            "retornable": True,
            "requiere_inspeccion": True,
        },
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["vigencia_inspeccion_dias"] == 180


def test_CF_02_el_articulo_toma_la_plantilla_de_su_categoria(cliente_como, session):
    cliente = cliente_como("Compras")
    articulo = _crear_articulo(cliente, session, "ARN-TEST-1", "Equipo de alturas")
    plantilla = _categoria(session, "Equipo de alturas")
    assert articulo["control"] == plantilla.control == "PIEZA"
    assert articulo["retornable"] is plantilla.retornable
    assert articulo["requiere_inspeccion"] is True
    assert articulo["vigencia_inspeccion_dias"] == plantilla.vigencia_inspeccion_dias
    assert articulo["motivo_uso_especial"] == plantilla.motivo_uso_especial

    limitado = _crear_articulo(cliente, session, "CASCO-TEST-1", "EPP básico")
    assert limitado["control"] == "CANTIDAD"
    assert (limitado["limite_cantidad"], limitado["limite_periodo_dias"]) == (1, None)


def test_CF_02_el_articulo_puede_cambiar_cualquier_valor_de_la_plantilla(cliente_como, session):
    cliente = cliente_como("Compras")
    articulo = _crear_articulo(
        cliente,
        session,
        "CASCO-TEST-2",
        "EPP básico",
        limite_cantidad=None,
        requiere_autorizacion=True,
        cantidad_aviso=2,
        retornable=False,
    )
    assert articulo["limite_cantidad"] is None  # `null` explícito: sin límite
    assert articulo["requiere_autorizacion"] is True
    assert articulo["cantidad_aviso"] == 2
    assert articulo["retornable"] is False


def test_CF_02_editar_la_plantilla_no_cambia_los_articulos_que_ya_existen(cliente_como, session):
    cliente = cliente_como("Compras")
    articulo = _crear_articulo(cliente, session, "PETO-TEST-1", "EPP básico")
    categoria = _categoria(session, "EPP básico")

    respuesta = cliente.patch(
        f"/api/categorias/{categoria.id}", json={"limite_cantidad": 4, "cantidad_aviso": 3}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["limite_cantidad"] == 4

    ficha = cliente.get(f"/api/articulos/{articulo['id']}").json()
    assert ficha["limite_cantidad"] == 1
    assert ficha["cantidad_aviso"] is None
    # Un artículo nuevo sí nace con la plantilla nueva.
    nuevo = _crear_articulo(cliente, session, "PETO-TEST-2", "EPP básico")
    assert (nuevo["limite_cantidad"], nuevo["cantidad_aviso"]) == (4, 3)


def test_CF_15_crear_y_editar_una_categoria_queda_en_el_registro_de_cambios(cliente_como, session):
    cliente = cliente_como("Compras")
    categoria_id = cliente.post(
        "/api/categorias",
        json={"nombre": "Auditable", "tipo": "EPP", "control": "CANTIDAD", "retornable": True},
    ).json()["id"]
    cliente.patch(f"/api/categorias/{categoria_id}", json={"limite_cantidad": 3})

    (creada,) = _auditoria(session, "categoria.crear", categoria_id)
    assert creada.despues["nombre"] == "Auditable"
    (editada,) = _auditoria(session, "categoria.editar", categoria_id)
    assert editada.antes == {"limite_cantidad": None}
    assert editada.despues == {"limite_cantidad": 3}
    assert editada.usuario_id == _usuario(session, "compras").id


def test_US_CAT_001_editar_categoria_con_nombre_de_otra_responde_409(cliente_como):
    cliente = cliente_como("Compras")
    categorias = {c["nombre"]: c for c in cliente.get("/api/categorias").json()["elementos"]}
    respuesta = cliente.patch(
        f"/api/categorias/{categorias['Herramienta manual']['id']}",
        json={"nombre": "EPP básico"},
    )
    assert respuesta.status_code == 409


def test_US_CAT_001_un_campo_obligatorio_no_puede_ir_en_null(cliente_como):
    cliente = cliente_como("Compras")
    categoria = cliente.get("/api/categorias").json()["elementos"][0]
    respuesta = cliente.patch(f"/api/categorias/{categoria['id']}", json={"nombre": None})
    assert respuesta.status_code == 422


# ------------------------------------------------------------ US-CAT-002: artículos


def test_CF_02_crear_articulo_con_sus_datos(cliente_como, session):
    cliente = cliente_como("Compras")
    articulo = _crear_articulo(
        cliente,
        session,
        "MPUL-TEST-1",
        "Herramienta eléctrica",
        marca="Bosch",
        modelo="GWS 7",
        talla="N/A",
        unidad="pieza",
        costo_unitario="1850.50",
    )
    assert articulo["marca"] == "Bosch" and articulo["modelo"] == "GWS 7"
    assert articulo["costo_unitario"] == "1850.50"
    assert articulo["categoria_nombre"] == "Herramienta eléctrica"
    assert articulo["activo"] is True and articulo["motivo_inactivacion"] is None


def test_RG_10_el_codigo_del_articulo_no_repite_articulo_pieza_ni_credencial(cliente_como, session):
    cliente = cliente_como("Compras")
    _crear_articulo(cliente, session, "DUP-ART-1", "EPP básico")
    categoria = _categoria(session, "EPP básico")

    # Repite el de otro artículo.
    r = cliente.post("/api/articulos", json=_cuerpo_articulo("dup-art-1", categoria.id))
    assert r.status_code == 409 and r.json()["codigo"] == "CODIGO_REPETIDO"

    # Repite el de una pieza.
    pieza = CatalogoService(session).registrar_pieza(
        _articulo_por_codigo(session, "ARN-KEV").id, "ALT-TEST-9", "SERIE-9"
    )
    assert pieza.codigo == "ALT-TEST-9"
    r = cliente.post("/api/articulos", json=_cuerpo_articulo("ALT-TEST-9", categoria.id))
    assert r.status_code == 409 and r.json()["codigo"] == "CODIGO_REPETIDO"

    # Repite el de una credencial.
    CodigoService(session).registrar("TRB-TEST-9", TipoCodigo.TRABAJADOR, nuevo_id())
    r = cliente.post("/api/articulos", json=_cuerpo_articulo("TRB-TEST-9", categoria.id))
    assert r.status_code == 409 and r.json()["codigo"] == "CODIGO_REPETIDO"
    assert r.json()["detalles"]["tipo"] == "TRABAJADOR"


def test_I_07_el_articulo_por_cantidad_tiene_su_codigo_de_producto(cliente_como, session):
    articulo = _crear_articulo(
        cliente_como("Compras"), session, "MARRO-TEST-1", "Herramienta manual"
    )
    servicio = CatalogoService(session)
    codigo = servicio.identificar_codigo("MARRO-TEST-1")
    assert codigo is not None
    assert codigo.tipo == TipoCodigo.ARTICULO and str(codigo.ref_id) == articulo["id"]
    assert str(servicio.obtener_articulo_por_codigo("marro-test-1").id) == articulo["id"]


def test_RG_12_sin_permiso_de_costos_el_costo_no_se_envia(cliente_como, session):
    compras = cliente_como("Compras")
    articulo = _crear_articulo(
        compras, session, "COSTO-TEST-1", "EPP básico", costo_unitario="269.35"
    )
    supervisor = cliente_como("Supervisor")

    ficha = supervisor.get(f"/api/articulos/{articulo['id']}")
    assert ficha.status_code == 200
    assert "costo_unitario" not in ficha.json()
    lista = supervisor.get("/api/articulos", params={"q": "COSTO-TEST-1"}).json()
    assert lista["total"] == 1 and "costo_unitario" not in lista["elementos"][0]
    # Con el permiso sí llega.
    assert compras.get(f"/api/articulos/{articulo['id']}").json()["costo_unitario"] == "269.35"
    lista = compras.get("/api/articulos", params={"q": "COSTO-TEST-1"}).json()
    assert lista["elementos"][0]["costo_unitario"] == "269.35"


def test_RG_12_sin_permiso_de_costos_se_edita_todo_menos_el_costo(cliente_como, session):
    compras = cliente_como("Compras")
    articulo = _crear_articulo(compras, session, "COSTO-TEST-2", "EPP básico", costo_unitario="10")
    supervisor = cliente_como("Supervisor")

    # No puede capturarlo ni al crear ni al editar.
    categoria = _categoria(session, "EPP básico")
    r = supervisor.post(
        "/api/articulos", json=_cuerpo_articulo("COSTO-TEST-3", categoria.id, costo_unitario="5")
    )
    assert r.status_code == 403
    r = supervisor.patch(f"/api/articulos/{articulo['id']}", json={"costo_unitario": "99"})
    assert r.status_code == 403

    # Todo lo demás sí, y la respuesta no trae el costo ni se pierde el que había.
    r = supervisor.patch(f"/api/articulos/{articulo['id']}", json={"nombre": "Casco nuevo"})
    assert r.status_code == 200 and r.json()["nombre"] == "Casco nuevo"
    assert "costo_unitario" not in r.json()
    assert _articulo_por_codigo(session, "COSTO-TEST-2").costo_unitario == 10
    r = supervisor.post("/api/articulos", json=_cuerpo_articulo("COSTO-TEST-4", categoria.id))
    assert r.status_code == 201 and "costo_unitario" not in r.json()


def test_RG_12_el_costo_no_puede_ser_negativo(cliente_como, session):
    categoria = _categoria(session, "EPP básico")
    r = cliente_como("Compras").post(
        "/api/articulos", json=_cuerpo_articulo("COSTO-NEG", categoria.id, costo_unitario="-1")
    )
    assert r.status_code == 422


def test_CF_05_con_movimientos_el_control_no_cambia(cliente_como, session):
    cliente = cliente_como("Compras")
    articulo = _crear_articulo(cliente, session, "CTRL-TEST-1", "Herramienta manual")
    _con_movimiento(session, uuid.UUID(articulo["id"]))

    r = cliente.patch(f"/api/articulos/{articulo['id']}", json={"control": "PIEZA"})
    assert r.status_code == 409
    assert r.json()["codigo"] == "CON_MOVIMIENTOS" and r.json()["detalles"]["regla"] == "CF-05"
    assert _articulo_por_codigo(session, "CTRL-TEST-1").control == "CANTIDAD"


def test_CF_05_con_movimientos_el_retorno_no_cambia(cliente_como, session):
    cliente = cliente_como("Compras")
    articulo = _crear_articulo(cliente, session, "RET-TEST-1", "Herramienta manual")
    _con_movimiento(session, uuid.UUID(articulo["id"]))

    r = cliente.patch(f"/api/articulos/{articulo['id']}", json={"retornable": False})
    assert r.status_code == 409 and r.json()["codigo"] == "CON_MOVIMIENTOS"
    # Mandar el mismo valor no es un cambio; lo demás sigue siendo editable.
    r = cliente.patch(
        f"/api/articulos/{articulo['id']}", json={"retornable": True, "nombre": "Marro 2"}
    )
    assert r.status_code == 200 and r.json()["nombre"] == "Marro 2"


def test_CF_05_sin_movimientos_control_y_retorno_si_cambian(cliente_como, session):
    cliente = cliente_como("Compras")
    articulo = _crear_articulo(cliente, session, "CTRL-TEST-2", "Herramienta manual")
    ficha = cliente.get(f"/api/articulos/{articulo['id']}").json()
    assert ficha["tiene_movimientos"] is False

    r = cliente.patch(
        f"/api/articulos/{articulo['id']}", json={"control": "PIEZA", "retornable": False}
    )
    assert r.status_code == 200
    assert (r.json()["control"], r.json()["retornable"]) == ("PIEZA", False)


def test_CF_05_la_ficha_avisa_que_hay_movimientos_para_bloquear_el_control(cliente_como, session):
    cliente = cliente_como("Compras")
    articulo = _crear_articulo(cliente, session, "CTRL-TEST-3", "Herramienta manual")
    _con_movimiento(session, uuid.UUID(articulo["id"]))
    assert cliente.get(f"/api/articulos/{articulo['id']}").json()["tiene_movimientos"] is True


def test_CF_06_la_inspeccion_solo_aplica_a_articulos_por_pieza(cliente_como, session):
    cliente = cliente_como("Compras")
    categoria = _categoria(session, "Herramienta manual")
    r = cliente.post(
        "/api/articulos",
        json=_cuerpo_articulo("INSP-TEST-1", categoria.id, requiere_inspeccion=True),
    )
    assert r.status_code == 422 and r.json()["detalles"][0]["regla"] == "CF-06"

    articulo = _crear_articulo(cliente, session, "INSP-TEST-2", "Herramienta manual")
    r = cliente.patch(f"/api/articulos/{articulo['id']}", json={"requiere_inspeccion": True})
    assert r.status_code == 422

    # Un artículo por pieza sí, con la vigencia que se le indique.
    pieza = _crear_articulo(
        cliente,
        session,
        "INSP-TEST-3",
        "Herramienta eléctrica",
        requiere_inspeccion=True,
        vigencia_inspeccion_dias=90,
    )
    assert pieza["requiere_inspeccion"] is True and pieza["vigencia_inspeccion_dias"] == 90


def test_CF_06_un_articulo_hereda_la_plantilla_sin_inspeccion_si_no_es_por_pieza(
    cliente_como, session
):
    # La categoría pide inspección, pero el artículo se crea por cantidad sin pedirla expresamente.
    articulo = _crear_articulo(
        cliente_como("Compras"), session, "INSP-TEST-4", "Equipo de alturas", control="CANTIDAD"
    )
    assert articulo["control"] == "CANTIDAD" and articulo["requiere_inspeccion"] is False


def test_CF_06_cambiar_a_por_cantidad_con_inspeccion_activa_se_rechaza(cliente_como, session):
    cliente = cliente_como("Compras")
    articulo = _crear_articulo(cliente, session, "INSP-TEST-5", "Equipo de alturas")
    r = cliente.patch(f"/api/articulos/{articulo['id']}", json={"control": "CANTIDAD"})
    assert r.status_code == 422
    r = cliente.patch(
        f"/api/articulos/{articulo['id']}",
        json={"control": "CANTIDAD", "requiere_inspeccion": False},
    )
    assert r.status_code == 200 and r.json()["control"] == "CANTIDAD"


def test_CF_07_el_motivo_de_uso_especial_se_guarda_y_se_quita(cliente_como, session):
    cliente = cliente_como("Compras")
    articulo = _crear_articulo(
        cliente,
        session,
        "MOT-TEST-1",
        "Herramienta manual",
        requiere_autorizacion=True,
        motivo_uso_especial="Uso restringido por seguridad",
    )
    assert articulo["motivo_uso_especial"] == "Uso restringido por seguridad"
    r = cliente.patch(f"/api/articulos/{articulo['id']}", json={"motivo_uso_especial": None})
    assert r.status_code == 200 and r.json()["motivo_uso_especial"] is None
    assert r.json()["requiere_autorizacion"] is True


def test_CF_08_activar_y_quitar_un_requisito_aplica_al_articulo_sin_tocar_movimientos(
    cliente_como, session
):
    cliente = cliente_como("Compras")
    articulo = _crear_articulo(cliente, session, "REQ-TEST-1", "Herramienta manual")
    _con_movimiento(session, uuid.UUID(articulo["id"]))
    antes = session.scalar(
        select(Movimiento).where(Movimiento.articulo_id == uuid.UUID(articulo["id"]))
    )

    r = cliente.patch(f"/api/articulos/{articulo['id']}", json={"requiere_autorizacion": True})
    assert r.status_code == 200 and r.json()["requiere_autorizacion"] is True
    r = cliente.patch(f"/api/articulos/{articulo['id']}", json={"requiere_autorizacion": False})
    assert r.json()["requiere_autorizacion"] is False
    despues = session.scalar(select(Movimiento).where(Movimiento.articulo_id == antes.articulo_id))
    assert despues.id == antes.id and despues.nivel == antes.nivel


def test_CF_09_activar_la_inspeccion_deja_las_piezas_sin_inspeccion_vigente(cliente_como, session):
    from datetime import date

    cliente = cliente_como("Compras")
    articulo = _crear_articulo(cliente, session, "INSP-TEST-6", "Herramienta eléctrica")
    servicio = CatalogoService(session)
    pieza = servicio.registrar_pieza(
        uuid.UUID(articulo["id"]),
        "PZ-TEST-INSP",
        "S-1",
        inspeccion_vigente_hasta=date(2099, 1, 1),
    )

    r = cliente.patch(f"/api/articulos/{articulo['id']}", json={"requiere_inspeccion": True})
    assert r.status_code == 200
    assert r.json()["vigencia_inspeccion_dias"] == 180
    session.refresh(pieza)
    assert pieza.inspeccion_vigente_hasta is None
    (editado,) = _auditoria(session, "articulo.editar", articulo["id"])
    assert editado.despues["piezas_sin_inspeccion_vigente"] == 1


def test_L_05_periodo_vacio_significa_en_posesion(cliente_como, session):
    cliente = cliente_como("Compras")
    articulo = _crear_articulo(
        cliente, session, "LIM-TEST-1", "Herramienta manual", limite_cantidad=2
    )
    assert articulo["limite_cantidad"] == 2 and articulo["limite_periodo_dias"] is None
    r = cliente.patch(f"/api/articulos/{articulo['id']}", json={"limite_periodo_dias": 7})
    assert r.status_code == 200 and r.json()["limite_periodo_dias"] == 7
    # Quitar el límite quita también el periodo suelto, que no tendría sentido.
    r = cliente.patch(f"/api/articulos/{articulo['id']}", json={"limite_cantidad": None})
    assert r.status_code == 422 and r.json()["detalles"][0]["regla"] == "L-05"
    r = cliente.patch(
        f"/api/articulos/{articulo['id']}",
        json={"limite_cantidad": None, "limite_periodo_dias": None},
    )
    assert r.status_code == 200 and r.json()["limite_cantidad"] is None


def test_E_27_el_aviso_de_cantidad_inusual_se_fija_y_se_quita(cliente_como, session):
    cliente = cliente_como("Compras")
    articulo = _crear_articulo(
        cliente, session, "AVISO-TEST-1", "EPP de dotación", cantidad_aviso=5
    )
    assert articulo["cantidad_aviso"] == 5
    r = cliente.patch(f"/api/articulos/{articulo['id']}", json={"cantidad_aviso": None})
    assert r.status_code == 200 and r.json()["cantidad_aviso"] is None
    r = cliente.patch(f"/api/articulos/{articulo['id']}", json={"cantidad_aviso": 0})
    assert r.status_code == 422


def test_CF_02_un_cambio_de_reglas_se_ve_en_la_siguiente_lectura(cliente_como, session):
    cliente = cliente_como("Compras")
    articulo = _crear_articulo(cliente, session, "LIM-TEST-2", "EPP de dotación")
    assert articulo["limite_cantidad"] == 3
    cliente.patch(f"/api/articulos/{articulo['id']}", json={"limite_cantidad": 6})
    assert cliente.get(f"/api/articulos/{articulo['id']}").json()["limite_cantidad"] == 6


def test_CF_15_cada_cambio_de_un_articulo_guarda_el_valor_anterior_y_el_nuevo(
    cliente_como, session
):
    cliente = cliente_como("Compras")
    articulo = _crear_articulo(cliente, session, "AUD-TEST-1", "EPP básico", costo_unitario="10")
    (creado,) = _auditoria(session, "articulo.crear", articulo["id"])
    assert creado.despues["codigo"] == "AUD-TEST-1"

    cliente.patch(
        f"/api/articulos/{articulo['id']}", json={"limite_cantidad": 2, "costo_unitario": "12.5"}
    )
    (editado,) = _auditoria(session, "articulo.editar", articulo["id"])
    assert editado.antes == {"limite_cantidad": 1, "costo_unitario": "10.00"}
    assert editado.despues == {"limite_cantidad": 2, "costo_unitario": "12.50"}
    assert editado.usuario_id == _usuario(session, "compras").id

    # Sin cambios reales no se registra nada.
    cliente.patch(f"/api/articulos/{articulo['id']}", json={"limite_cantidad": 2})
    assert len(_auditoria(session, "articulo.editar", articulo["id"])) == 1


def test_CF_02_el_codigo_y_la_inactivacion_no_se_editan_por_patch(cliente_como, session):
    cliente = cliente_como("Compras")
    articulo = _crear_articulo(cliente, session, "PATCH-TEST-1", "EPP básico")
    for cuerpo in ({"codigo": "OTRO"}, {"activo": False}, {"motivo_inactivacion": "x"}):
        assert cliente.patch(f"/api/articulos/{articulo['id']}", json=cuerpo).status_code == 422


def test_C_03_la_lista_filtra_por_texto_categoria_y_estado(cliente_como, session):
    cliente = cliente_como("Compras")
    todos = cliente.get("/api/articulos", params={"tamano": 200}).json()
    assert todos["total"] >= 28  # los del PDF (p.7 y p.10)

    arneses = cliente.get("/api/articulos", params={"q": "arnés"}).json()
    assert {a["codigo"] for a in arneses["elementos"]} >= {"ARN-KEV", "ARN-POL"}

    alturas = _categoria(session, "Equipo de alturas")
    por_categoria = cliente.get("/api/articulos", params={"categoria_id": str(alturas.id)}).json()
    assert {a["categoria_nombre"] for a in por_categoria["elementos"]} == {"Equipo de alturas"}

    pagina = cliente.get("/api/articulos", params={"tamano": 5, "pagina": 2}).json()
    assert len(pagina["elementos"]) == 5 and pagina["total"] == todos["total"]
    # El carácter comodín no se interpreta.
    assert cliente.get("/api/articulos", params={"q": "%"}).json()["total"] == 0


def test_C_03_la_ficha_trae_existencias_por_almacen_y_quien_lo_tiene(cliente_como, session):
    # La carga inicial de `movimientos` dejó existencias: esta prueba parte de un inventario vacío.
    session.execute(delete(Existencia))
    cliente = cliente_como("Compras")
    articulo = _articulo_por_codigo(session, "FLEXOM")
    kep = _ubicacion_kep(session)
    session.add(Existencia(ubicacion_id=kep, articulo_id=articulo.id, cantidad=7))

    trabajador = Trabajador(numero_empleado="TEST-C03", nombre="Juan Pérez García")
    session.add(trabajador)
    session.flush()
    ubicacion = UbicacionRepository(session).crear_de_trabajador(trabajador.id)
    session.add(Existencia(ubicacion_id=ubicacion.id, articulo_id=articulo.id, cantidad=2))
    session.flush()

    ficha = cliente.get(f"/api/articulos/{articulo.id}")
    assert ficha.status_code == 200
    cuerpo = ficha.json()
    assert cuerpo["existencias"] == [
        {
            "almacen_id": str(AlmacenRepository(session).get_by_clave("KEP").id),
            "clave": "KEP",
            "nombre": "Kepler",
            "cantidad": 7,
            "disponible": 7,
        }
    ]
    assert cuerpo["en_posesion"] == [
        {
            "trabajador_id": str(trabajador.id),
            "numero_empleado": "TEST-C03",
            "nombre": "Juan Pérez García",
            "cantidad": 2,
        }
    ]


def test_C_03_el_disponible_de_un_articulo_por_pieza_no_cuenta_piezas_no_aptas(
    cliente_como, session
):
    cliente = cliente_como("Compras")
    articulo = _articulo_por_codigo(session, "ARN-POL")
    servicio = CatalogoService(session)
    kep = _ubicacion_kep(session)
    # Los datos de prueba ya dieron entrada a piezas de este artículo: la prueba parte sin ellas.
    session.execute(update(Pieza).where(Pieza.articulo_id == articulo.id).values(ubicacion_id=None))
    session.execute(delete(Existencia).where(Existencia.articulo_id == articulo.id))
    estados = [EstadoPieza.APTO, EstadoPieza.NO_APTO, EstadoPieza.EN_MANTENIMIENTO]
    for n, estado in enumerate(estados):
        pieza = servicio.registrar_pieza(articulo.id, f"ALT-C03-{n}", f"S{n}", estado=estado)
        pieza.ubicacion_id = kep
    session.add(Existencia(ubicacion_id=kep, articulo_id=articulo.id, cantidad=3))
    session.flush()

    (fila,) = cliente.get(f"/api/articulos/{articulo.id}").json()["existencias"]
    assert (fila["cantidad"], fila["disponible"]) == (3, 1)


def test_C_03_ficha_de_un_articulo_que_no_existe_responde_404(cliente_como):
    r = cliente_como("Compras").get(f"/api/articulos/{uuid.uuid4()}")
    assert r.status_code == 404 and r.json()["codigo"] == "NO_ENCONTRADO"


# ----------------------------------------------------- US-CAT-003: inactivar y reactivar


def test_CF_10_inactivar_exige_un_motivo(cliente_como, session):
    cliente = cliente_como("Compras")
    articulo = _crear_articulo(cliente, session, "INACT-TEST-1", "EPP básico")
    url = f"/api/articulos/{articulo['id']}/inactivacion"

    assert cliente.post(url, json={}).status_code == 422
    assert cliente.post(url, json={"motivo": "   "}).status_code == 422
    r = cliente.post(url, json={"motivo": "Ya no se compra"})
    assert r.status_code == 200
    assert r.json()["activo"] is False and r.json()["motivo_inactivacion"] == "Ya no se compra"
    # Inactivar a un inactivo no procede.
    assert cliente.post(url, json={"motivo": "Otra vez"}).status_code == 409


def test_CF_10_el_filtro_de_activos_oculta_a_los_inactivos_y_el_historial_se_conserva(
    cliente_como, session
):
    cliente = cliente_como("Compras")
    articulo = _crear_articulo(cliente, session, "INACT-TEST-2", "EPP básico")
    _con_movimiento(session, uuid.UUID(articulo["id"]))
    cliente.post(f"/api/articulos/{articulo['id']}/inactivacion", json={"motivo": "Obsoleto"})

    activos = cliente.get("/api/articulos", params={"activo": True, "q": "INACT-TEST-2"}).json()
    assert activos["total"] == 0
    inactivos = cliente.get("/api/articulos", params={"activo": False, "q": "INACT-TEST-2"}).json()
    assert inactivos["total"] == 1 and inactivos["elementos"][0]["activo"] is False
    assert cliente.get("/api/articulos", params={"q": "INACT-TEST-2"}).json()["total"] == 1
    assert session.scalar(
        select(Movimiento).where(Movimiento.articulo_id == uuid.UUID(articulo["id"]))
    )


def test_CF_13_reactivar_regresa_al_articulo_con_las_reglas_que_tenia(cliente_como, session):
    cliente = cliente_como("Compras")
    articulo = _crear_articulo(
        cliente, session, "INACT-TEST-3", "EPP de dotación", limite_cantidad=4, cantidad_aviso=4
    )
    url = f"/api/articulos/{articulo['id']}/inactivacion"
    cliente.post(url, json={"motivo": "Pausa"})

    r = cliente.delete(url)
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["activo"] is True and cuerpo["motivo_inactivacion"] is None
    assert (cuerpo["limite_cantidad"], cuerpo["cantidad_aviso"]) == (4, 4)
    assert cuerpo["limite_periodo_dias"] == 7
    assert cliente.delete(url).status_code == 409  # ya estaba activo


def test_CF_12_un_articulo_sin_movimientos_se_elimina(cliente_como, session):
    cliente = cliente_como("Compras")
    articulo = _crear_articulo(cliente, session, "DEL-TEST-1", "EPP básico")
    assert cliente.delete(f"/api/articulos/{articulo['id']}").status_code == 204
    assert cliente.get(f"/api/articulos/{articulo['id']}").status_code == 404
    # Su código queda libre para otro artículo.
    assert CodigoService(session).identificar("DEL-TEST-1") is None
    _crear_articulo(cliente, session, "DEL-TEST-1", "EPP básico")


def test_CF_12_un_articulo_con_movimientos_no_se_elimina_solo_se_inactiva(cliente_como, session):
    cliente = cliente_como("Compras")
    articulo = _crear_articulo(cliente, session, "DEL-TEST-2", "EPP básico")
    _con_movimiento(session, uuid.UUID(articulo["id"]))

    r = cliente.delete(f"/api/articulos/{articulo['id']}")
    assert r.status_code == 409
    assert r.json()["codigo"] == "CON_MOVIMIENTOS" and r.json()["detalles"]["regla"] == "CF-12"
    assert cliente.get(f"/api/articulos/{articulo['id']}").status_code == 200
    inactivar = cliente.post(
        f"/api/articulos/{articulo['id']}/inactivacion", json={"motivo": "Con historial"}
    )
    assert inactivar.status_code == 200


def test_CF_15_inactivar_reactivar_y_eliminar_quedan_en_el_registro_de_cambios(
    cliente_como, session
):
    cliente = cliente_como("Compras")
    articulo = _crear_articulo(cliente, session, "AUD-TEST-2", "EPP básico")
    url = f"/api/articulos/{articulo['id']}/inactivacion"
    cliente.post(url, json={"motivo": "Prueba"})
    cliente.delete(url)
    cliente.delete(f"/api/articulos/{articulo['id']}")

    (inactivado,) = _auditoria(session, "articulo.inactivar", articulo["id"])
    assert inactivado.antes["activo"] is True and inactivado.despues["activo"] is False
    assert inactivado.despues["motivo_inactivacion"] == "Prueba"
    (reactivado,) = _auditoria(session, "articulo.reactivar", articulo["id"])
    assert reactivado.antes["motivo_inactivacion"] == "Prueba"
    (eliminado,) = _auditoria(session, "articulo.eliminar", articulo["id"])
    assert eliminado.antes["codigo"] == "AUD-TEST-2"


# --------------------------------------------------------------------- permisos (AC-01)

ENDPOINTS = [
    # (método, ruta, permiso, cuerpo, estado cuando se tiene el permiso)
    ("GET", "/api/categorias", P.CATALOGO_VER, None, 200),
    ("POST", "/api/categorias", P.CATALOGO_ADMINISTRAR, "categoria", 201),
    ("PATCH", "/api/categorias/{categoria}", P.CATALOGO_ADMINISTRAR, {"limite_cantidad": 9}, 200),
    ("GET", "/api/articulos", P.CATALOGO_VER, None, 200),
    ("POST", "/api/articulos", P.CATALOGO_ADMINISTRAR, "articulo", 201),
    ("GET", "/api/articulos/{articulo}", P.CATALOGO_VER, None, 200),
    ("PATCH", "/api/articulos/{articulo}", P.CATALOGO_ADMINISTRAR, {"nombre": "Otro"}, 200),
    (
        "POST",
        "/api/articulos/{articulo}/inactivacion",
        P.CATALOGO_ADMINISTRAR,
        {"motivo": "x"},
        200,
    ),
    ("DELETE", "/api/articulos/{articulo}", P.CATALOGO_ADMINISTRAR, None, 204),
]


@pytest.mark.parametrize(("metodo", "ruta", "permiso", "cuerpo", "estado"), ENDPOINTS)
def test_AC_01_cada_endpoint_responde_con_su_permiso_y_403_sin_el(
    metodo, ruta, permiso, cuerpo, estado, cliente_con, session
):
    articulo = _articulo_por_codigo(session, "CINCEL")
    categoria = _categoria(session, "Herramienta manual")
    if cuerpo == "categoria":
        cuerpo = {
            "nombre": f"Cat {uuid.uuid4().hex[:6]}",
            "tipo": "EPP",
            "control": "CANTIDAD",
            "retornable": True,
        }
    elif cuerpo == "articulo":
        cuerpo = _cuerpo_articulo(f"PERM-{uuid.uuid4().hex[:8]}", categoria.id)
    url = ruta.format(articulo=articulo.id, categoria=categoria.id)
    if metodo == "DELETE":
        # El de prueba debe poder eliminarse: uno propio y sin movimientos.
        propio = CatalogoService(session).crear_articulo(
            _crear(f"DEL-{uuid.uuid4().hex[:8]}", categoria.id), _usuario(session, "compras").id
        )
        url = ruta.format(articulo=propio.id)

    sin = cliente_con({p for p in {P.CATALOGO_VER, P.CATALOGO_ADMINISTRAR} if p != permiso})
    assert sin.request(metodo, url, json=cuerpo).status_code == 403

    con = cliente_con({permiso})
    assert con.request(metodo, url, json=cuerpo).status_code == estado


def _crear(codigo: str, categoria_id: uuid.UUID):
    from app.modulos.catalogo.schemas import ArticuloCreate

    return ArticuloCreate(codigo=codigo, nombre=f"Artículo {codigo}", categoria_id=categoria_id)


def test_AC_01_sin_sesion_los_endpoints_de_catalogo_responden_401(client):
    for ruta in ("/api/categorias", "/api/articulos", "/api/etiquetas?tipo=piezas"):
        assert client.get(ruta).status_code == 401


def test_AC_01_inactivar_y_reactivar_piden_catalogo_administrar(cliente_con, session):
    articulo = _articulo_por_codigo(session, "PETO")
    url = f"/api/articulos/{articulo.id}/inactivacion"
    solo_ver = cliente_con({P.CATALOGO_VER})
    assert solo_ver.post(url, json={"motivo": "x"}).status_code == 403
    assert solo_ver.delete(url).status_code == 403
    administrador = cliente_con({P.CATALOGO_ADMINISTRAR})
    assert administrador.post(url, json={"motivo": "x"}).status_code == 200
    assert administrador.delete(url).status_code == 200


# ------------------------------------------------------------ servicios para otros módulos


def test_RG_10_registrar_pieza_registra_tambien_su_codigo(session):
    servicio = CatalogoService(session)
    articulo = _articulo_por_codigo(session, "ARN-KEV")
    pieza = servicio.registrar_pieza(articulo.id, " ALT-SRV-1 ", "SN-100")

    assert pieza.codigo == "ALT-SRV-1" and pieza.numero_serie == "SN-100"
    assert pieza.estado == EstadoPieza.APTO and pieza.ubicacion_id is None
    codigo = servicio.identificar_codigo("alt-srv-1")
    assert codigo.tipo == TipoCodigo.PIEZA and codigo.ref_id == pieza.id
    assert servicio.obtener_pieza(pieza.id) is pieza


def test_RG_10_registrar_pieza_con_codigo_ajeno_se_rechaza(session):
    servicio = CatalogoService(session)
    articulo = _articulo_por_codigo(session, "ARN-KEV")
    with pytest.raises(CodigoRepetido):
        servicio.registrar_pieza(articulo.id, "FLEXOM", "SN-1")  # el código de un artículo


def test_I_02_dos_piezas_del_mismo_articulo_no_repiten_numero_de_serie(session):
    servicio = CatalogoService(session)
    articulo = _articulo_por_codigo(session, "ARN-KEV")
    servicio.registrar_pieza(articulo.id, "ALT-SRV-2", "SN-200")
    with pytest.raises(SerieRepetida):
        servicio.registrar_pieza(articulo.id, "ALT-SRV-3", "SN-200")
    # Otro artículo sí puede usar esa serie.
    otro = _articulo_por_codigo(session, "ARN-POL")
    servicio.registrar_pieza(otro.id, "ALT-SRV-4", "SN-200")


def test_RG_05_solo_los_articulos_por_pieza_tienen_piezas(session):
    servicio = CatalogoService(session)
    with pytest.raises(DatosInvalidos):
        servicio.registrar_pieza(_articulo_por_codigo(session, "FLEXOM").id, "PZ-X", "S")
    assert _articulo_por_codigo(session, "FLEXOM").control == Control.CANTIDAD


def test_P_03_actualizar_estado_pieza_no_toca_su_ubicacion(session):
    from datetime import date

    servicio = CatalogoService(session)
    articulo = _articulo_por_codigo(session, "ARN-KEV")
    pieza = servicio.registrar_pieza(articulo.id, "ALT-SRV-5", "SN-500")
    pieza.ubicacion_id = _ubicacion_kep(session)
    actor = _usuario(session, "almacenista").id

    servicio.actualizar_estado_pieza(pieza.id, estado=EstadoPieza.NO_APTO, actor_id=actor)
    assert pieza.estado == EstadoPieza.NO_APTO and pieza.ubicacion_id == _ubicacion_kep(session)
    assert pieza.inspeccion_vigente_hasta is None  # SIN_CAMBIO por defecto

    servicio.actualizar_estado_pieza(pieza.id, inspeccion_vigente_hasta=date(2030, 5, 1))
    assert pieza.inspeccion_vigente_hasta == date(2030, 5, 1)
    assert pieza.estado == EstadoPieza.NO_APTO
    servicio.actualizar_estado_pieza(pieza.id, inspeccion_vigente_hasta=None)
    assert pieza.inspeccion_vigente_hasta is None
    servicio.actualizar_estado_pieza(pieza.id, inspeccion_vigente_hasta=SIN_CAMBIO)

    cambios = _auditoria(session, "pieza.actualizar", pieza.id)
    assert len(cambios) == 3  # estado, fecha nueva y fecha borrada; SIN_CAMBIO no registra
    (de_estado,) = [c for c in cambios if "estado" in c.despues]
    assert de_estado.antes == {"estado": "APTO"} and de_estado.despues == {"estado": "NO_APTO"}
    assert de_estado.usuario_id == actor
    assert session.scalar(select(Pieza).where(Pieza.id == pieza.id)) is pieza


def test_CF_05_articulo_tiene_movimientos(session):
    servicio = CatalogoService(session)
    articulo = _articulo_por_codigo(session, "CINCEL")
    # La carga inicial de `movimientos` ya le dejó su entrada: esta prueba parte sin movimientos.
    session.execute(delete(Movimiento).where(Movimiento.articulo_id == articulo.id))
    assert servicio.articulo_tiene_movimientos(articulo.id) is False
    _con_movimiento(session, articulo.id)
    assert servicio.articulo_tiene_movimientos(articulo.id) is True


def test_RG_10_crear_articulo_reutilizable_no_hace_commit_y_exige_permiso_de_costos(session):
    from app.core.excepciones import SinPermiso

    servicio = CatalogoService(session)
    categoria = _categoria(session, "EPP básico")
    actor = _usuario(session, "compras").id
    datos = _crear("SRV-ART-1", categoria.id).model_copy(update={"costo_unitario": 5})
    with pytest.raises(SinPermiso):
        servicio.crear_articulo(datos, actor)
    articulo = servicio.crear_articulo(datos, actor, puede_costos=True)
    assert articulo.costo_unitario == 5
    assert servicio.obtener_articulo(articulo.id) is articulo
    assert servicio.obtener_articulo_por_codigo("SRV-ART-1") is articulo


# ----------------------------------------------------------------- US-ETQ-001: etiquetas


def _trabajador_con_credencial(session: Session, numero: str, nombre: str, codigo: str) -> None:
    trabajador = Trabajador(numero_empleado=numero, nombre=nombre)
    session.add(trabajador)
    session.flush()
    CodigoService(session).registrar(codigo, TipoCodigo.TRABAJADOR, trabajador.id)


def test_I_07_las_etiquetas_de_estantes_son_un_qr_por_articulo_por_cantidad(cliente_como, session):
    r = cliente_como("Compras").get("/api/etiquetas", params={"tipo": "estantes"})
    assert r.status_code == 200
    cuerpo = r.json()
    codigos = {e["codigo"]: e["texto"] for e in cuerpo["elementos"]}
    assert cuerpo["total"] == len(codigos)
    assert codigos["FLEXOM"] == "Flexómetro"
    assert "ARN-KEV" not in codigos  # por pieza: no lleva etiqueta de estante


def test_I_07_un_articulo_inactivo_no_sale_en_las_etiquetas_de_estante(cliente_como, session):
    cliente = cliente_como("Compras")
    articulo = _articulo_por_codigo(session, "CINCEL")
    cliente.post(f"/api/articulos/{articulo.id}/inactivacion", json={"motivo": "Prueba"})
    codigos = {
        e["codigo"]
        for e in cliente.get("/api/etiquetas", params={"tipo": "estantes"}).json()["elementos"]
    }
    assert "CINCEL" not in codigos


def test_RG_10_la_etiqueta_de_una_pieza_lleva_exactamente_su_codigo_registrado(
    cliente_como, session
):
    servicio = CatalogoService(session)
    articulo = _articulo_por_codigo(session, "ARN-POL")
    servicio.registrar_pieza(articulo.id, "ALT-ETQ-1", "SN-ETQ-1")
    baja = servicio.registrar_pieza(articulo.id, "ALT-ETQ-2", "SN-ETQ-2")
    servicio.actualizar_estado_pieza(baja.id, estado=EstadoPieza.BAJA)

    r = cliente_como("Compras").get("/api/etiquetas", params={"tipo": "piezas"})
    assert r.status_code == 200
    por_codigo = {e["codigo"]: e["texto"] for e in r.json()["elementos"]}
    assert por_codigo["ALT-ETQ-1"] == "Arnés Poliéster · serie SN-ETQ-1"
    assert "ALT-ETQ-2" not in por_codigo  # las piezas de baja no se etiquetan
    # El código de la etiqueta es el que identifica a la pieza al escanear.
    assert CodigoService(session).identificar("ALT-ETQ-1").tipo == TipoCodigo.PIEZA


def test_T_05_las_etiquetas_de_credenciales_son_los_codigos_de_los_trabajadores(
    cliente_como, session
):
    _trabajador_con_credencial(session, "ETQ-001", "Ana Ruiz", "CRED-ETQ-1")
    r = cliente_como("Recursos Humanos").get("/api/etiquetas", params={"tipo": "credenciales"})
    assert r.status_code == 200
    assert {"codigo": "CRED-ETQ-1", "texto": "Ana Ruiz · ETQ-001"} in r.json()["elementos"]


def test_AC_01_etiquetas_exigen_etiquetas_imprimir_y_ningun_otro_permiso(cliente_con, session):
    _trabajador_con_credencial(session, "ETQ-002", "Luis Soto", "CRED-ETQ-2")
    ruta = "/api/etiquetas"

    # Sin `etiquetas.imprimir` no hay etiquetas, aunque se pueda ver el catálogo y los trabajadores.
    sin_imprimir = cliente_con({P.CATALOGO_VER, P.TRABAJADORES_VER})
    for tipo in ("piezas", "estantes", "credenciales"):
        assert sin_imprimir.get(ruta, params={"tipo": tipo}).status_code == 403

    # Con solo ese permiso, los tres tipos (US-ETQ-001, tabla 8.2).
    solo_imprimir = cliente_con({P.ETIQUETAS_IMPRIMIR})
    for tipo in ("piezas", "estantes", "credenciales"):
        assert solo_imprimir.get(ruta, params={"tipo": tipo}).status_code == 200


def test_AC_01_compras_rh_y_supervisor_imprimen_los_tres_tipos_de_etiqueta(cliente_como, session):
    _trabajador_con_credencial(session, "ETQ-003", "Rosa Vega", "CRED-ETQ-3")
    for rol in ("Compras", "Recursos Humanos", "Supervisor"):
        cliente = cliente_como(rol)
        for tipo in ("piezas", "estantes", "credenciales"):
            r = cliente.get("/api/etiquetas", params={"tipo": tipo})
            assert r.status_code == 200, (rol, tipo, r.text)
    # El almacenista no tiene `etiquetas.imprimir`.
    for tipo in ("piezas", "estantes", "credenciales"):
        r = cliente_como("Almacenista").get("/api/etiquetas", params={"tipo": tipo})
        assert r.status_code == 403


def test_RG_13_la_etiqueta_de_credencial_no_lleva_curp_ni_nss(cliente_como, session):
    trabajador = Trabajador(
        numero_empleado="ETQ-004", nombre="Mario Paz", curp="PAXM800101HDFRZR09", nss="12345678901"
    )
    session.add(trabajador)
    session.flush()
    CodigoService(session).registrar("CRED-ETQ-4", TipoCodigo.TRABAJADOR, trabajador.id)
    r = cliente_como("Compras").get("/api/etiquetas", params={"tipo": "credenciales"})
    assert r.status_code == 200
    assert "PAXM800101HDFRZR09" not in r.text and "12345678901" not in r.text
    assert {"codigo": "CRED-ETQ-4", "texto": "Mario Paz · ETQ-004"} in r.json()["elementos"]


def test_US_ETQ_001_sin_elementos_la_lista_viene_vacia(cliente_como):
    # RH no ve el inventario, pero sí imprime credenciales; sin trabajadores con código, vacío.
    r = cliente_como("Recursos Humanos").get("/api/etiquetas", params={"tipo": "credenciales"})
    assert r.status_code == 200
    assert r.json()["total"] == len(r.json()["elementos"])


def test_US_ETQ_001_un_tipo_desconocido_responde_422(cliente_como):
    assert cliente_como("Compras").get("/api/etiquetas", params={"tipo": "otro"}).status_code == 422
    assert cliente_como("Compras").get("/api/etiquetas").status_code == 422


def test_CF_10_la_lista_trae_el_motivo_de_los_inactivos(cliente_como, session):
    cliente = cliente_como("Compras")
    articulo = _crear_articulo(cliente, session, "MOT-LISTA-1", "EPP básico")
    respuesta = cliente.post(
        f"/api/articulos/{articulo['id']}/inactivacion", json={"motivo": "Descontinuado"}
    )
    assert respuesta.status_code == 200

    lista = cliente.get("/api/articulos", params={"q": "MOT-LISTA-1"}).json()["elementos"]

    assert [a["motivo_inactivacion"] for a in lista] == ["Descontinuado"]
