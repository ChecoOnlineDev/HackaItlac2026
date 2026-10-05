"""Validación de la imagen de una firma en pantalla (F-02), sin dependencias de imágenes.

La interfaz exporta el lienzo como PNG (`canvas.toDataURL`, 900x450). Aquí se comprueba que lo
recibido sea un PNG completo y coherente, no solo que empiece con la cabecera de un PNG:

- los 8 bytes de la firma del formato y un tamaño mínimo razonable;
- un chunk `IHDR` primero, con ancho y alto dentro de rango;
- cada chunk con su suma de comprobación (CRC-32) correcta;
- al menos un chunk `IDAT` y un `IEND` al final, sin nada después;
- los datos de imagen se descomprimen y miden lo que dicen las dimensiones (en imágenes sin
  entrelazado), con un tope para no abrir una "bomba" de descompresión.

ALCANCE REAL: es un control de integridad del archivo. No impide que alguien dibuje o suba
cualquier imagen que sea un PNG válido; lo que impide es el atajo trivial de mandar nueve bytes
o una imagen vacía de relleno como si fuera la firma. La evidencia de la firma sigue siendo el
conjunto (usuario, dispositivo, hora, trazo y archivo ligados al vale; F-05).
"""

import struct
import zlib

from app.modulos.archivos.exceptions import ArchivoInvalido

SIGNATURA_PNG = bytes.fromhex("89504e470d0a1a0a")
TAMANO_MINIMO = 150  # bytes: un PNG completo con datos reales pesa mucho más
ANCHO_MINIMO, ALTO_MINIMO = 100, 50
ANCHO_MAXIMO, ALTO_MAXIMO = 4000, 4000

# Canales por tipo de color y profundidades de bits que admite cada uno (especificación PNG).
_CANALES = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
_PROFUNDIDADES = {
    0: {1, 2, 4, 8, 16},
    2: {8, 16},
    3: {1, 2, 4, 8},
    4: {8, 16},
    6: {8, 16},
}
_BLOQUE = 65536


def _invalida(motivo: str) -> ArchivoInvalido:
    return ArchivoInvalido(
        f"La firma no es una imagen válida ({motivo}). Vuelve a firmar.",
        [{"campo": "firma.imagen", "mensaje": motivo}],
    )


def validar_png_de_firma(contenido: bytes) -> None:
    """Lanza `ArchivoInvalido` (422) si `contenido` no es un PNG de firma aceptable."""
    if len(contenido) < TAMANO_MINIMO:
        raise _invalida("es demasiado pequeña")
    if not contenido.startswith(SIGNATURA_PNG):
        raise _invalida("no es un PNG")

    posicion = len(SIGNATURA_PNG)
    ancho = alto = profundidad = tipo_color = entrelazado = None
    idat: list[bytes] = []
    visto_iend = False
    primero = True
    while posicion < len(contenido):
        if visto_iend:
            raise _invalida("hay datos después del final de la imagen")
        if posicion + 12 > len(contenido):
            raise _invalida("está cortada")
        (largo,) = struct.unpack(">I", contenido[posicion : posicion + 4])
        tipo = contenido[posicion + 4 : posicion + 8]
        fin_datos = posicion + 8 + largo
        if fin_datos + 4 > len(contenido):
            raise _invalida("está cortada")
        datos = contenido[posicion + 8 : fin_datos]
        (crc,) = struct.unpack(">I", contenido[fin_datos : fin_datos + 4])
        if zlib.crc32(tipo + datos) & 0xFFFFFFFF != crc:
            raise _invalida("está dañada")

        if primero:
            if tipo != b"IHDR" or largo != 13:
                raise _invalida("le falta la cabecera")
            ancho, alto, profundidad, tipo_color, compresion, filtro, entrelazado = struct.unpack(
                ">IIBBBBB", datos
            )
            primero = False
        elif tipo == b"IHDR":
            raise _invalida("tiene una cabecera repetida")
        elif tipo == b"IDAT":
            idat.append(datos)
        elif tipo == b"IEND":
            visto_iend = True
        posicion = fin_datos + 4

    if primero or not visto_iend:
        raise _invalida("le falta el final")
    if not idat:
        raise _invalida("no trae datos de imagen")
    assert ancho is not None and alto is not None  # ya se leyó la cabecera
    if not (ANCHO_MINIMO <= ancho <= ANCHO_MAXIMO and ALTO_MINIMO <= alto <= ALTO_MAXIMO):
        raise _invalida(
            f"mide {ancho}x{alto} y debe medir entre {ANCHO_MINIMO}x{ALTO_MINIMO} "
            f"y {ANCHO_MAXIMO}x{ALTO_MAXIMO}"
        )
    if (
        tipo_color not in _CANALES
        or profundidad not in _PROFUNDIDADES[tipo_color]
        or compresion != 0
        or filtro != 0
        or entrelazado not in (0, 1)
    ):
        raise _invalida("tiene un formato que no se acepta")

    if entrelazado == 0:
        bits_por_pixel = _CANALES[tipo_color] * profundidad
        bytes_por_fila = (ancho * bits_por_pixel + 7) // 8
        esperado = alto * (1 + bytes_por_fila)
        _comprobar_datos(idat, esperado)
    else:  # entrelazado Adam7: solo se comprueba que descomprima y no sea una bomba
        _comprobar_datos(idat, None)


def _comprobar_datos(idat: list[bytes], esperado: int | None) -> None:
    """Descomprime los datos de imagen por bloques y comprueba su tamaño exacto (si se conoce)."""
    maximo = esperado if esperado is not None else ANCHO_MAXIMO * ALTO_MAXIMO * 8 + ALTO_MAXIMO
    descompresor = zlib.decompressobj()
    total = 0
    try:
        for trozo in idat:
            pendiente = trozo
            while pendiente:
                salida = descompresor.decompress(pendiente, _BLOQUE)
                total += len(salida)
                if total > maximo:
                    raise _invalida("sus datos no corresponden a su tamaño")
                pendiente = descompresor.unconsumed_tail
        total += len(descompresor.flush())
    except zlib.error as exc:
        raise _invalida("sus datos están dañados") from exc
    if total > maximo or not descompresor.eof:
        raise _invalida("sus datos no corresponden a su tamaño")
    if esperado is not None and total != esperado:
        raise _invalida("sus datos no corresponden a su tamaño")
