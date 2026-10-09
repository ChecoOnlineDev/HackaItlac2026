"""FEAT-001: reserva de folio, impresión y confirmación de ticket en papel."""

import uuid
from datetime import timedelta

from app.core.tiempo import hoy_mx
from app.modulos.acceso.repository import UsuarioRepository
from app.modulos.archivos.models import Adjunto
from app.modulos.proyectos.models import AsignacionProyecto, Proyecto
from tests.movimientos.ayudas import (
    a_data_url,
    abastecer,
    almacen,
    crear_articulo,
    crear_trabajador,
    cuerpo_entrega,
    png_valido,
)


def test_F_02_reserva_imprime_y_confirma_ticket_papel(
    almacenista, compras, session
):
    trabajador = crear_trabajador(session)
    admin = UsuarioRepository(session).get_by_usuario("admin")
    proyecto = Proyecto(
        clave="PAPEL-PRUEBA",
        nombre="Proyecto para ticket en papel",
        almacen_id=almacen(session).id,
        inicio=hoy_mx(),
        fin_estimado=hoy_mx() + timedelta(days=30),
        creado_por=admin.id,
    )
    session.add(proyecto)
    session.flush()
    session.add(
        AsignacionProyecto(
            trabajador_id=trabajador.id,
            proyecto_id=proyecto.id,
            inicio=hoy_mx(),
            principal=True,
            creado_por=admin.id,
        )
    )
    session.flush()
    articulo = crear_articulo(session, retornable=False)
    abastecer(compras, articulo, 3)
    cuerpo = cuerpo_entrega(trabajador, [{"codigo": articulo.codigo, "cantidad": 1}])
    cuerpo["observacion"] = "Entrega registrada para el proyecto de prueba."
    cuerpo["firma"] = {"modo": "PAPEL", "imagen": None, "trazo": []}

    preparada = almacenista.post("/api/vales/reservar-papel", json=cuerpo)
    assert preparada.status_code == 201, preparada.text
    ticket = preparada.json()
    assert ticket["folio"].startswith("KEP-ENT-")
    assert ticket["ticket"]["articulos"][0]["codigo"] == articulo.codigo
    assert ticket["ticket"]["leyenda"]
    assert ticket["ticket"]["proyecto"]["id"] == str(proyecto.id)
    repetida = almacenista.post("/api/vales/reservar-papel", json=cuerpo)
    assert repetida.status_code == 201
    assert repetida.json()["id"] == ticket["id"]
    assert repetida.json()["folio"] == ticket["folio"]

    borrador = almacenista.get(f"/api/publico/vales/{ticket['token']}")
    assert borrador.status_code == 200
    assert borrador.json()["integridad"] == "Borrador"

    cuerpo["reserva_papel_id"] = ticket["id"]
    cuerpo["firma"]["imagen"] = a_data_url(png_valido())
    emitido = almacenista.post("/api/vales", json=cuerpo)
    assert emitido.status_code == 201, emitido.text
    vale = emitido.json()
    assert vale["folio"] == ticket["folio"]
    assert vale["token"] == ticket["token"]

    comprobante = almacenista.get(f"/api/publico/vales/{ticket['token']}")
    assert comprobante.status_code == 200
    assert comprobante.json()["integridad"] != "Borrador"
    assert comprobante.json()["folio"] == vale["folio"]
    detalle = almacenista.get(f"/api/vales/por-token/{ticket['token']}")
    assert detalle.status_code == 200 and detalle.json()["id"] == vale["id"]
    assert detalle.json()["proyecto"]["id"] == str(proyecto.id)
    adjunto = session.query(Adjunto).filter_by(vale_id=uuid.UUID(vale["id"])).one()
    assert adjunto.tipo == "TICKET_FIRMADO"
