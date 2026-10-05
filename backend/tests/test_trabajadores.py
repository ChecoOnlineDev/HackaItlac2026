"""Módulo `trabajadores`: alta, ficha, reingreso, credencial, foto y baja.

Cada prueba lleva en su nombre el ID de la regla que comprueba. Como `movimientos` todavía no
existe, el resguardo y el vale de no adeudo se simulan insertando filas con los modelos.
"""

import itertools
import uuid
from collections.abc import Callable
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.excepciones import NoEncontrado
from app.core.ids import nuevo_id
from app.core.tiempo import ahora_utc, hoy_mx
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.acceso.repository import UsuarioRepository
from app.modulos.almacenes.repository import AlmacenRepository, UbicacionRepository
from app.modulos.auditoria.models import Auditoria
from app.modulos.catalogo.codigos import CodigoRepetido, CodigoService
from app.modulos.catalogo.models import Articulo, Categoria, Pieza, TipoCodigo
from app.modulos.movimientos.models import Existencia, Movimiento, TipoVale, Vale
from app.modulos.trabajadores import datos_prueba
from app.modulos.trabajadores.exceptions import TrabajadorConPendientes
from app.modulos.trabajadores.models import EstadoTrabajador, PeriodoContrato, Trabajador
from app.modulos.trabajadores.repository import TrabajadorRepository
from app.modulos.trabajadores.service import TrabajadorService

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
_contador = itertools.count(1)


# ---------------------------------------------------------------- utilidades


def _n() -> int:
    return next(_contador)


def payload(**cambios) -> dict:
    hoy = hoy_mx()
    n = _n()
    datos = {
        "nombre": f"Trabajador de prueba {n}",
        "numero_empleado": f"PRB-{n:05d}",
        "puesto": "Soldador",
        "area_obra": "Midrex",
        "inicio": (hoy - timedelta(days=10)).isoformat(),
        "fin": (hoy + timedelta(days=100)).isoformat(),
    }
    datos.update(cambios)
    return datos


@pytest.fixture
def rh(cliente_como: Callable[[str], TestClient]) -> TestClient:
    return cliente_como("Recursos Humanos")


@pytest.fixture
def almacenista(cliente_como: Callable[[str], TestClient]) -> TestClient:
    return cliente_como("Almacenista")


@pytest.fixture
def servicio(session: Session) -> TrabajadorService:
    return TrabajadorService(session)


@pytest.fixture
def actor(session: Session) -> Usuario:
    usuario = UsuarioRepository(session).get_by_usuario("rh")
    assert usuario is not None
    return usuario


@pytest.fixture
def archivos_tmp(tmp_path, monkeypatch):
    """Las fotos de las pruebas van a una carpeta temporal."""
    monkeypatch.setattr(get_settings(), "archivos_dir", tmp_path)
    return tmp_path


@pytest.fixture
def cliente_con(app, crear_usuario, iniciar_sesion) -> Callable[..., TestClient]:
    clientes: list[TestClient] = []

    def _cliente(*permisos: str) -> TestClient:
        usuario = crear_usuario(set(permisos))
        cliente = TestClient(app)
        assert iniciar_sesion(cliente, usuario).status_code == 200
        clientes.append(cliente)
        return cliente

    yield _cliente
    for c in clientes:
        c.close()


def dar_de_alta(rh: TestClient, **cambios) -> dict:
    respuesta = rh.post("/api/trabajadores", json=payload(**cambios))
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def trabajador_de_prueba(session: Session, numero: str) -> Trabajador:
    t = TrabajadorRepository(session).get_by_numero(numero)
    assert t is not None
    return t


def crear_articulo(session: Session, *, control: str, retornable: bool) -> Articulo:
    n = _n()
    categoria = Categoria(
        nombre=f"Categoría de prueba {n}",
        tipo="HERRAMIENTA",
        control=control,
        retornable=retornable,
    )
    session.add(categoria)
    session.flush()
    articulo = Articulo(
        codigo=f"ART-PRB-{n}",
        nombre=f"Artículo de prueba {n}",
        categoria_id=categoria.id,
        control=control,
        retornable=retornable,
    )
    session.add(articulo)
    session.flush()
    return articulo


def entregar(
    session: Session,
    trabajador: Trabajador,
    articulo: Articulo,
    *,
    cantidad: int = 1,
    almacen: str = "KEP",
    fecha=None,
) -> Pieza | None:
    """Simula lo que haría `movimientos` al entregar: vale, movimiento, existencia y pieza."""
    n = _n()
    sede = AlmacenRepository(session).get_by_clave(almacen)
    ubicaciones = UbicacionRepository(session)
    origen = ubicaciones.de_almacen(sede.id)
    destino = ubicaciones.de_trabajador(trabajador.id)
    responsable = UsuarioRepository(session).get_by_usuario("almacenista")
    vale = Vale(
        id_cliente=nuevo_id(),
        tipo=TipoVale.ENTREGA,
        folio=f"{almacen}-ENT-T{n:06d}",
        almacen_id=sede.id,
        trabajador_id=trabajador.id,
        responsable_id=responsable.id,
        token=uuid.uuid4().hex,
        creado_en=fecha or ahora_utc(),
    )
    session.add(vale)
    session.flush()
    pieza = None
    if articulo.control == "PIEZA":
        pieza = Pieza(
            articulo_id=articulo.id,
            codigo=f"PZA-PRB-{n}",
            numero_serie=f"SN-{n}",
            ubicacion_id=destino.id,
        )
        session.add(pieza)
        session.flush()
    session.add(
        Movimiento(
            vale_id=vale.id,
            renglon=1,
            articulo_id=articulo.id,
            pieza_id=pieza.id if pieza else None,
            cantidad=1 if pieza else cantidad,
            origen_id=origen.id,
            destino_id=destino.id,
            creado_en=fecha or ahora_utc(),
        )
    )
    session.add(Existencia(ubicacion_id=destino.id, articulo_id=articulo.id, cantidad=cantidad))
    session.flush()
    return pieza


def emitir_no_adeudo(session: Session, trabajador: Trabajador) -> Vale:
    n = _n()
    sede = AlmacenRepository(session).get_by_clave("KEP")
    responsable = UsuarioRepository(session).get_by_usuario("almacenista")
    vale = Vale(
        id_cliente=nuevo_id(),
        tipo=TipoVale.NO_ADEUDO,
        folio=f"KEP-NAD-T{n:06d}",
        almacen_id=sede.id,
        trabajador_id=trabajador.id,
        responsable_id=responsable.id,
        token=uuid.uuid4().hex,
    )
    session.add(vale)
    session.flush()
    return vale


def acciones_de_auditoria(session: Session, trabajador_id: str) -> list[str]:
    filas = session.scalars(
        select(Auditoria)
        .where(Auditoria.entidad == "trabajador", Auditoria.entidad_id == str(trabajador_id))
        .order_by(Auditoria.creado_en)
    )
    return [f.accion for f in filas]


# ============================================================ alta (T-01, T-03)


def test_T_03_alta_con_los_datos_obligatorios_deja_al_trabajador_activo_y_vigente(
    rh: TestClient, session: Session
) -> None:
    datos = payload(nombre="Pedro Páramo", puesto="Rigger", area_obra="Minas")
    respuesta = rh.post("/api/trabajadores", json=datos)

    assert respuesta.status_code == 201, respuesta.text
    ficha = respuesta.json()
    assert ficha["nombre"] == "Pedro Páramo"
    assert ficha["numero_empleado"] == datos["numero_empleado"]
    assert ficha["estado"] == "ACTIVO"
    assert ficha["puesto"] == "Rigger"
    assert ficha["area_obra"] == "Minas"
    assert ficha["periodo"]["inicio"] == datos["inicio"]
    assert ficha["vigencia"] == {"vigente": True, "motivo": None, "regla": "T-07"}
    assert ficha["situacion"] == "SIN_PENDIENTES"
    assert ficha["tiene_foto"] is False
    # RH tiene el permiso de datos personales: la clave aparece (vacía si no se capturó).
    assert ficha["curp"] is None and ficha["nss"] is None
    # Al darlo de alta se le crea su ubicación (el trabajador es una ubicación).
    trabajador = trabajador_de_prueba(session, datos["numero_empleado"])
    assert UbicacionRepository(session).de_trabajador(trabajador.id) is not None


def test_T_03_alta_guarda_tallas_curp_y_nss_opcionales(rh: TestClient) -> None:
    ficha = dar_de_alta(
        rh,
        tallas={"camisa": "L", "calzado": "28"},
        curp="gamc850505mdfrrr07",
        nss="12345678901",
    )
    assert ficha["tallas"] == {"camisa": "L", "calzado": "28"}
    assert ficha["curp"] == "GAMC850505MDFRRR07"
    assert ficha["nss"] == "12345678901"


@pytest.mark.parametrize(
    "falta", ["nombre", "numero_empleado", "puesto", "area_obra", "inicio", "fin"]
)
def test_T_03_faltar_un_dato_obligatorio_se_rechaza(rh: TestClient, falta: str) -> None:
    datos = payload()
    del datos[falta]
    respuesta = rh.post("/api/trabajadores", json=datos)
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "DATOS_INVALIDOS"
    assert respuesta.json()["detalles"][0]["campo"] == falta


def test_T_03_una_fecha_de_fin_anterior_al_inicio_se_rechaza(
    rh: TestClient, session: Session
) -> None:
    hoy = hoy_mx()
    datos = payload(inicio=hoy.isoformat(), fin=(hoy - timedelta(days=1)).isoformat())
    respuesta = rh.post("/api/trabajadores", json=datos)

    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "DATOS_INVALIDOS"
    assert respuesta.json()["detalles"]["campo"] == "fin"
    assert TrabajadorRepository(session).get_by_numero(datos["numero_empleado"]) is None


def test_T_03_un_periodo_de_un_solo_dia_es_valido(rh: TestClient) -> None:
    hoy = hoy_mx().isoformat()
    ficha = dar_de_alta(rh, inicio=hoy, fin=hoy)
    assert ficha["vigencia"]["vigente"] is True


def test_T_03_curp_y_nss_con_forma_incorrecta_se_rechazan(rh: TestClient) -> None:
    assert rh.post("/api/trabajadores", json=payload(curp="CORTA")).status_code == 422
    assert rh.post("/api/trabajadores", json=payload(nss="12AB")).status_code == 422


def test_T_01_un_numero_de_empleado_repetido_responde_409_con_la_persona(
    rh: TestClient,
) -> None:
    existente = dar_de_alta(rh, nombre="Persona Original")
    repetido = payload(numero_empleado=existente["numero_empleado"], nombre="Otra Persona")

    respuesta = rh.post("/api/trabajadores", json=repetido)

    assert respuesta.status_code == 409
    cuerpo = respuesta.json()
    assert cuerpo["codigo"] == "TRABAJADOR_EXISTE"
    assert cuerpo["detalles"]["regla"] == "T-02"
    assert cuerpo["detalles"]["coincide_por"] == "numero_empleado"
    assert cuerpo["detalles"]["trabajador"]["id"] == existente["id"]
    assert cuerpo["detalles"]["trabajador"]["nombre"] == "Persona Original"


def test_T_02_una_curp_repetida_tambien_ofrece_el_reingreso(rh: TestClient) -> None:
    existente = dar_de_alta(rh, curp="AAAA900101HDFRRR01")

    respuesta = rh.post("/api/trabajadores", json=payload(curp="AAAA900101HDFRRR01"))

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "TRABAJADOR_EXISTE"
    assert respuesta.json()["detalles"]["coincide_por"] == "curp"
    assert respuesta.json()["detalles"]["trabajador"]["id"] == existente["id"]


def test_T_03_el_alta_queda_en_la_auditoria_sin_guardar_curp_ni_nss(
    rh: TestClient, session: Session
) -> None:
    ficha = dar_de_alta(rh, curp="BBBB900101HDFRRR01", nss="12345678901")
    assert acciones_de_auditoria(session, ficha["id"]) == ["trabajador.alta"]
    fila = session.scalar(select(Auditoria).where(Auditoria.entidad_id == ficha["id"]))
    assert "BBBB900101HDFRRR01" not in str(fila.despues)
    assert "12345678901" not in str(fila.despues)


# ================================================================ vigencia (T-07, E-02)


def test_T_07_un_trabajador_activo_dentro_de_su_periodo_es_vigente(
    session: Session, servicio: TrabajadorService
) -> None:
    t = trabajador_de_prueba(session, "EMP-1001")
    assert servicio.es_vigente(t) is True
    assert servicio.motivo_no_vigente(t) is None
    assert servicio.periodo_vigente(t) is not None


def test_T_07_el_ultimo_dia_del_periodo_todavia_es_vigente(
    session: Session, servicio: TrabajadorService
) -> None:
    t = trabajador_de_prueba(session, "EMP-1002")  # contrato vencido hace 10 días
    periodo = servicio.periodo_vigente(t)
    assert servicio.es_vigente(t, periodo.fin) is True


def test_T_07_el_dia_despues_de_terminar_el_periodo_ya_no_es_vigente(
    session: Session, servicio: TrabajadorService
) -> None:
    t = trabajador_de_prueba(session, "EMP-1002")
    periodo = servicio.periodo_vigente(t)
    vigencia = servicio.evaluar_vigencia(t, periodo.fin + timedelta(days=1))
    assert vigencia.vigente is False
    assert vigencia.regla == "E-02"
    assert "contrato terminó" in vigencia.motivo
    assert periodo.fin.strftime("%d/%m/%Y") in vigencia.motivo


def test_T_07_un_periodo_que_aun_no_inicia_no_es_vigente_pero_el_trabajador_existe(
    session: Session, servicio: TrabajadorService
) -> None:
    t = trabajador_de_prueba(session, "EMP-1004")  # inicia en 15 días
    assert t.estado == EstadoTrabajador.ACTIVO
    vigencia = servicio.evaluar_vigencia(t)
    assert vigencia.vigente is False
    assert "inicia el" in vigencia.motivo


def test_T_07_el_alta_con_periodo_futuro_crea_al_trabajador_sin_vigencia(rh: TestClient) -> None:
    hoy = hoy_mx()
    ficha = dar_de_alta(
        rh,
        inicio=(hoy + timedelta(days=5)).isoformat(),
        fin=(hoy + timedelta(days=50)).isoformat(),
    )
    assert ficha["estado"] == "ACTIVO"
    assert ficha["vigencia"]["vigente"] is False
    assert ficha["vigencia"]["regla"] == "E-02"


def test_E_02_un_trabajador_en_baja_en_proceso_no_es_vigente(
    session: Session, servicio: TrabajadorService
) -> None:
    t = trabajador_de_prueba(session, "EMP-1003")
    vigencia = servicio.evaluar_vigencia(t)
    assert vigencia.vigente is False
    assert vigencia.regla == "E-02"
    assert "baja está en proceso" in vigencia.motivo
    assert "ya no forma parte de la plantilla" in vigencia.motivo.lower()


def test_E_02_un_trabajador_inactivo_no_es_vigente_aunque_su_periodo_incluya_hoy(
    session: Session, servicio: TrabajadorService
) -> None:
    t = trabajador_de_prueba(session, "EMP-1001")
    t.estado = EstadoTrabajador.INACTIVO
    vigencia = servicio.evaluar_vigencia(t)
    assert vigencia.vigente is False
    assert "ya no forma parte de la plantilla" in vigencia.motivo.lower()


def test_E_02_la_fecha_se_compara_en_la_zona_de_mexico(
    session: Session, servicio: TrabajadorService, monkeypatch
) -> None:
    from app.modulos.trabajadores import service as modulo

    t = trabajador_de_prueba(session, "EMP-1002")
    fin = servicio.periodo_vigente(t).fin
    monkeypatch.setattr(modulo, "hoy_mx", lambda: fin)
    assert servicio.es_vigente(t) is True
    monkeypatch.setattr(modulo, "hoy_mx", lambda: fin + timedelta(days=1))
    assert servicio.es_vigente(t) is False


# ============================================================ reingreso (T-02)


def test_T_02_el_reingreso_registra_un_periodo_nuevo_y_regresa_a_activo(
    rh: TestClient, session: Session, servicio: TrabajadorService
) -> None:
    t = trabajador_de_prueba(session, "EMP-1002")
    t.estado = EstadoTrabajador.INACTIVO
    session.flush()
    hoy = hoy_mx()

    respuesta = rh.post(
        f"/api/trabajadores/{t.id}/periodos",
        json={
            "inicio": hoy.isoformat(),
            "fin": (hoy + timedelta(days=180)).isoformat(),
            "puesto": "Supervisor de obra",
        },
    )

    assert respuesta.status_code == 201, respuesta.text
    ficha = respuesta.json()
    assert ficha["estado"] == "ACTIVO"
    assert ficha["vigencia"]["vigente"] is True
    assert ficha["puesto"] == "Supervisor de obra"
    assert ficha["area_obra"] == "HYL"  # se conserva del periodo anterior
    # Los periodos anteriores se conservan.
    assert len(TrabajadorRepository(session).periodos(t.id)) == 2
    assert "trabajador.periodo" in acciones_de_auditoria(session, t.id)


def test_T_02_extender_un_contrato_es_registrar_un_periodo_nuevo(
    rh: TestClient, session: Session
) -> None:
    t = trabajador_de_prueba(session, "EMP-1001")
    periodo = TrabajadorRepository(session).periodos(t.id)[0]
    nuevo_fin = (periodo.fin + timedelta(days=365)).isoformat()

    respuesta = rh.post(
        f"/api/trabajadores/{t.id}/periodos",
        json={"inicio": (periodo.fin + timedelta(days=1)).isoformat(), "fin": nuevo_fin},
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["estado"] == "ACTIVO"
    # Mientras el periodo anterior rige, sigue siendo vigente.
    assert respuesta.json()["vigencia"]["vigente"] is True
    assert len(TrabajadorRepository(session).periodos(t.id)) == 2


def test_T_02_un_reingreso_con_inicio_futuro_deja_activo_pero_no_vigente(
    rh: TestClient, session: Session
) -> None:
    t = trabajador_de_prueba(session, "EMP-1002")
    hoy = hoy_mx()

    respuesta = rh.post(
        f"/api/trabajadores/{t.id}/periodos",
        json={
            "inicio": (hoy + timedelta(days=7)).isoformat(),
            "fin": (hoy + timedelta(days=90)).isoformat(),
        },
    )

    ficha = respuesta.json()
    assert ficha["estado"] == "ACTIVO"
    assert ficha["vigencia"]["vigente"] is False
    assert "inicia el" in ficha["vigencia"]["motivo"]


def test_T_02_un_reingreso_con_fin_anterior_al_inicio_se_rechaza(
    rh: TestClient, session: Session
) -> None:
    t = trabajador_de_prueba(session, "EMP-1002")
    hoy = hoy_mx()
    respuesta = rh.post(
        f"/api/trabajadores/{t.id}/periodos",
        json={"inicio": hoy.isoformat(), "fin": (hoy - timedelta(days=1)).isoformat()},
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["detalles"]["campo"] == "fin"
    assert len(TrabajadorRepository(session).periodos(t.id)) == 1


def test_T_02_reingresar_a_un_trabajador_que_no_existe_responde_404(rh: TestClient) -> None:
    hoy = hoy_mx().isoformat()
    respuesta = rh.post(
        f"/api/trabajadores/{uuid.uuid4()}/periodos", json={"inicio": hoy, "fin": hoy}
    )
    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "NO_ENCONTRADO"


def test_B_05_los_pendientes_de_un_periodo_anterior_se_conservan_y_se_marcan(
    rh: TestClient, session: Session
) -> None:
    t = trabajador_de_prueba(session, "EMP-1002")
    articulo = crear_articulo(session, control="PIEZA", retornable=True)
    entregar(session, t, articulo, fecha=ahora_utc() - timedelta(days=300))
    t.estado = EstadoTrabajador.INACTIVO
    hoy = hoy_mx()

    ficha = rh.post(
        f"/api/trabajadores/{t.id}/periodos",
        json={"inicio": hoy.isoformat(), "fin": (hoy + timedelta(days=90)).isoformat()},
    ).json()

    assert ficha["estado"] == "ACTIVO"
    assert ficha["pendientes"]["total"] == 1
    assert ficha["pendientes"]["de_periodos_anteriores"] == 1
    assert ficha["pendientes"]["regla"] == "E-12"
    assert ficha["resguardo"][0]["de_periodo_anterior"] is True


# ============================================================ credencial (T-05)


def test_T_05_liga_la_credencial_escaneada_al_trabajador(
    rh: TestClient, session: Session, servicio: TrabajadorService
) -> None:
    ficha = dar_de_alta(rh)

    respuesta = rh.post(f"/api/trabajadores/{ficha['id']}/codigos", json={"codigo": " CRED-777 "})

    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json() == {"codigo": "CRED-777", "tipo": "TRABAJADOR", "generado": False}
    encontrado = servicio.obtener_por_codigo("CRED-777")
    assert encontrado is not None and str(encontrado.id) == ficha["id"]
    assert rh.get(f"/api/trabajadores/{ficha['id']}").json()["codigos"] == ["CRED-777"]


def test_T_05_sin_codigo_el_sistema_genera_uno_propio_para_imprimir(
    rh: TestClient, servicio: TrabajadorService
) -> None:
    ficha = dar_de_alta(rh)

    respuesta = rh.post(f"/api/trabajadores/{ficha['id']}/codigos", json={})

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["generado"] is True
    assert cuerpo["codigo"].startswith("TRB-")
    assert servicio.obtener_por_codigo(cuerpo["codigo"]).id == uuid.UUID(ficha["id"])


def test_T_05_un_codigo_ya_usado_por_otro_trabajador_se_rechaza_diciendo_de_quien_es(
    rh: TestClient,
) -> None:
    primero = dar_de_alta(rh, nombre="Dueña del código")
    segundo = dar_de_alta(rh)
    rh.post(f"/api/trabajadores/{primero['id']}/codigos", json={"codigo": "CRED-DUP-1"})

    respuesta = rh.post(f"/api/trabajadores/{segundo['id']}/codigos", json={"codigo": "CRED-DUP-1"})

    assert respuesta.status_code == 409
    cuerpo = respuesta.json()
    assert cuerpo["codigo"] == "CODIGO_REPETIDO"
    assert "Dueña del código" in cuerpo["mensaje"]
    assert cuerpo["detalles"]["tipo"] == "TRABAJADOR"
    assert cuerpo["detalles"]["ref_id"] == primero["id"]


def test_T_05_un_codigo_que_es_de_un_articulo_se_rechaza_diciendo_cual(
    rh: TestClient, session: Session
) -> None:
    articulo = crear_articulo(session, control="CANTIDAD", retornable=False)
    CodigoService(session).registrar("COD-DE-ARTICULO", TipoCodigo.ARTICULO, articulo.id)
    ficha = dar_de_alta(rh)

    respuesta = rh.post(
        f"/api/trabajadores/{ficha['id']}/codigos", json={"codigo": "COD-DE-ARTICULO"}
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "CODIGO_REPETIDO"
    assert articulo.nombre in respuesta.json()["mensaje"]


def test_T_05_ligar_dos_veces_el_mismo_codigo_al_mismo_trabajador_no_falla(
    rh: TestClient,
) -> None:
    ficha = dar_de_alta(rh)
    for _ in range(2):
        assert (
            rh.post(
                f"/api/trabajadores/{ficha['id']}/codigos", json={"codigo": "CRED-X-1"}
            ).status_code
            == 201
        )
    assert rh.get(f"/api/trabajadores/{ficha['id']}").json()["codigos"] == ["CRED-X-1"]


def test_T_05_un_trabajador_puede_tener_varios_codigos(rh: TestClient) -> None:
    ficha = dar_de_alta(rh)
    rh.post(f"/api/trabajadores/{ficha['id']}/codigos", json={"codigo": "CRED-V-1"})
    rh.post(f"/api/trabajadores/{ficha['id']}/codigos", json={})
    assert len(rh.get(f"/api/trabajadores/{ficha['id']}").json()["codigos"]) == 2


def test_T_05_obtener_por_codigo_devuelve_none_si_el_codigo_es_de_otra_cosa_o_no_existe(
    session: Session, servicio: TrabajadorService
) -> None:
    articulo = crear_articulo(session, control="CANTIDAD", retornable=False)
    CodigoService(session).registrar("COD-ART-OTRO", TipoCodigo.ARTICULO, articulo.id)
    assert servicio.obtener_por_codigo("COD-ART-OTRO") is None
    assert servicio.obtener_por_codigo("NO-EXISTE-999") is None
    assert servicio.obtener_por_codigo("TRB-1001").numero_empleado == "EMP-1001"


# ========================================================== ficha y búsqueda


def test_T_01_el_servicio_encuentra_por_numero_y_busca_por_nombre_o_numero(
    session: Session, servicio: TrabajadorService
) -> None:
    assert servicio.obtener_por_numero(" EMP-1001 ").nombre == "Juan Pérez Soto"
    assert servicio.obtener_por_numero("EMP-NO") is None
    assert [t.numero_empleado for t in servicio.buscar("ramírez")] == ["EMP-1003"]
    assert [t.numero_empleado for t in servicio.buscar("emp-1004")] == ["EMP-1004"]
    assert servicio.buscar("   ") == []
    assert servicio.buscar("100%") == []  # el comodín se escapa
    with pytest.raises(NoEncontrado):
        servicio.obtener(uuid.uuid4())


def test_T_01_la_ficha_de_un_trabajador_que_no_existe_responde_404(rh: TestClient) -> None:
    respuesta = rh.get(f"/api/trabajadores/{uuid.uuid4()}")
    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "NO_ENCONTRADO"


def test_RG_13_sin_el_permiso_de_datos_personales_la_ficha_no_trae_curp_ni_nss(
    almacenista: TestClient, rh: TestClient, session: Session
) -> None:
    t = trabajador_de_prueba(session, "EMP-1001")
    assert t.curp and t.nss

    como_almacenista = almacenista.get(f"/api/trabajadores/{t.id}")
    como_rh = rh.get(f"/api/trabajadores/{t.id}")

    assert como_almacenista.status_code == 200
    assert "curp" not in como_almacenista.json()
    assert "nss" not in como_almacenista.json()
    assert t.curp not in como_almacenista.text and t.nss not in como_almacenista.text
    assert como_rh.json()["curp"] == t.curp
    assert como_rh.json()["nss"] == t.nss


def test_RG_13_la_lista_y_la_ficha_breve_nunca_traen_curp_ni_nss(
    rh: TestClient, session: Session, servicio: TrabajadorService, actor: Usuario
) -> None:
    t = trabajador_de_prueba(session, "EMP-1001")
    lista = rh.get("/api/trabajadores", params={"q": "EMP-1001"})
    assert lista.status_code == 200
    assert "curp" not in lista.text and "nss" not in lista.text
    assert t.curp not in lista.text and t.nss not in lista.text
    breve = servicio.ficha_breve(t, actor).model_dump_json()
    assert t.curp not in breve and t.nss not in breve


def test_RG_13_la_ficha_indica_nombre_numero_puesto_area_vigencia_y_foto_al_almacenista(
    almacenista: TestClient, session: Session
) -> None:
    t = trabajador_de_prueba(session, "EMP-1001")
    ficha = almacenista.get(f"/api/trabajadores/{t.id}").json()
    assert ficha["nombre"] == "Juan Pérez Soto"
    assert ficha["numero_empleado"] == "EMP-1001"
    assert ficha["puesto"] == "Soldador"
    assert ficha["area_obra"] == "Midrex"
    assert ficha["vigencia"]["vigente"] is True
    assert ficha["tiene_foto"] is False
    assert ficha["foto_url"] is None


def test_E_17_la_ficha_muestra_el_resguardo_con_codigo_fecha_folio_y_almacen(
    almacenista: TestClient, session: Session
) -> None:
    t = trabajador_de_prueba(session, "EMP-1001")
    arnes = crear_articulo(session, control="PIEZA", retornable=True)
    pieza = entregar(session, t, arnes, almacen="CON")

    ficha = almacenista.get(f"/api/trabajadores/{t.id}").json()

    assert len(ficha["resguardo"]) == 1
    renglon = ficha["resguardo"][0]
    assert renglon["codigo"] == pieza.codigo
    assert renglon["numero_serie"] == pieza.numero_serie
    assert renglon["articulo"] == arnes.nombre
    assert renglon["almacen_clave"] == "CON"
    assert renglon["folio"].startswith("CON-ENT-")
    assert renglon["entregado_en"] is not None
    assert "costo" not in str(renglon)
    assert ficha["pendientes"] == {"total": 1, "de_periodos_anteriores": 0, "regla": None}


# ================================================================ lista (T-07, T-08, B-09)


def test_T_08_la_lista_trae_vigencia_y_situacion_de_cada_trabajador(rh: TestClient) -> None:
    respuesta = rh.get("/api/trabajadores", params={"q": "EMP-100", "tamano": 10})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["total"] == 4
    por_numero = {e["numero_empleado"]: e for e in cuerpo["elementos"]}
    assert por_numero["EMP-1001"]["vigencia"]["vigente"] is True
    assert por_numero["EMP-1002"]["vigencia"]["vigente"] is False
    assert por_numero["EMP-1003"]["estado"] == "BAJA_EN_PROCESO"
    assert por_numero["EMP-1004"]["vigencia"]["vigente"] is False
    assert por_numero["EMP-1001"]["situacion"] == "SIN_PENDIENTES"
    assert por_numero["EMP-1001"]["situacion_texto"] == "Sin pendientes"
    assert por_numero["EMP-1001"]["puesto"] == "Soldador"


def test_B_09_la_lista_distingue_sin_pendientes_con_pendientes_y_no_adeudo_emitido(
    rh: TestClient, session: Session
) -> None:
    con = trabajador_de_prueba(session, "EMP-1001")
    sin = trabajador_de_prueba(session, "EMP-1002")
    liberado = trabajador_de_prueba(session, "EMP-1003")
    entregar(session, con, crear_articulo(session, control="PIEZA", retornable=True))
    emitir_no_adeudo(session, liberado)
    liberado.estado = EstadoTrabajador.INACTIVO
    session.flush()

    def situacion_de(numero: str) -> str:
        elementos = rh.get("/api/trabajadores", params={"q": numero}).json()["elementos"]
        return elementos[0]["situacion"]

    assert situacion_de("EMP-1001") == "CON_PENDIENTES"
    assert situacion_de("EMP-1002") == "SIN_PENDIENTES"
    assert situacion_de("EMP-1003") == "NO_ADEUDO_EMITIDO"
    texto = rh.get("/api/trabajadores", params={"q": "EMP-1003"}).json()["elementos"][0]
    assert texto["situacion_texto"] == "No adeudo emitido"
    assert sin.estado == EstadoTrabajador.ACTIVO


def test_B_09_el_filtro_por_situacion_devuelve_solo_esa_situacion(
    rh: TestClient, session: Session
) -> None:
    con = trabajador_de_prueba(session, "EMP-1001")
    entregar(session, con, crear_articulo(session, control="PIEZA", retornable=True))

    pendientes = rh.get("/api/trabajadores", params={"situacion": "CON_PENDIENTES"}).json()
    assert [e["numero_empleado"] for e in pendientes["elementos"]] == ["EMP-1001"]
    assert pendientes["total"] == 1

    limpios = rh.get(
        "/api/trabajadores", params={"situacion": "SIN_PENDIENTES", "q": "EMP-100"}
    ).json()
    assert sorted(e["numero_empleado"] for e in limpios["elementos"]) == [
        "EMP-1002",
        "EMP-1003",
        "EMP-1004",
    ]

    assert rh.get("/api/trabajadores", params={"situacion": "INVENTADA"}).status_code == 422


def test_B_09_un_reingreso_deja_atras_el_no_adeudo_anterior(
    rh: TestClient, session: Session
) -> None:
    t = trabajador_de_prueba(session, "EMP-1003")
    emitir_no_adeudo(session, t)
    t.estado = EstadoTrabajador.INACTIVO
    session.flush()
    hoy = hoy_mx()

    ficha = rh.post(
        f"/api/trabajadores/{t.id}/periodos",
        json={"inicio": hoy.isoformat(), "fin": (hoy + timedelta(days=60)).isoformat()},
    ).json()

    assert ficha["situacion"] == "SIN_PENDIENTES"


def test_T_08_la_lista_se_busca_por_nombre_o_numero_y_se_pagina(rh: TestClient) -> None:
    por_nombre = rh.get("/api/trabajadores", params={"q": "torres luna"}).json()
    assert [e["numero_empleado"] for e in por_nombre["elementos"]] == ["EMP-1002"]

    primera = rh.get("/api/trabajadores", params={"q": "EMP-100", "pagina": 1, "tamano": 3}).json()
    segunda = rh.get("/api/trabajadores", params={"q": "EMP-100", "pagina": 2, "tamano": 3}).json()
    assert primera["total"] == 4 and len(primera["elementos"]) == 3
    assert len(segunda["elementos"]) == 1


# ============================================================== baja (B-01 a B-08)


def test_B_01_iniciar_la_baja_pasa_a_baja_en_proceso_y_ya_no_es_vigente(
    almacenista: TestClient, session: Session
) -> None:
    t = trabajador_de_prueba(session, "EMP-1001")

    respuesta = almacenista.post(f"/api/trabajadores/{t.id}/baja")

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "BAJA_EN_PROCESO"
    assert cuerpo["estado_texto"] == "Baja en proceso"
    assert "B-01" in cuerpo["reglas"]
    assert t.estado == EstadoTrabajador.BAJA_EN_PROCESO
    assert "trabajador.baja" in acciones_de_auditoria(session, t.id)


def test_B_02_al_iniciar_la_baja_responde_los_pendientes_de_todos_los_almacenes(
    almacenista: TestClient, session: Session
) -> None:
    t = trabajador_de_prueba(session, "EMP-1001")
    arnes = crear_articulo(session, control="PIEZA", retornable=True)
    taladro = crear_articulo(session, control="CANTIDAD", retornable=True)
    pieza = entregar(session, t, arnes, almacen="KEP")
    entregar(session, t, taladro, cantidad=2, almacen="MID")

    cuerpo = almacenista.post(f"/api/trabajadores/{t.id}/baja").json()

    assert cuerpo["puede_emitir_no_adeudo"] is False
    assert len(cuerpo["pendientes"]) == 2
    por_articulo = {p["articulo"]: p for p in cuerpo["pendientes"]}
    de_pieza = por_articulo[arnes.nombre]
    assert de_pieza["codigo"] == pieza.codigo
    assert de_pieza["almacen_clave"] == "KEP"
    assert de_pieza["folio"].startswith("KEP-ENT-")
    assert de_pieza["entregado_en"] is not None
    por_cantidad = por_articulo[taladro.nombre]
    assert por_cantidad["codigo"] == taladro.codigo
    assert por_cantidad["cantidad"] == 2
    assert por_cantidad["almacen_clave"] == "MID"


def test_B_03_los_consumibles_no_cuentan_como_pendientes(
    almacenista: TestClient, session: Session, servicio: TrabajadorService
) -> None:
    t = trabajador_de_prueba(session, "EMP-1001")
    guantes = crear_articulo(session, control="CANTIDAD", retornable=False)
    entregar(session, t, guantes, cantidad=10)
    assert servicio.pendientes_de(t.id) == []

    cuerpo = almacenista.post(f"/api/trabajadores/{t.id}/baja").json()

    assert cuerpo["pendientes"] == []
    assert cuerpo["puede_emitir_no_adeudo"] is True


def test_B_01_un_trabajador_que_nunca_recibio_nada_no_tiene_pendientes(
    almacenista: TestClient, session: Session
) -> None:
    t = trabajador_de_prueba(session, "EMP-1004")
    cuerpo = almacenista.post(f"/api/trabajadores/{t.id}/baja").json()
    assert cuerpo["pendientes"] == []
    assert cuerpo["puede_emitir_no_adeudo"] is True


def test_B_01_iniciar_de_nuevo_una_baja_en_proceso_solo_repite_los_pendientes(
    almacenista: TestClient, session: Session
) -> None:
    t = trabajador_de_prueba(session, "EMP-1003")  # ya está en baja en proceso
    respuesta = almacenista.post(f"/api/trabajadores/{t.id}/baja")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "BAJA_EN_PROCESO"
    assert "trabajador.baja" not in acciones_de_auditoria(session, t.id)


def test_T_06_no_se_inicia_la_baja_de_un_trabajador_inactivo(
    almacenista: TestClient, session: Session
) -> None:
    t = trabajador_de_prueba(session, "EMP-1001")
    t.estado = EstadoTrabajador.INACTIVO
    session.flush()
    respuesta = almacenista.post(f"/api/trabajadores/{t.id}/baja")
    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "CONFLICTO"


def test_B_01_iniciar_la_baja_de_un_trabajador_que_no_existe_responde_404(
    almacenista: TestClient,
) -> None:
    assert almacenista.post(f"/api/trabajadores/{uuid.uuid4()}/baja").status_code == 404


def test_B_07_rh_cancela_una_baja_en_proceso_y_el_trabajador_vuelve_a_activo(
    rh: TestClient, session: Session
) -> None:
    t = trabajador_de_prueba(session, "EMP-1003")

    respuesta = rh.delete(f"/api/trabajadores/{t.id}/baja")

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado"] == "ACTIVO"
    assert respuesta.json()["vigencia"]["vigente"] is True
    assert "trabajador.baja_cancelada" in acciones_de_auditoria(session, t.id)


def test_B_07_solo_se_cancela_una_baja_que_esta_en_proceso(
    rh: TestClient, session: Session
) -> None:
    activo = trabajador_de_prueba(session, "EMP-1001")
    respuesta = rh.delete(f"/api/trabajadores/{activo.id}/baja")
    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "CONFLICTO"

    inactivo = trabajador_de_prueba(session, "EMP-1002")
    inactivo.estado = EstadoTrabajador.INACTIVO
    session.flush()
    assert rh.delete(f"/api/trabajadores/{inactivo.id}/baja").status_code == 409


def test_B_08_marcar_inactivo_deja_al_trabajador_inactivo_y_lo_audita(
    session: Session, servicio: TrabajadorService, actor: Usuario
) -> None:
    t = trabajador_de_prueba(session, "EMP-1003")
    servicio.marcar_inactivo(t, actor)
    assert t.estado == EstadoTrabajador.INACTIVO
    assert "trabajador.inactivo" in acciones_de_auditoria(session, t.id)
    # Repetirlo no falla ni duplica el registro.
    servicio.marcar_inactivo(t, actor)
    assert acciones_de_auditoria(session, t.id).count("trabajador.inactivo") == 1


def test_B_04_marcar_inactivo_con_pendientes_se_rechaza(
    session: Session, servicio: TrabajadorService, actor: Usuario
) -> None:
    t = trabajador_de_prueba(session, "EMP-1003")
    entregar(session, t, crear_articulo(session, control="PIEZA", retornable=True))

    with pytest.raises(TrabajadorConPendientes) as error:
        servicio.marcar_inactivo(t, actor)

    assert error.value.codigo == "CON_PENDIENTES"
    assert len(error.value.detalles["pendientes"]) == 1
    assert t.estado == EstadoTrabajador.BAJA_EN_PROCESO


def test_T_06_un_trabajador_en_baja_en_proceso_se_reingresa_y_vuelve_a_activo(
    rh: TestClient, session: Session
) -> None:
    t = trabajador_de_prueba(session, "EMP-1003")
    hoy = hoy_mx()
    ficha = rh.post(
        f"/api/trabajadores/{t.id}/periodos",
        json={"inicio": hoy.isoformat(), "fin": (hoy + timedelta(days=30)).isoformat()},
    ).json()
    assert ficha["estado"] == "ACTIVO"


# ================================================================ foto (T-09)


def test_T_09_sube_la_foto_y_la_ficha_indica_que_la_tiene(
    rh: TestClient, almacenista: TestClient, archivos_tmp, session: Session
) -> None:
    ficha = dar_de_alta(rh)
    assert ficha["tiene_foto"] is False

    respuesta = rh.post(
        f"/api/trabajadores/{ficha['id']}/foto", files={"archivo": ("foto.png", PNG, "image/png")}
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {
        "tiene_foto": True,
        "foto_url": f"/api/trabajadores/{ficha['id']}/foto",
    }
    nueva = almacenista.get(f"/api/trabajadores/{ficha['id']}").json()
    assert nueva["tiene_foto"] is True
    assert nueva["foto_url"] == f"/api/trabajadores/{ficha['id']}/foto"
    assert "trabajador.foto" in acciones_de_auditoria(session, ficha["id"])
    assert any(archivos_tmp.rglob("*.png"))


def test_T_09_entrega_la_imagen_con_su_tipo_de_contenido_solo_con_sesion(
    rh: TestClient, almacenista: TestClient, client: TestClient, archivos_tmp
) -> None:
    ficha = dar_de_alta(rh)
    rh.post(f"/api/trabajadores/{ficha['id']}/foto", files={"archivo": ("f.png", PNG, "image/png")})

    con_sesion = almacenista.get(f"/api/trabajadores/{ficha['id']}/foto")
    sin_sesion = client.get(f"/api/trabajadores/{ficha['id']}/foto")

    assert con_sesion.status_code == 200
    assert con_sesion.headers["content-type"] == "image/png"
    assert con_sesion.content == PNG
    assert sin_sesion.status_code == 401


def test_T_09_el_tipo_se_detecta_por_el_contenido_no_por_el_nombre(
    rh: TestClient, archivos_tmp
) -> None:
    ficha = dar_de_alta(rh)
    jpeg = b"\xff\xd8\xff\xe0" + b"0" * 64
    rh.post(
        f"/api/trabajadores/{ficha['id']}/foto", files={"archivo": ("falsa.png", jpeg, "image/png")}
    )
    assert rh.get(f"/api/trabajadores/{ficha['id']}/foto").headers["content-type"] == "image/jpeg"


def test_T_09_sin_foto_la_consulta_responde_404_y_la_ficha_lo_indica(rh: TestClient) -> None:
    ficha = dar_de_alta(rh)
    respuesta = rh.get(f"/api/trabajadores/{ficha['id']}/foto")
    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "NO_ENCONTRADO"
    assert respuesta.json()["mensaje"] == "Sin foto registrada."


def test_T_09_un_archivo_que_no_es_imagen_se_rechaza(rh: TestClient, archivos_tmp) -> None:
    ficha = dar_de_alta(rh)
    respuesta = rh.post(
        f"/api/trabajadores/{ficha['id']}/foto",
        files={"archivo": ("nota.png", b"esto no es una imagen", "image/png")},
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "DATOS_INVALIDOS"
    assert rh.get(f"/api/trabajadores/{ficha['id']}").json()["tiene_foto"] is False


def test_T_09_una_imagen_mas_grande_que_el_tamano_permitido_se_rechaza(
    rh: TestClient, archivos_tmp
) -> None:
    ficha = dar_de_alta(rh)
    grande = PNG + b"0" * get_settings().archivo_tamano_maximo
    respuesta = rh.post(
        f"/api/trabajadores/{ficha['id']}/foto", files={"archivo": ("g.png", grande, "image/png")}
    )
    assert respuesta.status_code == 422
    assert "MB" in respuesta.json()["mensaje"]
    assert rh.get(f"/api/trabajadores/{ficha['id']}").json()["tiene_foto"] is False


def test_T_09_reemplazar_la_foto_guarda_un_adjunto_nuevo_y_deja_dos_registros_de_cambio(
    rh: TestClient, archivos_tmp, session: Session
) -> None:
    ficha = dar_de_alta(rh)
    url = f"/api/trabajadores/{ficha['id']}/foto"
    rh.post(url, files={"archivo": ("a.png", PNG, "image/png")})
    primero = trabajador_de_prueba(session, ficha["numero_empleado"]).foto_adjunto_id
    otra = b"\x89PNG\r\n\x1a\n" + b"1" * 80
    rh.post(url, files={"archivo": ("b.png", otra, "image/png")})
    segundo = trabajador_de_prueba(session, ficha["numero_empleado"]).foto_adjunto_id

    assert primero is not None and segundo is not None and primero != segundo
    assert rh.get(url).content == otra
    assert acciones_de_auditoria(session, ficha["id"]).count("trabajador.foto") == 2
    cambio = session.scalars(
        select(Auditoria)
        .where(Auditoria.accion == "trabajador.foto", Auditoria.entidad_id == ficha["id"])
        .order_by(Auditoria.creado_en.desc())
    ).first()
    assert cambio.antes == {"foto_adjunto_id": str(primero)}
    assert cambio.despues["foto_adjunto_id"] == str(segundo)


def test_T_09_la_foto_de_un_trabajador_que_no_existe_responde_404(
    rh: TestClient, archivos_tmp
) -> None:
    respuesta = rh.post(
        f"/api/trabajadores/{uuid.uuid4()}/foto", files={"archivo": ("a.png", PNG, "image/png")}
    )
    assert respuesta.status_code == 404


def test_T_09_la_foto_no_aparece_en_la_lista_ni_se_ve_sin_trabajadores_ver(
    rh: TestClient, cliente_con, archivos_tmp
) -> None:
    ficha = dar_de_alta(rh)
    rh.post(f"/api/trabajadores/{ficha['id']}/foto", files={"archivo": ("a.png", PNG, "image/png")})
    sin_ver = cliente_con(P.TRABAJADORES_VER_DATOS_PERSONALES)
    assert sin_ver.get(f"/api/trabajadores/{ficha['id']}/foto").status_code == 403


# ================================================= permisos: con el permiso responde, sin él 403


def _casos(t: Trabajador, otro: Trabajador):
    hoy = hoy_mx()
    fechas = {"inicio": hoy.isoformat(), "fin": (hoy + timedelta(days=30)).isoformat()}
    periodo = {"json": fechas}
    png = {"archivo": ("a.png", PNG, "image/png")}
    return [
        (P.TRABAJADORES_VER, "get", "/api/trabajadores", {}),
        (P.TRABAJADORES_VER, "get", f"/api/trabajadores/{t.id}", {}),
        (P.TRABAJADORES_VER, "get", f"/api/trabajadores/{t.id}/foto", {}),
        (P.TRABAJADORES_ADMINISTRAR, "post", "/api/trabajadores", {"json": payload()}),
        (
            P.TRABAJADORES_ADMINISTRAR,
            "post",
            f"/api/trabajadores/{t.id}/periodos",
            {"json": periodo},
        ),
        (P.TRABAJADORES_ADMINISTRAR, "post", f"/api/trabajadores/{t.id}/codigos", {"json": {}}),
        (P.TRABAJADORES_ADMINISTRAR, "post", f"/api/trabajadores/{t.id}/foto", {"files": png}),
        (P.TRABAJADORES_ADMINISTRAR, "delete", f"/api/trabajadores/{otro.id}/baja", {}),
        (P.TRABAJADORES_INICIAR_BAJA, "post", f"/api/trabajadores/{t.id}/baja", {}),
    ]


def test_AC_04_cada_endpoint_responde_con_su_permiso_y_da_403_sin_el(
    cliente_con, session: Session
) -> None:
    t = trabajador_de_prueba(session, "EMP-1001")
    otro = trabajador_de_prueba(session, "EMP-1003")  # en baja: se puede cancelar
    for permiso, metodo, ruta, extra in _casos(t, otro):
        sin = cliente_con(
            *(
                {
                    P.TRABAJADORES_VER,
                    P.TRABAJADORES_ADMINISTRAR,
                    P.TRABAJADORES_INICIAR_BAJA,
                    P.TRABAJADORES_VER_DATOS_PERSONALES,
                }
                - {permiso}
            )
        )
        con = cliente_con(permiso)
        r_sin = getattr(sin, metodo)(ruta, **extra)
        assert r_sin.status_code == 403, f"{metodo} {ruta} sin {permiso}: {r_sin.status_code}"
        assert r_sin.json()["codigo"] == "SIN_PERMISO"
        r_con = getattr(con, metodo)(ruta, **extra)
        assert r_con.status_code not in (401, 403), f"{metodo} {ruta} con {permiso}: {r_con.text}"


def test_AC_04_sin_sesion_todos_los_endpoints_responden_401(
    client: TestClient, session: Session
) -> None:
    t = trabajador_de_prueba(session, "EMP-1001")
    for _permiso, metodo, ruta, extra in _casos(t, t):
        assert getattr(client, metodo)(ruta, **extra).status_code == 401, f"{metodo} {ruta}"


def test_AC_04_el_permiso_se_verifica_por_clave_y_no_por_el_nombre_del_rol(
    cliente_con, crear_usuario, app, iniciar_sesion
) -> None:
    # Un rol llamado "Recursos Humanos" pero sin permisos no puede dar de alta.
    falso = crear_usuario(set(), nombre_rol="Recursos Humanos (copia)")
    cliente = TestClient(app)
    iniciar_sesion(cliente, falso)
    assert cliente.post("/api/trabajadores", json=payload()).status_code == 403
    # Un rol con otro nombre pero con el permiso sí puede.
    con_permiso = cliente_con(P.TRABAJADORES_ADMINISTRAR, P.TRABAJADORES_VER)
    assert con_permiso.post("/api/trabajadores", json=payload()).status_code == 201


def test_RG_13_con_el_permiso_de_datos_personales_en_otro_rol_se_envian_curp_y_nss(
    cliente_con, session: Session
) -> None:
    t = trabajador_de_prueba(session, "EMP-1001")
    solo_ver = cliente_con(P.TRABAJADORES_VER)
    con_datos = cliente_con(P.TRABAJADORES_VER, P.TRABAJADORES_VER_DATOS_PERSONALES)
    assert "curp" not in solo_ver.get(f"/api/trabajadores/{t.id}").json()
    assert con_datos.get(f"/api/trabajadores/{t.id}").json()["curp"] == t.curp


# ============================================================== datos de prueba


def test_datos_de_prueba_son_repetibles_y_cubren_las_cuatro_situaciones(
    session: Session, servicio: TrabajadorService
) -> None:
    from sqlalchemy import func

    antes = session.scalar(select(func.count()).select_from(Trabajador))
    periodos_antes = session.scalar(select(func.count()).select_from(PeriodoContrato))
    datos_prueba.cargar(session)
    datos_prueba.cargar(session)
    assert session.scalar(select(func.count()).select_from(Trabajador)) == antes
    assert session.scalar(select(func.count()).select_from(PeriodoContrato)) == periodos_antes

    vigente = trabajador_de_prueba(session, "EMP-1001")
    vencido = trabajador_de_prueba(session, "EMP-1002")
    en_baja = trabajador_de_prueba(session, "EMP-1003")
    por_iniciar = trabajador_de_prueba(session, "EMP-1004")
    assert servicio.es_vigente(vigente)
    assert not servicio.es_vigente(vencido) and vencido.estado == EstadoTrabajador.ACTIVO
    assert en_baja.estado == EstadoTrabajador.BAJA_EN_PROCESO
    assert not servicio.es_vigente(por_iniciar) and por_iniciar.estado == EstadoTrabajador.ACTIVO
    for numero, codigo in (
        ("EMP-1001", "TRB-1001"),
        ("EMP-1002", "TRB-1002"),
        ("EMP-1003", "TRB-1003"),
        ("EMP-1004", "TRB-1004"),
    ):
        assert servicio.obtener_por_codigo(codigo).numero_empleado == numero


def test_T_05_un_codigo_de_credencial_de_prueba_no_se_puede_ligar_a_otro(
    session: Session, servicio: TrabajadorService, actor: Usuario
) -> None:
    otro = trabajador_de_prueba(session, "EMP-1002")
    with pytest.raises(CodigoRepetido) as error:
        servicio.ligar_codigo(otro.id, "TRB-1001", actor)
    assert "Juan Pérez Soto" in error.value.mensaje


def test_T_02_la_ficha_lista_todos_los_periodos(rh: TestClient) -> None:
    creado = dar_de_alta(rh)
    hoy = hoy_mx()
    rh.post(
        f"/api/trabajadores/{creado['id']}/periodos",
        json={
            "inicio": (hoy + timedelta(days=400)).isoformat(),
            "fin": (hoy + timedelta(days=500)).isoformat(),
        },
    )

    ficha = rh.get(f"/api/trabajadores/{creado['id']}").json()

    assert len(ficha["periodos"]) == 2
    assert ficha["periodos"][0]["inicio"] > ficha["periodos"][1]["inicio"]
