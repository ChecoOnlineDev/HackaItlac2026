"""Pruebas de la fundación: salud, ids, constraints, migración, archivos y auditoría."""

import uuid
from datetime import UTC, datetime

import pytest
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError

from alembic import command
from app.config import get_settings
from app.core.errores_bd import (
    ERRNO_CHECK,
    ERRNO_LLAVE_FORANEA_HIJO,
    ERRNO_UNICO,
    es_restriccion,
    violacion,
)
from app.core.ids import nuevo_id
from app.core.tiempo import a_hora_mx, ahora_utc, hoy_mx
from app.db import Base, get_session
from app.modulos.acceso.models import Rol, Usuario
from app.modulos.almacenes.models import Almacen, TipoUbicacion, Ubicacion
from app.modulos.archivos.exceptions import ArchivoInvalido
from app.modulos.archivos.models import TipoAdjunto
from app.modulos.archivos.service import ArchivoService, decodificar_data_url
from app.modulos.auditoria.models import Auditoria
from app.modulos.auditoria.service import AuditoriaService
from app.modulos.catalogo.models import Articulo, Categoria
from app.modulos.movimientos.models import Existencia
from tests.conftest import (
    NOMBRE_BD_PRUEBAS,
    borrar_base,
    config_alembic,
    recrear_base,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32


# -------------------------------------------------------------------- salud


def test_salud_confirma_la_conexion_a_la_base(client):
    r = client.get("/api/salud")
    assert r.status_code == 200
    assert r.json() == {"estado": "ok", "base": "ok"}


def test_salud_sin_base_responde_503_sin_detalles_internos(app, client):
    class SesionRota:
        def execute(self, *_a, **_k):
            raise SQLAlchemyError("Access denied for user 'root'@'x' password=secreto")

    app.dependency_overrides[get_session] = lambda: SesionRota()
    r = client.get("/api/salud")
    assert r.status_code == 503
    assert r.json()["codigo"] == "SERVICIO_NO_DISPONIBLE"
    assert "secreto" not in r.text and "root" not in r.text


def test_una_ruta_inexistente_responde_404_con_el_formato_de_errores(client):
    r = client.get("/api/no-existe")
    assert r.status_code == 404
    assert r.json()["codigo"] == "NO_ENCONTRADO"
    assert set(r.json()) == {"codigo", "mensaje", "detalles"}


# ---------------------------------------------------------------------- ids


def test_RG_ids_son_uuid_version_7_y_crecen_con_el_tiempo():
    ids = [nuevo_id() for _ in range(50)]
    assert all(i.version == 7 for i in ids)
    assert ids == sorted(ids)
    assert len(set(ids)) == 50


def test_RG_11_las_fechas_se_guardan_en_utc_naive_y_se_muestran_en_hora_de_mexico():
    ahora = ahora_utc()
    assert ahora.tzinfo is None
    assert abs((datetime.now(UTC).replace(tzinfo=None) - ahora).total_seconds()) < 5
    enero = datetime(2026, 1, 15, 18, 0)
    assert a_hora_mx(enero).hour == 12  # UTC-6
    assert hoy_mx() is not None


def test_el_id_de_un_registro_nuevo_lo_pone_el_servidor_como_uuid7(session):
    rol = Rol(nombre="Rol de id")
    session.add(rol)
    session.flush()
    assert rol.id.version == 7
    assert rol.creado_en is not None and rol.creado_en.tzinfo is None


# ------------------------------------------------- traducción de constraints


def _insertar_usuario(session, nombre_usuario: str, rol_id) -> None:
    session.add(Usuario(usuario=nombre_usuario, nombre="X", contrasena_hash="h", rol_id=rol_id))
    session.flush()


def test_errores_bd_detecta_el_unico_violado_por_su_nombre(session):
    rol = Rol(nombre="Rol para unicos")
    session.add(rol)
    session.flush()
    _insertar_usuario(session, "repetido", rol.id)
    with pytest.raises(IntegrityError) as error:
        with session.begin_nested():
            _insertar_usuario(session, "repetido", rol.id)
    assert violacion(error.value).errno == ERRNO_UNICO
    assert es_restriccion(error.value, "uq_usuario_usuario")
    assert not es_restriccion(error.value, "uq_otro")


def test_errores_bd_detecta_la_llave_foranea_violada_por_su_nombre(session):
    with pytest.raises(IntegrityError) as error:
        with session.begin_nested():
            _insertar_usuario(session, "sin_rol", uuid.uuid4())
    assert violacion(error.value).errno == ERRNO_LLAVE_FORANEA_HIJO
    assert es_restriccion(error.value, "fk_usuario_rol_id_rol")


def test_RG_04_una_existencia_negativa_la_rechaza_la_base_y_se_detecta_por_nombre(session):
    almacen = session.scalar(select(Almacen).where(Almacen.clave == "KEP"))
    ubicacion = session.scalar(select(Ubicacion).where(Ubicacion.almacen_id == almacen.id))
    categoria = Categoria(
        nombre="Cat. prueba", tipo="HERRAMIENTA", control="CANTIDAD", retornable=True
    )
    session.add(categoria)
    session.flush()
    articulo = Articulo(
        codigo="T-001",
        nombre="Martillo",
        categoria_id=categoria.id,
        control="CANTIDAD",
        retornable=True,
    )
    session.add(articulo)
    session.flush()
    with pytest.raises(DBAPIError) as error:
        with session.begin_nested():
            session.add(Existencia(ubicacion_id=ubicacion.id, articulo_id=articulo.id, cantidad=-1))
            session.flush()
    assert violacion(error.value).errno == ERRNO_CHECK
    assert es_restriccion(error.value, "ck_existencia_cantidad_no_negativa")


def test_una_ubicacion_tiene_exactamente_un_destino_posible(session):
    almacen = session.scalar(select(Almacen).where(Almacen.clave == "KEP"))
    with pytest.raises(DBAPIError) as error:
        with session.begin_nested():
            session.add(
                Ubicacion(tipo=TipoUbicacion.VIRTUAL, almacen_id=almacen.id, virtual="BAJA")
            )
            session.flush()
    assert es_restriccion(error.value, "ck_ubicacion_exactamente_uno") or es_restriccion(
        error.value, "uq_ubicacion_virtual"
    )
    with pytest.raises(DBAPIError) as sin_nada:
        with session.begin_nested():
            session.add(Ubicacion(tipo=TipoUbicacion.ALMACEN))
            session.flush()
    assert es_restriccion(sin_nada.value, "ck_ubicacion_exactamente_uno")


def test_los_datos_de_prueba_dejan_seis_almacenes_y_cuatro_ubicaciones_virtuales(session):
    claves = set(session.scalars(select(Almacen.clave)))
    assert claves == {"KEP", "CON", "MID", "HYL", "LAM", "MIN"}
    virtuales = set(
        session.scalars(select(Ubicacion.virtual).where(Ubicacion.virtual.is_not(None)))
    )
    assert virtuales == {"PROVEEDOR", "EN_TRANSITO", "CONSUMIDO", "BAJA"}
    ubicaciones_almacen = session.scalars(
        select(Ubicacion).where(Ubicacion.almacen_id.is_not(None))
    ).all()
    assert len(ubicaciones_almacen) == 6
    kep = session.scalar(select(Almacen).where(Almacen.clave == "KEP"))
    con = session.scalar(select(Almacen).where(Almacen.clave == "CON"))
    mid = session.scalar(select(Almacen).where(Almacen.clave == "MID"))
    assert kep.padre_id is None and con.padre_id == kep.id and mid.padre_id == con.id


def test_los_datos_de_prueba_son_repetibles(session):
    from app.datos_prueba import cargar_todo

    antes = session.scalar(text("SELECT COUNT(*) FROM usuario"))
    cargar_todo(session)
    cargar_todo(session)
    assert session.scalar(text("SELECT COUNT(*) FROM usuario")) == antes
    assert session.scalar(text("SELECT COUNT(*) FROM rol")) >= 5


# ---------------------------------------------------------------- migración


def test_la_migracion_sube_baja_y_coincide_con_los_modelos():
    nombre = f"{NOMBRE_BD_PRUEBAS}_migra"
    recrear_base(nombre)
    ajustes = get_settings()
    url = ajustes.database_url.set(database=nombre)
    motor = create_engine(url)
    try:
        cfg = config_alembic()
        with motor.begin() as conexion:
            cfg.attributes["connection"] = conexion
            command.upgrade(cfg, "head")
        tablas = set(inspect(motor).get_table_names())
        esperadas = set(Base.metadata.tables) | {"alembic_version"}
        assert tablas == esperadas
        assert len(Base.metadata.tables) == 23  # las 21 del modelo de datos y puesto y dotacion

        # Los modelos y la migración no difieren (lo que revisa `alembic check`).
        with motor.connect() as conexion:
            contexto = MigrationContext.configure(conexion, opts={"compare_type": True})
            assert compare_metadata(contexto, Base.metadata) == []

        with motor.begin() as conexion:
            cfg.attributes["connection"] = conexion
            command.downgrade(cfg, "base")
        assert set(inspect(motor).get_table_names()) == {"alembic_version"}

        with motor.begin() as conexion:
            cfg.attributes["connection"] = conexion
            command.upgrade(cfg, "head")
        assert set(inspect(motor).get_table_names()) == esperadas
    finally:
        motor.dispose()
        borrar_base(nombre)


# ----------------------------------------------------------------- archivos


@pytest.fixture
def volumen(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "archivos_dir", tmp_path)
    return tmp_path


def _usuario_id(session):
    return session.scalar(select(Usuario.id).where(Usuario.usuario == "almacenista"))


def test_archivos_guarda_la_imagen_valida_con_nombre_generado_y_sha256(session, volumen):
    adjunto = ArchivoService(session).guardar(
        tipo=TipoAdjunto.FOTO_DANO, contenido=PNG, subido_por=_usuario_id(session)
    )
    assert adjunto.mime == "image/png"
    assert adjunto.tamano == len(PNG)
    assert len(adjunto.sha256) == 64
    assert adjunto.ruta.startswith("fotos_dano/") and adjunto.ruta.endswith(".png")
    assert (volumen / adjunto.ruta).read_bytes() == PNG
    leido, contenido = ArchivoService(session).leer(adjunto.id)
    assert contenido == PNG and leido.id == adjunto.id


def test_archivos_valida_el_tipo_por_el_contenido_y_no_por_lo_que_diga_el_cliente(session, volumen):
    servicio = ArchivoService(session)
    with pytest.raises(ArchivoInvalido):
        servicio.guardar(
            tipo=TipoAdjunto.FOTO_TRABAJADOR,
            contenido=b"MZ\x90\x00 programa.exe disfrazado de foto.jpg",
            subido_por=_usuario_id(session),
        )
    jpeg = servicio.guardar(
        tipo=TipoAdjunto.FOTO_TRABAJADOR, contenido=JPEG, subido_por=_usuario_id(session)
    )
    assert jpeg.mime == "image/jpeg"


def test_archivos_rechaza_vacio_y_demasiado_grande(session, volumen, monkeypatch):
    servicio = ArchivoService(session)
    with pytest.raises(ArchivoInvalido):
        servicio.guardar(tipo=TipoAdjunto.FIRMA, contenido=b"", subido_por=_usuario_id(session))
    monkeypatch.setattr(get_settings(), "archivo_tamano_maximo", 100)
    with pytest.raises(ArchivoInvalido) as error:
        servicio.guardar(
            tipo=TipoAdjunto.FIRMA, contenido=PNG + b"0" * 100, subido_por=_usuario_id(session)
        )
    assert error.value.detalles == {"tamano_maximo": 100}


def test_archivos_decodifica_la_imagen_de_un_data_url():
    import base64

    url = "data:image/png;base64," + base64.b64encode(PNG).decode()
    assert decodificar_data_url(url) == PNG
    with pytest.raises(ArchivoInvalido):
        decodificar_data_url("no es una imagen")


# ---------------------------------------------------------------- auditoria


def test_auditoria_registra_y_oculta_los_secretos(session):
    usuario_id = _usuario_id(session)
    AuditoriaService(session).registrar(
        usuario_id=usuario_id,
        accion="catalogo.articulo_editado",
        entidad="articulo",
        entidad_id=uuid.uuid4(),
        antes={"nombre": "A", "pin_hash": "xyz"},
        despues={"nombre": "B", "contrasena": "abc", "fecha": datetime(2026, 1, 1)},
    )
    session.commit()
    fila = session.scalar(select(Auditoria).where(Auditoria.accion == "catalogo.articulo_editado"))
    assert fila.antes == {"nombre": "A", "pin_hash": "[oculto]"}
    assert fila.despues["contrasena"] == "[oculto]"
    assert fila.despues["fecha"] == "2026-01-01T00:00:00"
