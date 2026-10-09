"""Revision de las filas de la tabla, una por una, sin escribir nada.

La usan la vista previa y la confirmacion: es la misma revision, asi lo que se ve es lo que se
guarda. Cada motivo de rechazo lleva el ID de su regla (`I-02`, `I-10`, `RG-10`...).

Las filas con error no se importan y se listan; las buenas si entran (flujo 5). Dos modos (I-10):
`ALTA` crea los articulos que faltan y suma a los que existen; `REPOSICION` solo suma a los que
existen. Las filas del mismo articulo por cantidad en el mismo almacen se consolidan en una
(I-06, RG-10: "Unido: filas 2, 5, 9"); un codigo de pieza o una serie repetidos siguen siendo
error. Una pieza sin serie entra con aviso (I-17) y una sin codigo de pieza recibe
`CODIGO-DEL-ARTICULO-NNN` (I-15). Una fila "buena" tiene que ser coherente con las buenas que
van antes en la misma tabla.

La categoria sugerida (I-14) nunca se aplica sola: en la vista previa una fila con sugerencia
pendiente se muestra sin categoria; al confirmar solo cuenta lo que la persona eligio.
"""

import re
import uuid
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from app.config import get_settings
from app.modulos.almacenes.models import Almacen, EstadoAlmacen, TipoAlmacen
from app.modulos.catalogo.models import Articulo, Categoria, Control, TipoCodigo
from app.modulos.importacion.categorias_sugeridas import (
    PREFIJOS,
    es_servicio,
    limpiar_nombre,
    sugerir,
)
from app.modulos.importacion.lectura import clave, texto_de_celda
from app.modulos.importacion.repository import ImportacionRepository
from app.modulos.importacion.schemas import CAMPOS, ImportacionIn

COSTO_MAXIMO = Decimal("9999999999.99")
# `existencia.cantidad` es un entero de 32 bits: una fila unida no puede pasar de ahi.
EXISTENCIA_MAXIMA = 2_000_000_000
LONGITUD = {
    "codigo": 64,
    "nombre": 150,
    "marca": 80,
    "serie": 80,
    "codigo_pieza": 64,
    "unidad": 20,
}
UNIDAD_POR_OMISION = "pieza"
# Datos que la reposicion ignora (I-10): solo lee codigo, cantidad, almacen, codigo_pieza y serie.
CAMPOS_IGNORADOS_EN_REPOSICION = ("nombre", "marca", "categoria", "costo", "unidad")
MENSAJE_NO_ENTERA = (
    "La cantidad debe ser un número entero. Usa una unidad menor "
    "(por ejemplo, 250 gramos en lugar de 0.25 kilos)."
)
_NOMBRES_CODIGO = {
    TipoCodigo.ARTICULO: "un artículo",
    TipoCodigo.PIEZA: "una pieza",
    TipoCodigo.TRABAJADOR: "un trabajador",
    TipoCodigo.VALE: "un vale",
}

_ENTERO = re.compile(r"[+-]?[0-9]+")
_CON_MILES = re.compile(r"[+-]?[0-9]{1,3}(,[0-9]{3})+")
_CON_COMA = re.compile(r"[+-]?[0-9,]+")
_DECIMALES = re.compile(r"[0-9]+")


@dataclass
class Motivo:
    regla: str
    campo: str | None
    codigo: str
    mensaje: str


@dataclass
class Sugerida:
    """La categoria que propone el diccionario (I-14) y por que."""

    categoria: Categoria | None  # None: ninguna regla coincidio (por revisar)
    motivo: str | None


@dataclass
class FilaBuena:
    """Una fila que se puede guardar, ya con todo resuelto. Varias filas del mismo articulo por
    cantidad y almacen son una sola (`unida_de` lleva las demas)."""

    fila: int
    codigo: str
    codigo_generado: bool
    nombre: str
    marca: str | None
    articulo: Articulo | None  # None: el articulo se crea
    categoria: Categoria | None  # solo de un articulo nuevo; None mientras sea solo sugerida
    categoria_sugerida: Categoria | None
    motivo_sugerencia: str | None
    control: str
    cantidad: int
    almacen: Almacen
    codigo_pieza: str | None
    numero_serie: str | None
    costo: Decimal | None
    saldo_antes: int
    saldo_despues: int
    unidad: str = UNIDAD_POR_OMISION
    codigo_pieza_generado: bool = False
    unida_de: list[int] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    @property
    def serie_pendiente(self) -> bool:
        return self.control == Control.PIEZA and not self.numero_serie

    @property
    def nuevo(self) -> bool:
        return self.articulo is None

    @property
    def estado(self) -> str:
        if self.unida_de:
            return "UNIDO"
        return "NUEVO" if self.nuevo else "EXISTENTE"


@dataclass
class FilaMala:
    fila: int
    datos: dict[str, str]
    motivos: list[Motivo]
    sugerida: Sugerida | None = None


@dataclass
class FilaExcluida:
    fila: int
    nombre: str
    motivo: str


@dataclass
class ArticuloPorCrear:
    codigo: str  # vacio hasta que se registra la primera fila buena (puede ser generado)
    nombre: str
    marca: str | None
    categoria: Categoria
    control: str
    costo: Decimal | None
    fila: int  # la primera fila que lo define
    filas: int = 1
    codigo_generado: bool = False
    unidad: str = UNIDAD_POR_OMISION
    pendiente: bool = False  # la categoria es solo una sugerencia que nadie ha elegido


@dataclass
class Resultado:
    columnas: dict[str, int | None]
    modo: str = "ALTA"
    avisos: list[str] = field(default_factory=list)
    buenas: list[FilaBuena] = field(default_factory=list)
    malas: list[FilaMala] = field(default_factory=list)
    excluidas: list[FilaExcluida] = field(default_factory=list)
    nuevos: dict[str, ArticuloPorCrear] = field(default_factory=dict)
    categorias_desconocidas: dict[str, tuple[str, list[int]]] = field(default_factory=dict)
    por_revisar: int = 0
    vacias: int = 0
    total: int = 0


@dataclass(frozen=True)
class Contexto:
    """Quien importa y lo que puede hacer."""

    puede_costos: bool
    puede_todos_los_almacenes: bool
    almacen_asignado_id: uuid.UUID | None
    puede_crear_articulos: bool = True
    cantidad_maxima: int = 100_000
    # Al confirmar, una sugerencia que la persona no eligio no se aplica (I-14).
    confirmando: bool = False


def parsear_cantidad(texto: str) -> tuple[int | None, str | None]:
    """Un entero escrito como `10`, `10.0` o `1,000`. Devuelve `(valor, None)` o
    `(None, "INVALIDA" | "NO_ENTERA")`. Nunca redondea (I-13): `0.25`, `0,25` y `1,5` no son
    enteros; la coma solo vale como separador de miles, en grupos de tres (`1,250` es 1250)."""
    limpio = texto.replace(" ", "")
    if not limpio:
        return None, "INVALIDA"
    entero, punto, decimales = limpio.partition(".")
    if "," in entero:
        if _CON_MILES.fullmatch(entero):
            entero = entero.replace(",", "")
        elif _CON_COMA.fullmatch(entero):
            return None, "NO_ENTERA"  # coma ambigua: `0,25`, `1,5`
        else:
            return None, "INVALIDA"
    elif not _ENTERO.fullmatch(entero):
        return None, "INVALIDA"
    if punto:
        if not _DECIMALES.fullmatch(decimales):
            return None, "INVALIDA"
        if decimales.strip("0") != "":
            return None, "NO_ENTERA"
    return int(entero), None


def _costo(texto: str) -> Decimal | None:
    limpio = texto.replace("$", "").replace(",", "").replace(" ", "")
    try:
        valor = Decimal(limpio)
    except InvalidOperation:
        return None
    if not valor.is_finite() or valor < 0 or valor > COSTO_MAXIMO:
        return None
    return valor.quantize(Decimal("0.01"))


class Analizador:
    def __init__(self, repository: ImportacionRepository, contexto: Contexto) -> None:
        self.repository = repository
        self.ctx = contexto
        self.modo = "ALTA"

    # ------------------------------------------------------------------ preparación

    def analizar(self, datos: ImportacionIn, columnas: dict[str, int | None]) -> Resultado:
        self.modo = datos.modo
        reposicion = self.modo == "REPOSICION"
        filas = [self._leer(f, columnas) for f in datos.filas]
        resultado = Resultado(columnas=columnas, modo=self.modo, total=len(filas))
        if reposicion:
            ignorados = [c for c in CAMPOS_IGNORADOS_EN_REPOSICION if any(f[c] for f in filas)]
            if ignorados:
                resultado.avisos.append(
                    "Se ignoraron las columnas de "
                    + ", ".join(ignorados)
                    + ": la reposición solo suma a artículos que ya existen y no cambia sus datos."
                )
            for f in filas:
                for c in CAMPOS_IGNORADOS_EN_REPOSICION:
                    f[c] = ""

        categorias = self.repository.categorias()
        por_nombre = {clave(c.nombre): c for c in categorias if c.activo}
        por_id = {c.id: c for c in categorias}
        elegidas = self._categorias_elegidas(datos, por_id)
        # EK-01, EK-02: todo entra al almacen central; la columna `almacen` se ignora (con aviso).
        almacenes = self.repository.almacenes()
        defecto = next((a for a in almacenes if a.tipo == TipoAlmacen.CENTRAL), None)
        if any(f["almacen"] for f in filas):
            resultado.avisos.append(
                "Se ignoró la columna de almacén: toda la mercancía entra a Kepler "
                "y de ahí se reparte por traspaso."
            )

        # Lo que la base ya sabe de los codigos, nombres y series de la tabla.
        codigos_tabla = {f["codigo"] for f in filas if f["codigo"]} | {
            f["codigo_pieza"] for f in filas if f["codigo_pieza"]
        }
        en_base = self.repository.codigos(codigos_tabla)
        articulos_base = self.repository.articulos(
            c.ref_id for c in en_base.values() if c.tipo == TipoCodigo.ARTICULO
        )
        por_nombre_articulo: dict[tuple[str, str], Articulo] = {}
        if not reposicion:
            sin_codigo = {
                limpiar_nombre(f["nombre"]) for f in filas if not f["codigo"] and f["nombre"]
            }
            for a in self.repository.articulos_por_nombre(sin_codigo):
                por_nombre_articulo.setdefault((clave(a.nombre), clave(a.marca or "")), a)
                articulos_base.setdefault(a.id, a)
        series_base = self.repository.series_en_uso(
            articulos_base.keys(), {f["serie"] for f in filas if f["serie"]}
        )

        estado = _Estado(
            categorias=por_nombre,
            categorias_por_id=por_id,
            elegidas=elegidas,
            por_fila=self._categorias_por_fila(datos, por_id),
            defecto=defecto,
            en_base=en_base,
            articulos_base=articulos_base,
            por_nombre_articulo=por_nombre_articulo,
            series_base=series_base,
            saldos_base=self.repository.saldos(articulos_base.keys()),
            claves_en_tabla={clave(c) for c in codigos_tabla},
        )
        columna_costo_con_datos = False
        for indice, f in enumerate(filas):
            numero = datos.primera_fila + indice
            if not any(f.values()):
                resultado.vacias += 1
                continue
            if f["costo"]:
                columna_costo_con_datos = True
            self._revisar(numero, f, resultado, estado)
        if (
            not reposicion
            and columnas.get("costo") is not None
            and columna_costo_con_datos
            and not self.ctx.puede_costos
        ):
            resultado.avisos.append(
                "Se ignoró la columna de costo: no tienes permiso para capturar costos."
            )
        resultado.buenas.sort(key=lambda b: b.fila)
        resultado.malas.sort(key=lambda m: m.fila)
        resultado.excluidas.sort(key=lambda x: x.fila)
        return resultado

    @staticmethod
    def _leer(fila: list, columnas: dict[str, int | None]) -> dict[str, str]:
        salida = {}
        for campo in CAMPOS:
            indice = columnas.get(campo)
            salida[campo] = (
                texto_de_celda(fila[indice]) if indice is not None and indice < len(fila) else ""
            )
        return salida

    @staticmethod
    def _categoria_activa(
        por_id: dict[uuid.UUID, Categoria], categoria_id: uuid.UUID, campo: str
    ) -> Categoria:
        from app.core.excepciones import DatosInvalidos

        elegida = por_id.get(categoria_id)
        if elegida is None or not elegida.activo:
            raise DatosInvalidos(
                "La categoría elegida no existe o está inactiva.",
                [{"campo": campo, "mensaje": "Elige una categoría activa."}],
            )
        return elegida

    def _categorias_elegidas(
        self, datos: ImportacionIn, por_id: dict[uuid.UUID, Categoria]
    ) -> _Elegidas:
        defecto = (
            self._categoria_activa(
                por_id, datos.categoria_por_defecto_id, "categoria_por_defecto_id"
            )
            if datos.categoria_por_defecto_id
            else None
        )
        mapa = {
            clave(nombre): self._categoria_activa(por_id, categoria_id, "mapa_categorias")
            for nombre, categoria_id in datos.mapa_categorias.items()
        }
        return _Elegidas(defecto=defecto, mapa=mapa)

    def _categorias_por_fila(
        self, datos: ImportacionIn, por_id: dict[uuid.UUID, Categoria]
    ) -> dict[int, Categoria]:
        return {
            int(fila): self._categoria_activa(por_id, categoria_id, "categoria_por_fila")
            for fila, categoria_id in datos.categoria_por_fila.items()
        }

    # --------------------------------------------------------------------- una fila

    def _revisar(self, numero: int, f: dict[str, str], res: Resultado, e: _Estado) -> None:
        motivos: list[Motivo] = []
        avisos: list[str] = []
        reposicion = self.modo == "REPOSICION"

        def malo(regla: str, campo: str | None, codigo: str, mensaje: str) -> None:
            motivos.append(Motivo(regla, campo, codigo, mensaje))

        nombre = "" if reposicion else limpiar_nombre(f["nombre"])
        if nombre and es_servicio(nombre):
            res.excluidas.append(FilaExcluida(numero, nombre, "Es un servicio, no un artículo."))
            return

        for campo, maximo in LONGITUD.items():
            if len(f[campo]) > maximo:
                malo(
                    "I-06",
                    campo,
                    "DEMASIADO_LARGO",
                    f"El dato «{campo.replace('_', ' ')}» pasa de {maximo} caracteres.",
                )
        codigo = f["codigo"]
        articulo: Articulo | None = None
        nuevo: ArticuloPorCrear | None = None
        categoria: Categoria | None = None
        sugerida: Sugerida | None = None
        control: str | None = None
        ident: str | None = None
        k = clave(codigo)

        # ---- el articulo
        if codigo:
            if len(codigo) <= LONGITUD["codigo"]:
                en_base = e.en_base.get(k)
                if en_base is not None and en_base.tipo != TipoCodigo.ARTICULO:
                    que = _NOMBRES_CODIGO.get(en_base.tipo, "otra cosa")
                    malo(
                        "RG-10",
                        "codigo",
                        "CODIGO_REPETIDO",
                        f"El código {codigo} ya identifica {que}. "
                        "Un código identifica una sola cosa.",
                    )
                elif en_base is not None:
                    articulo = e.articulos_base.get(en_base.ref_id)
                    if articulo is not None:
                        control = self._existente(articulo, malo)
                        ident = f"A:{articulo.id}"
                elif k in e.piezas_tabla:
                    malo(
                        "RG-10",
                        "codigo",
                        "CODIGO_REPETIDO",
                        f"El código {codigo} ya es el de una pieza en la fila "
                        f"{e.piezas_tabla[k]}. Un código identifica una sola cosa.",
                    )
                elif reposicion:
                    malo(
                        "I-10",
                        "codigo",
                        "ARTICULO_NO_EXISTE",
                        "Ese artículo no existe: dalo de alta primero.",
                    )
                else:
                    ident = f"C:{k}"
                    nuevo, categoria, control, sugerida = self._articulo_nuevo(
                        f, nombre, ident, numero, res, e, malo
                    )
        elif reposicion:
            malo("I-06", "codigo", "FALTA_CODIGO", "Falta el código del artículo.")
        elif not nombre:
            malo("I-06", "codigo", "FALTA_CODIGO", "Falta el código o el nombre del artículo.")
        else:
            llave = (clave(nombre), clave(f["marca"]))
            existente = e.por_nombre_articulo.get(llave)
            if existente is not None:
                articulo = existente
                control = self._existente(articulo, malo)
                ident = f"A:{articulo.id}"
            elif llave in e.nuevos_por_nombre:
                ident = e.nuevos_por_nombre[llave]
                nuevo = res.nuevos[ident]
                categoria, control = nuevo.categoria, nuevo.control
            else:
                ident = f"N:{llave[0]}|{llave[1]}"
                nuevo, categoria, control, sugerida = self._articulo_nuevo(
                    f, nombre, ident, numero, res, e, malo
                )

        # ---- avisos de un articulo que ya existe: nunca se actualiza nada
        if articulo is not None and not reposicion:
            self._avisar_diferencias(articulo, f, nombre, e, avisos)

        # ---- el almacen
        almacen = self._almacen(e, malo)

        # ---- cantidad, pieza y serie
        cantidad = 0
        codigo_pieza: str | None = None
        serie: str | None = None
        previa: FilaBuena | None = None
        pieza_generada = False
        if control == Control.CANTIDAD:
            cantidad = self._cantidad_por_cantidad(f["cantidad"], malo)
            if f["codigo_pieza"] or f["serie"]:
                avisos.append(
                    "Es un artículo por cantidad: se ignoran el código de pieza y la serie."
                )
            if almacen is not None and cantidad > 0 and ident is not None:
                previa = e.cantidades_tabla.get((ident, almacen.id))
                if previa is not None and previa.cantidad + cantidad > EXISTENCIA_MAXIMA:
                    malo(
                        "I-11",
                        "cantidad",
                        "CANTIDAD_EXCESIVA",
                        "Sumadas con las filas unidas, las cantidades pasan de lo que se puede "
                        "guardar.",
                    )
        elif control == Control.PIEZA:
            cantidad = 1
            assert ident is not None
            codigo_pieza, serie, pieza_generada = self._pieza(f, k, ident, articulo, e, malo)
            if not f["serie"]:
                avisos.append(
                    "Serie pendiente: la pieza entra sin número de serie; se puede completar "
                    "después."
                )
            requiere = (
                articulo.requiere_inspeccion
                if articulo
                else (categoria.requiere_inspeccion if categoria else False)
            )
            if requiere:
                avisos.append(
                    "Entra pendiente de inspección: no se podrá entregar hasta inspeccionarla."
                )

        # ---- el costo
        costo = None
        if not reposicion and self.ctx.puede_costos and f["costo"]:
            costo = _costo(f["costo"])
            if costo is None:
                malo(
                    "I-04",
                    "costo",
                    "COSTO_INVALIDO",
                    "El costo debe ser un número mayor o igual a cero.",
                )
            elif articulo is not None:
                avisos.append("El artículo ya existe: su costo no se cambia.")
                costo = None

        if costo is not None and costo >= get_settings().alto_valor_costo_minimo:
            avisos.append("Por su costo cuenta como alto valor.")
        if control == Control.CANTIDAD and (
            (categoria and categoria.alto_valor)
            or (costo is not None and costo >= get_settings().alto_valor_costo_minimo)
        ):
            avisos.append(
                "Conviene controlarlo por pieza, con serie, para saber quién tiene cada uno."
            )

        if motivos:
            visibles = {c: v for c, v in f.items() if self.ctx.puede_costos or c != "costo"}
            res.malas.append(FilaMala(numero, visibles, motivos, sugerida))
            return

        assert almacen is not None and control is not None and ident is not None
        pendiente = False
        if nuevo is not None:
            nuevo = res.nuevos.setdefault(ident, nuevo)  # la primera fila buena lo define
            nuevo.filas += 1
            pendiente = nuevo.pendiente
            if nuevo.fila != numero and nombre and clave(nombre) != clave(nuevo.nombre):
                avisos.append(f"Se usa el nombre de la fila {nuevo.fila}: «{nuevo.nombre}».")
            if costo is not None and nuevo.costo is None:
                nuevo.costo = costo
            if not nuevo.codigo:
                nuevo.codigo = self._generar_codigo(nuevo.categoria, e)
                nuevo.codigo_generado = True
            e.nuevos_por_nombre.setdefault((clave(nuevo.nombre), clave(nuevo.marca or "")), ident)
        if codigo:
            e.codigos_articulo_tabla.add(k)
        saldo_llave = (ident, almacen.id)
        saldo = e.saldos_tabla.get(saldo_llave)
        if saldo is None:
            saldo = e.saldos_base.get((articulo.id, almacen.id), 0) if articulo else 0

        if control == Control.CANTIDAD:
            if previa is not None:
                self._unir(previa, numero, cantidad, avisos)
                e.saldos_tabla[saldo_llave] = previa.saldo_despues
                return
        else:
            if pieza_generada:
                base = articulo.codigo if articulo else (nuevo.codigo if nuevo else codigo)
                codigo_pieza = self._generar_codigo_pieza(base, e)
            assert codigo_pieza is not None
            e.piezas_tabla[clave(codigo_pieza)] = numero
            if serie:
                e.series_tabla[(ident, clave(serie))] = numero
        fila_buena = FilaBuena(
            fila=numero,
            codigo=articulo.codigo if articulo else (nuevo.codigo if nuevo else codigo),
            codigo_generado=bool(nuevo and nuevo.codigo_generado),
            nombre=articulo.nombre if articulo else (nuevo.nombre if nuevo else nombre),
            marca=articulo.marca if articulo else (nuevo.marca if nuevo else None),
            articulo=articulo,
            categoria=None if pendiente else (nuevo.categoria if nuevo else None),
            categoria_sugerida=sugerida.categoria if sugerida else None,
            motivo_sugerencia=sugerida.motivo if sugerida and sugerida.categoria else None,
            control=control,
            cantidad=cantidad,
            almacen=almacen,
            codigo_pieza=codigo_pieza,
            numero_serie=serie,
            costo=costo,
            saldo_antes=saldo,
            saldo_despues=saldo + cantidad,
            unidad=articulo.unidad if articulo else (nuevo.unidad if nuevo else UNIDAD_POR_OMISION),
            codigo_pieza_generado=pieza_generada,
            avisos=avisos,
        )
        e.saldos_tabla[saldo_llave] = saldo + cantidad
        if control == Control.CANTIDAD:
            e.cantidades_tabla[(ident, almacen.id)] = fila_buena
        res.buenas.append(fila_buena)

    @staticmethod
    def _unir(previa: FilaBuena, numero: int, cantidad: int, avisos: list[str]) -> None:
        """Suma una fila del mismo articulo y almacen a la que ya esta (I-06)."""
        previa.cantidad += cantidad
        previa.saldo_despues += cantidad
        previa.unida_de.append(numero)
        filas = ", ".join(str(n) for n in (previa.fila, *previa.unida_de))
        previa.avisos = [a for a in previa.avisos if not a.startswith("Unido:")]
        previa.avisos.insert(0, f"Unido: filas {filas}")
        for aviso in avisos:
            if aviso not in previa.avisos and not aviso.startswith("Se usa el nombre"):
                previa.avisos.append(aviso)

    @staticmethod
    def _existente(articulo: Articulo, malo) -> str:
        """Un articulo que ya existe: si esta inactivo no recibe entradas (I-09)."""
        if not articulo.activo:
            motivo = f" ({articulo.motivo_inactivacion})" if articulo.motivo_inactivacion else ""
            malo(
                "I-09",
                "codigo",
                "ARTICULO_INACTIVO",
                f"{articulo.nombre} está inactivo{motivo}. No recibe entradas.",
            )
        return articulo.control

    @staticmethod
    def _avisar_diferencias(
        articulo: Articulo, f: dict[str, str], nombre: str, e: _Estado, avisos: list[str]
    ) -> None:
        """El archivo no cambia nada de un articulo que ya existe; solo se avisa si difiere."""
        if nombre and clave(nombre) != clave(articulo.nombre):
            avisos.append("El nombre del archivo es distinto del registrado; no se cambia.")
        if f["unidad"] and clave(f["unidad"]) != clave(articulo.unidad):
            avisos.append("La unidad del archivo es distinta de la registrada; no se cambia.")
        if f["marca"] and clave(f["marca"]) != clave(articulo.marca or ""):
            avisos.append("La marca del archivo es distinta de la registrada; no se cambia.")
        registrada = e.categorias_por_id.get(articulo.categoria_id)
        if (
            f["categoria"]
            and registrada is not None
            and clave(f["categoria"]) != clave(registrada.nombre)
        ):
            avisos.append("La categoría del archivo es distinta de la registrada; no se cambia.")

    # ----------------------------------------------------------------- piezas de la fila

    def _articulo_nuevo(
        self, f, nombre: str, ident: str, numero: int, res: Resultado, e: _Estado, malo
    ):
        """Resuelve un articulo que no existe: toma su categoria (CF-02) y su control. Si otra
        fila buena ya lo definio, se usa esa definicion. Devuelve
        `(nuevo, categoria, control, sugerida)`."""
        previo = res.nuevos.get(ident)
        if previo is not None:
            return previo, previo.categoria, previo.control, None
        if not self.ctx.puede_crear_articulos:
            malo(
                "I-10",
                "codigo",
                "SIN_PERMISO_CREAR",
                "No tienes permiso para dar de alta artículos: este no existe todavía.",
            )
            return None, None, None, None
        if not nombre:
            malo(
                "I-06", "nombre", "FALTA_NOMBRE", "Falta el nombre: el artículo no existe todavía."
            )
        categoria, sugerida, pendiente = self._categoria(f, nombre, numero, res, e, malo)
        if not nombre or categoria is None:
            return None, None, None, sugerida
        if not f["codigo"] and categoria.nombre not in PREFIJOS:
            malo(
                "I-06",
                "codigo",
                "FALTA_CODIGO",
                f"La categoría {categoria.nombre} no genera códigos: escribe el código del "
                "artículo.",
            )
            return None, None, None, sugerida
        nuevo = ArticuloPorCrear(
            codigo=f["codigo"],
            nombre=nombre,
            marca=f["marca"] or None,
            categoria=categoria,
            control=categoria.control,
            costo=None,
            fila=numero,
            filas=0,
            unidad=f["unidad"] or UNIDAD_POR_OMISION,
            pendiente=pendiente,
        )
        # Solo queda definido si la fila resulta buena: se registra al terminar la revision.
        return nuevo, categoria, categoria.control, sugerida

    def _categoria(self, f, nombre: str, numero: int, res: Resultado, e: _Estado, malo):
        """La categoria de un articulo nuevo, de mas a menos fuerte: la columna del archivo (o su
        equivalente en `mapa_categorias`), `categoria_por_fila` y `categoria_por_defecto_id`. La
        sugerencia (I-14) solo se calcula si el archivo no trae categoria y nunca se aplica sola.
        Devuelve `(categoria, sugerida, pendiente)`."""
        en_archivo = f["categoria"]
        sugerida: Sugerida | None = None
        if en_archivo:
            if clave(en_archivo) in e.categorias:
                return e.categorias[clave(en_archivo)], None, False
            elegida = e.elegidas.mapa.get(clave(en_archivo))
        else:
            elegida = None
            costo = _costo(f["costo"]) if self.ctx.puede_costos and f.get("costo") else None
            if (
                costo is not None
                and costo >= get_settings().alto_valor_costo_minimo
                and clave("Equipo de alto valor") in e.categorias
            ):
                sugerida = Sugerida(
                    e.categorias[clave("Equipo de alto valor")],
                    "Su costo es de " + str(get_settings().alto_valor_costo_minimo) + " o más",
                )
            elif nombre:
                sugerencia = sugerir(nombre)
                existente = e.categorias.get(clave(sugerencia.categoria)) if sugerencia else None
                if sugerencia is not None and existente is not None:
                    sugerida = Sugerida(existente, sugerencia.motivo)
                else:
                    sugerida = Sugerida(None, None)
        elegida = elegida or e.por_fila.get(numero) or e.elegidas.defecto
        if elegida is not None:
            return elegida, sugerida, False
        etiqueta = en_archivo or "(sin categoría)"
        if en_archivo:
            mensaje = f"La categoría «{en_archivo}» no existe. Elige una para estas filas."
        elif sugerida is not None and sugerida.categoria is not None:
            if not self.ctx.confirmando:
                # Se muestra la sugerencia sin aplicarla: la persona la ve y la acepta o la cambia.
                return sugerida.categoria, sugerida, True
            mensaje = (
                f"La categoría sugerida ({sugerida.categoria.nombre}) no se aplica sola: "
                "elígela en la fila."
            )
        else:
            res.por_revisar += 1
            mensaje = "No se pudo sugerir una categoría: elige una para esta fila."
        res.categorias_desconocidas.setdefault(clave(en_archivo), (etiqueta, []))[1].append(numero)
        malo("CF-02", "categoria", "CATEGORIA_DESCONOCIDA", mensaje)
        return None, sugerida, False

    def _generar_codigo(self, categoria: Categoria, e: _Estado) -> str:
        """`PREFIJO-NNNN`, consecutivo por categoria. En la confirmacion se llama con las
        categorias bloqueadas, asi dos lotes nunca reciben el mismo."""
        prefijo = PREFIJOS[categoria.nombre]
        if prefijo not in e.consecutivos:
            e.consecutivos[prefijo] = self.repository.ultimo_numero_con_prefijo(prefijo)
        while True:
            e.consecutivos[prefijo] += 1
            codigo = f"{prefijo}-{e.consecutivos[prefijo]:04d}"
            if clave(codigo) not in e.claves_en_tabla:
                return codigo

    def _generar_codigo_pieza(self, codigo_articulo: str, e: _Estado) -> str:
        """`CODIGO-DEL-ARTICULO-NNN` (I-15), consecutivo por articulo. Salta lo que ya trae la
        tabla; lo que ya hay en la base lo cubre el consecutivo inicial. En la confirmacion se
        llama con las categorias bloqueadas."""
        base = clave(codigo_articulo)
        if base not in e.consecutivos_pieza:
            e.consecutivos_pieza[base] = self.repository.ultimo_numero_con_prefijo(codigo_articulo)
        while True:
            e.consecutivos_pieza[base] += 1
            codigo = f"{codigo_articulo}-{e.consecutivos_pieza[base]:03d}"
            k = clave(codigo)
            if (
                k not in e.claves_en_tabla
                and k not in e.piezas_tabla
                and k not in e.codigos_articulo_tabla
            ):
                return codigo

    def _almacen(self, e: _Estado, malo) -> Almacen | None:
        """EK-01: el destino es siempre el almacen central (se resuelve por su tipo)."""
        almacen = e.defecto
        if almacen is None:
            malo("EK-01", "almacen", "FALTA_ALMACEN", "No hay un almacén central para dar entrada.")
            return None
        if almacen.estado == EstadoAlmacen.CERRADO:
            malo("I-01", "almacen", "ALMACEN_CERRADO", f"El almacén {almacen.nombre} está cerrado.")
            return None
        if not self.ctx.puede_todos_los_almacenes and almacen.id != self.ctx.almacen_asignado_id:
            malo(
                "AC-06",
                "almacen",
                "ALMACEN_AJENO",
                f"Solo puedes cargar inventario a tu almacén; {almacen.nombre} no es el tuyo.",
            )
            return None
        return almacen

    def _cantidad_por_cantidad(self, texto: str, malo) -> int:
        if not texto:
            malo("I-01", "cantidad", "FALTA_CANTIDAD", "Falta la cantidad.")
            return 0
        valor, error = parsear_cantidad(texto)
        if error == "NO_ENTERA":
            malo("I-13", "cantidad", "CANTIDAD_NO_ENTERA", MENSAJE_NO_ENTERA)
            return 0
        if valor is None:
            malo(
                "I-01",
                "cantidad",
                "CANTIDAD_INVALIDA",
                f"La cantidad «{texto}» no es un número entero.",
            )
            return 0
        if valor <= 0:
            malo("I-01", "cantidad", "CANTIDAD_INVALIDA", "La cantidad debe ser mayor que cero.")
            return 0
        if valor > self.ctx.cantidad_maxima:
            malo(
                "I-11",
                "cantidad",
                "CANTIDAD_EXCESIVA",
                f"La cantidad no puede pasar de {self.ctx.cantidad_maxima:,} por fila. "
                "Revisa que no sobre un cero.",
            )
            return 0
        return valor

    @staticmethod
    def _pieza(f, k, ident: str, articulo: Articulo | None, e: _Estado, malo):
        """Codigo y serie de la pieza (I-02). Devuelve `(codigo_pieza, serie, generado)`. Sin
        codigo de pieza se devuelve `None` con `generado` verdadero (se arma despues, I-15); sin
        serie queda `None` (serie pendiente, I-17)."""
        if f["cantidad"]:
            valor, _ = parsear_cantidad(f["cantidad"])
            if valor != 1:
                malo("RG-05", "cantidad", "CANTIDAD_INVALIDA", "Una pieza entra de una en una.")
        codigo_pieza: str | None = f["codigo_pieza"]
        generado = False
        if not codigo_pieza:
            generado = True
            codigo_pieza = None
            largo = len(articulo.codigo) if articulo else len(f["codigo"])
            if largo + 4 > LONGITUD["codigo_pieza"]:
                malo(
                    "I-15",
                    "codigo_pieza",
                    "DEMASIADO_LARGO",
                    "El código del artículo es muy largo para generar el de la pieza: "
                    "escribe el código de la pieza.",
                )
        elif len(codigo_pieza) <= LONGITUD["codigo_pieza"]:
            kp = clave(codigo_pieza)
            en_base = e.en_base.get(kp)
            if kp == k:
                malo(
                    "RG-10",
                    "codigo_pieza",
                    "CODIGO_REPETIDO",
                    "El código de la pieza no puede ser el del artículo.",
                )
            elif en_base is not None:
                que = _NOMBRES_CODIGO.get(en_base.tipo, "otra cosa")
                malo(
                    "I-02",
                    "codigo_pieza",
                    "CODIGO_REPETIDO",
                    f"El código {codigo_pieza} ya identifica {que}.",
                )
            elif kp in e.piezas_tabla:
                malo(
                    "I-02",
                    "codigo_pieza",
                    "CODIGO_REPETIDO",
                    f"El código {codigo_pieza} ya está en la fila {e.piezas_tabla[kp]}.",
                )
            elif kp in e.codigos_articulo_tabla:
                malo(
                    "RG-10",
                    "codigo_pieza",
                    "CODIGO_REPETIDO",
                    f"El código {codigo_pieza} ya es el de un artículo de esta tabla.",
                )
        serie: str | None = f["serie"] or None
        if serie is None:
            pass  # serie pendiente (I-17): no es error
        elif len(serie) <= LONGITUD["serie"]:
            ks = clave(serie)
            if articulo is not None and (articulo.id, ks) in e.series_base:
                malo(
                    "I-02",
                    "serie",
                    "SERIE_REPETIDA",
                    f"Ya existe una pieza de este artículo con el número de serie {serie}.",
                )
            elif (ident, ks) in e.series_tabla:
                malo(
                    "I-02",
                    "serie",
                    "SERIE_REPETIDA",
                    f"El número de serie {serie} ya está en la fila {e.series_tabla[(ident, ks)]}.",
                )
        return codigo_pieza, serie, generado


@dataclass
class _Elegidas:
    defecto: Categoria | None
    mapa: dict[str, Categoria]


@dataclass
class _Estado:
    """Lo que se sabe mientras se revisa la tabla, fila por fila."""

    categorias: dict[str, Categoria]
    categorias_por_id: dict[uuid.UUID, Categoria]
    elegidas: _Elegidas
    por_fila: dict[int, Categoria]
    defecto: Almacen | None
    en_base: dict
    articulos_base: dict
    por_nombre_articulo: dict[tuple[str, str], Articulo]
    series_base: set
    saldos_base: dict[tuple[uuid.UUID, uuid.UUID], int]
    claves_en_tabla: set[str]
    # Lo que ya aceptaron las filas buenas anteriores, con su numero de fila.
    piezas_tabla: dict[str, int] = field(default_factory=dict)
    series_tabla: dict[tuple[str, str], int] = field(default_factory=dict)
    cantidades_tabla: dict[tuple[str, uuid.UUID], FilaBuena] = field(default_factory=dict)
    saldos_tabla: dict[tuple[str, uuid.UUID], int] = field(default_factory=dict)
    codigos_articulo_tabla: set[str] = field(default_factory=set)
    nuevos_por_nombre: dict[tuple[str, str], str] = field(default_factory=dict)
    consecutivos: dict[str, int] = field(default_factory=dict)
    consecutivos_pieza: dict[str, int] = field(default_factory=dict)
