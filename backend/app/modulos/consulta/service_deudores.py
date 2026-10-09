"""DU-03: alcance por almacén; RH lee deudas sin ganar permiso de vales."""

from collections import defaultdict
from datetime import UTC

from app.core.tiempo import a_hora_mx
from app.modulos.acceso.permisos import P
from app.modulos.acceso.service import AccesoService
from app.modulos.consulta.exportacion import construir_csv, respuesta_csv
from app.modulos.consulta.repository_deudores import DeudoresRepository
from app.modulos.trabajadores.service import TrabajadorService


class DeudoresService:
    def __init__(self, session):
        self.session = session
        self.repository = DeudoresRepository(session)
        self.acceso = AccesoService(session)
        self.trabajadores = TrabajadorService(session)

    def _alcance(self, usuario):
        if self.acceso.tiene_permiso(usuario, P.TRABAJADORES_ADMINISTRAR):
            return None
        return self.acceso.alcance_del_usuario(usuario.id)

    @staticmethod
    def _utc(fecha):
        return fecha.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z") if fecha else None

    def _renglon(self, f, usuario):
        puede_vale = self.acceso.en_alcance(usuario, f.almacen_id)
        return {
            "articulo": {
                "id": f.articulo_id,
                "codigo": f.articulo_codigo,
                "nombre": f.articulo_nombre,
                "marca": f.marca,
            },
            "pieza": {
                "id": f.pieza_id,
                "codigo": f.pieza_codigo,
                "numero_serie": f.numero_serie,
                "serie_pendiente": not f.numero_serie,
            }
            if f.pieza_id
            else None,
            "cantidad": int(f.cantidad),
            "desde": self._utc(f.desde),
            "vale": {"id": f.vale_id if puede_vale else None, "folio": f.folio},
            "proyecto": {
                "id": f.proyecto_id,
                "nombre": f.proyecto_nombre,
                "estado": f.proyecto_estado,
            }
            if f.proyecto_id
            else None,
            "almacen": {
                "id": f.almacen_id,
                "clave": f.almacen_clave,
                "nombre": f.almacen_nombre,
                "estado": f.almacen_estado,
            },
            "alto_valor": bool(f.alto_valor),
            "requiere_inspeccion": f.requiere_inspeccion,
        }

    def consultar(self, usuario, filtros, pagina=1, tamano=50, formato="json"):
        alcance = self._alcance(usuario)
        filas, detalles, total, otros = self.repository.listado(
            alcance, filtros, pagina, tamano, formato == "csv"
        )
        por_trabajador = defaultdict(list)
        for fila in detalles:
            por_trabajador[fila.trabajador_id].append(fila)
        elementos = []
        for fila in filas:
            trabajador = self.trabajadores.obtener(fila.trabajador_id)
            motivo = self.trabajadores.motivo_no_vigente(trabajador)
            periodo = self.trabajadores.periodo_vigente(trabajador)
            deuda_anterior = bool(
                periodo and fila.desde and a_hora_mx(fila.desde).date() < periodo.inicio
            )
            proyectos = {
                d.proyecto_id: {
                    "id": d.proyecto_id,
                    "nombre": d.proyecto_nombre,
                    "estado": d.proyecto_estado,
                }
                for d in por_trabajador[fila.trabajador_id]
                if d.proyecto_id
            }
            elementos.append(
                {
                    "trabajador": {
                        "id": fila.trabajador_id,
                        "nombre": fila.trabajador_nombre,
                        "numero_empleado": fila.numero_empleado,
                        "tiene_foto": fila.foto_adjunto_id is not None,
                    },
                    "vigente": bool(fila.vigente),
                    "aviso": motivo + " Hay que recuperar lo que tiene o renovar su contrato."
                    if motivo
                    else None,
                    "de_periodo_anterior": deuda_anterior,
                    "aviso_periodo": "Viene de un contrato anterior." if deuda_anterior else None,
                    "proyectos": list(proyectos.values()),
                    "piezas": int(fila.piezas),
                    "unidades": int(fila.unidades),
                    "alto_valor": int(fila.alto_valor),
                    "desde": self._utc(fila.desde),
                    "otros_almacenes": int(otros.get(fila.trabajador_id, 0)),
                    "renglones": [
                        self._renglon(d, usuario) for d in por_trabajador[fila.trabajador_id]
                    ]
                    if filtros.get("trabajador_id")
                    else None,
                }
            )
        if formato == "csv":
            contenido = construir_csv(
                (
                    "Trabajador",
                    "Número",
                    "Artículo",
                    "Pieza",
                    "Serie",
                    "Cantidad",
                    "Desde",
                    "Folio",
                    "Proyecto",
                    "Almacén",
                    "Alto valor",
                ),
                (
                    (
                        d.trabajador_nombre,
                        d.numero_empleado,
                        d.articulo_nombre,
                        d.pieza_codigo,
                        d.numero_serie,
                        d.cantidad,
                        self._utc(d.desde),
                        d.folio,
                        d.proyecto_nombre or "Sin proyecto",
                        d.almacen_nombre,
                        "Sí" if d.alto_valor else "No",
                    )
                    for d in detalles
                ),
            )
            return respuesta_csv(contenido, "deudores.csv")
        return {
            "elementos": elementos,
            "total": total,
            "sin_registros": total == 0,
            "mensaje": "No hay trabajadores con adeudo." if not total else None,
            "resumen": self.repository.tarjetas(alcance, filtros),
        }

    def resumen(self, usuario, filtros, formato="json"):
        datos = self.repository.resumen(self._alcance(usuario), filtros)
        if formato == "csv":
            filas = []
            for tipo, lista in datos.items():
                for r in lista:
                    filas.append(
                        (
                            tipo,
                            r.get("almacen_nombre") or r.get("proyecto_nombre") or "Sin proyecto",
                            r["trabajadores"],
                            r["piezas"],
                            r["unidades"],
                            r["alto_valor"],
                            r["no_vigentes"],
                        )
                    )
            return respuesta_csv(
                construir_csv(
                    (
                        "Agrupación",
                        "Nombre",
                        "Trabajadores",
                        "Piezas",
                        "Unidades",
                        "Alto valor",
                        "No vigentes",
                    ),
                    filas,
                ),
                "deudores-resumen.csv",
            )
        return datos
