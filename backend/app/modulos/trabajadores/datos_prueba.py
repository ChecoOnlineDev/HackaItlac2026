"""Datos de prueba de `trabajadores`: cuatro trabajadores con credencial. Idempotente.

Las fechas de los periodos se calculan respecto de hoy cada vez que se carga, para que cada
trabajador conserve su situación (vigente, vencido, en baja o por iniciar). No son datos reales.
"""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tiempo import hoy_mx
from app.modulos.acceso.repository import UsuarioRepository
from app.modulos.almacenes.service import AlmacenService
from app.modulos.catalogo.codigos import CodigoService
from app.modulos.catalogo.models import Puesto, TipoCodigo
from app.modulos.trabajadores.models import EstadoTrabajador, PeriodoContrato, Trabajador
from app.modulos.trabajadores.repository import TrabajadorRepository

REFERENCIA = "Datos de prueba"

# (número, nombre, estado, puesto, área u obra, días de inicio, días de fin, código, CURP, NSS)
# Los días son respecto de hoy: negativo es antes, positivo es después.
TRABAJADORES = (
    (
        "EMP-1001",
        "Juan Pérez Soto",
        EstadoTrabajador.ACTIVO,
        "Soldador",
        "Midrex",
        -90,
        270,
        "TRB-1001",
        "PESJ900101HCLRTN09",
        "12345678901",
    ),
    (
        "EMP-1002",
        "María Torres Luna",
        EstadoTrabajador.ACTIVO,
        "Ayudante general",
        "HYL",
        -400,
        -10,
        "TRB-1002",
        None,
        None,
    ),
    (
        "EMP-1003",
        "Luis Ramírez Cruz",
        EstadoTrabajador.BAJA_EN_PROCESO,
        "Electricista",
        "Laminador",
        -200,
        160,
        "TRB-1003",
        None,
        None,
    ),
    (
        "EMP-1004",
        "Ana Gómez Rivas",
        EstadoTrabajador.ACTIVO,
        "Rigger",
        "Minas",
        15,
        380,
        "TRB-1004",
        None,
        None,
    ),
)


def cargar(session: Session) -> None:
    repositorio = TrabajadorRepository(session)
    ubicaciones = AlmacenService(session)
    codigos = CodigoService(session)
    usuarios = UsuarioRepository(session)
    creador = usuarios.get_by_usuario("rh") or usuarios.get_by_usuario("admin")
    if creador is None:
        raise RuntimeError("Los datos de `acceso` deben cargarse antes que los de `trabajadores`")
    hoy = hoy_mx()

    for numero, nombre, estado, puesto, area, d_inicio, d_fin, codigo, curp, nss in TRABAJADORES:
        trabajador = repositorio.get_by_numero(numero)
        if trabajador is None:
            trabajador = repositorio.add(
                Trabajador(
                    numero_empleado=numero,
                    nombre=nombre,
                    estado=estado,
                    curp=curp,
                    nss=nss,
                    tallas={"camisa": "M", "calzado": "27"},
                )
            )
        inicio, fin = hoy + timedelta(days=d_inicio), hoy + timedelta(days=d_fin)
        puesto_catalogo = session.scalar(select(Puesto).where(Puesto.nombre == puesto))
        periodos = repositorio.periodos(trabajador.id)
        propio = next((p for p in periodos if p.referencia == REFERENCIA), None)
        if propio is None:
            repositorio.add_periodo(
                PeriodoContrato(
                    trabajador_id=trabajador.id,
                    puesto=puesto,
                    puesto_id=puesto_catalogo.id if puesto_catalogo else None,
                    area_obra=area,
                    referencia=REFERENCIA,
                    inicio=inicio,
                    fin=fin,
                    creado_por=creador.id,
                )
            )
        else:
            propio.inicio, propio.fin = inicio, fin
            if propio.puesto_id is None and puesto_catalogo is not None:
                propio.puesto_id = puesto_catalogo.id
        ubicaciones.asegurar_ubicacion_de_trabajador(trabajador.id)
        codigos.registrar(codigo, TipoCodigo.TRABAJADOR, trabajador.id)
    session.flush()
