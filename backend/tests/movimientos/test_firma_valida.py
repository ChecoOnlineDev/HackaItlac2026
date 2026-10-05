"""Endurecimiento (H4, F-02): la firma de la entrega se valida de verdad.

Antes bastaban nueve bytes (la cabecera de un PNG y una letra) y un trazo vacío. Ahora la imagen
debe ser un PNG completo (cabecera, dimensiones razonables, datos de imagen y cierre, con sus
sumas de comprobación) y el trazo debe traer suficientes puntos `{x, y, t}`. El control no impide
que se dibuje cualquier cosa: impide el atajo trivial de mandar una imagen o un trazo de relleno.
"""

import base64
import struct
import zlib

import pytest

from app.modulos.archivos.exceptions import ArchivoInvalido
from app.modulos.archivos.models import TipoAdjunto
from app.modulos.archivos.service import ArchivoService
from tests.movimientos.ayudas import (
    FIRMA_PNG,
    a_data_url,
    abastecer,
    chunk_png,
    crear_articulo,
    crear_trabajador,
    cuerpo_entrega,
    existencia,
    firma_valida,
    png_valido,
    total_vales,
    trazo_valido,
)
from tests.movimientos.test_entrega import renglon

VALES = "/api/vales"


@pytest.fixture
def trabajador(session):
    return crear_trabajador(session)


@pytest.fixture
def guantes(compras, session):
    articulo = crear_articulo(session)
    abastecer(compras, articulo, 5)
    return articulo


def _confirmar(almacenista, trabajador, guantes, firma):
    return almacenista.post(
        VALES, json=cuerpo_entrega(trabajador, [renglon(guantes.codigo)], firma=firma)
    )


def _rechazada(almacenista, session, trabajador, guantes, firma, campo: str):
    vales = total_vales(session)
    r = _confirmar(almacenista, trabajador, guantes, firma)
    assert r.status_code == 422, r.text
    assert r.json()["codigo"] == "DATOS_INVALIDOS"
    assert campo in r.text
    assert total_vales(session) == vales and existencia(session, "KEP", guantes) == 5


def _png_con_ihdr(ancho: int, alto: int, *, datos_idat: bytes | None = None) -> bytes:
    """Un PNG con cabecera y cierre válidos y las dimensiones indicadas."""
    cabecera = struct.pack(">IIBBBBB", ancho, alto, 8, 2, 0, 0, 0)
    idat = datos_idat if datos_idat is not None else zlib.compress(bytes(ancho * 3 + 1) * alto)
    return (
        FIRMA_PNG
        + chunk_png(b"IHDR", cabecera)
        + chunk_png(b"IDAT", idat)
        + chunk_png(b"IEND", b"")
    )


# ---------------------------------------------------------------------------- la imagen


def test_F_02_nueve_bytes_no_sirven_de_firma(almacenista, session, trabajador, guantes):
    nueve = FIRMA_PNG + b"x"
    assert len(nueve) == 9
    firma = firma_valida(imagen=a_data_url(nueve))

    _rechazada(almacenista, session, trabajador, guantes, firma, "firma.imagen")


def test_F_02_una_firma_valida_se_acepta_con_trazo_plano_o_por_trazos(
    almacenista, session, trabajador, guantes
):
    # La interfaz manda una lista de trazos (cada uno, una lista de puntos {x, y, t}).
    por_trazos = firma_valida(trazo=[trazo_valido(15), trazo_valido(15)])
    r = _confirmar(almacenista, trabajador, guantes, por_trazos)
    assert r.status_code == 201, r.text
    # Y también se acepta una lista plana de puntos.
    r = _confirmar(almacenista, trabajador, guantes, firma_valida())
    assert r.status_code == 201, r.text


def test_F_02_la_firma_de_la_interfaz_900_por_450_se_acepta(
    almacenista, session, trabajador, guantes
):
    firma = firma_valida(imagen=a_data_url(png_valido(900, 450)))
    assert _confirmar(almacenista, trabajador, guantes, firma).status_code == 201


@pytest.mark.parametrize(
    ("ancho", "alto"),
    [(50, 20), (99, 150), (300, 49), (4001, 150), (300, 4001), (0, 0)],
)
def test_F_02_una_firma_con_dimensiones_fuera_de_rango_se_rechaza(
    almacenista, session, trabajador, guantes, ancho, alto
):
    firma = firma_valida(imagen=a_data_url(_png_con_ihdr(ancho, alto, datos_idat=b"x" * 200)))

    _rechazada(almacenista, session, trabajador, guantes, firma, "firma.imagen")


def test_F_02_un_png_sin_datos_de_imagen_o_sin_cierre_se_rechaza(
    almacenista, session, trabajador, guantes
):
    for png in (png_valido(con_idat=False), png_valido(con_iend=False)):
        # Con relleno al final para que el tamaño no sea la causa.
        firma = firma_valida(imagen=a_data_url(png + b"x" * 200))
        _rechazada(almacenista, session, trabajador, guantes, firma, "firma.imagen")


def test_F_02_un_png_con_la_suma_de_comprobacion_alterada_se_rechaza(
    almacenista, session, trabajador, guantes
):
    png = bytearray(png_valido())
    png[40] ^= 0xFF  # un byte dentro de los datos de imagen
    firma = firma_valida(imagen=a_data_url(bytes(png)))

    _rechazada(almacenista, session, trabajador, guantes, firma, "firma.imagen")


def test_F_02_los_datos_de_imagen_deben_ser_los_de_las_dimensiones_declaradas(
    almacenista, session, trabajador, guantes
):
    # Dice 300x150 pero trae los datos de una imagen mucho más chica.
    chico = png_valido(120, 60)
    idat = chico[chico.index(b"IDAT") + 4 : chico.index(b"IEND") - 8]
    firma = firma_valida(imagen=a_data_url(_png_con_ihdr(300, 150, datos_idat=idat)))

    _rechazada(almacenista, session, trabajador, guantes, firma, "firma.imagen")


def test_F_02_una_firma_jpeg_no_se_acepta_aunque_sea_imagen(
    almacenista, session, trabajador, guantes
):
    jpeg = bytes.fromhex("ffd8ffe0") + bytes(400)
    firma = firma_valida(imagen="data:image/jpeg;base64," + base64.b64encode(jpeg).decode())

    _rechazada(almacenista, session, trabajador, guantes, firma, "firma.imagen")


def test_F_02_el_servicio_de_archivos_tampoco_guarda_una_firma_de_nueve_bytes(session):
    from sqlalchemy import select

    from app.modulos.acceso.models import Usuario

    usuario_id = session.scalar(select(Usuario.id).where(Usuario.usuario == "almacenista"))
    with pytest.raises(ArchivoInvalido):
        ArchivoService(session).guardar(
            tipo=TipoAdjunto.FIRMA, contenido=FIRMA_PNG + b"x", subido_por=usuario_id
        )


# ----------------------------------------------------------------------------- el trazo


@pytest.mark.parametrize(
    "trazo",
    [
        [],
        trazo_valido(9),
        [trazo_valido(4), trazo_valido(5)],  # 9 puntos en total
    ],
)
def test_F_02_un_trazo_vacio_o_con_pocos_puntos_se_rechaza(
    almacenista, session, trabajador, guantes, trazo
):
    _rechazada(almacenista, session, trabajador, guantes, firma_valida(trazo=trazo), "firma.trazo")


def test_F_02_un_trazo_con_demasiados_puntos_se_rechaza(almacenista, session, trabajador, guantes):
    trazo = trazo_valido(20_001)

    _rechazada(almacenista, session, trabajador, guantes, firma_valida(trazo=trazo), "trazo")


@pytest.mark.parametrize(
    "punto",
    [
        {"x": "uno", "y": 2, "t": 3},
        {"x": 1, "y": None, "t": 3},
        {"x": 1, "y": 2},
        {"x": True, "y": 2, "t": 3},
        "no es un punto",
        [1, 2, 3],
    ],
)
def test_F_02_un_trazo_con_puntos_mal_formados_se_rechaza(
    almacenista, session, trabajador, guantes, punto
):
    trazo = [*trazo_valido(20), punto]

    r = _confirmar(almacenista, trabajador, guantes, firma_valida(trazo=trazo))

    assert r.status_code == 422, r.text
