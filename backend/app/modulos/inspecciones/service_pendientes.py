"""Lectura de inspecciones pendientes, con alcance asignado y acciones del servidor."""

from app.core.excepciones import NoEncontrado
from app.modulos.acceso.permisos import P
from app.modulos.acceso.service import AccesoService
from app.modulos.almacenes.models import TipoUbicacion
from app.modulos.inspecciones.repository_pendientes import PendientesRepository


class PendientesService:
    def __init__(self, session):
        self.session = session
        self.acceso = AccesoService(session)
        self.repository = PendientesRepository(session)

    def consultar(self, usuario, filtros=None, pagina=1, tamano=50, solo_contar=False):
        filtros = filtros or {}
        alcance = self.acceso.alcance_del_usuario(usuario.id)
        if (
            filtros.get("almacen_id")
            and alcance is not None
            and filtros["almacen_id"] not in alcance
        ):
            raise NoEncontrado()
        conteos, filas, total = self.repository.consultar(
            alcance, filtros, pagina, tamano, solo_contar
        )
        if solo_contar:
            return {"conteos": conteos}
        elementos = []
        for (
            pieza,
            articulo,
            categoria,
            ubicacion,
            almacen,
            trabajador,
            vale,
            movimiento,
            aviso,
            restantes,
        ) in filas:
            accion = "NINGUNA"
            if ubicacion.tipo == TipoUbicacion.TRABAJADOR:
                accion = "PEDIR_DEVOLUCION"
            elif ubicacion.tipo == TipoUbicacion.ALMACEN and self.acceso.tiene_permiso(
                usuario, P.PIEZAS_INSPECCIONAR
            ):
                accion = "INSPECCIONAR"
            visible_vale = vale and self.acceso.en_alcance(usuario, vale.almacen_id)
            elementos.append(
                {
                    "pieza": {
                        "id": pieza.id,
                        "codigo": pieza.codigo,
                        "numero_serie": pieza.numero_serie,
                        "serie_pendiente": not pieza.numero_serie,
                        "estado": pieza.estado,
                    },
                    "articulo": {
                        "id": articulo.id,
                        "codigo": articulo.codigo,
                        "nombre": articulo.nombre,
                        "categoria": {"id": categoria.id, "nombre": categoria.nombre},
                    },
                    "vigente_hasta": pieza.inspeccion_vigente_hasta,
                    "dias_restantes": restantes,
                    "dias_aviso": int(aviso),
                    "ubicacion": {
                        "tipo": "EN_TRANSITO"
                        if ubicacion.virtual == "EN_TRANSITO"
                        else ubicacion.tipo,
                        "almacen": {"id": almacen.id, "nombre": almacen.nombre}
                        if almacen
                        else None,
                        "trabajador": {
                            "id": trabajador.id,
                            "nombre": trabajador.nombre,
                            "numero_empleado": trabajador.numero_empleado,
                        }
                        if trabajador
                        else None,
                        "desde": movimiento.creado_en if movimiento else None,
                        "folio": vale.folio if visible_vale else None,
                        "vale_id": vale.id if visible_vale else None,
                        "destino": {"id": vale.destino_almacen_id}
                        if vale and vale.destino_almacen_id and ubicacion.virtual == "EN_TRANSITO"
                        else None,
                    },
                    "accion": accion,
                }
            )
        return {"conteos": conteos, "elementos": elementos, "total": total}

    def contar_resumen(self, usuario, almacen_id=None):
        return self.consultar(usuario, {"almacen_id": almacen_id}, solo_contar=True)["conteos"]
