"""AV-01 a AV-05, DU-01 a DU-08: deuda retornable, atribución y privacidad."""

import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import event, select

from app.config import get_settings
from app.core.tiempo import ahora_utc, hoy_mx
from app.modulos.acceso.models import Usuario, UsuarioAlmacen
from app.modulos.almacenes.models import Ubicacion, UbicacionVirtual
from app.modulos.almacenes.service import AlmacenService
from app.modulos.catalogo.models import Categoria, Control
from app.modulos.catalogo.schemas import ArticuloCreate
from app.modulos.catalogo.service import CatalogoService
from app.modulos.consulta.repository_deudores import DeudoresRepository
from app.modulos.movimientos.models import Existencia, Movimiento, Vale
from app.modulos.proyectos.models import Proyecto
from app.modulos.trabajadores.models import PeriodoContrato, Trabajador


@pytest.fixture
def contexto18(session):
    almacen = AlmacenService(session)
    kep = almacen.obtener_por_clave("KEP")
    mid = almacen.obtener_por_clave("MID")
    trabajador = Trabajador(
        numero_empleado="E18-" + uuid.uuid4().hex[:8],
        nombre="Trabajador deudor 018",
        estado="ACTIVO",
    )
    session.add(trabajador)
    session.flush()
    usuario = session.scalar(select(Usuario).where(Usuario.usuario == "admin"))
    session.add(
        PeriodoContrato(
            trabajador_id=trabajador.id,
            inicio=hoy_mx() - timedelta(days=60),
            fin=hoy_mx() + timedelta(days=30),
            creado_por=usuario.id,
        )
    )
    session.add(Ubicacion(tipo="TRABAJADOR", trabajador_id=trabajador.id))
    session.commit()
    proyecto = Proyecto(
        clave="PR18-" + uuid.uuid4().hex[:8],
        nombre="Proyecto 018",
        almacen_id=mid.id,
        inicio=hoy_mx() - timedelta(days=60),
        fin_estimado=hoy_mx() + timedelta(days=30),
        creado_por=usuario.id,
    )
    session.add(proyecto)
    session.commit()
    return (kep, mid, trabajador, usuario, proyecto)


def crear_deuda(
    session,
    contexto,
    *,
    clave="KEP",
    piezas=True,
    costo="15000",
    cantidad=1,
    consumible=False,
    viejo=False,
):
    kep, mid, trabajador, usuario, proyecto = contexto
    categoria = session.scalar(
        select(Categoria).where(
            Categoria.nombre == ("Herramienta eléctrica" if piezas else "Herramienta manual")
        )
    )
    datos = ArticuloCreate(
        codigo="DU18-" + uuid.uuid4().hex[:8],
        nombre="Equipo deuda 018",
        categoria_id=categoria.id,
        control=Control.PIEZA if piezas else Control.CANTIDAD,
        retornable=not consumible,
        costo_unitario=Decimal(costo),
    )
    catalogo = CatalogoService(session)
    articulo = catalogo.crear_articulo(datos, actor_id=usuario.id, puede_costos=True)
    servicio = AlmacenService(session)
    almacen = kep if clave == "KEP" else mid
    origen = servicio.ubicacion_de_almacen(almacen.id)
    destino = (
        servicio.ubicacion_virtual(UbicacionVirtual.CONSUMIDO)
        if consumible
        else servicio.ubicacion_de_trabajador(trabajador.id)
    )
    vale = Vale(
        id_cliente=uuid.uuid4(),
        tipo="ENTREGA",
        folio="D18-" + uuid.uuid4().hex[:8],
        almacen_id=almacen.id,
        trabajador_id=trabajador.id,
        proyecto_id=proyecto.id if proyecto else None,
        responsable_id=usuario.id,
        token=uuid.uuid4().hex,
        creado_en=ahora_utc() - timedelta(days=40 if viejo else 0),
    )
    session.add(vale)
    session.flush()
    pieza = None
    if piezas:
        pieza = catalogo.registrar_pieza(
            articulo.id, "P18-" + uuid.uuid4().hex[:8], "SER18-" + uuid.uuid4().hex[:8]
        )
        pieza.ubicacion_id = destino.id
    elif not consumible:
        session.add(Existencia(ubicacion_id=destino.id, articulo_id=articulo.id, cantidad=cantidad))
    movimiento = Movimiento(
        vale_id=vale.id,
        renglon=1,
        articulo_id=articulo.id,
        pieza_id=pieza.id if pieza else None,
        cantidad=1 if pieza else cantidad,
        origen_id=origen.id,
        destino_id=destino.id,
        trabajador_id=trabajador.id,
        creado_en=vale.creado_en,
    )
    session.add(movimiento)
    session.commit()
    return articulo, pieza, vale


def test_AV_01_AV_04_marca_inicial_renombrar_y_permiso(session, cliente_como):
    categoria = session.scalar(select(Categoria).where(Categoria.nombre == "Equipo de alto valor"))
    assert categoria.alto_valor is True
    admin = cliente_como("Administrador")
    respuesta = admin.patch(f"/api/categorias/{categoria.id}", json={"nombre": "Equipo crítico 18"})
    assert respuesta.status_code == 200 and respuesta.json()["alto_valor"] is True
    assert (
        cliente_como("Almacenista")
        .patch(f"/api/categorias/{categoria.id}", json={"alto_valor": False})
        .status_code
        == 403
    )
    assert (
        admin.patch(f"/api/categorias/{categoria.id}", json={"alto_valor": False}).status_code
        == 200
    )


def test_AV_02_AV_03_AV_05_alto_valor_costoso_sin_revelar_origen(
    session, contexto18, cliente_como, monkeypatch
):
    articulo, pieza, _ = crear_deuda(session, contexto18)
    almacenista = cliente_como("Almacenista")
    respuesta = almacenista.get(f"/api/articulos/{articulo.id}")
    assert respuesta.status_code == 200 and respuesta.json()["alto_valor"] is True
    assert "costo_unitario" not in respuesta.text and "alto_valor_motivo" not in respuesta.text
    compras = cliente_como("Compras")
    assert (
        compras.get(f"/api/articulos/{articulo.id}").json()["alto_valor_motivo"] == "Por su costo"
    )
    consulta = almacenista.get(
        "/api/seguimiento/piezas", params={"alto_valor": True, "q": pieza.codigo}
    )
    assert consulta.status_code == 200 and consulta.json()["total"] == 1
    monkeypatch.setattr(get_settings(), "alto_valor_costo_minimo", Decimal("20000"))
    assert (
        almacenista.get(
            "/api/seguimiento/piezas", params={"alto_valor": True, "q": pieza.codigo}
        ).json()["total"]
        == 0
    )


def test_DU_01_DU_02_DU_05_deuda_retornable_con_proyecto(session, contexto18, cliente_como):
    articulo, pieza, vale = crear_deuda(session, contexto18)
    trabajador = contexto18[2]
    supervisor = cliente_como("Supervisor")
    respuesta = supervisor.get(
        "/api/deudores", params={"trabajador_id": str(trabajador.id), "q": articulo.codigo}
    )
    assert respuesta.status_code == 200, respuesta.text
    item = respuesta.json()["elementos"][0]
    assert item["piezas"] == 1 and item["unidades"] == 0 and item["alto_valor"] == 1
    renglon = item["renglones"][0]
    assert renglon["vale"]["id"] == str(vale.id) and renglon["pieza"]["id"] == str(pieza.id)
    assert renglon["proyecto"]["id"] == str(vale.proyecto_id)
    assert (
        "costo" not in respuesta.text
        and "curp" not in respuesta.text
        and "nss" not in respuesta.text
    )
    crear_deuda(session, contexto18, piezas=False, cantidad=10, consumible=True, costo="100")
    assert (
        supervisor.get(
            "/api/deudores", params={"trabajador_id": str(trabajador.id), "q": articulo.codigo}
        ).json()["elementos"][0]["unidades"]
        == 0
    )


def test_DU_03_alcance_otros_almacenes_rh_sin_vales(session, contexto18, cliente_como):
    crear_deuda(session, contexto18)
    crear_deuda(session, contexto18, clave="MID")
    kep, mid, trabajador, _, _ = contexto18
    supervisor = cliente_como("Supervisor")
    fuera = supervisor.get("/api/deudores", params={"almacen_id": str(mid.id)})
    assert fuera.status_code == 200 and fuera.json()["total"] == 0
    visible = supervisor.get("/api/deudores", params={"trabajador_id": str(trabajador.id)}).json()[
        "elementos"
    ][0]
    assert visible["otros_almacenes"] >= 1
    assert all(r["almacen"]["id"] == str(kep.id) for r in visible["renglones"])
    rh = cliente_como("Recursos Humanos")
    respuesta = rh.get("/api/deudores", params={"trabajador_id": str(trabajador.id)})
    assert respuesta.status_code == 200, respuesta.text
    assert all(r["vale"]["id"] is None for r in respuesta.json()["elementos"][0]["renglones"])
    assert rh.get("/api/seguimiento/piezas").status_code == 403
    assert cliente_como("Almacenista").get("/api/deudores").status_code == 403


def test_DU_04_DU_06_antiguedad_serie_paginacion_sql(session, contexto18, cliente_como):
    _, pieza, _ = crear_deuda(session, contexto18, viejo=True)
    supervisor = cliente_como("Supervisor")
    respuesta = supervisor.get(
        "/api/deudores", params={"q": pieza.numero_serie, "antiguedad_dias": 30, "tamano": 1}
    )
    assert respuesta.status_code == 200 and respuesta.json()["total"] == 1, respuesta.text
    assert (
        supervisor.get(
            "/api/deudores", params={"q": pieza.numero_serie, "antiguedad_dias": 90}
        ).json()["total"]
        == 0
    )
    sentencias = []

    def observar(conn, cursor, statement, parameters, context, executemany):
        sentencias.append(statement)

    event.listen(session.get_bind(), "before_cursor_execute", observar)
    try:
        DeudoresRepository(session).listado({contexto18[0].id}, {"q": pieza.numero_serie}, 2, 25)
    finally:
        event.remove(session.get_bind(), "before_cursor_execute", observar)
    assert any("LIMIT" in sql and "GROUP BY" in sql and "row_number()" in sql for sql in sentencias)


def test_DU_07_resumen_csv_sin_costos(session, contexto18, cliente_como):
    crear_deuda(session, contexto18, piezas=False, cantidad=3)
    administrador = cliente_como("Administrador")
    respuesta = administrador.get("/api/deudores/resumen")
    assert (
        respuesta.status_code == 200
        and respuesta.json()["almacenes"]
        and respuesta.json()["proyectos"]
    )
    assert "costo" not in respuesta.text
    csv = administrador.get("/api/deudores/resumen", params={"formato": "csv"})
    assert csv.status_code == 200 and "text/csv" in csv.headers["content-type"]


def test_DU_08_consumo_neto_proyecto_y_valor_protegido(session, contexto18, cliente_como):
    articulo, _, vale = crear_deuda(
        session, contexto18, piezas=False, cantidad=9, consumible=True, costo="10"
    )
    # Una segunda entrega del mismo consumible, cancelada, suma y resta con el proyecto original.
    mov = session.scalar(select(Movimiento).where(Movimiento.vale_id == vale.id))
    otra = Vale(
        id_cliente=uuid.uuid4(),
        tipo="ENTREGA",
        folio="C18-" + uuid.uuid4().hex[:8],
        almacen_id=vale.almacen_id,
        trabajador_id=vale.trabajador_id,
        proyecto_id=vale.proyecto_id,
        responsable_id=vale.responsable_id,
        token=uuid.uuid4().hex,
        estado="CANCELADO",
    )
    session.add(otra)
    session.flush()
    session.add(
        Movimiento(
            vale_id=otra.id,
            renglon=1,
            articulo_id=articulo.id,
            cantidad=3,
            origen_id=mov.origen_id,
            destino_id=mov.destino_id,
            trabajador_id=vale.trabajador_id,
        )
    )
    cancelacion = Vale(
        id_cliente=uuid.uuid4(),
        tipo="CANCELACION",
        folio="K18-" + uuid.uuid4().hex[:8],
        almacen_id=vale.almacen_id,
        trabajador_id=vale.trabajador_id,
        vale_origen_id=otra.id,
        responsable_id=vale.responsable_id,
        token=uuid.uuid4().hex,
    )
    session.add(cancelacion)
    session.flush()
    session.add(
        Movimiento(
            vale_id=cancelacion.id,
            renglon=1,
            articulo_id=articulo.id,
            cantidad=3,
            origen_id=mov.destino_id,
            destino_id=mov.origen_id,
            trabajador_id=vale.trabajador_id,
        )
    )
    session.commit()
    ruta = f"/api/trabajadores/{contexto18[2].id}/consumo"
    respuesta = cliente_como("Almacenista").get(ruta)
    assert respuesta.status_code == 200, respuesta.text
    item = next(i for i in respuesta.json()["elementos"] if i["articulo"]["id"] == str(articulo.id))
    assert item["cantidad"] == 9 and item["por_proyecto"][0]["cantidad"] == 9
    assert "valor_total" not in respuesta.text and "costo" not in respuesta.text
    # Reducir la consulta a un único artículo impide reconstruir su costo mediante división.
    admin = cliente_como("Administrador")
    assert len(admin.get(ruta).json()["elementos"]) == 1
    assert admin.get(ruta).json()["valor_total"] is None


def test_AV_03_importacion_sugiere_costo_sin_aplicarlo(cliente_como):
    from tests.importacion.ayudas import cuerpo, fila

    compras = cliente_como("Compras")
    registro = fila(
        "IMP18-" + uuid.uuid4().hex[:8],
        nombre="Minipulidor industrial",
        categoria="",
        cantidad=1,
        costo=12000,
        serie="S-IMP18",
    )
    respuesta = compras.post("/api/importacion/vista-previa", json=cuerpo([registro]))
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    fila_resultado = (datos["filas_validas"] + datos["filas_error"])[0]
    assert fila_resultado["categoria_sugerida"]["nombre"] == "Equipo de alto valor"
    assert "costo" in fila_resultado["motivo_sugerencia"]
    registro[3] = "Herramienta eléctrica"
    explicita = compras.post("/api/importacion/vista-previa", json=cuerpo([registro])).json()[
        "filas_validas"
    ][0]
    assert explicita["categoria"]["nombre"] == "Herramienta eléctrica"
    assert "Por su costo cuenta como alto valor." in explicita["avisos"]


def test_DU_04_no_vigente_alto_valor_antes_de_deuda_mas_vieja(session, contexto18, cliente_como):
    crear_deuda(session, contexto18, viejo=True)
    trabajador = contexto18[2]
    periodo = session.scalar(
        select(PeriodoContrato).where(PeriodoContrato.trabajador_id == trabajador.id)
    )
    periodo.fin = hoy_mx() - timedelta(days=1)
    session.commit()
    respuesta = cliente_como("Supervisor").get(
        "/api/deudores", params={"proyecto_id": str(contexto18[4].id)}
    )
    assert respuesta.status_code == 200, respuesta.text
    item = respuesta.json()["elementos"][0]
    assert item["vigente"] is False and item["alto_valor"] == 1 and item["aviso"]
    assert respuesta.json()["resumen"]["no_vigentes_con_adeudo"] == 1


def test_DU_03_conjunto_de_dos_almacenes_y_compatibilidad_adeudos(
    session, contexto18, cliente_como
):
    crear_deuda(session, contexto18)
    crear_deuda(session, contexto18, clave="MID", piezas=False, cantidad=2)
    supervisor = session.scalar(select(Usuario).where(Usuario.usuario == "supervisor"))
    session.add(UsuarioAlmacen(usuario_id=supervisor.id, almacen_id=contexto18[1].id))
    session.commit()
    cliente = cliente_como("Supervisor")
    respuesta = cliente.get("/api/deudores", params={"trabajador_id": str(contexto18[2].id)})
    assert respuesta.status_code == 200, respuesta.text
    item = respuesta.json()["elementos"][0]
    assert item["piezas"] == 1 and item["unidades"] == 2 and item["otros_almacenes"] == 0
    assert {r["almacen"]["id"] for r in item["renglones"]} == {
        str(contexto18[0].id),
        str(contexto18[1].id),
    }
    anterior = cliente.get("/api/reportes/adeudos", params={"tamano": 200})
    assert anterior.status_code == 200, anterior.text
    cantidad_anterior = sum(
        r["cantidad"]
        for r in anterior.json()["elementos"]
        if r["trabajador_id"] == str(contexto18[2].id)
    )
    assert cantidad_anterior == item["piezas"] + item["unidades"]


def test_DU_02_cancelacion_no_cambia_entrega_original_por_cantidad(
    session, contexto18, cliente_como
):
    articulo, _, original = crear_deuda(session, contexto18, piezas=False, cantidad=1, viejo=True)
    movimiento = session.scalar(select(Movimiento).where(Movimiento.vale_id == original.id))
    posterior = Vale(
        id_cliente=uuid.uuid4(),
        tipo="ENTREGA",
        folio="D18C-" + uuid.uuid4().hex[:8],
        almacen_id=original.almacen_id,
        trabajador_id=original.trabajador_id,
        proyecto_id=original.proyecto_id,
        responsable_id=original.responsable_id,
        token=uuid.uuid4().hex,
        estado="CANCELADO",
    )
    session.add(posterior)
    session.flush()
    session.add(
        Movimiento(
            vale_id=posterior.id,
            renglon=1,
            articulo_id=articulo.id,
            cantidad=1,
            origen_id=movimiento.origen_id,
            destino_id=movimiento.destino_id,
            trabajador_id=original.trabajador_id,
        )
    )
    session.commit()
    respuesta = cliente_como("Supervisor").get(
        "/api/deudores", params={"trabajador_id": str(contexto18[2].id)}
    )
    assert respuesta.status_code == 200, respuesta.text
    deuda = respuesta.json()["elementos"][0]["renglones"][0]
    assert deuda["vale"]["id"] == str(original.id)
    assert deuda["cantidad"] == 1
