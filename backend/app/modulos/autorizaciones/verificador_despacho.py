"""Clasifica el despacho con la evaluación real; no toma decisiones del cliente."""

from app.modulos.autorizaciones.exceptions import RenglonNoAutorizable
from app.modulos.autorizaciones.repository import AutorizacionRepository
from app.modulos.autorizaciones.schemas import RenglonSolicitud
from app.modulos.proyectos.exceptions import ProyectoInvalido, ProyectoRequerido
from app.modulos.proyectos.service import ProyectoService


def evaluar_solicitud(session, usuario, almacen_id, datos):
    # Importación local: movimientos depende de autorizaciones para confirmar.
    from app.modulos.movimientos.models import Nivel
    from app.modulos.movimientos.service import MovimientoService

    evaluacion = MovimientoService(session).evaluar_para_autorizacion(
        usuario, almacen_id, datos.trabajador_id, [(r.codigo, r.cantidad) for r in datos.renglones]
    )
    rojo = next((m for m in evaluacion.motivos_vale if m.nivel == Nivel.ROJO), None)
    if rojo:
        raise RenglonNoAutorizable(rojo.mensaje, {"regla": rojo.regla, "nivel": "ROJO"})
    repository = AutorizacionRepository(session)
    salida = []
    for indice, r in enumerate(evaluacion.renglones, 1):
        if r.nivel == Nivel.ROJO:
            motivo = next(m for m in r.motivos if m.nivel == Nivel.ROJO)
            raise RenglonNoAutorizable(
                motivo.mensaje,
                {
                    "codigo": r.codigo,
                    "regla": motivo.regla,
                    "nivel": "ROJO",
                    "motivos": [{"regla": m.regla, "mensaje": m.mensaje} for m in r.motivos],
                },
            )
        epp = repository.es_epp(r.articulo_id)
        naranja = r.nivel == Nivel.NARANJA
        motivo = next((m for m in r.motivos if m.nivel == Nivel.NARANJA), None)
        salida.append(
            RenglonSolicitud(
                renglon=indice,
                codigo=r.codigo,
                cantidad=r.cantidad,
                articulo_id=r.articulo_id,
                articulo=(r.articulo or {}).get("nombre"),
                clase="EPP" if epp else "EXCEDENTE" if naranja else "CONTEXTO",
                incluye_excedente=naranja,
                observacion=datos.renglones[indice - 1].observacion,
                regla=motivo.regla if motivo else "DE-01" if epp else "DE-04",
                mensaje=motivo.mensaje[:255] if motivo else None,
                limite=r.extra.get("limite"),
                tiene=r.extra.get("tiene"),
                excedente=r.extra.get("excedente") or 0,
                autorizable=epp or naranja,
            )
        )
    proyectos = ProyectoService(session).proyectos_activos_del_trabajador(datos.trabajador_id)
    elegido = next((a.proyecto for a in proyectos if a.proyecto.id == datos.proyecto_id), None)
    if datos.proyecto_id and elegido is None:
        raise ProyectoInvalido(detalles=[{"regla": "PR-09"}])
    if not datos.proyecto_id and len(proyectos) > 1:
        raise ProyectoRequerido(detalles=[{"regla": "PR-09"}])
    if elegido is None and len(proyectos) == 1:
        elegido = proyectos[0].proyecto
    proyecto = (
        {"id": str(elegido.id), "clave": elegido.clave, "nombre": elegido.nombre}
        if elegido
        else None
    )
    return salida, proyecto
