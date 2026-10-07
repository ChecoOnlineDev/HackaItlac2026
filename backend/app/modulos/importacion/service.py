"""Reglas de negocio y control de la transaccion de la importacion (US-IMP-001, US-IMP-002).

La vista previa lee y no escribe. La confirmacion hace, en UNA sola transaccion:

0. en `ALTA`, bloquea las categorias (dos lotes que crean articulos se turnan: el segundo ve lo que
   creo el primero, y el consecutivo de codigos generados no se repite);
1. crea con `CatalogoService.crear_articulo` los articulos que faltan (con la plantilla de su
   categoria, CF-02); en `REPOSICION` nunca crea;
2. confirma con `MovimientoService.confirmar` un vale de ENTRADA por almacen (un vale por cada
   500 renglones si un almacen trae mas), con `id_cliente` determinista por (lote, almacen);
3. hace commit, o rollback de todo: si falla una entrada no queda ni un articulo ni un vale
   (RG-09, todo o nada de la importacion completa).

Repetir la confirmacion con el mismo `id_lote` devuelve lo ya guardado (200, `repetida`) sin
crear nada. Un archivo con la misma huella que una importacion anterior (I-12) pide
`confirmar_repetido`. Quien importa necesita `inventario.entradas`; dar de alta articulos pide
ademas `catalogo.administrar` (I-10) y el costo solo se acepta con `catalogo.costos` (RG-12); nunca
aparece en el vale.
"""

import hashlib
import json
import uuid
from collections import defaultdict
from datetime import datetime

from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError, InvalidRequestError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core import errores_bd
from app.core.excepciones import AppError, DatosInvalidos
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.acceso.service import AccesoService
from app.modulos.almacenes.models import Almacen
from app.modulos.almacenes.service import AlmacenService
from app.modulos.auditoria.service import AuditoriaService
from app.modulos.catalogo.models import Categoria
from app.modulos.catalogo.schemas import ArticuloCreate
from app.modulos.catalogo.service import CatalogoService
from app.modulos.importacion.analisis import (
    Analizador,
    Contexto,
    FilaBuena,
    FilaMala,
    Resultado,
)
from app.modulos.importacion.exceptions import (
    ArchivoInvalido,
    ArchivoRepetido,
    ImportacionCambio,
    LoteEnUso,
    SinFilasValidas,
)
from app.modulos.importacion.lectura import clave, leer_xlsx, proponer_columnas, texto_de_celda
from app.modulos.importacion.plantilla import generar_plantilla
from app.modulos.importacion.repository import ImportacionRepository
from app.modulos.importacion.schemas import (
    CAMPOS,
    AlmacenRefOut,
    ArchivoOut,
    ArchivoRepetidoOut,
    ArticuloCreadoOut,
    ArticuloNuevoOut,
    ArticuloRefOut,
    CategoriaDesconocidaOut,
    CategoriaRefOut,
    ColumnasIn,
    FilaErrorOut,
    FilaExcluidaOut,
    FilaValidaOut,
    ImportacionIn,
    ImportacionOut,
    MotivoOut,
    PiezaCreadaOut,
    ResumenImportacionOut,
    ResumenVistaPreviaOut,
    ValeImportadoOut,
    VistaPreviaOut,
)
from app.modulos.movimientos.models import TipoVale
from app.modulos.movimientos.schemas import ConfirmarIn, PiezaEntradaIn, RenglonIn
from app.modulos.movimientos.service import MovimientoService

# `ValeIn.renglones` admite hasta 500: un almacen con mas se parte en varios vales.
RENGLONES_POR_VALE = 500
INTENTOS = 3
ERRNO_INTERBLOQUEO = 1213


def _id_cliente(id_lote: uuid.UUID, almacen_id: uuid.UUID, parte: int) -> uuid.UUID:
    """El `id_cliente` del vale: el mismo (lote, almacen, parte) da siempre el mismo."""
    return uuid.uuid5(id_lote, f"importacion:{almacen_id}:{parte}")


def _ref(categoria: Categoria | None) -> CategoriaRefOut | None:
    return None if categoria is None else CategoriaRefOut(id=categoria.id, nombre=categoria.nombre)


class ImportacionService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ImportacionRepository(session)
        self.acceso = AccesoService(session)
        self.catalogo = CatalogoService(session)
        self.movimientos = MovimientoService(session)
        self.almacenes = AlmacenService(session)
        self.auditoria = AuditoriaService(session)

    # ----------------------------------------------------------------------- revisión

    @staticmethod
    def _faltan_columnas(modo: str, columnas: dict[str, int | None]) -> str | None:
        """Lo que falta para poder leer la tabla en ese modo (I-10), o `None`."""
        if modo == "REPOSICION":
            if columnas.get("codigo") is None:
                return "Falta la columna del código: la reposición solo suma a lo que ya existe."
        elif columnas.get("codigo") is None and columnas.get("nombre") is None:
            return "Falta la columna del código o la del nombre."
        return None

    def _columnas(self, datos: ImportacionIn) -> dict[str, int | None]:
        if datos.columnas is not None:
            columnas = datos.columnas.model_dump()
        else:
            columnas = proponer_columnas(datos.encabezados or [])
        falta = self._faltan_columnas(datos.modo, columnas)
        if falta:
            raise DatosInvalidos(
                f"{falta} Indica qué columna es cada dato.",
                [{"campo": "columnas", "mensaje": falta}],
            )
        return columnas

    def _analizar(
        self, usuario: Usuario, datos: ImportacionIn, *, confirmando: bool = False
    ) -> Resultado:
        contexto = Contexto(
            puede_costos=self.acceso.tiene_permiso(usuario, P.CATALOGO_COSTOS),
            puede_todos_los_almacenes=self.acceso.puede_operar_todos_los_almacenes(usuario),
            almacen_asignado_id=usuario.almacen_id,
            puede_crear_articulos=self.acceso.tiene_permiso(usuario, P.CATALOGO_ADMINISTRAR),
            cantidad_maxima=get_settings().importacion_cantidad_maxima,
            confirmando=confirmando,
        )
        analizador = Analizador(self.repository, contexto)
        return analizador.analizar(datos, self._columnas(datos))

    # ------------------------------------------------------------------------ huella

    @staticmethod
    def _huella(datos: ImportacionIn) -> str:
        """La huella del archivo (I-12): `sha256` del modo, las filas normalizadas (sin vacias,
        sin espacios de mas y en un orden fijo) y el almacen por defecto."""
        filas = []
        for fila in datos.filas:
            celdas = [texto_de_celda(c) for c in fila]
            while celdas and not celdas[-1]:
                celdas.pop()
            if celdas:
                filas.append(celdas)
        filas.sort()
        cuerpo = json.dumps(
            {
                "modo": datos.modo,
                "filas": filas,
                "almacen_por_defecto": clave(datos.almacen_por_defecto or ""),
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return hashlib.sha256(cuerpo.encode("utf-8")).hexdigest()

    def plantilla(self, usuario: Usuario, modo: str) -> bytes:
        """El `.xlsx` de ejemplo de ese modo. La columna de costo solo con `catalogo.costos`."""
        con_costo = self.acceso.tiene_permiso(usuario, P.CATALOGO_COSTOS)
        return generar_plantilla(modo, con_costo=con_costo)

    def vista_previa(self, usuario: Usuario, datos: ImportacionIn) -> VistaPreviaOut:
        """Revisa la tabla sin guardar nada (US-IMP-001, US-IMP-002)."""
        resultado = self._analizar(usuario, datos)
        fecha = self.repository.fecha_de_importacion(self._huella(datos))
        return self._vista_previa_out(usuario, resultado, fecha)

    def vista_previa_de_archivo(
        self, usuario: Usuario, nombre: str | None, contenido: bytes, modo: str = "ALTA"
    ) -> ArchivoOut:
        """Convierte un `.xlsx` en filas, propone las columnas y hace la vista previa."""
        hoja, filas = leer_xlsx(nombre, contenido)
        inicio = next((i for i, f in enumerate(filas) if any(f)), None)
        if inicio is None:
            raise ArchivoInvalido("El archivo no trae datos.", {"campo": "archivo"})
        encabezados = filas[inicio]
        datos = filas[inicio + 1 :]
        if not datos:
            raise ArchivoInvalido(
                "La hoja solo trae los encabezados: no hay filas que importar.",
                {"campo": "archivo"},
            )
        ancho = max(len(encabezados), *(len(f) for f in datos))
        encabezados = encabezados + [""] * (ancho - len(encabezados))
        datos = [f + [""] * (ancho - len(f)) for f in datos]
        columnas = proponer_columnas(encabezados)
        primera_fila = inicio + 2
        vista = None
        if self._faltan_columnas(modo, columnas) is None:
            cuerpo = ImportacionIn(
                modo=modo,
                filas=datos,
                columnas=ColumnasIn(**{c: i for c, i in columnas.items() if i is not None}),
                primera_fila=primera_fila,
            )
            vista = self.vista_previa(usuario, cuerpo)
        return ArchivoOut(
            hoja=hoja,
            encabezados=encabezados,
            columnas=columnas,
            primera_fila=primera_fila,
            filas=datos,
            vista_previa=vista,
        )

    # ----------------------------------------------------------------------- confirmar

    def confirmar(self, usuario: Usuario, datos: ImportacionIn) -> tuple[ImportacionOut, bool]:
        """Devuelve `(resumen, creada)`; `creada` es falso si el lote ya estaba confirmado."""
        self.acceso.exigir_permiso(usuario, P.INVENTARIO_ENTRADAS)
        if datos.id_lote is None:
            raise DatosInvalidos(
                "Falta el identificador del lote.",
                [{"campo": "id_lote", "mensaje": "Es obligatorio al confirmar."}],
            )
        for intento in range(1, INTENTOS + 1):
            try:
                self._aislar_transaccion()
                previa = self._lote_confirmado(usuario, datos)
                if previa is not None:
                    return previa, False
                huella = self._huella(datos)
                if not datos.confirmar_repetido:
                    fecha = self.repository.fecha_de_importacion(huella)
                    if fecha is not None:
                        raise ArchivoRepetido(fecha)
                salida = self._importar(usuario, datos, huella)
                self.session.commit()
                return salida, True
            except AppError:
                self.session.rollback()
                raise
            except DBAPIError as exc:
                self.session.rollback()
                violacion = errores_bd.violacion(exc)
                reintentable = violacion.errno in (
                    errores_bd.ERRNO_UNICO,
                    ERRNO_INTERBLOQUEO,
                )
                if reintentable and intento < INTENTOS:
                    continue  # otra confirmacion ganó: se vuelve a revisar con lo nuevo
                if violacion.errno == errores_bd.ERRNO_UNICO:
                    raise ImportacionCambio() from exc
                raise
            except Exception:
                self.session.rollback()
                raise
        raise AssertionError("inalcanzable")  # pragma: no cover

    def _aislar_transaccion(self) -> None:
        """Transaccion limpia en READ COMMITTED (igual que la confirmacion de un vale): en
        REPEATABLE READ la lectura de la sesion fijaria una foto y no se veria lo que otra
        confirmacion guardo. En las pruebas la sesion va dentro de una transaccion externa."""
        self.session.commit()
        if isinstance(self.session.get_bind(), Connection):
            return
        try:
            self.session.connection(execution_options={"isolation_level": "READ COMMITTED"})
        except InvalidRequestError:  # pragma: no cover - ya habia una transaccion abierta
            pass

    def _importar(self, usuario: Usuario, datos: ImportacionIn, huella: str) -> ImportacionOut:
        assert datos.id_lote is not None
        # Antes de revisar: dos lotes que crean articulos o codigos de pieza se turnan, y el segundo
        # ve lo que el primero creo (articulos, piezas y consecutivos de codigos generados).
        self.repository.bloquear_categorias()
        resultado = self._analizar(usuario, datos, confirmando=True)
        if not resultado.buenas:
            raise SinFilasValidas(
                detalles={
                    "filas_error": [
                        self._fila_error(m).model_dump(mode="json") for m in resultado.malas
                    ]
                }
            )
        puede_costos = self.acceso.tiene_permiso(usuario, P.CATALOGO_COSTOS)

        # 1. Los articulos que faltan (solo en ALTA), con la plantilla de su categoria.
        creados: dict[str, ArticuloCreadoOut] = {}
        for k, nuevo in resultado.nuevos.items():
            assert nuevo.codigo and not nuevo.pendiente
            articulo = self.catalogo.crear_articulo(
                ArticuloCreate(
                    codigo=nuevo.codigo,
                    nombre=nuevo.nombre,
                    marca=nuevo.marca,
                    categoria_id=nuevo.categoria.id,
                    unidad=nuevo.unidad,
                    costo_unitario=nuevo.costo if puede_costos else None,
                ),
                usuario.id,
                puede_costos=puede_costos,
            )
            creados[k] = ArticuloCreadoOut(
                id=articulo.id,
                codigo=articulo.codigo,
                codigo_generado=nuevo.codigo_generado,
                nombre=articulo.nombre,
                unidad=articulo.unidad,
                categoria=nuevo.categoria.nombre,
                control=articulo.control,
            )

        # 2. Un vale de ENTRADA por almacen, en orden de clave: los folios salen consecutivos.
        por_almacen: dict[uuid.UUID, list[FilaBuena]] = defaultdict(list)
        almacenes: dict[uuid.UUID, Almacen] = {}
        for fila in resultado.buenas:
            por_almacen[fila.almacen.id].append(fila)
            almacenes[fila.almacen.id] = fila.almacen
        vales: list[ValeImportadoOut] = []
        for almacen_id in sorted(por_almacen, key=lambda i: almacenes[i].clave):
            filas = por_almacen[almacen_id]
            almacen = almacenes[almacen_id]
            referencia = AlmacenRefOut(id=almacen.id, clave=almacen.clave, nombre=almacen.nombre)
            for parte, inicio in enumerate(range(0, len(filas), RENGLONES_POR_VALE)):
                trozo = filas[inicio : inicio + RENGLONES_POR_VALE]
                cuerpo = ConfirmarIn(
                    tipo=TipoVale.ENTRADA,
                    id_cliente=_id_cliente(datos.id_lote, almacen_id, parte),
                    almacen_id=almacen_id,
                    observacion="Importación de inventario desde una tabla.",
                    renglones=[self._renglon(f) for f in trozo],
                )
                vale, creado = self.movimientos.confirmar(
                    usuario, cuerpo, aislar=False, commit=False
                )
                if not creado:  # pragma: no cover - ya se revisó el lote al empezar
                    raise ImportacionCambio()
                vales.append(
                    ValeImportadoOut(
                        id=vale.id,
                        folio=vale.folio,
                        almacen=referencia,
                        renglones=len(trozo),
                        piezas=sum(1 for f in trozo if f.control == "PIEZA"),
                        unidades=sum(f.cantidad for f in trozo),
                    )
                )

        generados = {
            b.codigo_pieza for b in resultado.buenas if b.codigo_pieza_generado and b.codigo_pieza
        }
        piezas_creadas = self._piezas_creadas([v.id for v in vales], generados)

        salida = ImportacionOut(
            modo=datos.modo,
            id_lote=datos.id_lote,
            repetida=False,
            resumen=ResumenImportacionOut(
                filas_importadas=len(resultado.buenas),
                filas_con_error=len(resultado.malas),
                articulos_creados=len(creados),
                existentes=sum(1 for b in resultado.buenas if b.estado == "EXISTENTE"),
                unidos=sum(1 for b in resultado.buenas if b.estado == "UNIDO"),
                excluidas=len(resultado.excluidas),
                vales=len(vales),
                piezas=sum(v.piezas for v in vales),
                unidades=sum(v.unidades for v in vales),
                series_pendientes=sum(1 for p in piezas_creadas if p.serie_pendiente),
            ),
            articulos_creados=list(creados.values()),
            piezas_creadas=piezas_creadas,
            vales=vales,
            filas_error=[self._fila_error(m) for m in resultado.malas],
            avisos=resultado.avisos,
        )
        self.auditoria.registrar(
            usuario_id=usuario.id,
            accion="importacion.confirmar",
            entidad="importacion",
            entidad_id=datos.id_lote,
            despues={
                **salida.resumen.model_dump(),
                "modo": datos.modo,
                "huella": huella,
                **({"repetido": True} if datos.confirmar_repetido else {}),
                "folios": [v.folio for v in vales],
                # Para volver a listar las etiquetas si se repite el lote (I-15).
                "codigos_pieza_generados": sorted(generados),
            },
        )
        return salida

    def _piezas_creadas(
        self, vale_ids: list[uuid.UUID], generados: set[str]
    ) -> list[PiezaCreadaOut]:
        """Las piezas que entraron en esos vales, con su codigo definitivo (I-15)."""
        almacenes = {a.id: a for a in self.repository.almacenes()}
        salida = []
        for pieza, articulo, vale in self.repository.piezas_de_vales(vale_ids):
            almacen = almacenes[vale.almacen_id]
            salida.append(
                PiezaCreadaOut(
                    id=pieza.id,
                    codigo=pieza.codigo,
                    codigo_generado=pieza.codigo in generados,
                    articulo=ArticuloRefOut(
                        id=articulo.id, codigo=articulo.codigo, nombre=articulo.nombre
                    ),
                    numero_serie=pieza.numero_serie,
                    serie_pendiente=not pieza.numero_serie,
                    almacen=AlmacenRefOut(
                        id=almacen.id, clave=almacen.clave, nombre=almacen.nombre
                    ),
                )
            )
        return salida

    @staticmethod
    def _renglon(fila: FilaBuena) -> RenglonIn:
        if fila.control == "PIEZA":
            return RenglonIn(
                codigo=fila.codigo,
                cantidad=1,
                pieza=PiezaEntradaIn(
                    codigo=fila.codigo_pieza or "", numero_serie=fila.numero_serie
                ),
            )
        return RenglonIn(codigo=fila.codigo, cantidad=fila.cantidad)

    # --------------------------------------------------------------------- idempotencia

    def _lote_confirmado(self, usuario: Usuario, datos: ImportacionIn) -> ImportacionOut | None:
        """Si el lote ya se confirmó, lo que se guardó entonces; si no, `None`."""
        id_lote = datos.id_lote
        assert id_lote is not None
        almacenes = self.repository.almacenes()
        encontrados = self.repository.vales_por_id_cliente(
            _id_cliente(id_lote, a.id, 0) for a in almacenes
        )
        if not encontrados:
            return None
        vales = list(encontrados)
        for almacen in almacenes:
            parte = 1
            while True:
                siguiente = self.repository.vales_por_id_cliente(
                    [_id_cliente(id_lote, almacen.id, parte)]
                )
                if not siguiente:
                    break
                vales.extend(siguiente)
                parte += 1
        if any(v.responsable_id != usuario.id or v.tipo != TipoVale.ENTRADA for v in vales):
            raise LoteEnUso()
        resumen = self.repository.resumen_de_vales(v.id for v in vales)
        piezas_creadas = self._piezas_creadas(
            [v.id for v in vales], self.repository.codigos_de_piezas_generados(id_lote)
        )
        por_id = {a.id: a for a in almacenes}
        salida = []
        for v in sorted(vales, key=lambda v: v.folio):
            renglones, piezas, unidades = resumen.get(v.id, (0, 0, 0))
            almacen = por_id[v.almacen_id]
            salida.append(
                ValeImportadoOut(
                    id=v.id,
                    folio=v.folio,
                    almacen=AlmacenRefOut(
                        id=almacen.id, clave=almacen.clave, nombre=almacen.nombre
                    ),
                    renglones=renglones,
                    piezas=piezas,
                    unidades=unidades,
                )
            )
        return ImportacionOut(
            modo=datos.modo,
            id_lote=id_lote,
            repetida=True,
            resumen=ResumenImportacionOut(
                filas_importadas=sum(v.renglones for v in salida),
                filas_con_error=0,
                articulos_creados=0,
                existentes=0,
                unidos=0,
                excluidas=0,
                vales=len(salida),
                piezas=sum(v.piezas for v in salida),
                unidades=sum(v.unidades for v in salida),
                series_pendientes=sum(1 for p in piezas_creadas if p.serie_pendiente),
            ),
            articulos_creados=[],
            piezas_creadas=piezas_creadas,
            vales=salida,
            filas_error=[],
            avisos=["Este lote ya se había importado: no se guardó nada nuevo."],
        )

    # ------------------------------------------------------------------------- salida

    @staticmethod
    def _fila_error(mala: FilaMala) -> FilaErrorOut:
        campos: dict = {}
        if mala.sugerida is not None and mala.sugerida.categoria is not None:
            campos = {
                "categoria_sugerida": _ref(mala.sugerida.categoria),
                "motivo_sugerencia": mala.sugerida.motivo,
            }
        return FilaErrorOut(
            fila=mala.fila,
            estado="ERROR",
            datos={c: mala.datos[c] for c in CAMPOS if c in mala.datos},
            motivos=[
                MotivoOut(regla=m.regla, campo=m.campo, codigo=m.codigo, mensaje=m.mensaje)
                for m in mala.motivos
            ],
            **campos,
        )

    def _vista_previa_out(
        self, usuario: Usuario, res: Resultado, fecha: datetime | None = None
    ) -> VistaPreviaOut:
        puede_costos = self.acceso.tiene_permiso(usuario, P.CATALOGO_COSTOS)
        validas = []
        for b in res.buenas:
            campos = dict(
                fila=b.fila,
                estado=b.estado,
                codigo=b.codigo,
                codigo_generado=b.codigo_generado,
                nombre=b.nombre,
                marca=b.marca,
                categoria=_ref(b.categoria),
                categoria_sugerida=_ref(b.categoria_sugerida),
                motivo_sugerencia=b.motivo_sugerencia,
                control=b.control,
                articulo_nuevo=b.nuevo,
                cantidad=b.cantidad,
                unidad=b.unidad,
                saldo_antes=b.saldo_antes,
                saldo_despues=b.saldo_despues,
                unida_de=b.unida_de,
                almacen=AlmacenRefOut(
                    id=b.almacen.id, clave=b.almacen.clave, nombre=b.almacen.nombre
                ),
                codigo_pieza=b.codigo_pieza,
                codigo_pieza_generado=b.codigo_pieza_generado,
                numero_serie=b.numero_serie,
                serie_pendiente=b.serie_pendiente,
                avisos=b.avisos,
            )
            if puede_costos and b.costo is not None:
                campos["costo"] = b.costo
            validas.append(FilaValidaOut(**campos))
        nuevos = []
        for n in res.nuevos.values():
            campos = dict(
                codigo=n.codigo,
                nombre=n.nombre,
                marca=n.marca,
                categoria=None if n.pendiente else _ref(n.categoria),
                control=n.control,
                unidad=n.unidad,
                filas=n.filas,
            )
            if puede_costos and n.costo is not None:
                campos["costo"] = n.costo
            nuevos.append(ArticuloNuevoOut(**campos))
        return VistaPreviaOut(
            modo=res.modo,
            columnas=res.columnas,
            avisos=res.avisos,
            archivo_repetido=None if fecha is None else ArchivoRepetidoOut(fecha=fecha),
            resumen=ResumenVistaPreviaOut(
                total=res.total,
                validas=len(res.buenas),
                con_error=len(res.malas),
                vacias=res.vacias,
                articulos_nuevos=len(res.nuevos),
                existentes=sum(1 for b in res.buenas if b.estado == "EXISTENTE"),
                unidos=sum(1 for b in res.buenas if b.estado == "UNIDO"),
                excluidas=len(res.excluidas),
                por_revisar=res.por_revisar,
                piezas=sum(1 for b in res.buenas if b.control == "PIEZA"),
                unidades=sum(b.cantidad for b in res.buenas),
                almacenes=len({b.almacen.id for b in res.buenas}),
                series_pendientes=sum(1 for b in res.buenas if b.serie_pendiente),
            ),
            filas_validas=validas,
            filas_error=[self._fila_error(m) for m in res.malas],
            filas_excluidas=[
                FilaExcluidaOut(fila=x.fila, nombre=x.nombre, motivo=x.motivo)
                for x in res.excluidas
            ],
            articulos_nuevos=nuevos,
            categorias_desconocidas=[
                CategoriaDesconocidaOut(nombre=nombre, filas=filas)
                for nombre, filas in res.categorias_desconocidas.values()
            ],
        )
