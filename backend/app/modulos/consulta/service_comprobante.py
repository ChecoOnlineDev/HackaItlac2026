"""F-07/F-12: comprobante público mínimo, sin firma ni datos reservados."""

from app.core.excepciones import NoEncontrado
from app.core.tiempo import ahora_utc
from app.modulos.acceso.service import AccesoService
from app.modulos.almacenes.repository import AlmacenRepository
from app.modulos.movimientos.repository import MovimientoRepository
from app.modulos.movimientos.sello import SelloService
from app.modulos.trabajadores.repository import TrabajadorRepository


class ComprobanteService:
    def __init__(self, session):
        self.session = session
        self.vales = MovimientoRepository(session)
        self.sellos = SelloService(session)

    def publico(self, token):
        vale = self.vales.vale_por_token(token)
        if vale is None:
            reserva = self.vales.reserva_papel_por_token(token)
            if reserva is None or reserva.vale_id is not None or reserva.vence_en <= ahora_utc():
                raise NoEncontrado("No se encontró el comprobante.")
            ticket = reserva.ticket
            return {
                "folio": reserva.folio,
                "creado_en": ticket["creado_en"],
                "integridad": "Borrador",
                "regla": "F-02",
                "trabajador": ticket.get("trabajador"),
                "articulos": [
                    {**a, "numero_serie": None, "condicion": None}
                    for a in ticket.get("articulos", [])
                ],
            }
        verificacion = self.sellos.verificar_almacen(vale.almacen_id)
        trabajador = (
            TrabajadorRepository(self.session).get(vale.trabajador_id)
            if vale.trabajador_id
            else None
        )
        return {
            "folio": vale.folio,
            "creado_en": vale.creado_en,
            "integridad": verificacion["estados"].get(vale.id, "Sin sello"),
            "regla": "F-07",
            "trabajador": {
                "nombre": trabajador.nombre,
                "numero_empleado": trabajador.numero_empleado,
            }
            if trabajador
            else None,
            "articulos": [
                {
                    "renglon": m.renglon,
                    "codigo": p.codigo if p else a.codigo,
                    "nombre": a.nombre,
                    "marca": a.marca,
                    "modelo": a.modelo,
                    "talla": a.talla,
                    "numero_serie": p.numero_serie if p else None,
                    "cantidad": m.cantidad,
                    "condicion": m.condicion,
                }
                for m, a, p in self.vales.renglones_de(vale.id)
            ],
        }

    def integridad(self, actor, almacen_id=None):
        acceso = AccesoService(self.session)
        almacenes = AlmacenRepository(self.session).listar()
        if almacen_id is not None:
            almacenes = [a for a in almacenes if a.id == almacen_id]
        resultados = []
        for a in almacenes:
            if not acceso.en_alcance(actor, a.id):
                continue
            verificacion = self.sellos.verificar_almacen(a.id)
            verificacion.pop("estados")
            resultados.append(
                {"almacen": {"id": a.id, "clave": a.clave, "nombre": a.nombre}, **verificacion}
            )
        return {
            "regla": "F-06",
            "integro": all(r["integro"] for r in resultados),
            "almacenes": resultados,
        }
