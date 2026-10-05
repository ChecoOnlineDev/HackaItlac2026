"""Fixtures del módulo `consulta`.

`movimientos` e `inspecciones` todavía no escriben datos, así que `datos` inserta directamente,
con los modelos, filas consistentes: vale, movimiento, existencia, pieza y ubicaciones. Lo que
arma es lo que el motor de vales debe producir (ver "Qué movimientos genera cada vale" en
`docs/architecture/data-model.md`).
"""

import itertools
import uuid
from collections.abc import Callable
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.ids import nuevo_id
from app.core.tiempo import ahora_utc, hoy_mx
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.repository import UsuarioRepository
from app.modulos.almacenes.models import Almacen, Ubicacion, UbicacionVirtual
from app.modulos.almacenes.repository import AlmacenRepository, UbicacionRepository
from app.modulos.catalogo.codigos import CodigoService
from app.modulos.catalogo.models import Articulo, Categoria, Pieza, TipoCodigo
from app.modulos.inspecciones.models import AjusteVigencia, EventoPieza, Inspeccion
from app.modulos.movimientos.models import Existencia, Movimiento, TipoVale, Vale
from app.modulos.trabajadores.models import EstadoTrabajador, PeriodoContrato, Trabajador
from tests.conftest import UsuarioPrueba, iniciar_sesion_en

_contador = itertools.count(1)


def _n() -> int:
    return next(_contador)


class Datos:
    """Constructor de datos de prueba. Todo se inserta con `flush` dentro de la transacción."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.almacenes = AlmacenRepository(session)
        self.ubicaciones = UbicacionRepository(session)
        self.usuarios = UsuarioRepository(session)

    # ------------------------------------------------------------ lugares y personas

    def almacen(self, clave: str) -> Almacen:
        almacen = self.almacenes.get_by_clave(clave)
        assert almacen is not None
        return almacen

    def ub_almacen(self, clave: str) -> Ubicacion:
        ubicacion = self.ubicaciones.de_almacen(self.almacen(clave).id)
        assert ubicacion is not None
        return ubicacion

    def ub_virtual(self, virtual: UbicacionVirtual) -> Ubicacion:
        ubicacion = self.ubicaciones.virtual(virtual)
        assert ubicacion is not None
        return ubicacion

    def ub_trabajador(self, trabajador: Trabajador) -> Ubicacion:
        ubicacion = self.ubicaciones.de_trabajador(trabajador.id)
        assert ubicacion is not None
        return ubicacion

    def usuario(self, nombre_usuario: str) -> Usuario:
        usuario = self.usuarios.get_by_usuario(nombre_usuario)
        assert usuario is not None
        return usuario

    def trabajador(
        self,
        nombre: str | None = None,
        *,
        estado: str = EstadoTrabajador.ACTIVO,
        inicio: date | None = None,
        fin: date | None = None,
        codigo: str | None = None,
        curp: str | None = None,
        nss: str | None = None,
    ) -> Trabajador:
        n = _n()
        trabajador = Trabajador(
            numero_empleado=f"EMP-C{n:05d}",
            nombre=nombre or f"Trabajador de consulta {n}",
            estado=estado,
            curp=curp,
            nss=nss,
        )
        self.session.add(trabajador)
        self.session.flush()
        self.ubicaciones.crear_de_trabajador(trabajador.id)
        self.session.add(
            PeriodoContrato(
                trabajador_id=trabajador.id,
                puesto="Soldador",
                area_obra="Midrex",
                inicio=inicio or hoy_mx() - timedelta(days=30),
                fin=fin or hoy_mx() + timedelta(days=300),
                creado_por=self.usuario("admin").id,
            )
        )
        if codigo:
            CodigoService(self.session).registrar(codigo, TipoCodigo.TRABAJADOR, trabajador.id)
        self.session.flush()
        return trabajador

    # ----------------------------------------------------------------------- catálogo

    def articulo(
        self,
        nombre: str | None = None,
        *,
        control: str = "CANTIDAD",
        retornable: bool = True,
        unidad: str = "pieza",
        costo: str | None = None,
        codigo: str | None = None,
        categoria: Categoria | None = None,
    ) -> Articulo:
        n = _n()
        if categoria is None:
            categoria = Categoria(
                nombre=f"Categoría de consulta {n}",
                tipo="HERRAMIENTA",
                control=control,
                retornable=retornable,
            )
            self.session.add(categoria)
            self.session.flush()
        articulo = Articulo(
            codigo=codigo or f"ART-C{n:05d}",
            nombre=nombre or f"Artículo de consulta {n}",
            categoria_id=categoria.id,
            control=control,
            retornable=retornable,
            unidad=unidad,
            costo_unitario=costo,
        )
        self.session.add(articulo)
        self.session.flush()
        CodigoService(self.session).registrar(articulo.codigo, TipoCodigo.ARTICULO, articulo.id)
        return articulo

    def pieza(
        self,
        articulo: Articulo,
        ubicacion: Ubicacion | None = None,
        *,
        serie: str | None = None,
        estado: str = "APTO",
        vigente_hasta: date | None = None,
        codigo: str | None = None,
    ) -> Pieza:
        n = _n()
        pieza = Pieza(
            articulo_id=articulo.id,
            codigo=codigo or f"PZA-C{n:05d}",
            numero_serie=serie or f"SN-C{n:05d}",
            estado=estado,
            inspeccion_vigente_hasta=vigente_hasta,
            ubicacion_id=ubicacion.id if ubicacion else None,
        )
        self.session.add(pieza)
        self.session.flush()
        CodigoService(self.session).registrar(pieza.codigo, TipoCodigo.PIEZA, pieza.id)
        return pieza

    def existencia(self, ubicacion: Ubicacion, articulo: Articulo, cantidad: int) -> Existencia:
        fila = Existencia(ubicacion_id=ubicacion.id, articulo_id=articulo.id, cantidad=cantidad)
        self.session.add(fila)
        self.session.flush()
        return fila

    # ------------------------------------------------------------------ vales y movimientos

    def vale(
        self,
        tipo: str,
        almacen: str = "KEP",
        *,
        responsable: str | Usuario = "almacenista",
        trabajador: Trabajador | None = None,
        creado_en: datetime | None = None,
        estado: str = "EMITIDO",
        vale_origen: Vale | None = None,
        codigo_qr: str | None = None,
    ) -> Vale:
        n = _n()
        usuario = responsable if isinstance(responsable, Usuario) else self.usuario(responsable)
        vale = Vale(
            id_cliente=nuevo_id(),
            tipo=tipo,
            folio=f"{almacen}-{tipo[:3]}-C{n:06d}",
            almacen_id=self.almacen(almacen).id,
            trabajador_id=trabajador.id if trabajador else None,
            vale_origen_id=vale_origen.id if vale_origen else None,
            estado=estado,
            responsable_id=usuario.id,
            token=codigo_qr or uuid.uuid4().hex,
            creado_en=creado_en or ahora_utc(),
        )
        self.session.add(vale)
        self.session.flush()
        return vale

    def movimiento(
        self,
        vale: Vale,
        articulo: Articulo,
        origen: Ubicacion,
        destino: Ubicacion,
        *,
        cantidad: int = 1,
        pieza: Pieza | None = None,
        trabajador: Trabajador | None = None,
        creado_en: datetime | None = None,
        saldo_origen: int | None = None,
        saldo_destino: int | None = None,
        renglon: int | None = None,
    ) -> Movimiento:
        renglon = renglon or (
            self.session.query(Movimiento).filter(Movimiento.vale_id == vale.id).count() + 1
        )
        movimiento = Movimiento(
            vale_id=vale.id,
            renglon=renglon,
            articulo_id=articulo.id,
            pieza_id=pieza.id if pieza else None,
            cantidad=1 if pieza else cantidad,
            origen_id=origen.id,
            destino_id=destino.id,
            trabajador_id=trabajador.id if trabajador else None,
            saldo_origen=saldo_origen,
            saldo_destino=saldo_destino,
            creado_en=creado_en or vale.creado_en,
        )
        self.session.add(movimiento)
        self.session.flush()
        return movimiento

    def entrega(
        self,
        trabajador: Trabajador,
        articulo: Articulo,
        *,
        almacen: str = "KEP",
        cantidad: int = 1,
        pieza: Pieza | None = None,
        responsable: str | Usuario = "almacenista",
        creado_en: datetime | None = None,
        estado: str = "EMITIDO",
    ) -> Vale:
        """ENTREGA: retornable, del almacén al trabajador; consumible, a CONSUMIDO con el
        trabajador anotado (E-20, E-21). Deja la existencia y la pieza donde dice el motor."""
        vale = self.vale(
            TipoVale.ENTREGA,
            almacen,
            responsable=responsable,
            trabajador=trabajador,
            creado_en=creado_en,
            estado=estado,
        )
        origen = self.ub_almacen(almacen)
        if articulo.retornable:
            destino = self.ub_trabajador(trabajador)
            self.movimiento(
                vale,
                articulo,
                origen,
                destino,
                cantidad=cantidad,
                pieza=pieza,
                saldo_origen=0,
                saldo_destino=cantidad,
            )
            if pieza is not None:
                pieza.ubicacion_id = destino.id
            else:
                self._sumar_existencia(destino, articulo, cantidad)
        else:
            self.movimiento(
                vale,
                articulo,
                origen,
                self.ub_virtual(UbicacionVirtual.CONSUMIDO),
                cantidad=cantidad,
                trabajador=trabajador,
                saldo_origen=0,
                saldo_destino=cantidad,
            )
        self.session.flush()
        return vale

    def cancelar(
        self, vale: Vale, *, creado_en: datetime | None = None, responsable: str = "supervisor"
    ) -> Vale:
        """K-02: un vale de CANCELACION con los movimientos inversos, ligado al original."""
        cancelacion = self.vale(
            TipoVale.CANCELACION,
            self.session.get(Almacen, vale.almacen_id).clave,
            responsable=responsable,
            trabajador=self.session.get(Trabajador, vale.trabajador_id)
            if vale.trabajador_id
            else None,
            creado_en=creado_en,
            vale_origen=vale,
        )
        originales = (
            self.session.query(Movimiento)
            .filter(Movimiento.vale_id == vale.id)
            .order_by(Movimiento.renglon)
            .all()
        )
        for m in originales:
            self.movimiento(
                cancelacion,
                self.session.get(Articulo, m.articulo_id),
                self.session.get(Ubicacion, m.destino_id),
                self.session.get(Ubicacion, m.origen_id),
                cantidad=m.cantidad,
                pieza=self.session.get(Pieza, m.pieza_id) if m.pieza_id else None,
                trabajador=self.session.get(Trabajador, m.trabajador_id)
                if m.trabajador_id
                else None,
            )
        vale.estado = "CANCELADO"
        self.session.flush()
        return cancelacion

    def _sumar_existencia(self, ubicacion: Ubicacion, articulo: Articulo, cantidad: int) -> None:
        fila = self.session.get(Existencia, (ubicacion.id, articulo.id))
        if fila is None:
            self.existencia(ubicacion, articulo, cantidad)
        else:
            fila.cantidad += cantidad
            self.session.flush()

    # --------------------------------------------------------------------- inspecciones

    def inspeccion(
        self,
        pieza: Pieza,
        *,
        resultado: str = "APTO",
        fecha: date | None = None,
        vigente_hasta: date | None = None,
        usuario: str = "almacenista",
        creado_en: datetime | None = None,
        observacion: str | None = None,
    ) -> Inspeccion:
        fila = Inspeccion(
            pieza_id=pieza.id,
            fecha=fecha or hoy_mx(),
            resultado=resultado,
            vigente_hasta=vigente_hasta,
            observacion=observacion,
            usuario_id=self.usuario(usuario).id,
            creado_en=creado_en or ahora_utc(),
        )
        self.session.add(fila)
        self.session.flush()
        return fila

    def cambio_estado(
        self,
        pieza: Pieza,
        anterior: str,
        nuevo: str,
        *,
        creado_en: datetime | None = None,
        observacion: str | None = None,
    ) -> EventoPieza:
        fila = EventoPieza(
            pieza_id=pieza.id,
            estado_anterior=anterior,
            estado_nuevo=nuevo,
            observacion=observacion,
            usuario_id=self.usuario("almacenista").id,
            creado_en=creado_en or ahora_utc(),
        )
        self.session.add(fila)
        self.session.flush()
        return fila

    def ajuste_vigencia(
        self,
        pieza: Pieza,
        inspeccion: Inspeccion,
        *,
        anterior: date | None,
        nuevo: date,
        motivo: str = "Se revisó de nuevo",
        creado_en: datetime | None = None,
    ) -> AjusteVigencia:
        fila = AjusteVigencia(
            pieza_id=pieza.id,
            inspeccion_id=inspeccion.id,
            vigente_hasta_anterior=anterior,
            vigente_hasta_nuevo=nuevo,
            motivo=motivo,
            usuario_id=self.usuario("supervisor").id,
            creado_en=creado_en or ahora_utc(),
        )
        self.session.add(fila)
        self.session.flush()
        return fila


@pytest.fixture
def datos(session: Session) -> Datos:
    return Datos(session)


@pytest.fixture
def cliente_con(app, crear_usuario) -> Callable[..., TestClient]:
    """`cliente_con(P.X, P.Y, almacen="KEP")`: sesión de un usuario con exactamente esos
    permisos (sin almacén si no se indica)."""
    clientes: list[TestClient] = []

    def _cliente(*permisos: str, almacen: str | None = None) -> TestClient:
        usuario: UsuarioPrueba = crear_usuario(set(permisos), almacen=almacen)
        cliente = TestClient(app)
        respuesta = iniciar_sesion_en(cliente, usuario)
        assert respuesta.status_code == 200, respuesta.text
        clientes.append(cliente)
        return cliente

    yield _cliente
    for c in clientes:
        c.close()


@pytest.fixture
def usuario_de(crear_usuario, session):
    """El `Usuario` (modelo) creado con `crear_usuario`, para filtrar por su id."""

    def _usuario(nombre_usuario: str) -> Usuario:
        return UsuarioRepository(session).get_by_usuario(nombre_usuario)

    return _usuario
