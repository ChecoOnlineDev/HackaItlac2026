"""FEAT-019: UX-03 y UX-04, búsqueda legible dentro del alcance permitido."""


def test_ux03_busca_por_palabras_en_cualquier_orden_y_sin_acentos(cliente_como, datos):
    trabajador = datos.trabajador("Juan Pérez López")
    cliente = cliente_como("Almacenista")
    respuesta = cliente.get("/api/busqueda", params={"q": "PEREZ juan"})
    assert respuesta.status_code == 200, respuesta.text
    assert str(trabajador.id) in [t["id"] for t in respuesta.json()["trabajadores"]["elementos"]]
    assert respuesta.json()["trabajadores"]["elementos"][0]["vigencia"]["vigente"] is True
    lista = cliente.get("/api/trabajadores", params={"q": "perez juan"})
    assert lista.status_code == 200, lista.text
    assert str(trabajador.id) in lista.text


def test_ux03_por_codigo_de_credencial(cliente_como, datos):
    trabajador = datos.trabajador("Persona sin coincidencia", codigo="UX-CRED-19")
    respuesta = cliente_como("Almacenista").get("/api/busqueda", params={"q": "UX-CRED"})
    assert respuesta.status_code == 200, respuesta.text
    resultado = respuesta.json()["trabajadores"]["elementos"][0]
    assert resultado["id"] == str(trabajador.id)
    assert resultado["credencial"] == "UX-CRED-19"
    assert "curp" not in resultado and "nss" not in resultado


def test_ux03_por_marca_y_relevancia(cliente_como, datos):
    articulo = datos.articulo("Martillo de mango largo")
    articulo.marca = "Truper"
    datos.session.flush()
    cliente = cliente_como("Almacenista")
    respuesta = cliente.get("/api/busqueda", params={"q": "largo truper"})
    assert respuesta.status_code == 200, respuesta.text
    assert [a["id"] for a in respuesta.json()["articulos"]["elementos"]] == [str(articulo.id)]


def test_ux04_texto_de_ubicacion_y_cantidades(cliente_como, datos):
    trabajador = datos.trabajador("Juan del resguardo")
    articulo = datos.articulo("Flexómetro UX19", retornable=True)
    datos.existencia(datos.ub_almacen("KEP"), articulo, 3)
    datos.existencia(datos.ub_trabajador(trabajador), articulo, 5)
    pieza_articulo = datos.articulo("Arnés UX19", control="PIEZA")
    datos.pieza(pieza_articulo, datos.ub_trabajador(trabajador))
    respuesta = cliente_como("Almacenista").get("/api/busqueda", params={"q": "UX19"})
    assert respuesta.status_code == 200, respuesta.text
    cantidad = next(
        a for a in respuesta.json()["articulos"]["elementos"] if a["id"] == str(articulo.id)
    )
    assert cantidad["en_almacen"] == 3 and cantidad["con_trabajadores"] == 5
    assert respuesta.json()["piezas"]["elementos"][0]["ubicacion_texto"].startswith(
        "En resguardo de Juan"
    )
    assert "costo_unitario" not in respuesta.text


def test_ux04_pieza_en_transito_muestra_el_almacen_destino(cliente_como, datos):
    from app.modulos.almacenes.models import UbicacionVirtual
    from app.modulos.movimientos.models import EstadoVale

    articulo = datos.articulo("Arnés en traslado UX19", control="PIEZA")
    transito = datos.ub_virtual(UbicacionVirtual.EN_TRANSITO)
    pieza = datos.pieza(articulo, transito)
    vale = datos.vale("TRASPASO", "KEP", estado=EstadoVale.EN_TRANSITO)
    vale.destino_almacen_id = datos.almacen("CON").id
    datos.movimiento(
        vale,
        articulo,
        datos.ub_almacen("KEP"),
        transito,
        pieza=pieza,
    )

    respuesta = cliente_como("Almacenista").get("/api/busqueda", params={"q": "Arnés traslado"})
    assert respuesta.status_code == 200, respuesta.text
    resultado = respuesta.json()["piezas"]["elementos"][0]
    assert resultado["ubicacion_texto"] == "En tránsito a Contratistas"


def test_ux04_tamano_maximo(cliente_como):
    cliente = cliente_como("Almacenista")
    assert cliente.get("/api/busqueda", params={"q": "prueba", "tamano": 200}).status_code == 422


def test_ux06_etiquetas_por_articulo(cliente_como, datos):
    articulo = datos.articulo("Piezas del artículo UX19", control="PIEZA")
    otro = datos.articulo("Otro artículo UX19", control="PIEZA")
    elegida = datos.pieza(articulo, datos.ub_almacen("KEP"))
    datos.pieza(otro, datos.ub_almacen("KEP"))
    respuesta = cliente_como("Recursos Humanos").get(
        "/api/etiquetas", params={"tipo": "piezas", "articulo_id": str(articulo.id)}
    )
    assert respuesta.status_code == 200, respuesta.text
    assert [e["codigo"] for e in respuesta.json()["elementos"]] == [elegida.codigo]


def test_ux06_etiquetas_por_lote(cliente_como, datos):
    from app.core.ids import nuevo_id
    from app.modulos.almacenes.models import UbicacionVirtual
    from app.modulos.movimientos.models import Movimiento

    articulo = datos.articulo("Piezas lote UX19", control="PIEZA")
    pieza = datos.pieza(articulo, datos.ub_almacen("KEP"))
    vale = datos.vale("ENTRADA")
    lote = nuevo_id()
    vale.lote_id = lote
    datos.session.add(
        Movimiento(
            vale_id=vale.id,
            renglon=1,
            articulo_id=articulo.id,
            pieza_id=pieza.id,
            origen_id=datos.ub_virtual(UbicacionVirtual.PROVEEDOR).id,
            destino_id=datos.ub_almacen("KEP").id,
            cantidad=1,
        )
    )
    datos.session.flush()
    respuesta = cliente_como("Recursos Humanos").get(
        "/api/etiquetas", params={"tipo": "piezas", "lote_id": str(lote)}
    )
    assert respuesta.status_code == 200, respuesta.text
    assert [e["codigo"] for e in respuesta.json()["elementos"]] == [pieza.codigo]


def test_ux06_credenciales_por_rango_de_alta(cliente_como, datos):
    from datetime import datetime

    en_rango = datos.trabajador("Alta UX19 dentro", codigo="UX-ALTA-DENTRO")
    fuera = datos.trabajador("Alta UX19 fuera", codigo="UX-ALTA-FUERA")
    inactivo = datos.trabajador("Alta UX19 inactivo", codigo="UX-ALTA-INACTIVO", estado="INACTIVO")
    en_rango.creado_en = datetime(2026, 10, 9, 5, 59)
    fuera.creado_en = datetime(2026, 10, 9, 6, 0)
    inactivo.creado_en = en_rango.creado_en
    datos.session.flush()
    respuesta = cliente_como("Recursos Humanos").get(
        "/api/etiquetas",
        params={"tipo": "credenciales", "alta_desde": "2026-10-08", "alta_hasta": "2026-10-08"},
    )
    assert respuesta.status_code == 200, respuesta.text
    assert [e["codigo"] for e in respuesta.json()["elementos"]] == ["UX-ALTA-DENTRO"]


def test_ux06_filtro_que_no_corresponde_al_tipo_y_permiso(cliente_como, datos):
    articulo = datos.articulo("Filtro UX19")
    cliente = cliente_como("Recursos Humanos")
    assert (
        cliente.get(
            "/api/etiquetas", params={"tipo": "credenciales", "articulo_id": str(articulo.id)}
        ).status_code
        == 422
    )
    assert (
        cliente.get(
            "/api/etiquetas", params={"tipo": "piezas", "alta_desde": "2026-10-08"}
        ).status_code
        == 422
    )
    assert (
        cliente_como("Almacenista")
        .get("/api/etiquetas", params={"tipo": "piezas", "articulo_id": str(articulo.id)})
        .status_code
        == 403
    )
