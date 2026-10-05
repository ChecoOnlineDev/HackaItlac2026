"""Fixtures de las pruebas de endurecimiento de seguridad.

Las de concurrencia necesitan conexiones propias y datos CONFIRMADOS (la fixture normal envuelve
todo en una transacción que dos hilos no verían); `usuario_confirmado` los crea y los borra al
final.
"""

import threading
import uuid
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.modulos.acceso.models import Rol, RolPermiso, Usuario
from app.modulos.auditoria.models import Auditoria
from app.seguridad import hashear_secreto

CONTRASENA = "Clave-prueba-123"
PIN = "4321"


@dataclass(frozen=True)
class UsuarioConfirmado:
    id: uuid.UUID
    usuario: str
    contrasena: str
    pin: str


@pytest.fixture
def sesion_independiente(engine) -> Iterator[Callable[[], Session]]:
    abiertas: list[Session] = []

    def _nueva() -> Session:
        sesion = Session(bind=engine, autoflush=False, expire_on_commit=False)
        abiertas.append(sesion)
        return sesion

    yield _nueva
    for s in abiertas:
        s.close()


@pytest.fixture
def usuario_confirmado(sesion_independiente) -> Iterator[Callable[..., UsuarioConfirmado]]:
    """Un rol y un usuario con commit real; se borran al terminar la prueba."""
    creados: list[tuple[uuid.UUID, uuid.UUID]] = []

    def _crear(permisos: set[str], *, almacen_id=None, con_pin: bool = True) -> UsuarioConfirmado:
        s = sesion_independiente()
        rol = Rol(nombre=f"Rol endurecimiento {uuid.uuid4().hex[:8]}")
        s.add(rol)
        s.flush()
        for permiso in permisos:
            s.add(RolPermiso(rol_id=rol.id, permiso=permiso))
        nombre = f"endurecimiento_{uuid.uuid4().hex[:10]}"
        usuario = Usuario(
            nombre="Usuario de endurecimiento",
            usuario=nombre,
            contrasena_hash=hashear_secreto(CONTRASENA),
            pin_hash=hashear_secreto(PIN) if con_pin else None,
            rol_id=rol.id,
            almacen_id=almacen_id,
        )
        s.add(usuario)
        s.commit()
        creados.append((usuario.id, rol.id))
        return UsuarioConfirmado(usuario.id, nombre, CONTRASENA, PIN)

    yield _crear

    s = sesion_independiente()
    for usuario_id, rol_id in creados:
        s.execute(delete(Auditoria).where(Auditoria.usuario_id == usuario_id))
        s.execute(delete(Auditoria).where(Auditoria.entidad_id == str(usuario_id)))
        s.execute(delete(Usuario).where(Usuario.id == usuario_id))
        s.execute(delete(RolPermiso).where(RolPermiso.rol_id == rol_id))
        s.execute(delete(Rol).where(Rol.id == rol_id))
    s.commit()


def en_paralelo(llamadas: list[Callable[[], object]]) -> list[object]:
    """Ejecuta las llamadas a la vez (todas esperan en una barrera) y devuelve sus resultados."""
    barrera = threading.Barrier(len(llamadas))

    def correr(llamada):
        barrera.wait(timeout=60)
        try:
            return llamada()
        except Exception as exc:  # el resultado de un hilo que falla es la excepción
            return exc

    with ThreadPoolExecutor(max_workers=len(llamadas)) as pool:
        futuros = [pool.submit(correr, c) for c in llamadas]
        return [f.result(timeout=300) for f in futuros]
