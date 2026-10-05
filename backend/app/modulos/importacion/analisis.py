"""Revision de las filas de la tabla, una por una, sin escribir nada.

La usan la vista previa y la confirmacion: es la misma revision, asi lo que se ve es lo que se
guarda. Cada motivo de rechazo lleva el ID de su regla (`I-02`, `I-09`, `RG-10`...).

Las filas con error no se importan y se listan; las buenas si entran (flujo 5). Una fila "buena"
tambien tiene que ser coherente con las buenas que van antes en la misma tabla: dos filas con
el mismo codigo de pieza, o el mismo articulo por cantidad en el mismo almacen, son un conflicto
y la segunda se rechaza con el numero de la primera.
"""

import uuid
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from app.modulos.almacenes.models import Almacen, EstadoAlmacen
from app.modulos.catalogo.models import Articulo, Categoria, Control, TipoCodigo
from app.modulos.importacion.lectura import clave, texto_de_celda
from app.modulos.importacion.repository import ImportacionRepository
from app.modulos.importacion.schemas import CAMPOS, ImportacionIn

CANTIDAD_MAXIMA = 1_000_000
COSTO_MAXIMO = Decimal("9999999999.99")
LONGITUD = {"codigo": 64, "nombre": 150, "marca": 80, "serie": 80, "codigo_pieza": 64}
_NOMBRES_CODIGO = {
    TipoCodigo.ARTICULO: "un artículo",
    TipoCodigo.PIEZA: "una pieza",
    TipoCodigo.TRABAJADOR: "un trabajador",
    TipoCodigo.VALE: "un vale",
}


@dataclass
class Motivo:
    regla: str
    campo: str | None
    codigo: str
    mensaje: str


@dataclass
class FilaBuena:
    """Una fila que se puede guardar, ya con todo resuelto."""

    fila: int
    codigo: str
    nombre: str
    marca: str | None
    articulo: Articulo | None  # None: el articulo se crea
    categoria: Categoria | None  # solo de un articulo nuevo
    control: str
    cantidad: int
    almacen: Almacen
    codigo_pieza: str | None
    numero_serie: str | None
    costo: Decimal | None
    avisos: list[str] = field(default_factory=list)

    @property
    def nuevo(self) -> bool:
        return self.articulo is None


@dataclass
class FilaMala:
    fila: int
    datos: dict[str, str]
    motivos: list[Motivo]


@dataclass
class ArticuloPorCrear:
    codigo: str
    nombre: str
    marca: str | None
    categoria: Categoria
    control: str
    costo: Decimal | None
    fila: int  # la primera fila que lo define
    filas: int = 1


@dataclass
class Resultado:
    columnas: dict[str, int | None]
    avisos: list[str] = field(default_factory=list)
    buenas: list[FilaBuena] = field(default_factory=list)
    malas: list[FilaMala] = field(default_factory=list)
    nuevos: dict[str, ArticuloPorCrear] = field(default_factory=dict)
    categorias_desconocidas: dict[str, tuple[str, list[int]]] = field(default_factory=dict)
    vacias: int = 0
    total: int = 0


@dataclass(frozen=True)
class Contexto:
    """Quien importa y lo que puede hacer."""

    puede_costos: bool
    puede_todos_los_almacenes: bool
    almacen_asignado_id: uuid.UUID | None
    almacen_compras: str = "KEP"


def _entero(texto: str) -> int | None:
    """Un entero escrito como `10`, `10.0` o `1,000`; `None` si no lo es."""
    limpio = texto.replace(" ", "").replace(",", "")
    if not limpio:
        return None
    entero, _, decimales = limpio.partition(".")
    if decimales.strip("0") != "":
        return None
    if not (entero.isascii() and entero.lstrip("+-").isdigit()):
        return None
    return int(entero)


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

    # ------------------------------------------------------------------ preparación

    def analizar(self, datos: ImportacionIn, columnas: dict[str, int | None]) -> Resultado:
        filas = [self._leer(f, columnas) for f in datos.filas]
        resultado = Resultado(columnas=columnas, total=len(filas))

        categorias = self.repository.categorias()
        por_nombre = {clave(c.nombre): c for c in categorias if c.activo}
        por_id = {c.id: c for c in categorias}
        elegidas = self._categorias_elegidas(datos, por_id)
        almacenes = self.repository.almacenes()
        por_clave_almacen: dict[str, Almacen] = {}
        for a in almacenes:
            por_clave_almacen[clave(a.clave)] = a
        for a in almacenes:
            por_clave_almacen.setdefault(clave(a.nombre), a)
        defecto = self._almacen_por_defecto(datos, por_clave_almacen, almacenes)

        # Lo que la base ya sabe de los codigos y series de la tabla.
        codigos_tabla = {f["codigo"] for f in filas if f["codigo"]} | {
            f["codigo_pieza"] for f in filas if f["codigo_pieza"]
        }
        en_base = self.repository.codigos(codigos_tabla)
        articulos_base = self.repository.articulos(
            c.ref_id for c in en_base.values() if c.tipo == TipoCodigo.ARTICULO
        )
        series_base = self.repository.series_en_uso(
            articulos_base.keys(), {f["serie"] for f in filas if f["serie"]}
        )

        estado = _Estado(
            categorias=por_nombre,
            elegidas=elegidas,
            almacenes=por_clave_almacen,
            defecto=defecto,
            en_base=en_base,
            articulos_base=articulos_base,
            series_base=series_base,
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
            columnas.get("costo") is not None
            and columna_costo_con_datos
            and not self.ctx.puede_costos
        ):
            resultado.avisos.append(
                "Se ignoró la columna de costo: no tienes permiso para capturar costos."
            )
        resultado.buenas.sort(key=lambda b: b.fila)
        resultado.malas.sort(key=lambda m: m.fila)
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
    def _categorias_elegidas(datos: ImportacionIn, por_id: dict[uuid.UUID, Categoria]) -> _Elegidas:
        from app.core.excepciones import DatosInvalidos

        def categoria(categoria_id: uuid.UUID, campo: str) -> Categoria:
            elegida = por_id.get(categoria_id)
            if elegida is None or not elegida.activo:
                raise DatosInvalidos(
                    "La categoría elegida no existe o está inactiva.",
                    [{"campo": campo, "mensaje": "Elige una categoría activa."}],
                )
            return elegida

        defecto = (
            categoria(datos.categoria_por_defecto_id, "categoria_por_defecto_id")
            if datos.categoria_por_defecto_id
            else None
        )
        mapa = {
            clave(nombre): categoria(categoria_id, "mapa_categorias")
            for nombre, categoria_id in datos.mapa_categorias.items()
        }
        return _Elegidas(defecto=defecto, mapa=mapa)

    def _almacen_por_defecto(
        self,
        datos: ImportacionIn,
        por_clave: dict[str, Almacen],
        almacenes: list[Almacen],
    ) -> Almacen | None:
        if not self.ctx.puede_todos_los_almacenes:
            return next((a for a in almacenes if a.id == self.ctx.almacen_asignado_id), None)
        if datos.almacen_por_defecto and datos.almacen_por_defecto.strip():
            return por_clave.get(clave(datos.almacen_por_defecto))
        return por_clave.get(clave(self.ctx.almacen_compras))

    # --------------------------------------------------------------------- una fila

    def _revisar(self, numero: int, f: dict[str, str], res: Resultado, e: _Estado) -> None:
        motivos: list[Motivo] = []
        avisos: list[str] = []

        def malo(regla: str, campo: str | None, codigo: str, mensaje: str) -> None:
            motivos.append(Motivo(regla, campo, codigo, mensaje))

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
        control: str | None = None
        k = clave(codigo)

        # ---- el articulo
        if not codigo:
            malo("I-06", "codigo", "FALTA_CODIGO", "Falta el código del artículo.")
        elif len(codigo) <= LONGITUD["codigo"]:
            en_base = e.en_base.get(k)
            if en_base is not None and en_base.tipo != TipoCodigo.ARTICULO:
                que = _NOMBRES_CODIGO.get(en_base.tipo, "otra cosa")
                malo(
                    "RG-10",
                    "codigo",
                    "CODIGO_REPETIDO",
                    f"El código {codigo} ya identifica {que}. Un código identifica una sola cosa.",
                )
            elif en_base is not None:
                articulo = e.articulos_base.get(en_base.ref_id)
                if articulo is not None and not articulo.activo:
                    motivo = (
                        f" ({articulo.motivo_inactivacion})" if articulo.motivo_inactivacion else ""
                    )
                    malo(
                        "I-09",
                        "codigo",
                        "ARTICULO_INACTIVO",
                        f"{articulo.nombre} está inactivo{motivo}. No recibe entradas.",
                    )
                control = articulo.control if articulo else None
            elif k in e.piezas_tabla:
                malo(
                    "RG-10",
                    "codigo",
                    "CODIGO_REPETIDO",
                    f"El código {codigo} ya es el de una pieza en la fila {e.piezas_tabla[k]}. "
                    "Un código identifica una sola cosa.",
                )
            else:
                nuevo, categoria, control = self._articulo_nuevo(f, k, res, e, malo, numero)

        # ---- el almacen
        almacen = self._almacen(f["almacen"], e, malo)

        # ---- cantidad, pieza y serie
        cantidad = 0
        codigo_pieza: str | None = None
        serie: str | None = None
        if control == Control.CANTIDAD:
            cantidad = self._cantidad_por_cantidad(f["cantidad"], malo)
            if f["codigo_pieza"] or f["serie"]:
                avisos.append(
                    "Es un artículo por cantidad: se ignoran el código de pieza y la serie."
                )
            if almacen is not None and cantidad > 0:
                previa = e.cantidades_tabla.get((k, almacen.id))
                if previa is not None:
                    malo(
                        "RG-10",
                        "codigo",
                        "ARTICULO_REPETIDO",
                        f"El artículo {codigo} ya está en la fila {previa} para el mismo "
                        "almacén. Suma las cantidades en una sola fila.",
                    )
        elif control == Control.PIEZA:
            cantidad = 1
            codigo_pieza, serie = self._pieza(f, k, articulo, e, malo)
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
        if self.ctx.puede_costos and f["costo"]:
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

        if motivos:
            visibles = {c: v for c, v in f.items() if self.ctx.puede_costos or c != "costo"}
            res.malas.append(FilaMala(numero, visibles, motivos))
            return

        assert almacen is not None and control is not None
        if nuevo is not None:
            nuevo = res.nuevos.setdefault(k, nuevo)  # la primera fila buena lo define
            nuevo.filas += 1
            if nuevo.fila != numero and f["nombre"] and clave(f["nombre"]) != clave(nuevo.nombre):
                avisos.append(f"Se usa el nombre de la fila {nuevo.fila}: «{nuevo.nombre}».")
            if costo is not None and nuevo.costo is None:
                nuevo.costo = costo
        e.codigos_articulo_tabla.add(k)
        if control == Control.CANTIDAD:
            e.cantidades_tabla[(k, almacen.id)] = numero
        else:
            assert codigo_pieza is not None and serie is not None
            e.piezas_tabla[clave(codigo_pieza)] = numero
            e.series_tabla[(k, clave(serie))] = numero
        res.buenas.append(
            FilaBuena(
                fila=numero,
                codigo=articulo.codigo if articulo else codigo,
                nombre=articulo.nombre if articulo else (nuevo.nombre if nuevo else f["nombre"]),
                marca=articulo.marca if articulo else (nuevo.marca if nuevo else None),
                articulo=articulo,
                categoria=nuevo.categoria if nuevo else None,
                control=control,
                cantidad=cantidad,
                almacen=almacen,
                codigo_pieza=codigo_pieza,
                numero_serie=serie,
                costo=costo,
                avisos=avisos,
            )
        )

    # ----------------------------------------------------------------- piezas de la fila

    def _articulo_nuevo(self, f, k, res: Resultado, e: _Estado, malo, numero: int):
        """Resuelve un articulo que no existe: toma su categoria (CF-02) y su control. Si otra
        fila buena ya lo definio, se usa esa definicion."""
        previo = res.nuevos.get(k)
        if previo is not None:
            return previo, previo.categoria, previo.control
        nombre = f["nombre"]
        if not nombre:
            malo(
                "I-06", "nombre", "FALTA_NOMBRE", "Falta el nombre: el artículo no existe todavía."
            )
        categoria = self._categoria(f["categoria"], numero, res, e, malo)
        if not nombre or categoria is None:
            return None, None, None
        nuevo = ArticuloPorCrear(
            codigo=f["codigo"],
            nombre=nombre,
            marca=f["marca"] or None,
            categoria=categoria,
            control=categoria.control,
            costo=None,
            fila=numero,
            filas=0,
        )
        # Solo queda definido si la fila resulta buena: se registra al terminar la revision.
        return nuevo, categoria, categoria.control

    def _categoria(self, nombre: str, numero: int, res: Resultado, e: _Estado, malo):
        if nombre and clave(nombre) in e.categorias:
            return e.categorias[clave(nombre)]
        elegida = e.elegidas.mapa.get(clave(nombre)) if nombre else None
        elegida = elegida or e.elegidas.defecto
        if elegida is not None:
            return elegida
        etiqueta = nombre or "(sin categoría)"
        res.categorias_desconocidas.setdefault(clave(nombre), (etiqueta, []))[1].append(numero)
        mensaje = (
            f"La categoría «{nombre}» no existe. Elige una para estas filas."
            if nombre
            else "Falta la categoría del artículo nuevo. Elige una para estas filas."
        )
        malo("CF-02", "categoria", "CATEGORIA_DESCONOCIDA", mensaje)
        return None

    def _almacen(self, texto: str, e: _Estado, malo) -> Almacen | None:
        if texto:
            almacen = e.almacenes.get(clave(texto))
            if almacen is None:
                malo(
                    "I-01",
                    "almacen",
                    "ALMACEN_DESCONOCIDO",
                    f"El almacén «{texto}» no existe. Usa su clave o su nombre.",
                )
                return None
        else:
            almacen = e.defecto
            if almacen is None:
                malo("I-01", "almacen", "FALTA_ALMACEN", "Falta el almacén de la fila.")
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

    @staticmethod
    def _cantidad_por_cantidad(texto: str, malo) -> int:
        if not texto:
            malo("I-01", "cantidad", "FALTA_CANTIDAD", "Falta la cantidad.")
            return 0
        valor = _entero(texto)
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
        if valor > CANTIDAD_MAXIMA:
            malo(
                "I-01",
                "cantidad",
                "CANTIDAD_INVALIDA",
                f"La cantidad no puede pasar de {CANTIDAD_MAXIMA:,}.",
            )
            return 0
        return valor

    @staticmethod
    def _pieza(f, k, articulo: Articulo | None, e: _Estado, malo):
        """Codigo y serie de la pieza (I-02). Devuelve `(codigo_pieza, serie)` o `None` en lo que
        falla."""
        if f["cantidad"]:
            valor = _entero(f["cantidad"])
            if valor != 1:
                malo("RG-05", "cantidad", "CANTIDAD_INVALIDA", "Una pieza entra de una en una.")
        codigo_pieza: str | None = f["codigo_pieza"]
        if not codigo_pieza:
            malo("I-02", "codigo_pieza", "FALTA_CODIGO_PIEZA", "Falta el código de la pieza.")
            codigo_pieza = None
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
        serie: str | None = f["serie"]
        if not serie:
            malo("I-02", "serie", "FALTA_SERIE", "Falta el número de serie de la pieza.")
            serie = None
        elif len(serie) <= LONGITUD["serie"]:
            ks = clave(serie)
            if articulo is not None and (articulo.id, ks) in e.series_base:
                malo(
                    "I-02",
                    "serie",
                    "SERIE_REPETIDA",
                    f"Ya existe una pieza de este artículo con el número de serie {serie}.",
                )
            elif (k, ks) in e.series_tabla:
                malo(
                    "I-02",
                    "serie",
                    "SERIE_REPETIDA",
                    f"El número de serie {serie} ya está en la fila {e.series_tabla[(k, ks)]}.",
                )
        return codigo_pieza, serie


@dataclass
class _Elegidas:
    defecto: Categoria | None
    mapa: dict[str, Categoria]


@dataclass
class _Estado:
    """Lo que se sabe mientras se revisa la tabla, fila por fila."""

    categorias: dict[str, Categoria]
    elegidas: _Elegidas
    almacenes: dict[str, Almacen]
    defecto: Almacen | None
    en_base: dict
    articulos_base: dict
    series_base: set
    # Lo que ya aceptaron las filas buenas anteriores, con su numero de fila.
    piezas_tabla: dict[str, int] = field(default_factory=dict)
    series_tabla: dict[tuple[str, str], int] = field(default_factory=dict)
    cantidades_tabla: dict[tuple[str, uuid.UUID], int] = field(default_factory=dict)
    codigos_articulo_tabla: set[str] = field(default_factory=set)
