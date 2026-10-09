"""BT-01…08: lectura por operación, DTO seguros y relaciones ocultas fuera del alcance."""

from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.core.tiempo import hoy_mx
from app.modulos.acceso.permisos import P
from app.modulos.acceso.service import AccesoService
from app.modulos.almacenes.models import Almacen, Ubicacion
from app.modulos.consulta.exportacion import construir_csv, respuesta_csv
from app.modulos.consulta.repository_bitacora import BitacoraRepository
from app.modulos.consulta.schemas import TEXTO_TIPO_VALE
from app.modulos.consulta.service import rango_utc
from app.modulos.movimientos.exceptions import ValeNoEncontrado
from app.modulos.movimientos.models import Movimiento
from app.modulos.movimientos.repository import MovimientoRepository
from app.modulos.movimientos.schemas import RenglonValeOut, UbicacionOut
from app.modulos.proyectos.models import Proyecto
from app.modulos.trabajadores.models import Trabajador


def referencia(obj, campos=("id", "nombre")):
    return {c: getattr(obj, c) for c in campos} if obj else None


def pagina_salida(elementos, total):
    return {
        "elementos": elementos,
        "total": total,
        "sin_registros": total == 0,
        "mensaje": "No hay vales con esos filtros" if total == 0 else None,
    }


class BitacoraService:
    def __init__(self, session):
        self.session = session
        self.repository = BitacoraRepository(session)
        self.vales = MovimientoRepository(session)
        self.acceso = AccesoService(session)

    def _vale(self, id, usuario):
        vale = self.vales.vale(id)
        if vale is None or not self.acceso.en_alcance(
            usuario, vale.almacen_id, vale.destino_almacen_id
        ):
            raise ValeNoEncontrado()
        return vale

    def consultar(self, usuario, f, pagina=1, tamano=25, formato="json"):
        ids = self.acceso.alcance_del_usuario(usuario.id)
        if f.almacen_id and ids is not None and f.almacen_id not in ids:
            if formato == "csv":
                return respuesta_csv(
                    construir_csv(
                        [
                            "Fecha",
                            "Folio",
                            "Tipo",
                            "Almacén",
                            "Responsable",
                            "Renglones",
                            "Unidades",
                            "Estado",
                        ],
                        [],
                    ),
                    "bitacora.csv",
                )
            return pagina_salida([], 0)
        if f.desde is None and f.hasta is None and f.lote_id is None:
            f = f.model_copy(update={"desde": hoy_mx() - timedelta(days=6), "hasta": hoy_mx()})
        inicio, fin = rango_utc(f.desde, f.hasta)
        vales, total = self.repository.pagina(
            f,
            ids,
            usuario.id,
            inicio,
            fin,
            1 if formato == "csv" else pagina,
            1000000 if formato == "csv" else tamano,
        )
        stats = self.repository.totales([v.id for v in vales], f)
        filas = [self._fila(v, stats.get(v.id), usuario, f) for v in vales]
        if formato == "csv":
            return respuesta_csv(
                construir_csv(
                    [
                        "Fecha",
                        "Folio",
                        "Tipo",
                        "Almacén",
                        "Responsable",
                        "Renglones",
                        "Unidades",
                        "Estado",
                    ],
                    (
                        [
                            datetime.fromisoformat(v["creado_en"]),
                            v["folio"],
                            v["tipo_texto"],
                            v["almacen"]["nombre"],
                            v["responsable"]["nombre"],
                            v["renglones"],
                            v["unidades"],
                            v["estado"],
                        ]
                        for v in filas
                    ),
                ),
                "bitacora.csv",
            )
        agrupados = defaultdict(list)
        for fila in filas:
            agrupados[fila["lote_id"] or fila["id"]].append(fila)
        elementos = []
        for grupo in agrupados.values():
            if len(grupo) == 1:
                elementos.append(grupo[0])
                continue
            primero = grupo[0]
            cancelados = sum(v["estado"] == "CANCELADO" for v in grupo)
            elemento = {
                k: primero[k]
                for k in (
                    "lote_id",
                    "origen_lote",
                    "creado_en",
                    "tipo",
                    "tipo_texto",
                    "almacen",
                    "responsable",
                    "direccion",
                    "direccion_texto",
                )
            }
            elemento.update(
                clase="LOTE",
                vales=sorted(grupo, key=lambda v: v["folio"]),
                renglones=sum(v["renglones"] for v in grupo),
                unidades=sum(v["unidades"] for v in grupo),
                coincidencias=sum(v["coincidencias"] or 0 for v in grupo)
                if f.articulo_id or len(f.q.strip()) >= 2
                else None,
                estado_texto="Cancelado"
                if cancelados == len(grupo)
                else f"{cancelados} de {len(grupo)} cancelado"
                if cancelados
                else "Emitido",
            )
            elementos.append(elemento)
        elementos.sort(key=lambda v: v["creado_en"], reverse=True)
        return pagina_salida(elementos, total)

    def _relacion(self, relacionado, usuario, texto):
        visible = self.acceso.en_alcance(
            usuario, relacionado.almacen_id, relacionado.destino_almacen_id
        )
        return {
            "id": relacionado.id if visible else None,
            "folio": relacionado.folio if visible else None,
            "creado_en": relacionado.creado_en.isoformat(timespec="seconds") + "Z",
            "texto": texto
            if visible
            else f"Movimiento en otro almacén el {relacionado.creado_en:%d/%m/%Y}",
            "relacion": relacionado.tipo,
        }

    def _fila(self, vale, stats, usuario, filtros):
        almacen = self.session.get(Almacen, vale.almacen_id)
        destino = (
            self.session.get(Almacen, vale.destino_almacen_id) if vale.destino_almacen_id else None
        )
        trabajador = (
            self.session.get(Trabajador, vale.trabajador_id) if vale.trabajador_id else None
        )
        origen = self.vales.vale(vale.vale_origen_id) if vale.vale_origen_id else None
        cancelacion = self.vales.cancelacion_de(vale.id) if vale.estado == "CANCELADO" else None
        direccion = None
        if filtros.almacen_id and stats and stats.renglones:
            if vale.tipo == "TRASPASO" and vale.destino_almacen_id == filtros.almacen_id:
                direccion = (
                    "EN_CAMINO"
                    if vale.estado in ("EN_TRANSITO", "RECIBIDO_CON_DIFERENCIAS")
                    else None
                )
            else:
                entrada = self.session.scalar(
                    select(Movimiento.id)
                    .join(Ubicacion, Ubicacion.id == Movimiento.destino_id)
                    .where(
                        Movimiento.vale_id == vale.id, Ubicacion.almacen_id == filtros.almacen_id
                    )
                    .limit(1)
                )
                direccion = "ENTRADA" if entrada else "SALIDA"
        titulares = self.session.scalar(
            select(func.count(func.distinct(Movimiento.trabajador_id))).where(
                Movimiento.vale_id == vale.id, Movimiento.trabajador_id.is_not(None)
            )
        )
        return {
            "clase": "VALE",
            "id": vale.id,
            "folio": vale.folio,
            "lote_id": vale.lote_id,
            "origen_lote": "TRASPASO_EXCEL"
            if vale.tipo == "TRASPASO" and vale.lote_id
            else "IMPORTACION"
            if vale.lote_id
            else None,
            "tipo": vale.tipo,
            "tipo_texto": TEXTO_TIPO_VALE.get(vale.tipo, vale.tipo),
            "estado": vale.estado,
            "estado_texto": "Cancelado"
            if vale.estado == "CANCELADO"
            else vale.estado.replace("_", " ").capitalize(),
            "creado_en": vale.creado_en.isoformat(timespec="seconds") + "Z",
            "almacen": referencia(almacen, ("id", "clave", "nombre")),
            "destino": referencia(destino, ("id", "clave", "nombre")),
            "responsable": referencia(self.vales.usuario(vale.responsable_id)),
            "trabajador": referencia(trabajador, ("id", "numero_empleado", "nombre")),
            "tiene_varios_titulares": trabajador is None and (titulares or 0) > 1,
            "titulares": int(titulares or 0),
            "archivo_repetido": self.repository.archivo_repetido(vale.lote_id)
            if vale.lote_id
            else False,
            "proyecto": referencia(self.session.get(Proyecto, vale.proyecto_id))
            if vale.proyecto_id
            else None,
            "renglones": stats.renglones if stats else 0,
            "unidades": int(stats.unidades) if stats else 0,
            "coincidencias": int(stats.coincidencias)
            if stats and (filtros.articulo_id or len(filtros.q.strip()) >= 2)
            else None,
            "direccion": direccion,
            "direccion_texto": {
                "ENTRADA": "Entrada",
                "SALIDA": "Salida",
                "EN_CAMINO": "En camino",
            }.get(direccion),
            "vale_origen": self._relacion(origen, usuario, "Vale original") if origen else None,
            "cancelacion": self._relacion(cancelacion, usuario, "Cancelación")
            if cancelacion
            else None,
            "capturado_sin_conexion": False,
            "capturado_en": None,
        }

    def renglones(self, id, usuario, q="", pagina=1, tamano=50):
        self._vale(id, usuario)
        filas, total = self.repository.renglones(id, q, pagina, tamano)
        lugares = self.vales.ubicaciones(
            [id for m, _, _ in filas for id in (m.origen_id, m.destino_id)]
        )

        def lugar(id):
            ub, nombre, clave = lugares[id]
            return UbicacionOut(tipo=ub.virtual or ub.tipo, nombre=nombre, clave=clave)

        salida = [
            RenglonValeOut(
                renglon=m.renglon,
                articulo_id=a.id,
                articulo=a.nombre,
                marca=a.marca,
                modelo=a.modelo,
                talla=a.talla,
                codigo_articulo=a.codigo,
                pieza_id=p.id if p else None,
                codigo_pieza=p.codigo if p else None,
                numero_serie=p.numero_serie if p else None,
                cantidad=m.cantidad,
                condicion=m.condicion,
                nivel=m.nivel,
                reglas=m.reglas or [],
                observacion=m.observacion,
                origen=lugar(m.origen_id),
                destino=lugar(m.destino_id),
                saldo_origen=m.saldo_origen,
                saldo_destino=m.saldo_destino,
            )
            for m, a, p in filas
        ]
        return pagina_salida(salida, total)

    def enriquecer_detalle(self, id, usuario):
        vale = self._vale(id, usuario)
        filas = self.repository.resumen(id)
        valor = self.acceso.tiene_permiso(usuario, P.REPORTES_VALOR_INVENTARIO)
        resumen = [
            {
                "categoria": {"id": r.id, "nombre": r.nombre},
                "renglones": r.renglones,
                "unidades": int(r.unidades),
                **(
                    {"valor": str(r.valor.quantize(Decimal(".01"))) if r.articulos > 1 else None}
                    if valor
                    else {}
                ),
            }
            for r in filas
        ]
        # Un total menos categorías visibles tampoco debe reconstruir un artículo oculto.
        total_seguro = valor and all(r.articulos > 1 for r in filas)
        salida = {
            "resumen": {
                "categorias": resumen,
                **(
                    {
                        "valor_total": str(
                            sum((r.valor for r in filas), Decimal(0)).quantize(Decimal(".01"))
                        )
                        if total_seguro
                        else None
                    }
                    if valor
                    else {}
                ),
            },
            "relacionados": [
                self._relacion(
                    v,
                    usuario,
                    "Otra parte del lote"
                    if v.lote_id == vale.lote_id and vale.lote_id
                    else "Vale relacionado",
                )
                for v in self.repository.relacionados(vale)
            ],
            "lote": None,
            "capturado_sin_conexion": False,
            "capturado_en": None,
        }
        if vale.lote_id:
            partes = self.repository.lote(vale.lote_id, self.acceso.alcance_del_usuario(usuario.id))
            from app.modulos.consulta.schemas_bitacora import BitacoraFilters

            stats = self.repository.totales([v.id for v in partes], BitacoraFilters())
            salida["lote"] = {
                "id": vale.lote_id,
                "parte": next(i for i, v in enumerate(partes, 1) if v.id == vale.id),
                "partes": len(partes),
                "renglones": sum(s.renglones for s in stats.values()),
                "unidades": sum(int(s.unidades) for s in stats.values()),
                "vales": [{"id": v.id, "folio": v.folio, "estado": v.estado} for v in partes],
            }
        return salida
