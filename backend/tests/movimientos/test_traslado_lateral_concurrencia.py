# ruff: noqa: F811  (los fixtures importados se piden por nombre en cada prueba)
"""Concurrencia real de la autorización de traslado (X-19, A-03): dos envíos simultáneos con la
MISMA autorización usan una sola vez. Hilos con conexiones propias y datos CONFIRMADOS: los vales
y las existencias los borra `limpieza`; aquí se borra además el usuario y la autorización de la
prueba (ver `conftest.py`)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update

from app.main import create_app
from app.modulos.acceso.models import Rol, RolPermiso, SesionDispositivo, Usuario
from app.modulos.acceso.permisos import P
from app.modulos.auditoria.models import Auditoria
from app.modulos.autorizaciones.models import Autorizacion
from app.modulos.movimientos.models import Vale
from app.seguridad import hashear_secreto
from tests.conftest import UsuarioPrueba, iniciar_sesion_en
from tests.movimientos.ayudas import abastecer
from tests.movimientos.conftest import (  # noqa: F401
    cliente_independiente,
    limpieza,
    sesion_independiente,
)
from tests.movimientos.test_concurrencia import en_paralelo
from tests.movimientos.test_traspaso_concurrencia import (
    almacen,
    almacenista_de,  # noqa: F401  (fixture)
    cantidad_en,
    escenario,  # noqa: F401  (fixture)
    recepcion,
    renglon,
    traspasar,
    vales_de,
)

AUT = "/api/autorizaciones"
VALES = "/api/vales"


@pytest.fixture
def ana_real(sesion_independiente):
    """Una usuaria de Midrex con solo `traspasos.operar`, con commits reales; se borra al final."""
    s = sesion_independiente()
    sufijo = uuid.uuid4().hex[:8]
    rol = Rol(nombre=f"Rol lateral {sufijo}")
    s.add(rol)
    s.flush()
    for permiso in (P.TRASPASOS_OPERAR,):
        s.add(RolPermiso(rol_id=rol.id, permiso=permiso))
    usuario = Usuario(
        usuario=f"ana_{sufijo}",
        nombre="Ana de prueba",
        contrasena_hash=hashear_secreto("Clave-prueba-123"),
        rol_id=rol.id,
        almacen_id=almacen(s, "MID"),
        activo=True,
    )
    s.add(usuario)
    s.commit()
    yield UsuarioPrueba(usuario.usuario, "Clave-prueba-123")

    limpio = sesion_independiente()
    ana_id = limpio.scalar(select(Usuario.id).where(Usuario.usuario == usuario.usuario))
    autorizaciones = list(
        limpio.scalars(select(Autorizacion.id).where(Autorizacion.solicitada_por == ana_id))
    )
    limpio.execute(
        update(Vale).where(Vale.autorizacion_id.in_(autorizaciones)).values(autorizacion_id=None)
    )
    limpio.execute(delete(Autorizacion).where(Autorizacion.id.in_(autorizaciones)))
    limpio.execute(delete(SesionDispositivo).where(SesionDispositivo.usuario_id == ana_id))
    limpio.execute(delete(Auditoria).where(Auditoria.usuario_id == ana_id))
    limpio.execute(delete(Usuario).where(Usuario.id == ana_id))
    limpio.execute(delete(RolPermiso).where(RolPermiso.rol_id == rol.id))
    limpio.execute(delete(Rol).where(Rol.id == rol.id))
    limpio.commit()


def test_x19_dos_envios_simultaneos_con_la_misma_autorizacion_solo_usan_una(
    ana_real,  # primero: se borra al final, cuando `limpieza` ya borró sus vales
    escenario,
    almacenista_de,
    sesion_independiente,
):
    guantes = escenario.articulo(retornable=False)
    s = sesion_independiente()
    # 10 en Kepler, que bajan por Contratistas hasta Midrex con sus recepciones.
    abastecer(escenario.compras, guantes, 10)
    origen = "KEP"
    for destino in ("CON", "MID"):
        envio = traspasar(
            almacenista_de(origen), almacen(s, destino), [renglon(guantes.codigo, 10)]
        )
        assert envio.status_code == 201, envio.text
        recibido = recepcion(
            almacenista_de(destino), envio.json()["id"], [renglon(guantes.codigo, 10)]
        )
        assert recibido.status_code == 201, recibido.text
        origen = destino

    hyl = almacen(s, "HYL")  # antes de los hilos: la sesión no se comparte
    app = create_app()
    clientes: list[TestClient] = []

    def cliente_ana() -> TestClient:
        c = TestClient(app)
        assert iniciar_sesion_en(c, ana_real).status_code == 200
        clientes.append(c)
        return c

    try:
        c1, c2 = cliente_ana(), cliente_ana()
        renglones = [renglon(guantes.codigo, 2)]
        pedida = c1.post(
            AUT,
            json={
                "tipo": "TRASLADO",
                "destino_almacen_id": str(hyl),
                "renglones": renglones,
                "motivo": "Prueba de concurrencia",
            },
        )
        assert pedida.status_code == 201, pedida.text
        autorizacion_id = pedida.json()["id"]
        aprobada = almacenista_de("MID").post(
            f"{AUT}/{autorizacion_id}/resolucion", json={"decision": "APROBAR"}
        )
        assert aprobada.status_code == 200, aprobada.text

        def enviar(cliente):
            return cliente.post(
                VALES,
                json={
                    "tipo": "TRASPASO",
                    "destino_almacen_id": str(hyl),
                    "id_cliente": str(uuid.uuid4()),
                    "autorizacion_id": autorizacion_id,
                    "renglones": renglones,
                },
            )

        r1, r2 = en_paralelo([lambda: enviar(c1), lambda: enviar(c2)])
        assert sorted([r1.status_code, r2.status_code]) == [201, 409], (r1.text, r2.text)
        perdedor = r1 if r1.status_code == 409 else r2
        assert perdedor.json()["codigo"] == "AUTORIZACION_INVALIDA"

        s = sesion_independiente()
        assert len(vales_de(s, guantes, "TRASPASO")) == 3  # KEP->CON, CON->MID y el lateral
        assert cantidad_en(s, guantes, almacen_clave="MID") == 8  # salió una sola vez
        assert cantidad_en(s, guantes, virtual="EN_TRANSITO") == 2
        assert s.get(Autorizacion, uuid.UUID(autorizacion_id)).estado == "USADA"
    finally:
        for c in clientes:
            c.close()
