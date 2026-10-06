"""Datos de prueba de `solicitudes_compra`: tres solicitudes de ejemplo en distintos estados.

- Midrex: una urgente PENDIENTE de una herramienta que no está en el catálogo (una llave métrica,
  el caso del track: una herramienta con medidas europeas que el almacén no tiene).
- Kepler: una EN_COMPRA que Compras ya tomó.
- Kepler: una INGRESADA, ligada al vale de ENTRADA real `KEP-ING-000001` de la carga inicial.

Es idempotente: cada solicitud lleva un `id_cliente` fijo y, si ya existe, no se repite ni se
vuelve a mover de estado. Todo pasa por el servicio del módulo y solo hace `flush`; el commit lo
hace `app/datos_prueba.py`. No escribe inventario: la entrada del tercer caso ya existe.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modulos.acceso.repository import UsuarioRepository
from app.modulos.catalogo.repository import ArticuloRepository
from app.modulos.movimientos.models import TipoVale, Vale
from app.modulos.solicitudes_compra.models import EstadoSolicitud, Urgencia
from app.modulos.solicitudes_compra.schemas import CambioEstadoIn, SolicitudCreate
from app.modulos.solicitudes_compra.service import SolicitudCompraService

NAMESPACE = uuid.UUID("c3a1f0d2-6b7e-4e1a-9d52-0f3b8a7e6c41")

E = EstadoSolicitud


def id_cliente_de(nombre: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, f"solicitud-compra/{nombre}")


def cargar(session: Session) -> None:
    usuarios = UsuarioRepository(session)
    articulos = ArticuloRepository(session)
    alm_mid = usuarios.get_by_usuario("alm_mid")
    supervisor = usuarios.get_by_usuario("supervisor")
    compras = usuarios.get_by_usuario("compras")
    if alm_mid is None or supervisor is None or compras is None:
        raise RuntimeError("Los datos de `acceso` deben cargarse antes que los de las solicitudes")
    servicio = SolicitudCompraService(session)

    # 1. Midrex: urgente, sin artículo de catálogo, esperando a Compras.
    servicio.crear(
        alm_mid,
        SolicitudCreate(
            id_cliente=id_cliente_de("midrex-llave-metrica"),
            descripcion="Llave métrica 24 mm",
            cantidad=2,
            motivo="Mantenimiento de un equipo europeo en Midrex: la llave que tenemos no ajusta",
            urgencia=Urgencia.URGENTE,
        ),
        commit=False,
    )

    # 2. Kepler: un artículo del catálogo que Compras ya tomó.
    respirador = articulos.get_by_codigo("RESP-6200")
    if respirador is not None:
        solicitud, _ = servicio.crear(
            supervisor,
            SolicitudCreate(
                id_cliente=id_cliente_de("kepler-respiradores"),
                articulo_id=respirador.id,
                cantidad=20,
                motivo="Parada de mantenimiento de la próxima semana: se agotó el stock",
                urgencia=Urgencia.URGENTE,
            ),
            commit=False,
        )
        if solicitud.estado == E.PENDIENTE:
            servicio.cambiar_estado(
                compras,
                solicitud.id,
                CambioEstadoIn(estado=E.EN_COMPRA, nota="Cotizando con dos proveedores."),
                commit=False,
            )

    # 3. Kepler: ya comprada e ingresada con una entrada real de la carga inicial.
    flexometro = articulos.get_by_codigo("FLEXOM")
    if flexometro is not None:
        solicitud, _ = servicio.crear(
            supervisor,
            SolicitudCreate(
                id_cliente=id_cliente_de("kepler-flexometros"),
                articulo_id=flexometro.id,
                cantidad=10,
                motivo="Reposición para las cuadrillas de Kepler",
                urgencia=Urgencia.NORMAL,
            ),
            commit=False,
        )
        vale = session.scalar(
            select(Vale)
            .where(Vale.folio == "KEP-ING-000001", Vale.tipo == TipoVale.ENTRADA)
            .limit(1)
        )
        pasos = {
            E.PENDIENTE: [
                CambioEstadoIn(estado=E.EN_COMPRA),
                CambioEstadoIn(estado=E.COMPRADA, nota="Orden levantada con el proveedor."),
                CambioEstadoIn(
                    estado=E.INGRESADA,
                    nota="Ya está en el almacén.",
                    vale_entrada_id=vale.id if vale else None,
                ),
            ],
        }
        for paso in pasos.get(solicitud.estado, []):
            solicitud = servicio.cambiar_estado(compras, solicitud.id, paso, commit=False)
    session.flush()
