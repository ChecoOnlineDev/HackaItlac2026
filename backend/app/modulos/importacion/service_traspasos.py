"""Importacion de traspasos por lista de Excel (FEAT-009, TR-01 a TR-09).

Un archivo es UN traspaso: un origen (el almacen de quien sube; con `almacenes.todos` lo elige) y
un destino elegido. La vista previa y la confirmacion evaluan cada fila con las MISMAS reglas de
la captura manual llamando a `MovimientoService.evaluar` (X-02, X-03, X-04, X-09, AL-04); aqui no
se repite ninguna. La importacion NO escribe vales ni existencias: confirma con
`MovimientoService.confirmar(tipo=TRASPASO)`, en una sola transaccion (RG-09):

    permiso -> lote ya confirmado (200) -> revision -> tope de 500 -> almacen cerrado -> ruta
    (X-03, X-16 a X-18; con `autorizacion_id` la valida `movimientos`) -> archivo repetido ->
    filas en rojo (todo o nada, o dejar fuera) -> vale -> auditoria.

El `id_cliente` del vale sale del `id_lote` (uuid5): repetir el lote devuelve el mismo vale.
"""

import hashlib
import io
import json
import uuid

from openpyxl import Workbook
from openpyxl.styles import Font
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError, InvalidRequestError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core import errores_bd
from app.core.excepciones import AppError, DatosInvalidos, NoEncontrado
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.acceso.service import AccesoService
from app.modulos.almacenes.exceptions import AlmacenCerrado
from app.modulos.almacenes.models import Almacen, EstadoAlmacen
from app.modulos.almacenes.service import AlmacenService
from app.modulos.auditoria.service import AuditoriaService
from app.modulos.autorizaciones.exceptions import AutorizacionInvalida, AutorizacionPropia
from app.modulos.autorizaciones.service import AutorizacionService, RenglonVale
from app.modulos.catalogo.models import Articulo, Pieza, TipoCodigo
from app.modulos.catalogo.service import CatalogoService
from app.modulos.importacion.analisis_traspasos import (
    ROJO,
    FilaAnalizada,
    FilaLeida,
    MotivoFila,
    codigo_de_motivo,
    huella_de_filas,
    leer_filas,
    preparar,
)
from app.modulos.importacion.exceptions import (
    ArchivoInvalido,
    ArchivoRepetido,
    ImportacionCambio,
    LoteEnUso,
)
from app.modulos.importacion.exceptions_traspasos import FilasConError, TraspasoMuyGrande
from app.modulos.importacion.lectura import leer_xlsx, proponer_columnas
from app.modulos.importacion.repository import ImportacionRepository
from app.modulos.importacion.repository_traspasos import TraspasoImportRepository
from app.modulos.importacion.schemas import AlmacenRefOut
from app.modulos.importacion.schemas_traspasos import (
    CAMPOS_TRASPASO,
    ArchivoRepetidoTraspasoOut,
    ArchivoTraspasoOut,
    ColumnasTraspasoIn,
    FilaDejadaFueraOut,
    FilaTraspasoOut,
    MotivoFilaOut,
    PiezaFilaOut,
    ResumenTraspasoOut,
    ResumenVistaTraspasoOut,
    RutaOut,
    TraspasoConfirmarIn,
    TraspasoIn,
    TraspasoOut,
    ValeTraspasoOut,
    VistaPreviaTraspasoOut,
)
from app.modulos.movimientos.exceptions import RutaSoloAdministrador
from app.modulos.movimientos.models import EstadoVale, Nivel, TipoVale
from app.modulos.movimientos.schemas import (
    CANTIDAD_MAXIMA,
    ConfirmarIn,
    RenglonIn,
    RutaEvaluacionOut,
    ValeIn,
)
from app.modulos.movimientos.service import MovimientoService

# Un vale admite hasta 500 renglones (`ValeIn.renglones`): un traspaso no se parte (TR-07).
RENGLONES_MAXIMOS = 500
INTENTOS = 3
ERRNO_INTERBLOQUEO = 1213
ACCION_AUDITORIA = "importacion.traspaso"
# Reglas de la ruta, de la más específica a la menos (TR-05); X-18 solo informa.
REGLAS_DE_RUTA = ("X-17", "X-16", "X-03", "X-18")
LARGO_CONSTANCIA = 380


def _id_cliente(id_lote: uuid.UUID) -> uuid.UUID:
    """El `id_cliente` del vale: el mismo lote da siempre el mismo."""
    return uuid.uuid5(id_lote, "importacion-traspaso")


def _ref(almacen: Almacen) -> AlmacenRefOut:
    return AlmacenRefOut(id=almacen.id, clave=almacen.clave, nombre=almacen.nombre)


def _motivos_out(motivos: list[MotivoFila]) -> list[MotivoFilaOut]:
    return [MotivoFilaOut(regla=m.regla, codigo=m.codigo, mensaje=m.mensaje) for m in motivos]


def _falta(campo: str, mensaje: str) -> DatosInvalidos:
    return DatosInvalidos(mensaje, [{"campo": campo, "mensaje": mensaje}])


class _Revision:
    """Lo que sale de revisar un archivo."""

    def __init__(self) -> None:
        self.origen: Almacen
        self.destino: Almacen
        self.leidas: list[FilaLeida] = []
        self.filas: list[FilaAnalizada] = []
        self.ruta_motivo: MotivoFila | None = None
        self.ruta: RutaEvaluacionOut | None = None
        self.autorizada = False
        self.autorizacion_error: str | None = None
        self.motivos_vale: list[MotivoFila] = []
        self.cerrado: Almacen | None = None
        self.avisos: list[str] = []

    @property
    def excedido(self) -> bool:
        return len(self.filas) > RENGLONES_MAXIMOS

    @property
    def rojas(self) -> list[FilaAnalizada]:
        return [f for f in self.filas if f.nivel == ROJO]

    @property
    def confirmables(self) -> list[FilaAnalizada]:
        return [f for f in self.filas if f.nivel != ROJO]


class TraspasoImportService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ImportacionRepository(session)
        self.propio = TraspasoImportRepository(session)
        self.acceso = AccesoService(session)
        self.catalogo = CatalogoService(session)
        self.movimientos = MovimientoService(session)
        self.autorizaciones = AutorizacionService(session)
        self.almacenes = AlmacenService(session)
        self.auditoria = AuditoriaService(session)

    # ------------------------------------------------------------------- plantilla

    def plantilla(self) -> bytes:
        """El `.xlsx` de ejemplo: columnas, una fila de ejemplo y las instrucciones."""
        libro = Workbook()
        hoja = libro.active
        assert hoja is not None
        hoja.title = "Plantilla"
        hoja.append(["codigo", "nombre", "cantidad", "codigo pieza", "serie"])
        hoja.append(["GUA-001", "Guantes de carnaza", 6, "", ""])
        hoja.append(["ALT-024", "Arnés de poliéster", "", "ALT-024-0007", "SN-5521"])
        for celda in hoja[1]:
            celda.font = Font(bold=True)
        for letra, ancho in zip("ABCDE", (18, 32, 12, 22, 18), strict=True):
            hoja.column_dimensions[letra].width = ancho
        ayuda = libro.create_sheet("Instrucciones")
        ayuda.append(["Dato", "Qué poner"])
        for celda in ayuda[1]:
            celda.font = Font(bold=True)
        ayuda.append(["codigo", "Código del artículo que se traspasa (artículos por cantidad)."])
        ayuda.append(
            [
                "nombre",
                "Opcional, solo de ayuda: se compara con el catálogo para avisar de un error.",
            ]
        )
        ayuda.append(["cantidad", "Número entero. Para una pieza no hace falta."])
        ayuda.append(["codigo pieza", "Código de la pieza: una fila por pieza."])
        ayuda.append(["serie", "Opcional: sirve para comprobar que es la pieza correcta."])
        ayuda.append([])
        for nota in (
            "Un archivo es un traspaso: el origen y el destino se eligen en pantalla.",
            "Hasta 500 renglones por archivo; cada pieza cuenta como uno.",
            "Las filas del mismo artículo se unen en una.",
            "La cantidad es un número entero: en lugar de 0.25 kilos, escribe 250 gramos.",
            "Solo se mueve lo que ya existe: un código que no existe es un error.",
            "Las demás columnas se ignoran.",
        ):
            ayuda.append([nota])
        ayuda.column_dimensions["A"].width = 18
        ayuda.column_dimensions["B"].width = 80
        salida = io.BytesIO()
        libro.save(salida)
        return salida.getvalue()

    # -------------------------------------------------------------------- revision

    def _identificar(self, codigo: str) -> tuple[Articulo | None, Pieza | None]:
        fila = self.catalogo.identificar_codigo(codigo)
        if fila is None:
            return None, None
        try:
            if fila.tipo == TipoCodigo.ARTICULO:
                return self.catalogo.obtener_articulo(fila.ref_id), None
            if fila.tipo == TipoCodigo.PIEZA:
                pieza = self.catalogo.obtener_pieza(fila.ref_id)
                return self.catalogo.obtener_articulo(pieza.articulo_id), pieza
        except NoEncontrado:
            return None, None
        return None, None  # credencial de trabajador o vale

    def _origen_y_destino(self, usuario: Usuario, datos: TraspasoIn) -> tuple[Almacen, Almacen]:
        if datos.destino_almacen_id is None:
            raise _falta("destino_almacen_id", "Elige a qué almacén se envía.")
        origen_id = self.movimientos.resolver_almacen_del_vale(usuario, datos.almacen_id)
        origen = self.almacenes.obtener(origen_id)
        destino = self.almacenes.obtener(datos.destino_almacen_id)
        if destino.id == origen.id:
            raise _falta("destino_almacen_id", "El destino debe ser otro almacén, no el de origen.")
        return origen, destino

    def _revisar(self, usuario: Usuario, datos: TraspasoIn) -> _Revision:
        rev = _Revision()
        rev.origen, rev.destino = self._origen_y_destino(usuario, datos)
        columnas = datos.columnas.model_dump(include=set(CAMPOS_TRASPASO))
        if columnas["codigo"] is None and columnas["codigo_pieza"] is None:
            raise _falta(
                "columnas", "Falta la columna del código del artículo o la del código de pieza."
            )
        ignoradas = datos.columnas.ignoradas()
        if ignoradas:
            rev.avisos.append(
                "Se ignoran las columnas de " + ", ".join(ignoradas) + ": el traspaso solo lee "
                "código, nombre (de ayuda), cantidad, código de pieza y serie."
            )
        rev.leidas = leer_filas(datos.filas, columnas, datos.primera_fila)
        rev.filas = preparar(
            rev.leidas,
            self._identificar,
            cantidad_maxima=get_settings().importacion_cantidad_maxima,
            suma_maxima=CANTIDAD_MAXIMA,
        )
        for f in rev.filas:
            if f.unida_de:
                junto = ", ".join(str(n) for n in [f.fila, *f.unida_de])
                rev.avisos.append(f"Unido: filas {junto}")
        for almacen in (rev.origen, rev.destino):
            if almacen.estado == EstadoAlmacen.CERRADO:
                rev.cerrado = rev.cerrado or almacen
        self._evaluar(usuario, rev)
        self._revisar_autorizacion(usuario, rev, datos.autorizacion_id)
        return rev

    def _revisar_autorizacion(
        self, usuario: Usuario, rev: _Revision, autorizacion_id: uuid.UUID | None
    ) -> None:
        """X-17 y X-19: ¿sirve la `autorizacion_id` para las filas que no están en rojo? Solo
        informa (la vista previa); al confirmar la valida de nuevo `movimientos`, que es quien la
        gasta, junto con el vale."""
        if (
            autorizacion_id is None
            or rev.ruta is None
            or rev.ruta.autoriza != "SUPERVISOR_ORIGEN"
            or not rev.confirmables
        ):
            return
        renglones = [
            RenglonVale(f.pieza.codigo if f.pieza else f.articulo.codigo, f.cantidad)  # type: ignore[union-attr]
            for f in rev.confirmables
        ]
        try:
            self.autorizaciones.validar_traslado_para_vale(
                autorizacion_id, rev.origen.id, rev.destino.id, renglones, usuario
            )
        except (AutorizacionInvalida, AutorizacionPropia, NoEncontrado) as exc:
            rev.autorizacion_error = exc.mensaje
            return
        rev.autorizada = True

    def _evaluar(self, usuario: Usuario, rev: _Revision) -> None:
        """Pasa las filas por el evaluador de movimientos, de 500 en 500 (cada artículo y cada
        pieza aparecen una sola vez, así que el renglón i del vale es la fila i)."""
        candidatas = [f for f in rev.filas if not f.con_error_local]
        ubicacion_origen = self.almacenes.ubicacion_de_almacen(rev.origen.id).id
        trozos = [
            candidatas[i : i + RENGLONES_MAXIMOS]
            for i in range(0, len(candidatas), RENGLONES_MAXIMOS)
        ] or [[]]
        for numero, trozo in enumerate(trozos):
            cuerpo = ValeIn(
                tipo=TipoVale.TRASPASO,
                almacen_id=rev.origen.id,
                destino_almacen_id=rev.destino.id,
                renglones=[
                    RenglonIn(
                        codigo=(f.pieza.codigo if f.pieza else f.articulo.codigo),  # type: ignore[union-attr]
                        cantidad=f.cantidad,
                    )
                    for f in trozo
                ],
            )
            evaluacion = self.movimientos.evaluar(usuario, cuerpo)
            if numero == 0:
                rev.ruta = evaluacion.ruta
                for m in evaluacion.motivos:
                    if m.regla in REGLAS_DE_RUTA:
                        # TR-05: la ruta se evalúa una vez; manda la más específica (X-17, X-16,
                        # X-03). X-18 solo informa.
                        actual = rev.ruta_motivo.regla if rev.ruta_motivo else None
                        if m.regla != "X-18" and (
                            actual is None
                            or REGLAS_DE_RUTA.index(m.regla) < REGLAS_DE_RUTA.index(actual)
                        ):
                            rev.ruta_motivo = MotivoFila(m.regla, "RUTA", m.mensaje, m.nivel.value)
                    elif m.regla == "X-20":  # aviso que no bloquea
                        rev.avisos.append(m.mensaje)
                    else:
                        rev.motivos_vale.append(
                            MotivoFila(m.regla, codigo_de_motivo(m.regla, False), m.mensaje)
                        )
            for f, r in zip(trozo, evaluacion.renglones, strict=True):
                f.nivel = r.nivel.value
                if f.nivel == Nivel.VERDE.value and f.con_aviso_local:  # TR-13
                    f.nivel = Nivel.AMARILLO.value
                for m in r.motivos:
                    f.motivos.append(
                        MotivoFila(
                            m.regla,
                            codigo_de_motivo(m.regla, f.pieza is not None),
                            m.mensaje,
                            m.nivel.value,
                        )
                    )
                if f.pieza is not None:
                    f.disponible = 1 if f.pieza.ubicacion_id == ubicacion_origen else 0
                else:
                    f.disponible = r.disponible or 0

    # ----------------------------------------------------------------------- huella

    @staticmethod
    def _huella(rev: _Revision) -> str:
        """`sha256` de las filas normalizadas (en orden fijo), el origen y el destino (TR-08)."""
        cuerpo = json.dumps(
            {
                "modo": "TRASPASO",
                "origen": str(rev.origen.id),
                "destino": str(rev.destino.id),
                "filas": huella_de_filas(rev.leidas),
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return hashlib.sha256(cuerpo.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------ vista previa

    def vista_previa(self, usuario: Usuario, datos: TraspasoIn) -> VistaPreviaTraspasoOut:
        return self._salida_vista(self._revisar(usuario, datos))

    def vista_previa_de_archivo(
        self,
        usuario: Usuario,
        nombre: str | None,
        contenido: bytes,
        destino_almacen_id: uuid.UUID | None,
        almacen_id: uuid.UUID | None,
    ) -> ArchivoTraspasoOut:
        if destino_almacen_id is None:
            raise _falta("destino_almacen_id", "Elige a qué almacén se envía.")
        hoja, filas = leer_xlsx(nombre, contenido)
        inicio = next((i for i, f in enumerate(filas) if any(f)), None)
        if inicio is None:
            raise ArchivoInvalido("El archivo no trae datos.", {"campo": "archivo"})
        encabezados = filas[inicio]
        datos = filas[inicio + 1 :]
        if not datos:
            raise ArchivoInvalido(
                "La hoja solo trae los encabezados: no hay filas que traspasar.",
                {"campo": "archivo"},
            )
        ancho = max(len(encabezados), *(len(f) for f in datos))
        encabezados = encabezados + [""] * (ancho - len(encabezados))
        datos = [f + [""] * (ancho - len(f)) for f in datos]
        columnas = proponer_columnas(encabezados)
        primera_fila = inicio + 2
        vista = None
        if columnas["codigo"] is not None or columnas["codigo_pieza"] is not None:
            cuerpo = TraspasoIn(
                filas=datos,
                columnas=ColumnasTraspasoIn(**{c: i for c, i in columnas.items() if i is not None}),
                primera_fila=primera_fila,
                destino_almacen_id=destino_almacen_id,
                almacen_id=almacen_id,
            )
            vista = self.vista_previa(usuario, cuerpo)
        return ArchivoTraspasoOut(
            hoja=hoja,
            encabezados=encabezados,
            columnas=columnas,
            primera_fila=primera_fila,
            filas=datos,
            vista_previa=vista,
        )

    def _ruta(self, rev: _Revision) -> RutaOut:
        motivo = rev.ruta_motivo
        assert motivo is not None and rev.ruta is not None
        return RutaOut(
            habitual=motivo.nivel == Nivel.VERDE.value,
            nivel=motivo.nivel,
            pide_observacion=motivo.nivel == Nivel.AMARILLO.value,
            mensaje=motivo.mensaje,
            clase=rev.ruta.clase,
            autoriza=rev.ruta.autoriza,
            autorizadores_disponibles=rev.ruta.autorizadores_disponibles,
            autorizada=rev.autorizada,
        )

    def _salida_vista(self, rev: _Revision) -> VistaPreviaTraspasoOut:
        ruta = self._ruta(rev)
        fecha = self.propio.fecha_de_huella(self._huella(rev))
        motivos = list(rev.motivos_vale)
        if rev.cerrado is not None and not any(m.regla == "AL-04" for m in motivos):
            motivos.insert(0, MotivoFila("AL-04", "ALMACEN_CERRADO", "Ese almacén está cerrado."))
        confirmables = rev.confirmables
        errores = len(rev.rojas)
        avisos = list(rev.avisos)
        if fecha is not None:
            avisos.append("Este archivo ya se usó para otro traspaso.")
        if rev.excedido:
            avisos.append(
                f"Pasa de {RENGLONES_MAXIMOS} renglones: divide el archivo en varios traspasos."
            )
        return VistaPreviaTraspasoOut(
            origen=_ref(rev.origen),
            destino=_ref(rev.destino),
            ruta=ruta,
            motivos=_motivos_out(motivos),
            puede_confirmar=bool(
                confirmables
                and errores == 0
                and not motivos
                and ruta.nivel != Nivel.ROJO.value
                and (ruta.autoriza != "SUPERVISOR_ORIGEN" or ruta.autorizada)  # X-17
                and not rev.excedido
            ),
            autorizacion_error=rev.autorizacion_error,
            archivo_repetido=None if fecha is None else ArchivoRepetidoTraspasoOut(fecha=fecha),
            resumen=ResumenVistaTraspasoOut(
                total=len(rev.filas),
                ok=sum(1 for f in rev.filas if f.nivel == Nivel.VERDE.value),
                avisos=sum(1 for f in rev.filas if f.nivel not in (Nivel.VERDE.value, ROJO)),
                errores=errores,
                unidades=sum(f.cantidad for f in confirmables),
                piezas=sum(1 for f in confirmables if f.pieza is not None),
                excedido=rev.excedido,
            ),
            filas=[self._fila_out(f) for f in rev.filas],
            avisos=avisos,
        )

    @staticmethod
    def _fila_out(f: FilaAnalizada) -> FilaTraspasoOut:
        pieza = None
        if f.pieza is not None:
            pieza = PiezaFilaOut(
                id=f.pieza.id, codigo=f.pieza.codigo, numero_serie=f.pieza.numero_serie
            )
        return FilaTraspasoOut(
            fila=f.fila,
            codigo=f.codigo,
            articulo=f.articulo.nombre if f.articulo else None,
            pieza=pieza,
            cantidad=f.cantidad,
            disponible_en_origen=f.disponible,
            nivel=f.nivel,
            unida_de=f.unida_de,
            motivos=_motivos_out(f.motivos),
        )

    # -------------------------------------------------------------------- confirmar

    def confirmar(self, usuario: Usuario, datos: TraspasoConfirmarIn) -> tuple[TraspasoOut, bool]:
        """Devuelve `(resumen, creada)`; `creada` es falso si el lote ya estaba confirmado."""
        self.acceso.exigir_permiso(usuario, P.TRASPASOS_OPERAR)
        if datos.id_lote is None:
            raise _falta("id_lote", "Falta el identificador del lote.")
        for intento in range(1, INTENTOS + 1):
            try:
                self._aislar_transaccion()
                previa = self._lote_confirmado(usuario, datos.id_lote)
                if previa is not None:
                    return previa, False
                salida = self._importar(usuario, datos)
                self.session.commit()
                return salida, True
            except AppError:
                self.session.rollback()
                raise
            except DBAPIError as exc:
                self.session.rollback()
                violacion = errores_bd.violacion(exc)
                reintentable = violacion.errno in (errores_bd.ERRNO_UNICO, ERRNO_INTERBLOQUEO)
                if reintentable and intento < INTENTOS:
                    continue  # otra confirmacion gano: se vuelve a revisar con lo nuevo
                if violacion.errno == errores_bd.ERRNO_UNICO:
                    raise ImportacionCambio() from exc
                raise
            except Exception:
                self.session.rollback()
                raise
        raise AssertionError("inalcanzable")  # pragma: no cover

    def _aislar_transaccion(self) -> None:
        """Transaccion limpia en READ COMMITTED (igual que la importacion de entradas)."""
        self.session.commit()
        if isinstance(self.session.get_bind(), Connection):
            return
        try:
            self.session.connection(execution_options={"isolation_level": "READ COMMITTED"})
        except InvalidRequestError:  # pragma: no cover - ya habia una transaccion abierta
            pass

    def _importar(self, usuario: Usuario, datos: TraspasoConfirmarIn) -> TraspasoOut:
        assert datos.id_lote is not None
        rev = self._revisar(usuario, datos)
        if rev.excedido:  # TR-07
            raise TraspasoMuyGrande(
                detalles={
                    "regla": "TR-07",
                    "renglones": len(rev.filas),
                    "maximo": RENGLONES_MAXIMOS,
                }
            )
        if rev.cerrado is not None:  # AL-04
            raise AlmacenCerrado(rev.cerrado)
        self._exigir_ruta(usuario, rev, datos)  # X-03
        huella = self._huella(rev)
        if not datos.confirmar_repetido:  # TR-08
            fecha = self.propio.fecha_de_huella(huella)
            if fecha is not None:
                raise ArchivoRepetido(fecha)
        rojas = rev.rojas
        if rojas and not datos.dejar_fuera_errores:  # TR-06
            raise FilasConError(detalles={"filas": self._detalle_filas(rojas)})
        buenas = rev.confirmables
        if not buenas:
            raise DatosInvalidos(
                "No hay filas que se puedan traspasar. Corrige los errores del archivo.",
                {"filas": self._detalle_filas(rojas)},
            )
        observacion = self._observacion(datos.observacion, rojas)

        cuerpo = ConfirmarIn(
            tipo=TipoVale.TRASPASO,
            id_cliente=_id_cliente(datos.id_lote),
            almacen_id=rev.origen.id,
            destino_almacen_id=rev.destino.id,
            observacion=observacion,
            autorizacion_id=datos.autorizacion_id,
            renglones=[
                RenglonIn(
                    codigo=(f.pieza.codigo if f.pieza else f.articulo.codigo),  # type: ignore[union-attr]
                    cantidad=f.cantidad,
                )
                for f in buenas
            ],
        )
        vale, creado = self.movimientos.confirmar(
            usuario, cuerpo, aislar=False, commit=False, lote_id=datos.id_lote
        )
        if not creado:  # pragma: no cover - ya se reviso el lote al empezar
            raise ImportacionCambio()

        piezas = sum(1 for f in buenas if f.pieza is not None)
        unidades = sum(f.cantidad for f in buenas)
        resumen = ResumenTraspasoOut(
            filas_importadas=len(buenas),
            filas_dejadas_fuera=len(rojas),
            unidades=unidades,
            piezas=piezas,
        )
        self.auditoria.registrar(
            usuario_id=usuario.id,
            accion=ACCION_AUDITORIA,
            entidad="importacion",
            entidad_id=datos.id_lote,
            despues={
                **resumen.model_dump(),
                "vale_id": str(vale.id),
                "folio": vale.folio,
                "origen": rev.origen.clave,
                "destino": rev.destino.clave,
                "huella": huella,
                **(
                    {"autorizacion_id": str(datos.autorizacion_id)}
                    if datos.autorizacion_id and rev.autorizada
                    else {}
                ),
                **({"repetido": True} if datos.confirmar_repetido else {}),
                **(
                    {"filas_dejadas_fuera": [f.fila for f in rojas], "dejar_fuera_errores": True}
                    if rojas
                    else {}
                ),
            },
        )
        return TraspasoOut(
            id_lote=datos.id_lote,
            repetida=False,
            vale=ValeTraspasoOut(
                id=vale.id,
                folio=vale.folio,
                token=vale.token,
                estado=EstadoVale.EN_TRANSITO.value,
                origen=_ref(rev.origen),
                destino=_ref(rev.destino),
                renglones=len(buenas),
                piezas=piezas,
                unidades=unidades,
            ),
            resumen=resumen,
            filas_dejadas_fuera=[
                FilaDejadaFueraOut(fila=f.fila, motivos=_motivos_out(f.motivos)) for f in rojas
            ],
            avisos=rev.avisos,
        )

    @staticmethod
    def _detalle_filas(filas: list[FilaAnalizada]) -> list[dict]:
        return [
            {
                "fila": f.fila,
                "motivos": [m.model_dump() for m in _motivos_out(f.motivos)],
            }
            for f in filas
        ]

    def _exigir_ruta(self, usuario: Usuario, rev: _Revision, datos: TraspasoConfirmarIn) -> None:
        """X-03: otra ruta que la habitual, solo con `almacenes.todos` y con observacion."""
        ruta = self._ruta(rev)
        if ruta.nivel == Nivel.ROJO.value:
            raise RutaSoloAdministrador(
                detalles={
                    "regla": "X-03",
                    "origen": _ref(rev.origen).model_dump(mode="json"),
                    "destino": _ref(rev.destino).model_dump(mode="json"),
                }
            )
        if ruta.pide_observacion and not (datos.observacion or "").strip():
            assert rev.ruta_motivo is not None
            regla = rev.ruta_motivo.regla  # X-16 (envío propio) o X-03 (ruta no habitual)
            mensaje = (
                "Escribe para qué se manda este traslado."
                if regla == "X-16"
                else "Anota por qué se envía por una ruta que no es la habitual."
            )
            raise DatosInvalidos(
                mensaje, [{"campo": "observacion", "mensaje": mensaje, "regla": regla}]
            )

    @staticmethod
    def _observacion(escrita: str | None, rojas: list[FilaAnalizada]) -> str | None:
        """TR-06: al dejar fuera filas, el vale lo dice (cuantas y cuales)."""
        if not rojas:
            return escrita
        numeros = [str(f.fila) for f in rojas]
        lista = ""
        for i, n in enumerate(numeros):
            siguiente = (", " if lista else "") + n
            if len(lista) + len(siguiente) > LARGO_CONSTANCIA - 60:
                lista += f" y {len(numeros) - i} más"
                break
            lista += siguiente
        cuantas = "1 fila" if len(rojas) == 1 else f"{len(rojas)} filas"
        constancia = f"Se dejaron fuera {cuantas} con error del archivo (filas {lista})."
        return f"{escrita} {constancia}" if escrita else constancia

    # ------------------------------------------------------------------ idempotencia

    def _lote_confirmado(self, usuario: Usuario, id_lote: uuid.UUID) -> TraspasoOut | None:
        """Si el lote ya se confirmo, el mismo vale; si no, `None`."""
        vales = self.repository.vales_por_id_cliente([_id_cliente(id_lote)])
        if not vales:
            return None
        vale = vales[0]
        if vale.responsable_id != usuario.id or vale.tipo != TipoVale.TRASPASO:
            raise LoteEnUso()
        renglones, piezas, unidades = self.repository.resumen_de_vales([vale.id]).get(
            vale.id, (0, 0, 0)
        )
        origen = self.almacenes.obtener(vale.almacen_id)
        assert vale.destino_almacen_id is not None
        destino = self.almacenes.obtener(vale.destino_almacen_id)
        return TraspasoOut(
            id_lote=id_lote,
            repetida=True,
            vale=ValeTraspasoOut(
                id=vale.id,
                folio=vale.folio,
                token=vale.token,
                estado=vale.estado,
                origen=_ref(origen),
                destino=_ref(destino),
                renglones=renglones,
                piezas=piezas,
                unidades=unidades,
            ),
            resumen=ResumenTraspasoOut(
                filas_importadas=renglones, filas_dejadas_fuera=0, unidades=unidades, piezas=piezas
            ),
            filas_dejadas_fuera=[],
            avisos=["Este lote ya se había importado: no se guardó nada nuevo."],
        )
