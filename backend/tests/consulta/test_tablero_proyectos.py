"""TB-04 a TB-08 / T-2 con MySQL real y movimientos coherentes."""

from datetime import timedelta

from sqlalchemy import select

from app.core.tiempo import ahora_utc, hoy_mx
from app.modulos.acceso.models import Usuario, UsuarioAlmacen
from app.modulos.acceso.permisos import P
from app.modulos.movimientos.models import Existencia
from app.modulos.proyectos.models import Proyecto

RUTA = "/api/tablero/proyectos"


def proyecto(datos, clave="TB-UNO", almacen="MID", **cambios):
    p = Proyecto(
        clave=clave,
        nombre=clave,
        almacen_id=datos.almacen(almacen).id,
        inicio=hoy_mx(),
        fin_estimado=hoy_mx() + timedelta(days=30),
        creado_por=datos.usuario("admin").id,
        **cambios,
    )
    datos.session.add(p)
    datos.session.flush()
    return p


def entrega(datos, p, t, a, **cambios):
    v = datos.entrega(t, a, **cambios)
    v.proyecto_id = p.id if p else None
    datos.session.flush()
    return v


def consultar(c, **parametros):
    r = c.get(RUTA, params=parametros)
    assert r.status_code == 200, r.text
    return r.json()


def cliente(cliente_con, *, almacen="MID", valor=False, costos=False):
    permisos = [P.TABLERO_VER, "proyectos.ver"]
    if valor:
        permisos.append(P.REPORTES_VALOR_INVENTARIO)
    if costos:
        permisos.append(P.CATALOGO_COSTOS)
    return cliente_con(*permisos, almacen=almacen)


def test_TB_05_exige_los_dos_permisos(cliente_con):
    assert cliente_con(P.TABLERO_VER, almacen="MID").get(RUTA).status_code == 403
    assert cliente_con("proyectos.ver", almacen="MID").get(RUTA).status_code == 403


def test_TB_06_proyecto_del_otro_almacen_y_ultima_entrega_de_cantidad(cliente_con, datos):
    uno = proyecto(datos)
    dos = proyecto(datos, "TB-DOS", "HYL")
    t, a = datos.trabajador(), datos.articulo(costo="10")
    entrega(datos, uno, t, a, almacen="CON", cantidad=4, creado_en=ahora_utc() - timedelta(hours=1))
    entrega(datos, dos, t, a, almacen="CON", cantidad=2)
    # Una devolución parcial reduce el resguardo; el remanente corresponde a la última entrega.
    devolucion = datos.vale("DEVOLUCION", "CON", trabajador=t)
    datos.movimiento(devolucion, a, datos.ub_trabajador(t), datos.ub_almacen("CON"), cantidad=1)
    e = datos.session.get(Existencia, (datos.ub_trabajador(t).id, a.id))
    e.cantidad -= 1
    datos.session.flush()
    mid = consultar(cliente(cliente_con))
    hyl = consultar(cliente(cliente_con, almacen="HYL", valor=True, costos=True))
    assert mid["proyectos"][0]["total"]["unidades"] == 0
    assert hyl["proyectos"][0]["retornables_en_resguardo"] == {"unidades": 5, "valor": "50.00"}
    assert consultar(cliente(cliente_con, almacen="CON"))["proyectos"] == []


def test_TB_05_consumible_cancelado_se_resta_en_fecha_original(cliente_con, datos):
    p, t, a = proyecto(datos), datos.trabajador(), datos.articulo(retornable=False, costo="12")
    v = entrega(
        datos, p, t, a, almacen="CON", cantidad=3, creado_en=ahora_utc() - timedelta(days=12)
    )
    datos.cancelar(v, creado_en=ahora_utc())
    resultado = consultar(
        cliente(cliente_con, valor=True, costos=True),
        desde=(hoy_mx() - timedelta(days=15)).isoformat(),
        hasta=(hoy_mx() - timedelta(days=10)).isoformat(),
    )
    assert resultado["proyectos"][0]["consumibles_consumidos"] == {"unidades": 0, "valor": "0.00"}


def test_TB_05_cerrado_con_resguardo_y_sin_proyecto_del_alcance(cliente_con, datos):
    p = proyecto(datos, estado="CERRADO")
    t, a = datos.trabajador(), datos.articulo()
    entrega(datos, p, t, a, almacen="CON", cantidad=2)
    entrega(datos, None, datos.trabajador(), a, almacen="MID", cantidad=3)
    entrega(datos, None, datos.trabajador(), a, almacen="HYL", cantidad=7)
    r = consultar(cliente(cliente_con))
    assert r["proyectos"][0]["estado"] == "CERRADO"
    assert r["proyectos"][0]["retornables_en_resguardo"]["unidades"] == 2
    assert r["sin_proyecto"]["retornables_en_resguardo"]["unidades"] == 3
    assert r["proyectos"][0]["articulos_sin_costo"] == 1


def test_TB_04_T2_importes_y_privacidad_por_categoria(cliente_con, datos):
    p, t, a = proyecto(datos), datos.trabajador(), datos.articulo(costo="23")
    entrega(datos, p, t, a, almacen="CON", cantidad=2)
    for con_valor in (False, True):
        r = consultar(cliente(cliente_con, valor=con_valor), proyecto_id=str(p.id))
        fila = r["proyectos"][0]
        assert fila["total"] == {"unidades": 2, "valor": None}
        assert fila["por_categoria"][0]["total"]["valor"] is None
        assert "costo_unitario" not in str(r) and "curp" not in str(r)
    r = consultar(cliente(cliente_con, valor=True, costos=True))
    assert r["proyectos"][0]["total"]["valor"] == "46.00"


def test_TB_07_conjunto_selectores_no_cambian_activo(cliente_con, datos):
    mid, hyl = proyecto(datos), proyecto(datos, "TB-DOS", "HYL")
    c = cliente(cliente_con)
    sesion = c.get("/api/sesion").json()
    id = sesion["usuario"]["id"]
    usuario = datos.session.scalar(
        select(Usuario).where(Usuario.usuario == sesion["usuario"]["usuario"])
    )
    datos.session.add(UsuarioAlmacen(usuario_id=usuario.id, almacen_id=datos.almacen("HYL").id))
    datos.session.flush()
    r = consultar(c)
    assert {p["id"] for p in r["proyectos"]} == {str(mid.id), str(hyl.id)}
    assert len(r["alcance"]["almacenes"]) == 2
    assert r["alcance"]["nombre"] == "Tus 2 almacenes"
    assert len(consultar(c, almacen_id=str(hyl.almacen_id))["proyectos"]) == 1
    assert consultar(c, proyecto_id=str(hyl.id))["proyectos"][0]["id"] == str(hyl.id)
    assert c.get("/api/sesion").json()["almacen"]["id"] == str(mid.almacen_id)
    assert id == str(usuario.id)


def test_TB_08_tarjetas_y_conteos_reservados(cliente_con, datos):
    p = proyecto(datos)
    p.fin_estimado = hoy_mx() - timedelta(days=1)
    p.inicio = hoy_mx() - timedelta(days=10)
    datos.session.flush()
    r = cliente(cliente_con).get("/api/tablero/resumen").json()
    assert [p["id"] for p in r["proyectos_por_vencer"]] == [str(p.id)]
    assert r["almacenes_sin_proyecto"] is None
    assert r["inspecciones_por_vencer"] is None
    sin = cliente_con(P.TABLERO_VER, almacen="MID").get("/api/tablero/resumen").json()
    assert sin["proyectos_por_vencer"] is None
    admin = cliente_con(P.TABLERO_VER, P.ALMACENES_ADMINISTRAR, P.ALMACENES_TODOS)
    vacios = admin.get("/api/tablero/resumen").json()["almacenes_sin_proyecto"]
    assert any(a["id"] == str(datos.almacen("HYL").id) for a in vacios)
    assert all(a["id"] != str(p.almacen_id) for a in vacios)


def test_TB_06_cada_pieza_conserva_su_proyecto(cliente_con, datos):
    uno, dos = proyecto(datos), proyecto(datos, "TB-DOS", "HYL")
    t, a = datos.trabajador(), datos.articulo(control="PIEZA")
    p1, p2 = datos.pieza(a, datos.ub_almacen("CON")), datos.pieza(a, datos.ub_almacen("CON"))
    entrega(datos, uno, t, a, almacen="CON", pieza=p1)
    entrega(datos, dos, t, a, almacen="CON", pieza=p2)
    c = cliente_con(P.TABLERO_VER, "proyectos.ver", P.ALMACENES_TODOS)
    filas = {p["id"]: p for p in consultar(c)["proyectos"]}
    assert filas[str(uno.id)]["retornables_en_resguardo"]["unidades"] == 1
    assert filas[str(dos.id)]["retornables_en_resguardo"]["unidades"] == 1


def test_TB_06_cancelar_ultima_entrega_restaura_atribucion_anterior(cliente_con, datos):
    uno, dos = proyecto(datos), proyecto(datos, "TB-DOS")
    t, a = datos.trabajador(), datos.articulo()
    entrega(datos, uno, t, a, cantidad=4, creado_en=ahora_utc() - timedelta(hours=1))
    ultima = entrega(datos, dos, t, a, cantidad=2)
    datos.cancelar(ultima)
    e = datos.session.get(Existencia, (datos.ub_trabajador(t).id, a.id))
    e.cantidad -= 2
    datos.session.flush()
    filas = {p["id"]: p for p in consultar(cliente(cliente_con))["proyectos"]}
    assert filas[str(uno.id)]["retornables_en_resguardo"]["unidades"] == 4
    assert filas[str(dos.id)]["retornables_en_resguardo"]["unidades"] == 0


def test_TB_04_unidades_visibles_sin_permiso_de_valor(cliente_con, datos):
    c = cliente_con(P.TABLERO_VER, almacen="MID")
    antes = c.get("/api/tablero/resumen").json()["inventario_unidades"]
    a, t = datos.articulo(costo="10"), datos.trabajador()
    datos.existencia(datos.ub_almacen("MID"), a, 5)
    datos.entrega(t, a, almacen="MID", cantidad=3)
    despues = c.get("/api/tablero/resumen").json()["inventario_unidades"]
    assert despues["en_almacen"] - antes["en_almacen"] == 5
    assert despues["en_resguardo"] - antes["en_resguardo"] == 3
    assert despues["total"] - antes["total"] == 8
    assert c.get("/api/tablero/valor").status_code == 403
