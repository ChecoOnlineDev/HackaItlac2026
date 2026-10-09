"""DU-08/RG-12: cantidad visible por persona, valor sólo agregado y protegido."""

from collections import defaultdict
from decimal import Decimal

from app.core.tiempo import hoy_mx
from app.modulos.acceso.permisos import P
from app.modulos.acceso.service import AccesoService
from app.modulos.consulta.repository_consumo_trabajador import ConsumoTrabajadorRepository
from app.modulos.consulta.service import rango_utc
from app.modulos.trabajadores.service import TrabajadorService


class ConsumoTrabajadorService:
    def __init__(self, session):
        self.session = session
        self.repository = ConsumoTrabajadorRepository(session)
        self.trabajadores = TrabajadorService(session)
        self.acceso = AccesoService(session)

    def consultar(self, trabajador_id, usuario, desde=None, hasta=None):
        trabajador = self.trabajadores.obtener(trabajador_id)
        periodo = self.trabajadores.periodo_vigente(trabajador)
        personalizado = desde is not None or hasta is not None
        desde = desde or (periodo.inicio if periodo else trabajador.creado_en.date())
        hasta = hasta or hoy_mx()
        inicio, fin = rango_utc(desde, hasta)
        filas = self.repository.consultar(trabajador_id, inicio, fin)
        recomendado = {
            r.articulo.id: r.recomendada
            for r in self.trabajadores.dotacion_de(trabajador).renglones
        }
        articulos = {}
        valores = defaultdict(lambda: Decimal(0))
        cantidades = defaultdict(set)
        proyectos = {}
        for f in filas:
            item = articulos.setdefault(
                f.articulo_id,
                {
                    "articulo": {"id": f.articulo_id, "codigo": f.codigo, "nombre": f.nombre},
                    "unidad": f.unidad,
                    "cantidad": 0,
                    "recomendado": recomendado.get(f.articulo_id),
                    "por_proyecto": [],
                },
            )
            item["cantidad"] += int(f.cantidad)
            proyecto = {"id": f.proyecto_id, "nombre": f.proyecto_nombre} if f.proyecto_id else None
            item["por_proyecto"].append({"proyecto": proyecto, "cantidad": int(f.cantidad)})
            proyectos[f.proyecto_id] = proyecto
            valores[f.proyecto_id] += (f.costo_unitario or Decimal(0)) * int(f.cantidad)
            cantidades[f.proyecto_id].add(f.articulo_id)
        origen = (
            "PERSONALIZADO"
            if personalizado
            else (
                "CONTRATO_VIGENTE"
                if self.trabajadores.es_vigente(trabajador)
                else "ULTIMO_CONTRATO"
            )
        )
        salida = {
            "periodo": {"desde": desde, "hasta": hasta, "origen": origen},
            "elementos": list(articulos.values()),
        }
        if self.acceso.tiene_permiso(usuario, P.REPORTES_VALOR_INVENTARIO):
            # RG-12: con un único artículo la división reconstruiría el costo unitario.
            ocultos = set().union(*(ids for ids in cantidades.values() if len(ids) <= 1))
            total_seguro = len(articulos) > 1 and len(ocultos) != 1
            salida["valor_total"] = (
                str(sum(valores.values(), Decimal(0)).quantize(Decimal("0.01")))
                if total_seguro
                else None
            )
            salida["valor_por_proyecto"] = [
                {
                    "proyecto": proyectos[id],
                    "valor": str(valor.quantize(Decimal("0.01")))
                    if len(cantidades[id]) > 1
                    else None,
                }
                for id, valor in valores.items()
            ]
            if not total_seguro:
                salida["aviso_valor"] = "No se muestra para no revelar el costo de un artículo."
        return salida
