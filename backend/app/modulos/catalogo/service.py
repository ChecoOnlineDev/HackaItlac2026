"""Reglas de negocio del catálogo y control de la transacción.

Dueño de `categoria`, `articulo`, `pieza` y `codigo`. Los métodos públicos para otros módulos
(`obtener_articulo`, `registrar_pieza`, `actualizar_estado_pieza`, ...) solo hacen `flush`: el
commit es del módulo que los llama, para que todo quede en su misma transacción. Los métodos que
atienden endpoints (`crear_categoria`, `actualizar_articulo`, ...) hacen el commit aquí.
"""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from typing import Any

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.errores_bd import ERRNO_CHECK, ERRNO_LLAVE_FORANEA_PADRE, ERRNO_UNICO, violacion
from app.core.excepciones import AppError, DatosInvalidos, SinPermiso
from app.core.ids import nuevo_id
from app.core.paginacion import Pagina, Paginacion
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.acceso.service import AccesoService
from app.modulos.almacenes.service import AlmacenService
from app.modulos.auditoria.service import AuditoriaService
from app.modulos.catalogo.codigos import CodigoRepetido, CodigoService
from app.modulos.catalogo.exceptions import (
    ArticuloNoEncontrado,
    CategoriaNoEncontrada,
    ConMovimientos,
    EnDotacion,
    EstadoRepetido,
    NombreRepetido,
    PiezaNoEncontrada,
    SerieRepetida,
)
from app.modulos.catalogo.models import (
    Articulo,
    Categoria,
    Codigo,
    Control,
    EstadoPieza,
    Pieza,
    TipoCodigo,
)
from app.modulos.catalogo.repository import (
    ArticuloRepository,
    CategoriaRepository,
    EtiquetaRepository,
    FiltroArticulos,
    PiezaRepository,
)
from app.modulos.catalogo.schemas import (
    CAMPOS_REGLA,
    ArticuloCreate,
    ArticuloFichaOut,
    ArticuloFilters,
    ArticuloListItem,
    ArticuloOut,
    ArticuloUpdate,
    CategoriaCreate,
    CategoriaFilters,
    CategoriaOut,
    CategoriaUpdate,
    EtiquetaOut,
    EtiquetasOut,
    ExistenciaAlmacenOut,
    PiezaPoseidaOut,
    PoseedorOut,
    TipoEtiqueta,
)

# Vigencia de la inspección cuando se activa sin indicar los días (5.4 de las reglas; supuesto).
VIGENCIA_INSPECCION_DEFECTO_DIAS = 180


class _SinCambio:
    """Marca "no cambiar este campo", para distinguirlo de `None` (borrar la fecha)."""

    def __repr__(self) -> str:
        return "SIN_CAMBIO"


SIN_CAMBIO = _SinCambio()

CAMPOS_CATEGORIA = ("nombre", "tipo", "control", "retornable", *CAMPOS_REGLA)
# Lo único que un PATCH puede tocar de un artículo (el código y la inactivación tienen su ruta).
CAMPOS_EDITABLES_ARTICULO = (
    "nombre",
    "marca",
    "modelo",
    "categoria_id",
    "control",
    "retornable",
    "talla",
    "unidad",
    "costo_unitario",
    *CAMPOS_REGLA,
)
CAMPOS_AUDITADOS_ARTICULO = ("codigo", *CAMPOS_EDITABLES_ARTICULO, "activo", "motivo_inactivacion")


def _columnas(objeto: Any) -> dict[str, Any]:
    """Todas las columnas de un modelo como diccionario."""
    return {c.key: getattr(objeto, c.key) for c in sa_inspect(type(objeto)).mapper.column_attrs}


def _foto(objeto: Any, campos: tuple[str, ...]) -> dict[str, Any]:
    return {c: getattr(objeto, c) for c in campos}


def validar_reglas(control: str, reglas: dict[str, Any]) -> None:
    """Coherencia de una plantilla o de las reglas de un artículo (CF-06, L-05)."""
    errores: list[dict[str, str]] = []
    if reglas["requiere_inspeccion"] and control != Control.PIEZA:
        errores.append(
            {
                "campo": "requiere_inspeccion",
                "mensaje": "La inspección solo aplica a artículos por pieza.",
                "regla": "CF-06",
            }
        )
    if reglas["limite_periodo_dias"] is not None and reglas["limite_cantidad"] is None:
        errores.append(
            {
                "campo": "limite_cantidad",
                "mensaje": "Indica la cantidad del límite o quita el periodo.",
                "regla": "L-05",
            }
        )
    if errores:
        raise DatosInvalidos(errores[0]["mensaje"], errores)


def _vigencia_por_defecto(reglas: dict[str, Any]) -> None:
    """Una inspección activada sin días de vigencia usa el valor inicial de 5.4."""
    if reglas["requiere_inspeccion"] and reglas["vigencia_inspeccion_dias"] is None:
        reglas["vigencia_inspeccion_dias"] = VIGENCIA_INSPECCION_DEFECTO_DIAS


class CatalogoService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.categorias = CategoriaRepository(session)
        self.articulos = ArticuloRepository(session)
        self.piezas = PiezaRepository(session)
        self.etiquetas = EtiquetaRepository(session)
        self.codigos = CodigoService(session)
        self.auditoria = AuditoriaService(session)
        self.acceso = AccesoService(session)
        self.almacenes = AlmacenService(session)

    # ------------------------------------------------------------- transacción

    @contextmanager
    def _transaccion(self) -> Iterator[None]:
        """Una operación = una transacción: confirma al salir bien y revierte si algo falla."""
        try:
            yield
            self.session.commit()
        except DBAPIError as exc:
            self.session.rollback()
            traducido = self._traducir(exc)
            if traducido is None:
                raise
            raise traducido from exc
        except Exception:
            self.session.rollback()
            raise

    @staticmethod
    def _traducir(exc: DBAPIError) -> AppError | None:
        """Convierte un constraint violado en un error del dominio; `None` si no se reconoce."""
        v = violacion(exc)
        if v.errno == ERRNO_UNICO and v.restriccion == "uq_articulo_codigo":
            return CodigoRepetido("Ese código ya está en uso.", {"campo": "codigo"})
        if v.errno == ERRNO_UNICO and v.restriccion == "uq_categoria_nombre":
            return NombreRepetido(detalles={"campo": "nombre"})
        if v.errno == ERRNO_UNICO and v.restriccion == "uq_pieza_articulo_id_numero_serie":
            return SerieRepetida(detalles={"campo": "numero_serie"})
        if v.errno == ERRNO_LLAVE_FORANEA_PADRE:
            return ConMovimientos(
                "El artículo ya tiene historial: solo se puede inactivar.",
                {"regla": "CF-12"},
            )
        if v.errno == ERRNO_CHECK:
            return DatosInvalidos(
                "Revisa los datos capturados.",
                [{"campo": v.restriccion, "mensaje": "Valor no válido."}],
            )
        return None

    def _ver_costos(self, usuario: Usuario) -> bool:
        """RG-12: el costo solo lo ve y lo captura quien tiene `catalogo.costos`."""
        return self.acceso.tiene_permiso(usuario, P.CATALOGO_COSTOS)

    def _exigir_limites(self, usuario: Usuario, cambios: dict[str, Any]) -> None:
        """AC-30: cambiar el límite de entrega pide `catalogo.limites`, aparte de administrar."""
        if {"limite_cantidad", "limite_periodo_dias"} & cambios.keys() and (
            not self.acceso.tiene_permiso(usuario, P.CATALOGO_LIMITES)
        ):
            raise SinPermiso("No tienes permiso para cambiar los límites de entrega.")

    # ----------------------------------------------------------------- categorías

    def obtener_categoria(self, categoria_id: uuid.UUID) -> Categoria:
        categoria = self.categorias.get(categoria_id)
        if categoria is None:
            raise CategoriaNoEncontrada()
        return categoria

    def listar_categorias(
        self, filtros: CategoriaFilters, pagina: Paginacion
    ) -> Pagina[CategoriaOut]:
        filas, total = self.categorias.listar(
            activo=filtros.activo, offset=pagina.offset, limit=pagina.limit
        )
        return Pagina[CategoriaOut](
            elementos=[CategoriaOut.model_validate(c) for c in filas], total=total
        )

    def crear_categoria(self, datos: CategoriaCreate, usuario: Usuario) -> CategoriaOut:
        """CF-01: nombre único, tipo y plantilla. CF-15: queda en el registro de cambios."""
        valores = datos.model_dump()
        self._exigir_limites(
            usuario, {k: v for k, v in valores.items() if k.startswith("limite_") and v is not None}
        )
        _vigencia_por_defecto(valores)
        validar_reglas(valores["control"], valores)
        with self._transaccion():
            if self.categorias.get_by_nombre(valores["nombre"]) is not None:
                raise NombreRepetido(detalles={"campo": "nombre", "regla": "CF-01"})
            categoria = self.categorias.add(Categoria(**valores))
            self.auditoria.registrar(
                usuario_id=usuario.id,
                accion="categoria.crear",
                entidad="categoria",
                entidad_id=categoria.id,
                despues=_foto(categoria, CAMPOS_CATEGORIA),
            )
        return CategoriaOut.model_validate(categoria)

    def actualizar_categoria(
        self, categoria_id: uuid.UUID, datos: CategoriaUpdate, usuario: Usuario
    ) -> CategoriaOut:
        """CF-02: editar la plantilla no cambia los artículos que ya existen."""
        categoria = self.obtener_categoria(categoria_id)
        cambios = datos.model_dump(exclude_unset=True)
        nuevos = {**_foto(categoria, CAMPOS_CATEGORIA), **cambios}
        if cambios.get("requiere_inspeccion") and "vigencia_inspeccion_dias" not in cambios:
            _vigencia_por_defecto(nuevos)
        validar_reglas(nuevos["control"], nuevos)
        diferencias = {k: v for k, v in nuevos.items() if getattr(categoria, k) != v}
        self._exigir_limites(usuario, diferencias)
        if not diferencias:
            return CategoriaOut.model_validate(categoria)

        with self._transaccion():
            if "nombre" in diferencias:
                otra = self.categorias.get_by_nombre(diferencias["nombre"])
                if otra is not None and otra.id != categoria.id:
                    raise NombreRepetido(detalles={"campo": "nombre", "regla": "CF-01"})
            antes = {k: getattr(categoria, k) for k in diferencias}
            for campo, valor in diferencias.items():
                setattr(categoria, campo, valor)
            self.session.flush()
            self.auditoria.registrar(
                usuario_id=usuario.id,
                accion="categoria.editar",
                entidad="categoria",
                entidad_id=categoria.id,
                antes=antes,
                despues=diferencias,
            )
        return CategoriaOut.model_validate(categoria)

    # ------------------------------------------------------------------ artículos

    def obtener_articulo(self, articulo_id: uuid.UUID) -> Articulo:
        """El artículo, o `ArticuloNoEncontrado` (404). Para otros módulos."""
        articulo = self.articulos.get(articulo_id)
        if articulo is None:
            raise ArticuloNoEncontrado()
        return articulo

    def obtener_articulo_por_codigo(self, codigo: str) -> Articulo:
        """El artículo cuyo código (QR de producto o de estante) es `codigo`; 404 si no hay.

        Solo busca códigos de artículo: el de una pieza se resuelve con `identificar_codigo`.
        """
        articulo = self.articulos.get_by_codigo(codigo.strip())
        if articulo is None:
            raise ArticuloNoEncontrado()
        return articulo

    def articulo_tiene_movimientos(self, articulo_id: uuid.UUID) -> bool:
        """Verdadero si hay algún movimiento del artículo (CF-05, CF-12). Solo lectura."""
        return self.articulos.tiene_movimientos(articulo_id)

    def _salida_articulo(
        self, articulo: Articulo, categoria_nombre: str, ver_costos: bool
    ) -> dict[str, Any]:
        datos = _columnas(articulo)
        if not ver_costos:
            datos.pop("costo_unitario")  # sin el campo, la respuesta no lo trae (RG-12)
        datos["categoria_nombre"] = categoria_nombre
        return datos

    def _articulo_out(self, articulo: Articulo, usuario: Usuario) -> ArticuloOut:
        categoria = self.obtener_categoria(articulo.categoria_id)
        return ArticuloOut(
            **self._salida_articulo(articulo, categoria.nombre, self._ver_costos(usuario))
        )

    def listar_articulos(
        self, filtros: ArticuloFilters, pagina: Paginacion, usuario: Usuario
    ) -> Pagina[ArticuloListItem]:
        filas, total = self.articulos.listar(
            FiltroArticulos(
                q=filtros.q,
                categoria_id=filtros.categoria_id,
                activo=filtros.activo,
                offset=pagina.offset,
                limit=pagina.limit,
            )
        )
        ver_costos = self._ver_costos(usuario)
        return Pagina[ArticuloListItem](
            elementos=[
                ArticuloListItem(**self._salida_articulo(a, nombre, ver_costos))
                for a, nombre in filas
            ],
            total=total,
        )

    def ficha_articulo(self, articulo_id: uuid.UUID, usuario: Usuario) -> ArticuloFichaOut:
        """C-03: reglas, existencias por almacén y quién lo tiene. AC-06: sin `almacenes.todos`,
        las existencias son solo las del almacén del usuario; `en_posesion` es el resguardo de los
        trabajadores y se ve completo (el trabajador es una ubicación, no un almacén)."""
        articulo = self.obtener_articulo(articulo_id)
        categoria = self.obtener_categoria(articulo.categoria_id)
        datos = self._salida_articulo(articulo, categoria.nombre, self._ver_costos(usuario))
        ve_todos = self.acceso.puede_operar_todos_los_almacenes(usuario)
        return ArticuloFichaOut(
            **datos,
            tiene_movimientos=self.articulos.tiene_movimientos(articulo.id),
            existencias=[
                ExistenciaAlmacenOut(
                    almacen_id=a.id,
                    clave=a.clave,
                    nombre=a.nombre,
                    cantidad=cantidad,
                    disponible=disponible,
                )
                for a, cantidad, disponible in self.almacenes.existencias_de_articulo(articulo.id)
                if ve_todos or a.id == usuario.almacen_id
            ],
            en_posesion=self._poseedores(articulo, usuario, ve_todos),
        )

    def _poseedores(
        self, articulo: Articulo, usuario: Usuario, ve_todos: bool
    ) -> list[PoseedorOut]:
        """SG-02: quién lo tiene, con cantidad, fecha y folio de la entrega y, por pieza, el
        código y la serie de cada una. AC-06: el vale de otro almacén no se nombra."""
        poseedores = []
        # La consulta vive en el repositorio de `almacenes`; no hay un método de servicio para ella
        for p in self.almacenes.posesion_de_articulo(articulo.id, articulo.control):
            propio = ve_todos or (
                usuario.almacen_id is not None and p.vale_almacen_id == usuario.almacen_id
            )
            poseedores.append(
                PoseedorOut(
                    trabajador_id=p.trabajador.id,
                    numero_empleado=p.trabajador.numero_empleado,
                    nombre=p.trabajador.nombre,
                    cantidad=p.cantidad,
                    desde=p.desde,
                    vale_id=p.vale_id if propio else None,
                    folio=p.folio if propio else None,
                    piezas=[
                        PiezaPoseidaOut(id=z.id, codigo=z.codigo, numero_serie=z.numero_serie)
                        for z in p.piezas
                    ],
                )
            )
        return poseedores

    def crear_articulo(
        self, datos: ArticuloCreate, actor_id: uuid.UUID, *, puede_costos: bool = False
    ) -> Articulo:
        """Crea un artículo copiando la plantilla de su categoría (CF-02). Sin commit.

        Lo reutiliza la importación de inventario: el llamador hace el commit. Un código ya usado
        por un artículo, pieza o credencial lanza `CodigoRepetido` (RG-10); un costo sin
        `puede_costos` lanza `SinPermiso` (RG-12). El código del artículo también queda
        registrado como su QR de producto o de estante (I-07).
        """
        categoria = self.obtener_categoria(datos.categoria_id)
        puestos = datos.model_fields_set

        control = datos.control or categoria.control
        retornable = categoria.retornable if datos.retornable is None else datos.retornable
        reglas: dict[str, Any] = {}
        for campo in CAMPOS_REGLA:
            valor = getattr(datos, campo)
            if campo in ("requiere_inspeccion", "requiere_autorizacion"):
                reglas[campo] = getattr(categoria, campo) if valor is None else valor
            elif campo in puestos:
                reglas[campo] = valor  # `null` explícito: sin esa regla
            else:
                reglas[campo] = getattr(categoria, campo)
        if datos.requiere_inspeccion is None and control != Control.PIEZA:
            reglas["requiere_inspeccion"] = False  # la inspección solo aplica a piezas (CF-06)
        _vigencia_por_defecto(reglas)
        validar_reglas(control, reglas)

        if datos.costo_unitario is not None and not puede_costos:
            raise SinPermiso("No tienes permiso para capturar costos.")

        articulo = Articulo(
            id=nuevo_id(),
            codigo=datos.codigo,
            nombre=datos.nombre,
            marca=datos.marca,
            modelo=datos.modelo,
            categoria_id=categoria.id,
            control=control,
            retornable=retornable,
            talla=datos.talla,
            unidad=datos.unidad,
            costo_unitario=datos.costo_unitario,
            **reglas,
        )
        self.codigos.registrar(datos.codigo, TipoCodigo.ARTICULO, articulo.id)
        self.articulos.add(articulo)
        self.auditoria.registrar(
            usuario_id=actor_id,
            accion="articulo.crear",
            entidad="articulo",
            entidad_id=articulo.id,
            despues=_foto(articulo, CAMPOS_AUDITADOS_ARTICULO),
        )
        return articulo

    def crear(self, datos: ArticuloCreate, usuario: Usuario) -> ArticuloOut:
        """Endpoint `POST /articulos`: crea y confirma."""
        self._exigir_limites(
            usuario,
            {
                k: v
                for k, v in datos.model_dump(exclude_unset=True).items()
                if k.startswith("limite_") and v is not None
            },
        )
        with self._transaccion():
            articulo = self.crear_articulo(
                datos, usuario.id, puede_costos=self._ver_costos(usuario)
            )
        return self._articulo_out(articulo, usuario)

    def actualizar_articulo(
        self, articulo_id: uuid.UUID, datos: ArticuloUpdate, usuario: Usuario
    ) -> ArticuloOut:
        """Edita datos, límite, aviso y requisitos. Con movimientos no cambia control ni retorno."""
        articulo = self.obtener_articulo(articulo_id)
        puede_costos = self._ver_costos(usuario)
        pedidos = {
            k: v
            for k, v in datos.model_dump(exclude_unset=True).items()
            if k in CAMPOS_EDITABLES_ARTICULO
        }
        diferencias = {k: v for k, v in pedidos.items() if getattr(articulo, k) != v}

        if "costo_unitario" in diferencias and not puede_costos:
            raise SinPermiso("No tienes permiso para capturar costos.")
        self._exigir_limites(usuario, diferencias)

        cambia_control = {"control", "retornable"} & diferencias.keys()
        if cambia_control:
            self._exigir_sin_movimientos(articulo, "control" in diferencias)
        if "categoria_id" in diferencias:
            self.obtener_categoria(diferencias["categoria_id"])

        nuevos = {**_foto(articulo, CAMPOS_EDITABLES_ARTICULO), **diferencias}
        activa_inspeccion = diferencias.get("requiere_inspeccion") is True
        if activa_inspeccion:
            _vigencia_por_defecto(nuevos)
            if nuevos["vigencia_inspeccion_dias"] != articulo.vigencia_inspeccion_dias:
                diferencias["vigencia_inspeccion_dias"] = nuevos["vigencia_inspeccion_dias"]
        validar_reglas(nuevos["control"], nuevos)
        self._exigir_limite_sobre_dotacion(articulo, nuevos["limite_cantidad"])

        if not diferencias:
            return self._articulo_out(articulo, usuario)

        with self._transaccion():
            antes = {k: getattr(articulo, k) for k in diferencias}
            for campo, valor in diferencias.items():
                setattr(articulo, campo, valor)
            despues = dict(diferencias)
            if activa_inspeccion:
                # CF-09: sus piezas quedan sin inspección vigente hasta inspeccionarse.
                despues["piezas_sin_inspeccion_vigente"] = self.piezas.quitar_inspeccion_vigente(
                    articulo.id
                )
            self.session.flush()
            self.auditoria.registrar(
                usuario_id=usuario.id,
                accion="articulo.editar",
                entidad="articulo",
                entidad_id=articulo.id,
                antes=antes,
                despues=despues,
            )
        return self._articulo_out(articulo, usuario)

    def _exigir_limite_sobre_dotacion(self, articulo: Articulo, limite: int | None) -> None:
        """D-04: el límite no puede quedar por debajo de lo recomendado en algún puesto."""
        if limite is None:
            return
        maxima = self.articulos.dotacion_maxima(articulo.id)
        if maxima is not None and maxima > limite:
            mensaje = (
                f"El límite no puede ser menor que la cantidad recomendada en una dotación "
                f"({maxima}). Ajusta primero la dotación del puesto."
            )
            raise DatosInvalidos(
                mensaje, [{"campo": "limite_cantidad", "mensaje": mensaje, "regla": "D-04"}]
            )

    def _exigir_sin_movimientos(self, articulo: Articulo, cambia_control: bool) -> None:
        """CF-05: control y retorno no cambian si el artículo ya tiene movimientos."""
        if self.articulos.tiene_movimientos(articulo.id):
            raise ConMovimientos(
                "El artículo ya tiene movimientos: su control y su retorno no se pueden cambiar. "
                "Crea un artículo nuevo e inactiva este.",
                {"regla": "CF-05"},
            )
        if cambia_control and self.articulos.tiene_piezas(articulo.id):
            raise ConMovimientos(
                "El artículo ya tiene piezas registradas: su control no se puede cambiar.",
                {"regla": "CF-05"},
            )

    def inactivar_articulo(
        self, articulo_id: uuid.UUID, motivo: str, usuario: Usuario
    ) -> ArticuloOut:
        """CF-10: inactivar exige un motivo. El historial y las existencias se conservan."""
        articulo = self.obtener_articulo(articulo_id)
        motivo = (motivo or "").strip()
        if not motivo:
            raise DatosInvalidos(
                "Escribe el motivo para inactivar.",
                [{"campo": "motivo", "mensaje": "Escribe el motivo.", "regla": "CF-10"}],
            )
        if not articulo.activo:
            raise EstadoRepetido("El artículo ya está inactivo.")
        with self._transaccion():
            articulo.activo = False
            articulo.motivo_inactivacion = motivo
            self.session.flush()
            self.auditoria.registrar(
                usuario_id=usuario.id,
                accion="articulo.inactivar",
                entidad="articulo",
                entidad_id=articulo.id,
                antes={"activo": True, "motivo_inactivacion": None},
                despues={"activo": False, "motivo_inactivacion": motivo},
            )
        return self._articulo_out(articulo, usuario)

    def reactivar_articulo(self, articulo_id: uuid.UUID, usuario: Usuario) -> ArticuloOut:
        """CF-13: vuelve a operar con las reglas que tenía."""
        articulo = self.obtener_articulo(articulo_id)
        if articulo.activo:
            raise EstadoRepetido("El artículo ya está activo.")
        with self._transaccion():
            motivo = articulo.motivo_inactivacion
            articulo.activo = True
            articulo.motivo_inactivacion = None
            self.session.flush()
            self.auditoria.registrar(
                usuario_id=usuario.id,
                accion="articulo.reactivar",
                entidad="articulo",
                entidad_id=articulo.id,
                antes={"activo": False, "motivo_inactivacion": motivo},
                despues={"activo": True, "motivo_inactivacion": None},
            )
        return self._articulo_out(articulo, usuario)

    def eliminar_articulo(self, articulo_id: uuid.UUID, usuario: Usuario) -> None:
        """CF-12: solo se elimina un artículo sin movimientos; con ellos, solo se inactiva."""
        articulo = self.obtener_articulo(articulo_id)
        if self.articulos.en_dotacion(articulo.id):
            raise EnDotacion(
                "El artículo está en la dotación de un puesto: quítalo de ahí o inactívalo.",
                {"regla": "D-01"},
            )
        if self.articulos.tiene_movimientos(articulo.id) or self.articulos.tiene_piezas(
            articulo.id
        ):
            raise ConMovimientos(
                "El artículo ya tiene movimientos: no se puede eliminar, solo inactivar.",
                {"regla": "CF-12"},
            )
        with self._transaccion():
            antes = _foto(articulo, CAMPOS_AUDITADOS_ARTICULO)
            self.articulos.eliminar(articulo)
            self.auditoria.registrar(
                usuario_id=usuario.id,
                accion="articulo.eliminar",
                entidad="articulo",
                entidad_id=articulo_id,
                antes=antes,
            )

    # --------------------------------------------------------------------- piezas

    def obtener_pieza(self, pieza_id: uuid.UUID) -> Pieza:
        """La pieza, o `PiezaNoEncontrada` (404). Para otros módulos."""
        pieza = self.piezas.get(pieza_id)
        if pieza is None:
            raise PiezaNoEncontrada()
        return pieza

    def identificar_codigo(self, codigo: str) -> Codigo | None:
        """Qué cosa identifica un código (trabajador, artículo, pieza o vale), o `None`."""
        return self.codigos.identificar(codigo)

    def registrar_pieza(
        self,
        articulo_id: uuid.UUID,
        codigo: str,
        numero_serie: str | None = None,
        *,
        estado: EstadoPieza = EstadoPieza.APTO,
        inspeccion_vigente_hasta: date | None = None,
    ) -> Pieza:
        """Crea una pieza de un artículo por pieza y registra su código (I-02). Sin commit.

        Nace sin ubicación: la primera la fija `movimientos` con la entrada. Un código ya usado
        lanza `CodigoRepetido`; una serie repetida del mismo artículo, `SerieRepetida`. No revisa
        si el artículo está inactivo (I-09): eso lo decide la entrada.
        """
        articulo = self.obtener_articulo(articulo_id)
        if articulo.control != Control.PIEZA:
            raise DatosInvalidos(
                "Solo los artículos por pieza tienen piezas.",
                [{"campo": "articulo_id", "mensaje": "El artículo es por cantidad."}],
            )
        numero_serie = (numero_serie or "").strip() or None
        if numero_serie and self.piezas.get_by_serie(articulo.id, numero_serie) is not None:
            raise SerieRepetida(detalles={"campo": "numero_serie"})
        pieza = Pieza(
            id=nuevo_id(),
            articulo_id=articulo.id,
            codigo=codigo.strip(),
            numero_serie=numero_serie,
            estado=estado,
            inspeccion_vigente_hasta=inspeccion_vigente_hasta,
        )
        self.codigos.registrar(codigo, TipoCodigo.PIEZA, pieza.id)
        return self.piezas.add(pieza)

    def actualizar_estado_pieza(
        self,
        pieza_id: uuid.UUID,
        *,
        estado: EstadoPieza | str | None = None,
        inspeccion_vigente_hasta: date | None | _SinCambio = SIN_CAMBIO,
        actor_id: uuid.UUID | None = None,
    ) -> Pieza:
        """Único camino para cambiar `pieza.estado` e `inspeccion_vigente_hasta`. Sin commit.

        `estado=None` lo deja igual; `inspeccion_vigente_hasta=SIN_CAMBIO` (por defecto) lo deja
        igual y `None` borra la fecha. La `ubicacion_id` NO se toca aquí: solo `movimientos`.
        Registra el cambio en la auditoría con `actor_id`.
        """
        pieza = self.obtener_pieza(pieza_id)
        antes: dict[str, Any] = {}
        despues: dict[str, Any] = {}
        if estado is not None:
            nuevo = EstadoPieza(estado)
            if pieza.estado != nuevo:
                antes["estado"], despues["estado"] = pieza.estado, nuevo.value
                pieza.estado = nuevo
        if not isinstance(inspeccion_vigente_hasta, _SinCambio):
            if pieza.inspeccion_vigente_hasta != inspeccion_vigente_hasta:
                antes["inspeccion_vigente_hasta"] = pieza.inspeccion_vigente_hasta
                despues["inspeccion_vigente_hasta"] = inspeccion_vigente_hasta
                pieza.inspeccion_vigente_hasta = inspeccion_vigente_hasta
        if despues:
            self.session.flush()
            self.auditoria.registrar(
                usuario_id=actor_id,
                accion="pieza.actualizar",
                entidad="pieza",
                entidad_id=pieza.id,
                antes=antes,
                despues=despues,
            )
        return pieza

    # ------------------------------------------------------------------ etiquetas

    def listar_etiquetas(self, tipo: TipoEtiqueta, usuario: Usuario) -> EtiquetasOut:
        """US-ETQ-001. El permiso `etiquetas.imprimir` (ya exigido por el router) basta.

        El QR contiene exactamente `codigo` (RG-10); `texto` es lo legible junto a él. Una
        credencial solo lleva nombre, número de empleado y puesto, nunca CURP ni NSS
        (RG-13).
        """
        elementos: list[EtiquetaOut]
        if tipo == TipoEtiqueta.CREDENCIALES:
            elementos = [
                EtiquetaOut(
                    codigo=c, texto=f"{n} · {e}", nombre=n, numero_empleado=e, puesto=p or None
                )
                for c, n, e, p in self.etiquetas.credenciales()
            ]
        else:
            filas = (
                self.etiquetas.piezas()
                if tipo == TipoEtiqueta.PIEZAS
                else self.etiquetas.estantes()
            )
            elementos = [EtiquetaOut(codigo=c, texto=t) for c, t in filas]
        return EtiquetasOut(elementos=elementos, total=len(elementos))
