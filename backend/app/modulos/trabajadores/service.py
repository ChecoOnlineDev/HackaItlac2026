"""Reglas de `trabajadores` y control de la transacción.

Dos grupos de métodos:

- Los que atienden un endpoint (`crear`, `registrar_periodo`, `ligar_codigo`, `subir_foto`,
  `iniciar_baja`, `cancelar_baja`): hacen su propio `commit` y registran la auditoría.
- Los que usan otros módulos (`obtener`, `obtener_por_codigo`, `obtener_por_numero`, `buscar`,
  `es_vigente`, `evaluar_vigencia`, `motivo_no_vigente`, `periodo_vigente`, `pendientes_de`,
  `ficha_breve`, `marcar_inactivo`): no hacen `commit`; lo hace el service que los llama.
"""

import secrets
import uuid
from datetime import date

from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.errores_bd import es_restriccion
from app.core.tiempo import a_hora_mx, hoy_mx
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.acceso.service import AccesoService
from app.modulos.almacenes.service import AlmacenService
from app.modulos.archivos.models import TipoAdjunto
from app.modulos.archivos.service import ArchivoService
from app.modulos.auditoria.service import AuditoriaService
from app.modulos.catalogo.codigos import CodigoRepetido, CodigoService
from app.modulos.catalogo.models import Articulo, Pieza, TipoCodigo
from app.modulos.movimientos.models import Vale
from app.modulos.trabajadores.exceptions import (
    EstadoTrabajadorInvalido,
    PeriodoInvalido,
    TrabajadorConPendientes,
    TrabajadorExiste,
    TrabajadorNoEncontrado,
    TrabajadorSinFoto,
)
from app.modulos.trabajadores.models import EstadoTrabajador, PeriodoContrato, Trabajador
from app.modulos.trabajadores.repository import TrabajadorRepository
from app.modulos.trabajadores.schemas import (
    TEXTO_ESTADO,
    TEXTO_SITUACION,
    BajaOut,
    CodigoOut,
    FichaBreveOut,
    FichaOut,
    FiltrosTrabajadores,
    FotoOut,
    PendienteOut,
    PeriodoCreate,
    PeriodoOut,
    ResumenPendientesOut,
    Situacion,
    TrabajadorCreate,
    TrabajadorListItem,
    VigenciaOut,
)
from app.modulos.trabajadores.tipos import Pendiente, Vigencia

_ALFABETO_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _fecha(valor: date) -> str:
    return valor.strftime("%d/%m/%Y")


def elegir_periodo(periodos: list[PeriodoContrato], fecha: date) -> PeriodoContrato | None:
    """El periodo que incluye `fecha`; si ninguno, el más reciente. `periodos` va del más
    reciente al más antiguo."""
    for periodo in periodos:
        if periodo.inicio <= fecha <= periodo.fin:
            return periodo
    return periodos[0] if periodos else None


def calcular_vigencia(estado: str, periodos: list[PeriodoContrato], fecha: date) -> Vigencia:
    """T-07: vigente es estar Activo y que `fecha` caiga dentro de un periodo (el último día
    todavía cuenta). Si no, E-02 con el motivo."""
    if estado == EstadoTrabajador.INACTIVO:
        return Vigencia(False, "Ya no forma parte de la plantilla: su baja ya se completó.", "E-02")
    if estado == EstadoTrabajador.BAJA_EN_PROCESO:
        return Vigencia(
            False, "Ya no forma parte de la plantilla: su baja está en proceso.", "E-02"
        )
    if any(p.inicio <= fecha <= p.fin for p in periodos):
        return Vigencia(True, None, "T-07")
    futuros = sorted(p.inicio for p in periodos if p.inicio > fecha)
    if futuros:
        return Vigencia(
            False,
            f"Todavía no forma parte de la plantilla: su contrato inicia el {_fecha(futuros[0])}.",
            "E-02",
        )
    if periodos:
        return Vigencia(
            False,
            "Ya no forma parte de la plantilla: su contrato terminó el "
            f"{_fecha(max(p.fin for p in periodos))}.",
            "E-02",
        )
    return Vigencia(False, "Ya no forma parte de la plantilla: no tiene contrato.", "E-02")


class TrabajadorService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.trabajadores = TrabajadorRepository(session)
        self.auditoria = AuditoriaService(session)
        self.almacenes = AlmacenService(session)
        self.codigos = CodigoService(session)
        self.archivos = ArchivoService(session)
        self.acceso = AccesoService(session)

    # =============================================== para otros módulos (sin commit)

    def obtener(self, trabajador_id: uuid.UUID) -> Trabajador:
        """El trabajador, o `TrabajadorNoEncontrado` (404)."""
        trabajador = self.trabajadores.get(trabajador_id)
        if trabajador is None:
            raise TrabajadorNoEncontrado()
        return trabajador

    def obtener_por_codigo(self, codigo: str) -> Trabajador | None:
        """El trabajador dueño de un código escaneado (su credencial), o `None` si el código no
        existe o es de otra cosa (artículo, pieza o vale)."""
        fila = self.codigos.identificar(codigo)
        if fila is None or fila.tipo != TipoCodigo.TRABAJADOR:
            return None
        return self.trabajadores.get(fila.ref_id)

    def obtener_por_numero(self, numero_empleado: str) -> Trabajador | None:
        """El trabajador con ese número de empleado (tecleado en el mostrador), o `None`."""
        return self.trabajadores.get_by_numero(numero_empleado.strip())

    def buscar(self, q: str, limite: int = 20) -> list[Trabajador]:
        """Coincidencias por parte del nombre o del número de empleado, ordenadas por nombre."""
        if not q or not q.strip():
            return []
        return self.trabajadores.buscar(q, limite)

    def periodo_vigente(
        self, trabajador: Trabajador, fecha: date | None = None
    ) -> PeriodoContrato | None:
        """El periodo que incluye `fecha` (hoy en México por defecto). Si ninguno la incluye,
        el más reciente, para poder mostrar su vencimiento. `None` solo si no tiene periodos."""
        periodos = self.trabajadores.periodos(trabajador.id)
        return elegir_periodo(periodos, fecha or hoy_mx())

    def evaluar_vigencia(self, trabajador: Trabajador, fecha: date | None = None) -> Vigencia:
        """T-07 y E-02. `Vigencia(vigente, motivo, regla)`: con `vigente=False`, `motivo` es el
        texto para el usuario ("Ya no forma parte de la plantilla: …") y `regla` es "E-02"."""
        periodos = self.trabajadores.periodos(trabajador.id)
        return calcular_vigencia(trabajador.estado, periodos, fecha or hoy_mx())

    def es_vigente(self, trabajador: Trabajador, fecha: date | None = None) -> bool:
        """T-07: Activo y con `fecha` (hoy en México) dentro de su periodo."""
        return self.evaluar_vigencia(trabajador, fecha).vigente

    def motivo_no_vigente(self, trabajador: Trabajador, fecha: date | None = None) -> str | None:
        """El motivo de E-02, o `None` si el trabajador es vigente."""
        return self.evaluar_vigencia(trabajador, fecha).motivo

    def pendientes_de(self, trabajador_id: uuid.UUID) -> list[Pendiente]:
        """B-02 y E-17: retornables en resguardo del trabajador, de todos los almacenes, con
        código, fecha de entrega, folio y almacén. Los consumibles no cuentan (B-03). Solo lee."""
        return self.trabajadores.pendientes(trabajador_id)

    def ficha_breve(self, trabajador: Trabajador, actor: Usuario) -> FichaBreveOut:
        """Lo que ve el almacenista al identificar al trabajador (E-17, RG-13): nombre, número,
        puesto, área, vigencia, foto y resguardo. Nunca CURP ni NSS. La foto solo se indica a
        quien tiene `trabajadores.ver`."""
        periodos = self.trabajadores.periodos(trabajador.id)
        pendientes = self.pendientes_de(trabajador.id)
        return self._ficha_breve(trabajador, actor, periodos, pendientes)

    def marcar_inactivo(self, trabajador: Trabajador, actor: Usuario) -> Trabajador:
        """B-08: al emitirse el vale de no adeudo el trabajador queda Inactivo hasta el reingreso.

        Lo llama `movimientos` dentro de su transacción: no hace `commit`. Rechaza con
        `TrabajadorConPendientes` (CON_PENDIENTES) si aún tiene retornables en resguardo."""
        if trabajador.estado == EstadoTrabajador.INACTIVO:
            return trabajador
        pendientes = self.pendientes_de(trabajador.id)
        if pendientes:
            raise TrabajadorConPendientes(
                "No se puede dejar inactivo: tiene equipo pendiente de devolver.",
                {"regla": "B-04", "pendientes": [self._pendiente_json(p) for p in pendientes]},
            )
        antes = trabajador.estado
        trabajador.estado = EstadoTrabajador.INACTIVO
        self.auditoria.registrar(
            usuario_id=actor.id,
            accion="trabajador.inactivo",
            entidad="trabajador",
            entidad_id=trabajador.id,
            antes={"estado": antes},
            despues={"estado": trabajador.estado, "regla": "B-08"},
        )
        self.session.flush()
        return trabajador

    # ============================================================= alta (T-03)

    def crear(self, datos: TrabajadorCreate, actor: Usuario) -> Trabajador:
        """Alta (T-03): trabajador Activo, su primer periodo y su ubicación. Si el número o la
        CURP ya existen lanza `TrabajadorExiste` con la persona, para ofrecer el reingreso."""
        self._validar_periodo(datos.inicio, datos.fin)
        self._rechazar_si_existe(datos.numero_empleado, datos.curp)
        try:
            trabajador = self.trabajadores.add(
                Trabajador(
                    numero_empleado=datos.numero_empleado,
                    nombre=datos.nombre,
                    curp=datos.curp,
                    nss=datos.nss,
                    tallas=datos.tallas,
                    estado=EstadoTrabajador.ACTIVO,
                )
            )
        except DBAPIError as exc:
            self.session.rollback()
            if es_restriccion(exc, "uq_trabajador_numero_empleado") or es_restriccion(
                exc, "uq_trabajador_curp"
            ):
                self._rechazar_si_existe(datos.numero_empleado, datos.curp)
            raise
        self.trabajadores.add_periodo(
            PeriodoContrato(
                trabajador_id=trabajador.id,
                puesto=datos.puesto,
                area_obra=datos.area_obra,
                referencia=datos.referencia,
                inicio=datos.inicio,
                fin=datos.fin,
                creado_por=actor.id,
            )
        )
        self.almacenes.asegurar_ubicacion_de_trabajador(trabajador.id)
        self.auditoria.registrar(
            usuario_id=actor.id,
            accion="trabajador.alta",
            entidad="trabajador",
            entidad_id=trabajador.id,
            despues={
                "numero_empleado": trabajador.numero_empleado,
                "nombre": trabajador.nombre,
                "puesto": datos.puesto,
                "area_obra": datos.area_obra,
                "inicio": datos.inicio,
                "fin": datos.fin,
                "con_curp": datos.curp is not None,
                "con_nss": datos.nss is not None,
                "con_tallas": datos.tallas is not None,
                "regla": "T-03",
            },
        )
        self.session.commit()
        return trabajador

    def _rechazar_si_existe(self, numero_empleado: str, curp: str | None) -> None:
        existente = self.trabajadores.get_by_numero(numero_empleado)
        campo = "numero_empleado"
        if existente is None and curp:
            existente = self.trabajadores.get_by_curp(curp)
            campo = "curp"
        if existente is None:
            return
        cual = "ese número de empleado" if campo == "numero_empleado" else "esa CURP"
        raise TrabajadorExiste(
            f"Ya existe un trabajador con {cual}: {existente.nombre}. ¿Quieres reingresarlo?",
            {
                "regla": "T-02",
                "coincide_por": campo,
                "trabajador": {
                    "id": str(existente.id),
                    "numero_empleado": existente.numero_empleado,
                    "nombre": existente.nombre,
                    "estado": existente.estado,
                },
            },
        )

    @staticmethod
    def _validar_periodo(inicio: date, fin: date) -> None:
        if fin < inicio:
            raise PeriodoInvalido(
                "La fecha de fin no puede ser anterior a la de inicio.",
                {"campo": "fin", "regla": "T-03"},
            )

    # ====================================================== reingreso (T-02)

    def registrar_periodo(
        self, trabajador_id: uuid.UUID, datos: PeriodoCreate, actor: Usuario
    ) -> Trabajador:
        """Reingreso o extensión (T-02): periodo nuevo y regreso a Activo. Los periodos
        anteriores y los pendientes se conservan (B-05)."""
        self._validar_periodo(datos.inicio, datos.fin)
        trabajador = self.trabajadores.get(trabajador_id, para_actualizar=True)
        if trabajador is None:
            raise TrabajadorNoEncontrado()
        anterior = (self.trabajadores.periodos(trabajador.id) or [None])[0]
        puesto = datos.puesto or (anterior.puesto if anterior else None)
        area_obra = datos.area_obra or (anterior.area_obra if anterior else None)
        periodo = self.trabajadores.add_periodo(
            PeriodoContrato(
                trabajador_id=trabajador.id,
                puesto=puesto,
                area_obra=area_obra,
                referencia=datos.referencia,
                inicio=datos.inicio,
                fin=datos.fin,
                creado_por=actor.id,
            )
        )
        estado_antes = trabajador.estado
        trabajador.estado = EstadoTrabajador.ACTIVO
        self.auditoria.registrar(
            usuario_id=actor.id,
            accion="trabajador.periodo",
            entidad="trabajador",
            entidad_id=trabajador.id,
            antes={"estado": estado_antes},
            despues={
                "estado": trabajador.estado,
                "periodo_id": periodo.id,
                "puesto": puesto,
                "area_obra": area_obra,
                "inicio": periodo.inicio,
                "fin": periodo.fin,
                "regla": "T-02",
            },
        )
        self.session.commit()
        return trabajador

    # ========================================================== códigos (T-05)

    def ligar_codigo(
        self, trabajador_id: uuid.UUID, codigo: str | None, actor: Usuario
    ) -> CodigoOut:
        """Liga la credencial escaneada o, sin `codigo`, genera un código propio (T-05).
        Un código que ya es de otra cosa lanza `CodigoRepetido` diciendo de quién es."""
        trabajador = self.obtener(trabajador_id)
        generado = not codigo
        if generado:
            codigo = self._generar_codigo()
        try:
            fila = self.codigos.registrar(codigo, TipoCodigo.TRABAJADOR, trabajador.id)
        except CodigoRepetido as exc:
            self.session.rollback()
            dueno = self._describir_dueno(exc.detalles or {})
            raise CodigoRepetido(
                f"El código {exc.detalles['codigo']} ya está en uso por {dueno}.",
                {**exc.detalles, "regla": "T-05", "descripcion": dueno},
            ) from exc
        self.auditoria.registrar(
            usuario_id=actor.id,
            accion="trabajador.codigo",
            entidad="trabajador",
            entidad_id=trabajador.id,
            despues={"codigo": fila.codigo, "generado": generado, "regla": "T-05"},
        )
        self.session.commit()
        return CodigoOut(codigo=fila.codigo, tipo=fila.tipo, generado=generado)

    def _generar_codigo(self) -> str:
        for _ in range(20):
            candidato = "TRB-" + "".join(secrets.choice(_ALFABETO_CODIGO) for _ in range(8))
            if self.codigos.identificar(candidato) is None:
                return candidato
        raise RuntimeError("No se pudo generar un código libre")  # pragma: no cover

    def _describir_dueno(self, detalles: dict) -> str:
        """Quién es el dueño de un código, en palabras: 'el trabajador X (número)', etc."""
        tipo, ref = detalles.get("tipo"), detalles.get("ref_id")
        try:
            ref_id = uuid.UUID(str(ref))
        except ValueError:
            return "otra cosa"
        if tipo == TipoCodigo.TRABAJADOR:
            otro = self.trabajadores.get(ref_id)
            if otro:
                return f"el trabajador {otro.nombre} (número {otro.numero_empleado})"
        elif tipo == TipoCodigo.ARTICULO:
            articulo = self.session.get(Articulo, ref_id)
            if articulo:
                return f"el artículo {articulo.nombre}"
        elif tipo == TipoCodigo.PIEZA:
            pieza = self.session.get(Pieza, ref_id)
            if pieza:
                articulo = self.session.get(Articulo, pieza.articulo_id)
                return f"una pieza de {articulo.nombre if articulo else 'un artículo'}"
        elif tipo == TipoCodigo.VALE:
            vale = self.session.get(Vale, ref_id)
            if vale:
                return f"el vale {vale.folio}"
        return "otra cosa"

    # ============================================================== foto (T-09)

    def subir_foto(self, trabajador_id: uuid.UUID, contenido: bytes, actor: Usuario) -> FotoOut:
        """Sube o reemplaza la foto (T-09). `ArchivoService` valida tipo por contenido y tamaño.
        Cada foto es un adjunto nuevo; el cambio queda en la auditoría."""
        trabajador = self.trabajadores.get(trabajador_id, para_actualizar=True)
        if trabajador is None:
            raise TrabajadorNoEncontrado()
        adjunto = self.archivos.guardar(
            tipo=TipoAdjunto.FOTO_TRABAJADOR, contenido=contenido, subido_por=actor.id
        )
        anterior = trabajador.foto_adjunto_id
        trabajador.foto_adjunto_id = adjunto.id
        self.auditoria.registrar(
            usuario_id=actor.id,
            accion="trabajador.foto",
            entidad="trabajador",
            entidad_id=trabajador.id,
            antes={"foto_adjunto_id": anterior},
            despues={"foto_adjunto_id": adjunto.id, "sha256": adjunto.sha256, "regla": "T-09"},
        )
        self.session.commit()
        return FotoOut(tiene_foto=True, foto_url=self._foto_url(trabajador))

    def leer_foto(self, trabajador_id: uuid.UUID) -> tuple[str, bytes]:
        """El tipo de contenido y los bytes de la foto. `TrabajadorSinFoto` (404) si no tiene.
        El permiso `trabajadores.ver` lo exige el endpoint."""
        trabajador = self.obtener(trabajador_id)
        if trabajador.foto_adjunto_id is None:
            raise TrabajadorSinFoto()
        adjunto, contenido = self.archivos.leer(trabajador.foto_adjunto_id)
        return adjunto.mime, contenido

    @staticmethod
    def tamano_maximo_foto() -> int:
        return get_settings().archivo_tamano_maximo

    # ============================================================== baja (B-xx)

    def iniciar_baja(self, trabajador_id: uuid.UUID, actor: Usuario) -> BajaOut:
        """B-01: pasa a Baja en proceso (ya no recibe entregas) y responde sus pendientes (B-02).
        Si la baja ya estaba en proceso, solo vuelve a responder los pendientes."""
        trabajador = self.trabajadores.get(trabajador_id, para_actualizar=True)
        if trabajador is None:
            raise TrabajadorNoEncontrado()
        if trabajador.estado == EstadoTrabajador.INACTIVO:
            raise EstadoTrabajadorInvalido(
                "El trabajador ya está inactivo: su baja ya se completó.", {"regla": "T-06"}
            )
        if trabajador.estado == EstadoTrabajador.ACTIVO:
            trabajador.estado = EstadoTrabajador.BAJA_EN_PROCESO
            self.auditoria.registrar(
                usuario_id=actor.id,
                accion="trabajador.baja",
                entidad="trabajador",
                entidad_id=trabajador.id,
                antes={"estado": EstadoTrabajador.ACTIVO},
                despues={"estado": trabajador.estado, "regla": "B-01"},
            )
            self.session.commit()
        pendientes = self.pendientes_de(trabajador.id)
        return BajaOut(
            id=trabajador.id,
            estado=trabajador.estado,
            estado_texto=TEXTO_ESTADO[trabajador.estado],
            pendientes=self._pendientes_out(pendientes, None),
            puede_emitir_no_adeudo=not pendientes,
            reglas=["B-01", "B-02", "B-03"],
        )

    def cancelar_baja(self, trabajador_id: uuid.UUID, actor: Usuario) -> Trabajador:
        """B-07: RH cancela una baja en proceso y el trabajador vuelve a Activo."""
        trabajador = self.trabajadores.get(trabajador_id, para_actualizar=True)
        if trabajador is None:
            raise TrabajadorNoEncontrado()
        if trabajador.estado != EstadoTrabajador.BAJA_EN_PROCESO:
            raise EstadoTrabajadorInvalido(
                "Solo se puede cancelar una baja que está en proceso.", {"regla": "B-07"}
            )
        trabajador.estado = EstadoTrabajador.ACTIVO
        self.auditoria.registrar(
            usuario_id=actor.id,
            accion="trabajador.baja_cancelada",
            entidad="trabajador",
            entidad_id=trabajador.id,
            antes={"estado": EstadoTrabajador.BAJA_EN_PROCESO},
            despues={"estado": trabajador.estado, "regla": "B-07"},
        )
        self.session.commit()
        return trabajador

    # ================================================================ consultas

    def ficha(self, trabajador_id: uuid.UUID, actor: Usuario) -> FichaOut:
        return self.construir_ficha(self.obtener(trabajador_id), actor)

    def construir_ficha(self, trabajador: Trabajador, actor: Usuario) -> FichaOut:
        """Ficha completa. CURP y NSS solo con `trabajadores.ver_datos_personales` (RG-13): sin
        el permiso los campos ni se asignan, y la respuesta no los incluye."""
        periodos = self.trabajadores.periodos(trabajador.id)
        pendientes = self.pendientes_de(trabajador.id)
        breve = self._ficha_breve(trabajador, actor, periodos, pendientes)
        periodo = elegir_periodo(periodos, hoy_mx())
        situacion = self.trabajadores.situacion_de(trabajador.id)
        campos: dict = {
            **breve.model_dump(),
            "periodo": PeriodoOut.model_validate(periodo) if periodo else None,
            "periodos": [PeriodoOut.model_validate(p) for p in periodos],
            "situacion": situacion,
            "situacion_texto": TEXTO_SITUACION[situacion],
            "tallas": trabajador.tallas,
            "codigos": [
                c.codigo for c in self.codigos.codigos_de(TipoCodigo.TRABAJADOR, trabajador.id)
            ],
        }
        if self.acceso.tiene_permiso(actor, P.TRABAJADORES_VER_DATOS_PERSONALES):
            campos["curp"] = trabajador.curp
            campos["nss"] = trabajador.nss
        return FichaOut(**campos)

    def listar(
        self, filtros: FiltrosTrabajadores, *, limit: int, offset: int
    ) -> tuple[list[TrabajadorListItem], int]:
        """Lista con vigencia y situación (T-07, T-08, B-09). Sin CURP ni NSS."""
        filas, total = self.trabajadores.listar(
            q=filtros.q, situacion=filtros.situacion, limit=limit, offset=offset
        )
        periodos = self.trabajadores.periodos_de([f.trabajador.id for f in filas])
        hoy = hoy_mx()
        elementos = []
        for fila in filas:
            t = fila.trabajador
            lista = periodos.get(t.id, [])
            periodo = elegir_periodo(lista, hoy)
            vigencia = calcular_vigencia(t.estado, lista, hoy)
            if fila.con_pendientes:
                situacion = Situacion.CON_PENDIENTES
            elif fila.no_adeudo_emitido:
                situacion = Situacion.NO_ADEUDO_EMITIDO
            else:
                situacion = Situacion.SIN_PENDIENTES
            elementos.append(
                TrabajadorListItem(
                    id=t.id,
                    numero_empleado=t.numero_empleado,
                    nombre=t.nombre,
                    estado=t.estado,
                    estado_texto=TEXTO_ESTADO[t.estado],
                    puesto=periodo.puesto if periodo else None,
                    area_obra=periodo.area_obra if periodo else None,
                    periodo_inicio=periodo.inicio if periodo else None,
                    periodo_fin=periodo.fin if periodo else None,
                    vigencia=VigenciaOut(**vars(vigencia)),
                    situacion=situacion,
                    situacion_texto=TEXTO_SITUACION[situacion],
                    tiene_foto=t.foto_adjunto_id is not None,
                )
            )
        return elementos, total

    # ================================================================== ayudas

    def _ficha_breve(
        self,
        trabajador: Trabajador,
        actor: Usuario,
        periodos: list[PeriodoContrato],
        pendientes: list[Pendiente],
    ) -> FichaBreveOut:
        hoy = hoy_mx()
        periodo = elegir_periodo(periodos, hoy)
        vigencia = calcular_vigencia(trabajador.estado, periodos, hoy)
        ve_foto = self.acceso.tiene_permiso(actor, P.TRABAJADORES_VER)
        resguardo = self._pendientes_out(pendientes, periodo)
        anteriores = sum(1 for p in resguardo if p.de_periodo_anterior)
        return FichaBreveOut(
            id=trabajador.id,
            numero_empleado=trabajador.numero_empleado,
            nombre=trabajador.nombre,
            estado=trabajador.estado,
            estado_texto=TEXTO_ESTADO[trabajador.estado],
            puesto=periodo.puesto if periodo else None,
            area_obra=periodo.area_obra if periodo else None,
            vigencia=VigenciaOut(**vars(vigencia)),
            tiene_foto=ve_foto and trabajador.foto_adjunto_id is not None,
            foto_url=self._foto_url(trabajador) if ve_foto else None,
            resguardo=resguardo,
            pendientes=ResumenPendientesOut(
                total=len(resguardo),
                de_periodos_anteriores=anteriores,
                regla="E-12" if anteriores else None,
            ),
        )

    @staticmethod
    def _foto_url(trabajador: Trabajador) -> str | None:
        if trabajador.foto_adjunto_id is None:
            return None
        return f"/api/trabajadores/{trabajador.id}/foto"

    @staticmethod
    def _pendientes_out(
        pendientes: list[Pendiente], periodo: PeriodoContrato | None
    ) -> list[PendienteOut]:
        """E-12: un pendiente es de un periodo anterior si se entregó antes de que empezara el
        periodo que rige hoy."""
        salida = []
        for p in pendientes:
            anterior = bool(
                periodo
                and p.entregado_en is not None
                and a_hora_mx(p.entregado_en).date() < periodo.inicio
            )
            salida.append(PendienteOut(**vars(p), de_periodo_anterior=anterior))
        return salida

    @staticmethod
    def _pendiente_json(p: Pendiente) -> dict:
        return {
            "articulo": p.articulo,
            "codigo": p.codigo,
            "cantidad": p.cantidad,
            "folio": p.folio,
            "almacen": p.almacen,
            "entregado_en": p.entregado_en.isoformat() if p.entregado_en else None,
        }
