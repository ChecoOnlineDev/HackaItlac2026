"""PR-01 a PR-07 y PR-13; otros módulos usan asignar_en_transaccion sin commit."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.excepciones import Conflicto, DatosInvalidos, NoEncontrado
from app.core.paginacion import Pagina, Paginacion
from app.core.tiempo import ahora_utc, hoy_mx
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.service import AccesoService
from app.modulos.almacenes.exceptions import AlmacenCerrado
from app.modulos.auditoria.service import AuditoriaService
from app.modulos.proyectos.exceptions import (
    AsignacionRepetida,
    ClaveRepetida,
    ProyectoCerrado,
    ProyectoConVales,
    ProyectoInvalido,
)
from app.modulos.proyectos.models import AsignacionProyecto, Proyecto
from app.modulos.proyectos.repository import ProyectoRepository
from app.modulos.proyectos.schemas import (
    AlmacenRef,
    AsignacionIn,
    AsignacionOut,
    CierreIn,
    CierreOut,
    ProyectoCreate,
    ProyectoOut,
    ProyectoUpdate,
    ReaperturaIn,
    TerminoOut,
)


class ProyectoService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = ProyectoRepository(session)
        self.acceso = AccesoService(session)
        self.auditoria = AuditoriaService(session)

    def situacion(self, p: Proyecto):
        if p.estado == "CERRADO":
            return "CERRADO"
        if p.inicio > hoy_mx():
            return "POR_INICIAR"
        return "FIN_VENCIDO" if p.fin_estimado < hoy_mx() else "VIGENTE"

    def ficha(self, p: Proyecto):
        return ProyectoOut(
            id=p.id,
            clave=p.clave,
            nombre=p.nombre,
            almacen=AlmacenRef.model_validate(self.repository.almacen_ref(p.almacen_id)),
            inicio=p.inicio,
            fin_estimado=p.fin_estimado,
            estado=p.estado,
            situacion=self.situacion(p),
            asignable=p.estado == "ACTIVO" and p.fin_estimado >= hoy_mx(),
            trabajadores_asignados=self.repository.conteo(p.id),
            cerrado_en=p.cerrado_en,
            motivo_cierre=p.motivo_cierre,
            creado_en=p.creado_en,
            aviso=(
                (
                    f"Este proyecto queda en {self.repository.almacen_ref(p.almacen_id).nombre}: "
                    "úsalo para personal general."
                )
                if self.repository.almacen_ref(p.almacen_id).tipo != "PROYECTO"
                else None
            ),
        )

    def _visible(self, p: Proyecto, actor: Usuario):
        return self.acceso.tiene_permiso(actor, "proyectos.asignar") or self.acceso.en_alcance(
            actor, p.almacen_id
        )

    def obtener(self, id, actor=None, *, bloquear=False):
        p = self.repository.get(id, bloquear=bloquear)
        if p is None or (actor is not None and not self._visible(p, actor)):
            raise NoEncontrado("No se encontró el proyecto.")
        return p

    def listar(
        self,
        actor,
        pagina: Paginacion,
        *,
        almacen_id=None,
        situacion=None,
        q=None,
        asignables=False,
        por_vencer=False,
    ):
        alcance = (
            None
            if self.acceso.tiene_permiso(actor, "proyectos.asignar")
            else self.acceso.alcance_del_usuario(actor.id)
        )
        proyectos, total = self.repository.listar(
            pagina,
            hoy_mx(),
            alcance=alcance,
            almacen_id=almacen_id,
            situacion=situacion,
            q=q,
            asignables=asignables,
            por_vencer=por_vencer,
        )
        return Pagina(elementos=[self.ficha(p) for p in proyectos], total=total)

    def _fechas(self, inicio, fin):
        if fin < inicio:
            raise DatosInvalidos(
                "El fin estimado no puede ser anterior al inicio.",
                [{"campo": "fin_estimado", "regla": "PR-02"}],
            )

    def _almacen(self, id):
        a = self.repository.almacen(id)
        if a is None:
            raise NoEncontrado("No se encontró el almacén.")
        if a.estado != "ACTIVO":
            error = AlmacenCerrado(a)
            error.detalles["regla"] = "PR-01"
            raise error
        return a

    def _registrar(self, actor, accion, p, antes=None):
        self.auditoria.registrar(
            usuario_id=actor.id,
            accion=accion,
            entidad="proyecto",
            entidad_id=p.id,
            antes=antes,
            despues=self.ficha(p).model_dump(mode="json"),
        )

    def crear(self, datos: ProyectoCreate, actor):
        self.acceso.exigir_permiso(actor, "proyectos.administrar")
        self._fechas(datos.inicio, datos.fin_estimado)
        try:
            self._almacen(datos.almacen_id)
            if self.repository.clave_existe(datos.clave):
                raise ClaveRepetida()
            p = self.repository.add(Proyecto(**datos.model_dump(), creado_por=actor.id))
            self._registrar(actor, "proyecto.crear", p)
            self.session.commit()
            return self.ficha(p)
        except IntegrityError as e:
            self.session.rollback()
            if "uq_proyecto_clave" in str(e.orig):
                raise ClaveRepetida() from e
            raise
        except Exception:
            self.session.rollback()
            raise

    def editar(self, id, datos: ProyectoUpdate, actor):
        self.acceso.exigir_permiso(actor, "proyectos.administrar")
        try:
            p = self.obtener(id, actor, bloquear=True)
            if p.estado == "CERRADO":
                raise ProyectoCerrado()
            cambios = datos.model_dump(exclude_unset=True)
            if any(v is None for v in cambios.values()):
                raise DatosInvalidos(
                    "Los campos del proyecto no pueden quedar vacíos.", [{"regla": "PR-03"}]
                )
            if any(
                k in cambios and cambios[k] != getattr(p, k) for k in ("clave", "almacen_id")
            ) and self.repository.tiene_vales(p.id):
                raise ProyectoConVales()
            self._fechas(
                cambios.get("inicio", p.inicio), cambios.get("fin_estimado", p.fin_estimado)
            )
            if "almacen_id" in cambios:
                self._almacen(cambios["almacen_id"])
            if "clave" in cambios and self.repository.clave_existe(cambios["clave"], p.id):
                raise ClaveRepetida()
            antes = self.ficha(p).model_dump(mode="json")
            for k, v in cambios.items():
                setattr(p, k, v)
            self.session.flush()
            self._registrar(actor, "proyecto.editar", p, antes)
            self.session.commit()
            return self.ficha(p)
        except IntegrityError as e:
            self.session.rollback()
            if "uq_proyecto_clave" in str(e.orig):
                raise ClaveRepetida() from e
            raise
        except Exception:
            self.session.rollback()
            raise

    def _terminar(self, a, actor):
        a.terminada_en = ahora_utc()
        a.terminada_por = actor.id
        a.fin = hoy_mx()
        self.auditoria.registrar(
            usuario_id=actor.id,
            accion="asignacion.terminar",
            entidad="asignacion_proyecto",
            entidad_id=a.id,
            despues={"fin": a.fin, "terminada_en": a.terminada_en},
        )

    def cerrar(self, id, datos: CierreIn, actor):
        self.acceso.exigir_permiso(actor, "proyectos.administrar")
        try:
            p = self.obtener(id, actor, bloquear=True)
            if p.estado == "CERRADO":
                raise Conflicto("El proyecto ya está cerrado.", [{"regla": "PR-04"}])
            antes = self.ficha(p).model_dump(mode="json")
            asignaciones = self.repository.activas(p.id)
            terminadas = []
            for a in asignaciones:
                self.repository.trabajador(a.trabajador_id, bloquear=True)
                self.repository.refrescar_asignacion(a)
                if a.terminada_en is None:
                    self._terminar(a, actor)
                    terminadas.append(a)
            asignaciones = terminadas
            p.estado, p.cerrado_en, p.motivo_cierre = "CERRADO", ahora_utc(), datos.motivo
            self.session.flush()
            sin_proyecto = sum(
                not any(
                    a.terminada_en is None for a in self.repository.asignaciones(t, bloquear=True)
                )
                for t in {a.trabajador_id for a in asignaciones}
            )
            self._registrar(actor, "proyecto.cerrar", p, antes)
            self.session.commit()
            return CierreOut(
                **self.ficha(p).model_dump(),
                asignaciones_terminadas=len(asignaciones),
                trabajadores_sin_proyecto=sin_proyecto,
            )
        except Exception:
            self.session.rollback()
            raise

    def reabrir(self, id, datos: ReaperturaIn, actor):
        self.acceso.exigir_permiso(actor, "proyectos.administrar")
        try:
            p = self.obtener(id, actor, bloquear=True)
            if p.estado == "ACTIVO":
                raise Conflicto("El proyecto ya está abierto.", [{"regla": "PR-05"}])
            self._almacen(p.almacen_id)
            fin = datos.fin_estimado or p.fin_estimado
            if fin < hoy_mx():
                raise DatosInvalidos(
                    "Indica un fin estimado igual o posterior a hoy.",
                    [{"campo": "fin_estimado", "regla": "PR-05"}],
                )
            self._fechas(p.inicio, fin)
            antes = self.ficha(p).model_dump(mode="json")
            p.estado, p.fin_estimado, p.cerrado_en, p.motivo_cierre = "ACTIVO", fin, None, None
            self.session.flush()
            self._registrar(actor, "proyecto.reabrir", p, antes)
            self.session.commit()
            return self.ficha(p)
        except Exception:
            self.session.rollback()
            raise

    def asignaciones_del_trabajador(self, id, *, bloquear=False):
        if self.repository.trabajador(id) is None:
            raise NoEncontrado("No se encontró el trabajador.")
        return [
            AsignacionOut(
                id=a.id,
                asignacion_id=a.id,
                proyecto=self.ficha(self.obtener(a.proyecto_id)),
                principal=a.principal,
                inicio=a.inicio,
                fin=a.fin,
                creado_en=a.creado_en,
                terminada_en=a.terminada_en,
            )
            for a in self.repository.asignaciones(id, bloquear=bloquear)
        ]

    def proyectos_activos_del_trabajador(self, id, *, bloquear=False):
        return [
            a
            for a in self.asignaciones_del_trabajador(id, bloquear=bloquear)
            if a.terminada_en is None and a.proyecto.estado == "ACTIVO"
        ]

    def validar_asignable(self, id, *, bloquear=False):
        p = self.repository.get(id, bloquear=bloquear)
        if p is None or p.estado != "ACTIVO" or p.fin_estimado < hoy_mx():
            raise ProyectoInvalido(detalles=[{"campo": "proyecto_id", "regla": "PR-11"}])
        return p

    def asignar_en_transaccion(self, id, datos: AsignacionIn, actor):
        """PR-11/13. El llamador controla commit cuando crea trabajador o contrato."""
        self.acceso.exigir_permiso(actor, "proyectos.asignar")
        p = self.repository.get(datos.proyecto_id, bloquear=True)
        if p is None:
            raise ProyectoInvalido(detalles=[{"regla": "PR-13"}])
        if p.estado != "ACTIVO" or p.fin_estimado < hoy_mx():
            raise ProyectoInvalido(detalles=[{"regla": "PR-13"}])
        t = self.repository.trabajador(id, bloquear=True)
        if t is None:
            raise NoEncontrado("No se encontró el trabajador.")
        if t.estado == "INACTIVO":
            raise Conflicto("Reingresa al trabajador antes de asignarlo.", [{"regla": "PR-13"}])
        activas = [
            a for a in self.repository.asignaciones(id, bloquear=True) if a.terminada_en is None
        ]
        if any(a.proyecto_id == p.id for a in activas):
            raise AsignacionRepetida(detalles=[{"regla": "PR-13"}])
        anterior = None
        if datos.reemplaza_asignacion_id:
            anterior = next((a for a in activas if a.id == datos.reemplaza_asignacion_id), None)
            if anterior is None:
                raise Conflicto(
                    "La asignación que intentas cambiar ya terminó.", [{"regla": "PR-13"}]
                )
            self._terminar(anterior, actor)
            self.session.flush()
        if anterior is None and datos.principal is True and any(a.principal for a in activas):
            raise Conflicto(
                "El trabajador ya tiene un proyecto principal. Cambia esa asignación.",
                [{"campo": "principal", "regla": "PR-13"}],
            )
        principal = (
            anterior.principal
            if anterior
            else (datos.principal is not False and not any(a.principal for a in activas))
        )
        a = self.repository.add(
            AsignacionProyecto(
                trabajador_id=id,
                proyecto_id=p.id,
                inicio=datos.inicio or hoy_mx(),
                principal=principal,
                creado_por=actor.id,
            )
        )
        self.auditoria.registrar(
            usuario_id=actor.id,
            accion="asignacion.crear",
            entidad="asignacion_proyecto",
            entidad_id=a.id,
            despues={"trabajador_id": id, "proyecto_id": p.id, "principal": principal},
        )
        return a

    def asignar(self, id, datos, actor):
        try:
            self.asignar_en_transaccion(id, datos, actor)
            self.session.commit()
            return self.asignaciones_del_trabajador(id)
        except IntegrityError as e:
            self.session.rollback()
            if "uq_asignacion_proyecto_activa" in str(e.orig):
                raise AsignacionRepetida() from e
            raise
        except Exception:
            self.session.rollback()
            raise

    def terminar(self, id, asignacion_id, actor):
        self.acceso.exigir_permiso(actor, "proyectos.asignar")
        try:
            # Siempre proyecto antes que trabajador, igual que asignar y cerrar.
            a = self.repository.asignacion(asignacion_id)
            if a is None or a.trabajador_id != id:
                raise NoEncontrado("No se encontró la asignación.")
            self.obtener(a.proyecto_id, bloquear=True)
            self.repository.trabajador(id, bloquear=True)
            self.repository.refrescar_asignacion(a)
            if a.terminada_en is not None:
                raise Conflicto("La asignación ya terminó.", [{"regla": "PR-13"}])
            self._terminar(a, actor)
            self.session.flush()
            self.session.commit()
            asignaciones = self.asignaciones_del_trabajador(id)
            return TerminoOut(
                asignaciones=asignaciones,
                queda_sin_proyecto=not any(a.terminada_en is None for a in asignaciones),
            )
        except Exception:
            self.session.rollback()
            raise
