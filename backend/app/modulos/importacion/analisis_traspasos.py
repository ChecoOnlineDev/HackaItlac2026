"""Revision de la tabla de un traspaso (FEAT-009, TR-04): funciones sin base de datos.

Lee las filas con el mapeo de columnas, identifica cada codigo (con una funcion que recibe el
servicio), revisa lo que se puede revisar sin el origen (codigo existente, cantidad entera
I-13, pieza una sola vez, serie) y consolida el mismo articulo por cantidad. Lo que depende del
origen (X-02, X-04, X-09, AL-04, X-03) lo evalua `MovimientoService.evaluar`, con las mismas
reglas de la captura manual: aqui no se repite ninguna.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

from app.modulos.catalogo.models import Articulo, Pieza
from app.modulos.importacion.analisis import MENSAJE_NO_ENTERA, parsear_cantidad
from app.modulos.importacion.lectura import clave, texto_de_celda

ROJO = "ROJO"
AMARILLO = "AMARILLO"
Identificar = Callable[[str], tuple[Articulo | None, Pieza | None]]


@dataclass
class MotivoFila:
    regla: str
    codigo: str
    mensaje: str
    nivel: str = ROJO


@dataclass
class FilaLeida:
    fila: int
    codigo: str
    cantidad: str
    codigo_pieza: str
    serie: str
    nombre: str = ""


@dataclass
class FilaAnalizada:
    fila: int
    codigo: str
    articulo: Articulo | None = None
    pieza: Pieza | None = None
    cantidad: int = 0
    unida_de: list[int] = field(default_factory=list)
    motivos: list[MotivoFila] = field(default_factory=list)
    nivel: str = "VERDE"
    disponible: int = 0

    @property
    def con_error_local(self) -> bool:
        return any(m.nivel == ROJO for m in self.motivos)

    @property
    def con_aviso_local(self) -> bool:
        return any(m.nivel == AMARILLO for m in self.motivos)

    def amarillo(self, regla: str, codigo: str, mensaje: str) -> None:
        """Un aviso que no bloquea (TR-13); no baja el nivel si la fila ya está en rojo."""
        self.motivos.append(MotivoFila(regla, codigo, mensaje, AMARILLO))
        if self.nivel != ROJO:
            self.nivel = AMARILLO

    def rojo(self, regla: str, codigo: str, mensaje: str) -> None:
        self.motivos.append(MotivoFila(regla, codigo, mensaje))
        self.nivel = ROJO


def _celda(fila: list, indice: int | None) -> str:
    if indice is None or indice >= len(fila):
        return ""
    return texto_de_celda(fila[indice])


def leer_filas(
    filas: list[list], columnas: dict[str, int | None], primera_fila: int
) -> list[FilaLeida]:
    """Las filas con datos (las vacias se saltan) con el numero que tienen en la hoja."""
    leidas = []
    for i, fila in enumerate(filas):
        leida = FilaLeida(
            fila=primera_fila + i,
            codigo=_celda(fila, columnas.get("codigo")),
            cantidad=_celda(fila, columnas.get("cantidad")),
            codigo_pieza=_celda(fila, columnas.get("codigo_pieza")),
            serie=_celda(fila, columnas.get("serie")),
            nombre=_celda(fila, columnas.get("nombre")),
        )
        if leida.codigo or leida.cantidad or leida.codigo_pieza or leida.serie:
            leidas.append(leida)
        elif any(texto_de_celda(c) for c in fila):
            # Trae datos solo en columnas que el traspaso no lee: se avisa como fila sin codigo.
            leidas.append(leida)
    return leidas


def huella_de_filas(leidas: list[FilaLeida]) -> list[list[str]]:
    """Las filas normalizadas y en orden fijo, para la huella del archivo (TR-08)."""
    filas = [
        [clave(f.codigo), clave(f.cantidad), clave(f.codigo_pieza), clave(f.serie)] for f in leidas
    ]
    filas.sort()
    return filas


def _nuevo_error_de_codigo(f: FilaAnalizada, texto: str, es_pieza: bool) -> None:
    cosa = "la pieza" if es_pieza else "el artículo"
    f.rojo("X-02", "ARTICULO_NO_EXISTE", f"El código {texto} no existe: no es de {cosa}.")


def preparar(
    leidas: list[FilaLeida],
    identificar: Identificar,
    *,
    cantidad_maxima: int,
    suma_maxima: int,
) -> list[FilaAnalizada]:
    """Una `FilaAnalizada` por fila que queda (las unidas a otra ya no aparecen)."""
    resultado: list[FilaAnalizada] = []
    piezas_vistas: dict[uuid.UUID, int] = {}
    por_articulo: dict[uuid.UUID, FilaAnalizada] = {}

    for leida in leidas:
        f = FilaAnalizada(fila=leida.fila, codigo=leida.codigo_pieza or leida.codigo)
        resultado.append(f)
        if not f.codigo:
            f.rojo("X-02", "ARTICULO_NO_EXISTE", "Falta el código del artículo o de la pieza.")
            continue

        articulo, pieza = identificar(f.codigo)
        if leida.codigo_pieza and pieza is None:
            if articulo is None:
                _nuevo_error_de_codigo(f, f.codigo, True)
            else:
                f.rojo("X-02", "ARTICULO_NO_EXISTE", f"El código {f.codigo} no es de una pieza.")
            continue
        if articulo is None:
            _nuevo_error_de_codigo(f, f.codigo, False)
            continue
        f.articulo, f.pieza = articulo, pieza
        _revisar_nombre(f, leida)

        if pieza is not None:
            _revisar_pieza(f, leida, piezas_vistas)
            continue
        if articulo.control == "PIEZA":
            f.rojo(
                "TR-04",
                "FALTA_CODIGO_PIEZA",
                f"{articulo.nombre} se controla por pieza: pon el código de cada pieza, una "
                "fila por pieza.",
            )
            continue
        _revisar_cantidad(f, leida, cantidad_maxima)
        if f.con_error_local:
            continue
        primera = por_articulo.get(articulo.id)
        if primera is None:
            por_articulo[articulo.id] = f
        elif primera.cantidad + f.cantidad > suma_maxima:
            f.rojo(
                "I-11", "CANTIDAD_INVALIDA", "Sumando las filas del mismo artículo, pasa del tope."
            )
        else:
            primera.cantidad += f.cantidad
            primera.unida_de.append(f.fila)
            for aviso in f.motivos:  # TR-13: el aviso de la fila unida no se pierde
                if aviso.nivel == AMARILLO:
                    primera.amarillo(aviso.regla, aviso.codigo, f"Fila {f.fila}: {aviso.mensaje}")
            resultado.pop()  # esta fila queda dentro de la primera
    return resultado


def _revisar_nombre(f: FilaAnalizada, leida: FilaLeida) -> None:
    """TR-13: la columna `nombre` es una ayuda de quien arma el archivo. Si no se parece al
    nombre del catálogo para ese código, la fila avisa (amarillo): quizá el código está mal."""
    if not leida.nombre or f.articulo is None:
        return
    escrito, catalogo = clave(leida.nombre), clave(f.articulo.nombre)
    if escrito == catalogo or escrito in catalogo or catalogo in escrito:
        return
    f.amarillo(
        "TR-13",
        "NOMBRE_NO_COINCIDE",
        f"El nombre «{leida.nombre}» no es el del catálogo para {f.codigo} "
        f"({f.articulo.nombre}). Revisa que el código esté bien.",
    )


def _revisar_pieza(f: FilaAnalizada, leida: FilaLeida, vistas: dict[uuid.UUID, int]) -> None:
    pieza = f.pieza
    assert pieza is not None
    f.cantidad = 1
    if leida.cantidad:
        valor, _ = parsear_cantidad(leida.cantidad)
        if valor != 1:
            f.rojo("RG-05", "CANTIDAD_INVALIDA", "Una pieza se traspasa de una en una.")
            return
    if leida.serie and pieza.numero_serie and clave(leida.serie) != clave(pieza.numero_serie):
        f.rojo(
            "TR-04",
            "SERIE_NO_COINCIDE",
            f"La serie {leida.serie} no es la de la pieza {pieza.codigo} ({pieza.numero_serie}).",
        )
        return
    anterior = vistas.get(pieza.id)
    if anterior is not None:
        f.rojo("TR-04", "PIEZA_REPETIDA", f"Esta pieza ya viene en la fila {anterior}.")
        return
    vistas[pieza.id] = f.fila


def _revisar_cantidad(f: FilaAnalizada, leida: FilaLeida, maxima: int) -> None:
    if not leida.cantidad:
        f.rojo("I-01", "CANTIDAD_INVALIDA", "Falta la cantidad.")
        return
    valor, error = parsear_cantidad(leida.cantidad)
    if error == "NO_ENTERA":
        f.rojo("I-13", "CANTIDAD_NO_ENTERA", MENSAJE_NO_ENTERA)
    elif valor is None:
        f.rojo(
            "I-01",
            "CANTIDAD_INVALIDA",
            f"La cantidad «{leida.cantidad}» no es un número entero.",
        )
    elif valor <= 0:
        f.rojo("I-01", "CANTIDAD_INVALIDA", "La cantidad debe ser mayor que cero.")
    elif valor > maxima:
        f.rojo("I-11", "CANTIDAD_INVALIDA", f"La cantidad pasa del tope de {maxima}.")
    else:
        f.cantidad = valor


def codigo_de_motivo(regla: str, es_pieza: bool) -> str:
    """El `codigo` por fila de un motivo del evaluador de movimientos."""
    if regla == "X-02":
        return "PIEZA_NO_ESTA_EN_ORIGEN" if es_pieza else "SIN_EXISTENCIA_EN_ORIGEN"
    return {
        "X-04": "PIEZA_NO_APTA",
        "X-09": "ARTICULO_INACTIVO",
        "RG-05": "CANTIDAD_INVALIDA",
    }.get(regla, regla.replace("-", "_"))
