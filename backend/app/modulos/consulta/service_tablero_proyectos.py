"""TB-05 a TB-07. Resguardo de hoy y consumo neto del rango por proyecto."""

from collections import defaultdict
from decimal import Decimal

from app.core.tiempo import ahora_utc, hoy_mx
from app.modulos.acceso.alcance_almacenes import dentro_del_alcance
from app.modulos.acceso.permisos import P
from app.modulos.consulta.exceptions import RangoFechasDemasiadoLargo
from app.modulos.consulta.repository import ConsultaRepository
from app.modulos.consulta.repository_tablero_proyectos import TableroProyectosRepository
from app.modulos.consulta.schemas_tablero import DIAS_MAXIMOS_RANGO
from app.modulos.consulta.schemas_tablero_proyectos import (
    ProyectosTableroOut,
    ProyectoUsoOut,
    RangoUsoOut,
    TotalUsoOut,
    UsoCategoriaOut,
    UsoOut,
)
from app.modulos.consulta.service import rango_utc
from app.modulos.consulta.service_tablero import TableroService
from app.modulos.proyectos.service import ProyectoService


class Acumulado:
    def __init__(self):
        self.unidades = {"retornables": 0, "consumibles": 0}
        self.valores = {"retornables": Decimal(0), "consumibles": Decimal(0)}
        self.con_costo = {"retornables": set(), "consumibles": set()}
        self.sin_costo = set()

    def agregar(self, tipo, articulo_id, cantidad, costo):
        self.unidades[tipo] += cantidad
        if costo is None:
            self.sin_costo.add(articulo_id)
        else:
            self.con_costo[tipo].add(articulo_id)
            self.valores[tipo] += cantidad * Decimal(costo)

    def salida(self, ve_valor, ve_costos):
        def importe(tipos):
            articulos = set().union(*(self.con_costo[t] for t in tipos))
            # T-2: un agregado de un solo artículo permitiría deducir su costo.
            if not ve_valor or (not ve_costos and len(articulos) == 1):
                return None
            return f"{sum((self.valores[t] for t in tipos), Decimal(0)):.2f}"

        def total(tipos):
            return TotalUsoOut(unidades=sum(self.unidades[t] for t in tipos), valor=importe(tipos))

        return UsoOut(
            retornables_en_resguardo=total(["retornables"]),
            consumibles_consumidos=total(["consumibles"]),
            total=total(["retornables", "consumibles"]),
            articulos_sin_costo=len(self.sin_costo),
        )


class TableroProyectosService:
    def __init__(self, session):
        self.tablero = TableroService(session)
        self.repository = TableroProyectosRepository(session)
        self.consultas = ConsultaRepository(session)
        self.proyectos = ProyectoService(session)

    def uso(self, usuario, filtros):
        acceso = self.tablero.acceso
        acceso.exigir_permiso(usuario, P.TABLERO_VER)
        acceso.exigir_permiso(usuario, "proyectos.ver")
        hasta = filtros.hasta or hoy_mx()
        desde = filtros.desde or hasta.replace(day=1)
        inicio, fin = rango_utc(desde, hasta)
        if (hasta - desde).days > DIAS_MAXIMOS_RANGO:
            raise RangoFechasDemasiadoLargo()
        alcance = self.tablero._alcance(usuario, filtros.almacen_id)
        x = frozenset() if alcance.vacio else alcance.almacen_id
        proyectos = self.repository.proyectos(x, filtros.proyecto_id)
        por_id = {p.id: p for p in proyectos}
        totales = defaultdict(Acumulado)
        categorias = defaultdict(lambda: defaultdict(Acumulado))
        nombres = self.repository.categorias()

        def agregar(id, tipo, art, cat, nombre, cantidad, costo):
            totales[id].agregar(tipo, art, cantidad, costo)
            categorias[id][cat].agregar(tipo, art, cantidad, costo)
            nombres[cat] = nombre

        if not alcance.vacio:
            for p in self.consultas.pendientes():
                if p.proyecto_id is not None:
                    if p.proyecto_id not in por_id:
                        continue
                elif filtros.proyecto_id is not None or (
                    x is not None and not dentro_del_alcance(p.almacen_id, x)
                ):
                    continue
                agregar(
                    p.proyecto_id,
                    "retornables",
                    p.articulo.id,
                    p.articulo.categoria_id,
                    nombres[p.articulo.categoria_id],
                    p.cantidad,
                    p.articulo.costo_unitario,
                )
            for f in self.repository.consumibles(inicio, fin, x):
                if f.proyecto_id is not None and f.proyecto_id not in por_id:
                    continue
                if f.proyecto_id is None and filtros.proyecto_id is not None:
                    continue
                agregar(
                    f.proyecto_id,
                    "consumibles",
                    f.articulo_id,
                    f.categoria_id,
                    f.categoria,
                    int(f.cantidad),
                    f.costo,
                )

        ve_valor = acceso.tiene_permiso(usuario, P.REPORTES_VALOR_INVENTARIO)
        ve_costos = acceso.tiene_permiso(usuario, P.CATALOGO_COSTOS)
        salida = []
        for p in proyectos:
            uso = totales[p.id].salida(ve_valor, ve_costos)
            if (
                p.estado == "CERRADO"
                and uso.retornables_en_resguardo.unidades == 0
                and uso.consumibles_consumidos.unidades == 0
            ):
                continue
            ficha = self.proyectos.ficha(p)
            reparto = None
            if filtros.proyecto_id is not None:
                orden = sorted(
                    categorias[p.id].items(), key=lambda kv: -sum(kv[1].unidades.values())
                )
                reparto = [
                    UsoCategoriaOut(
                        **a.salida(ve_valor, ve_costos).model_dump(),
                        categoria={"id": id, "nombre": nombres[id]},
                        nombre=nombres[id],
                    )
                    for id, a in orden[:6]
                ]
                if len(orden) > 6:
                    otros = Acumulado()
                    for _, a in orden[6:]:
                        for tipo in otros.unidades:
                            otros.unidades[tipo] += a.unidades[tipo]
                            otros.valores[tipo] += a.valores[tipo]
                            otros.con_costo[tipo].update(a.con_costo[tipo])
                        otros.sin_costo.update(a.sin_costo)
                    reparto.append(
                        UsoCategoriaOut(
                            **otros.salida(ve_valor, ve_costos).model_dump(),
                            categoria=None,
                            nombre="Otras",
                        )
                    )
            salida.append(
                ProyectoUsoOut(
                    **uso.model_dump(),
                    id=p.id,
                    clave=p.clave,
                    nombre=p.nombre,
                    almacen=ficha.almacen.model_dump(),
                    inicio=p.inicio,
                    fin_estimado=p.fin_estimado,
                    estado=p.estado,
                    situacion=ficha.situacion,
                    trabajadores_asignados=ficha.trabajadores_asignados,
                    por_categoria=reparto,
                )
            )
        ordenar_por_valor = ve_valor and all(p.total.valor is not None for p in salida)
        salida.sort(
            key=lambda p: (
                -(Decimal(p.total.valor) if ordenar_por_valor else p.total.unidades),
                p.nombre.casefold(),
            )
        )
        return ProyectosTableroOut(
            alcance=self.tablero._alcance_out(alcance, usuario),
            rango=RangoUsoOut(desde=desde, hasta=hasta),
            proyectos=salida,
            sin_proyecto=totales[None].salida(ve_valor, ve_costos),
            generado_en=ahora_utc(),
        )
