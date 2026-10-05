# Backend

FastAPI síncrono (PyMySQL), SQLAlchemy 2, Alembic y MySQL 8.4. Las reglas del proyecto están en
`../AGENTS.md` y el mapa de módulos en `../docs/architecture/overview.md`.

## Puesta en marcha

```
cp ../.env.example ../.env              # y cambia los valores
docker compose up -d db                 # en la raíz del repo; espera a "healthy"
uv sync
uv run alembic upgrade head
uv run python -m app.datos_prueba       # repetible
uv run fastapi dev app/main.py --port 21002
```

`GET http://localhost:21002/api/salud` responde `{"estado":"ok","base":"ok"}`.
Documentación interactiva de la API: `http://localhost:21002/api/docs`.

## Comandos

| Acción | Comando |
|---|---|
| Pruebas | `uv run pytest` |
| Lint / formato | `uv run ruff check .` / `uv run ruff format .` |
| Migración nueva | `uv run alembic revision --autogenerate -m "descripcion"` (revisar a mano) |
| Verificar que modelos y migraciones coinciden | `uv run alembic check` |
| Deshacer todo | `uv run alembic downgrade base` |

## Variables de entorno (`../.env`)

| Variable | Para qué | Por defecto |
|---|---|---|
| `MYSQL_HOST`, `MYSQL_PUERTO` | Dónde está MySQL (puerto del host) | `localhost`, `21001` |
| `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD` | Base y usuario de la aplicación | `imhotep`, `imhotep`, sin valor |
| `MYSQL_ROOT_PASSWORD` | Crea el contenedor y las bases de pruebas | sin valor |
| `CLAVE_SESION` | Firma del token de sesión | cambiarla |
| `SESION_HORAS` | Duración de la sesión | `12` |
| `COOKIE_SEGURA` | `true` bajo HTTPS; `false` en desarrollo local por http | `false` |
| `ARCHIVOS_DIR` | Volumen de firmas y fotos | `./almacenamiento` |
| `ARCHIVO_TAMANO_MAXIMO` | Bytes máximos por archivo | `2097152` |
| `CLAVE_DATOS_PRUEBA`, `PIN_DATOS_PRUEBA` | Contraseña y PIN de los usuarios de prueba | ver `.env.example` |
| `TEST_DB_SUFFIX` | Sufijo de la base de pruebas | `main` |

## Datos de prueba

`uv run python -m app.datos_prueba` carga los seis almacenes (KEP, CON, MID, HYL, LAM, MIN), las
ubicaciones, los cinco roles iniciales con los permisos de la sección 8.2 de las reglas y un
usuario por rol. **Son datos de prueba, no reales.** Todos usan la contraseña `CLAVE_DATOS_PRUEBA`;
`admin` y `supervisor` tienen además el PIN `PIN_DATOS_PRUEBA`.

| Usuario | Rol | Almacén |
|---|---|---|
| `admin` | Administrador | todos |
| `supervisor` | Supervisor | todos |
| `compras` | Compras | todos |
| `rh` | Recursos Humanos | ninguno |
| `almacenista` | Almacenista | KEP |
| `alm_con`, `alm_mid`, `alm_hyl`, `alm_lam`, `alm_min` | Almacenista | CON, MID, HYL, LAM, MIN |

## Pruebas

Corren contra MySQL real. La base se llama `{MYSQL_DATABASE}_test_{TEST_DB_SUFFIX}`, se vuelve a
crear en cada corrida y se carga con los datos de prueba. Cada prueba corre en una transacción que
se revierte. **Si varias carpetas de trabajo corren pruebas en paralelo contra el mismo MySQL, cada
una debe usar un `TEST_DB_SUFFIX` distinto.**

Fixtures (`tests/conftest.py`): `client`, `session`, `cliente_como("Almacenista")`,
`usuario_por_rol("Almacenista")`, `crear_usuario({permisos}, almacen="KEP")` e `iniciar_sesion`.
Las pruebas de reglas llevan su ID en el nombre, por ejemplo `test_AC_04_...`.

## Cómo construir un módulo

1. Llena su `models.py` (si tiene tablas nuevas: migración nueva, nunca editar `0001`), `schemas.py`,
   `repository.py`, `service.py`, `exceptions.py` y `router.py`. El router ya está montado en `main.py`.
2. Cada endpoint declara su permiso: `Depends(requiere_permiso(P.ENTREGAS_CREAR))`.
3. El service hace el `commit`; el repository solo `add`, `flush` y consultas.
4. Una excepción de dominio hereda de `app.core.excepciones`; si usa un código nuevo, agrégalo a
   `STATUS_POR_CODIGO` en `app/core/handlers.py` y al contrato de la API.
5. Para detectar un constraint violado captura `DBAPIError` (un CHECK llega como `OperationalError`) y
   usa `app.core.errores_bd.es_restriccion(exc, "uq_...")`.
