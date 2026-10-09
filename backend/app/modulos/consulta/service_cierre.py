"""CP-04: igualdad contable desde la bitácora y resguardo al final del rango."""

from collections import defaultdict
from datetime import UTC, datetime, time, timedelta

from app.core.tiempo import ZONA_MX
from app.modulos.acceso.service import AccesoService
from app.modulos.almacenes.exceptions import AlmacenNoEncontrado
from app.modulos.almacenes.models import UbicacionVirtual
from app.modulos.consulta.repository_cierre import CierreRepository
from app.modulos.consulta.schemas_cierre import CierreOut
from app.modulos.movimientos.models import TipoVale


def _inicio_utc(dia):
    return datetime.combine(dia, time.min, ZONA_MX).astimezone(UTC).replace(tzinfo=None)


class CierreService:
    def __init__(self, session):
        self.repository = CierreRepository(session)
        self.acceso = AccesoService(session)

    def consultar(self, usuario, almacen_id, filtros):
        almacen = self.repository.almacen(almacen_id)
        if not almacen or not self.acceso.en_alcance(usuario, almacen_id):
            raise AlmacenNoEncontrado()
        ubicacion = self.repository.ubicacion(almacen_id)
        inicio, fin = _inicio_utc(filtros.desde), _inicio_utc(filtros.hasta + timedelta(days=1))
        articulos, filas, ubicaciones, trabajadores = self.repository.historial(ubicacion.id, fin)
        columnas = (
            "saldo_inicial",
            "recibido_traspasos",
            "devuelto_a_almacen",
            "otras_entradas",
            "consumido",
            "entregado_trabajadores",
            "regresado",
            "faltantes",
            "otras_salidas",
            "saldo_final",
            "devuelto_por_trabajadores",
            "cerrado_sin_devolucion",
            "en_resguardo",
        )
        totales = {a.id: dict.fromkeys(columnas, 0) for a in articulos}
        lotes = defaultdict(list)
        lotes_por_movimiento, descuentos = {}, {}
        for m, tipo, vale_original in filas:
            origen, destino = ubicaciones[m.origen_id], ubicaciones[m.destino_id]
            t = totales[m.articulo_id]
            if m.origen_id == ubicacion.id or m.destino_id == ubicacion.id:
                signo = (1 if m.destino_id == ubicacion.id else 0) - (
                    1 if m.origen_id == ubicacion.id else 0
                )
                t["saldo_final"] += signo * m.cantidad
                if m.creado_en < inicio:
                    t["saldo_inicial"] += signo * m.cantidad
                elif tipo == TipoVale.CANCELACION:
                    # RG-02/K-02: el movimiento inverso corrige la clasificación, no la oculta.
                    if signo > 0:
                        clave = {
                            UbicacionVirtual.CONSUMIDO: "consumido",
                            UbicacionVirtual.EN_TRANSITO: "regresado",
                            UbicacionVirtual.BAJA: "faltantes",
                        }.get(
                            origen.virtual,
                            "entregado_trabajadores"
                            if origen.tipo == "TRABAJADOR"
                            else "otras_salidas",
                        )
                        t[clave] -= m.cantidad
                    elif signo < 0:
                        t[
                            "devuelto_a_almacen"
                            if destino.tipo == "TRABAJADOR"
                            else "otras_entradas"
                        ] -= m.cantidad
                elif signo > 0:
                    clave = (
                        "recibido_traspasos"
                        if destino.tipo == "ALMACEN" and tipo == TipoVale.RECEPCION
                        else "devuelto_a_almacen"
                        if origen.tipo == "TRABAJADOR"
                        else "otras_entradas"
                    )
                    t[clave] += m.cantidad
                elif signo < 0:
                    if destino.virtual == UbicacionVirtual.CONSUMIDO:
                        clave = "consumido"
                    elif destino.tipo == "TRABAJADOR":
                        clave = "entregado_trabajadores"
                    elif tipo == TipoVale.TRASPASO or destino.tipo == "ALMACEN":
                        clave = "regresado"
                    elif tipo == TipoVale.AJUSTE and destino.virtual == UbicacionVirtual.BAJA:
                        clave = "faltantes"
                    else:
                        clave = "otras_salidas"
                    t[clave] += m.cantidad
            if destino.tipo == "TRABAJADOR":
                if tipo == TipoVale.CANCELACION:
                    # Cancela una devolución: restaura los lotes exactos que esa devolución tomó.
                    for lote, cantidad, clase in descuentos.get((vale_original, m.renglon), []):
                        lote["restante"] += cantidad
                        lote[clase] -= cantidad
                else:
                    lote = {
                        "almacen_id": origen.almacen_id,
                        "fecha": m.creado_en,
                        "pieza_id": m.pieza_id,
                        "restante": m.cantidad,
                        "devuelto": 0,
                        "cerrado": 0,
                        "cancelado": False,
                    }
                    lotes[(destino.trabajador_id, m.articulo_id)].append(lote)
                    lotes_por_movimiento[(m.vale_id, m.renglon)] = lote
            if origen.tipo == "TRABAJADOR":
                pendiente = m.cantidad
                candidatos = lotes[(origen.trabajador_id, m.articulo_id)]
                if tipo == TipoVale.CANCELACION:
                    # Cancela una entrega: prioridad al lote original, nunca a otra entrega FIFO.
                    original = lotes_por_movimiento.get((vale_original, m.renglon))
                    if original is not None:
                        original["cancelado"] = True
                        candidatos = [
                            original,
                            *[lote for lote in candidatos if lote is not original],
                        ]
                tomados = []
                for lote in candidatos:
                    if m.pieza_id is not None and lote["pieza_id"] != m.pieza_id:
                        continue
                    cantidad = min(pendiente, lote["restante"])
                    lote["restante"] -= cantidad
                    clase = "cerrado" if "V-09" in (m.reglas or []) else "devuelto"
                    lote[clase] += cantidad
                    tomados.append((lote, cantidad, clase))
                    pendiente -= cantidad
                    if not pendiente:
                        break
                descuentos[(m.vale_id, m.renglon)] = tomados
        resguardos = defaultdict(lambda: defaultdict(int))
        for (trabajador_id, articulo_id), entregas in lotes.items():
            for lote in entregas:
                if lote["cancelado"] or lote["almacen_id"] != almacen_id or lote["fecha"] < inicio:
                    continue
                t = totales[articulo_id]
                t["devuelto_por_trabajadores"] += lote["devuelto"]
                t["cerrado_sin_devolucion"] += lote["cerrado"]
                t["en_resguardo"] += lote["restante"]
                resguardos[articulo_id][trabajador_id] += lote["restante"]
        salida = []
        for a in articulos:
            t = totales[a.id]
            entradas = (
                t["saldo_inicial"]
                + t["recibido_traspasos"]
                + t["devuelto_a_almacen"]
                + t["otras_entradas"]
            )
            salidas = sum(
                t[c]
                for c in (
                    "consumido",
                    "entregado_trabajadores",
                    "regresado",
                    "faltantes",
                    "otras_salidas",
                    "saldo_final",
                )
            )
            diferencia = entradas - salidas
            salida.append(
                {
                    "articulo_id": a.id,
                    "codigo": a.codigo,
                    "nombre": a.nombre,
                    "unidad": a.unidad,
                    **t,
                    "diferencia": diferencia,
                    "cuadra": diferencia == 0,
                    "trabajadores": [
                        {
                            "id": id,
                            "nombre": trabajadores[id].nombre,
                            "numero_empleado": trabajadores[id].numero_empleado,
                            "cantidad": cantidad,
                        }
                        for id, cantidad in sorted(
                            resguardos[a.id].items(), key=lambda e: trabajadores[e[0]].nombre
                        )
                        if cantidad > 0
                    ],
                }
            )
        return CierreOut(
            almacen={
                "id": almacen.id,
                "clave": almacen.clave,
                "nombre": almacen.nombre,
                "estado": almacen.estado,
            },
            desde=filtros.desde,
            hasta=filtros.hasta,
            articulos=salida,
            cuadra=all(a["cuadra"] for a in salida),
        )
