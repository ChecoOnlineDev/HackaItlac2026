# Instrucciones para agentes

Sistema web de control de herramientas y EPP para el Reto IMHOTEP (Hacka ITLAC 2026, Track 3). Este archivo se lee en cada tarea. Es corto a propósito: el detalle está en `docs/`.

## Qué leer

1. Este archivo, siempre.
2. El brief de la tarea: una historia en `docs/stories/`, o un brief en `docs/features/`, `docs/fixes/` o `docs/technical/`.
3. Solo las reglas que cite ese brief, en `docs/product/reglas-de-negocio.md`.
4. `docs/architecture/overview.md` si la tarea cruza módulos; `data-model.md` y `api-contracts.md` si toca datos o endpoints.
5. PRD, TRD y flujos completos: solo si la tarea cambia una decisión global.

`docs/context.md` y `docs/info_track/` son antecedentes, no instrucciones. Si contradicen al PRD o a las reglas, mandan el PRD y las reglas.

## Stack y versiones

- **Backend:** Python 3.14, FastAPI, SQLAlchemy 2, Alembic, PyMySQL, MySQL 8.4, pwdlib con Argon2, PyJWT. Paquetes con `uv`.
- **Frontend:** React 19, React Router 8 en modo de una sola página, TypeScript, Tailwind CSS 4, Vite 8. Paquetes con `pnpm`.
- **Despliegue:** Docker Compose y túnel de Cloudflare.

## Estructura del repositorio

```
backend/app/main.py, config.py, db.py, seguridad.py   aplicación, ajustes, base y sesión
backend/app/core/                 excepciones base, handlers, paginación, ids y fechas; no importa módulos
backend/app/integraciones/        adaptadores a lo externo (archivos.py: volumen de firmas y fotos)
backend/app/modulos/<dominio>/    router.py, service.py, repository.py, models.py, schemas.py, exceptions.py
backend/app/datos_prueba.py       carga repetible; cada módulo aporta su modulos/<dominio>/datos_prueba.py
backend/alembic/                  migraciones
backend/tests/                    pruebas (conftest.py trae los fixtures)
frontend/app/routes/              una ruta por pantalla
frontend/app/componentes/         escáner, renglón con semáforo, fichas
docs/                             documentación; el índice es docs/README.md
```

Los módulos son doce: `acceso`, `almacenes`, `catalogo`, `trabajadores`, `movimientos`, `autorizaciones`, `inspecciones`, `consulta`, `importacion`, `archivos`, `auditoria` y `solicitudes_compra`. Todos tienen su `router.py` montado en `main.py`: quien construye un módulo llena sus archivos y no toca `main.py`. El backend es **síncrono** (PyMySQL): endpoints con `def` y `Session` de SQLAlchemy. Flujo: Router, Service, Repository, Model; el service controla la transacción y el repository nunca hace commit. Detalle en `docs/architecture/overview.md`.

El frontend es la aplicación construida: `routes.ts` registra una ruta por pantalla (`routes/operacion`, `consulta`, `personas`, `inventario`, `supervision`), `componentes/` agrupa lo reutilizable por área (`dominio` trae el escáner, el renglón con semáforo, la ficha, la firma y el QR; `ui` los componentes base), `api/` es el cliente de la API y `sesion/` la sesión y el menú según permisos. `components/` (en inglés) es el código base de shadcn.

## Arquitectura y límites

- Un solo desplegable: FastAPI entrega la API bajo `/api` y la interfaz ya construida.
- Toda operación de inventario es un movimiento entre dos ubicaciones. El trabajador es una ubicación.
- **Solo el módulo `movimientos` escribe** vales, movimientos, existencias y la ubicación de las piezas.
- El módulo `consulta` solo lee.
- Las reglas de negocio viven en el servidor. La interfaz muestra lo que el servidor evalúa y no decide nada.

## Reglas obligatorias

- Los movimientos y los vales no se actualizan ni se borran. Un error se corrige con un movimiento inverso.
- Las existencias cambian solo junto con un movimiento, en la misma transacción.
- Cada regla que se implementa lleva su ID (por ejemplo `E-06`) en la respuesta de la evaluación y en el nombre de su prueba.
- Los permisos se verifican en el servidor, en cada endpoint, por su clave (`modulo.accion`). Nunca se compara el nombre del rol. El catálogo está en la sección 8 de las reglas.
- Los datos reservados se envían solo con su permiso de información: el costo pide `catalogo.costos`; CURP y NSS piden `trabajadores.ver_datos_personales`.
- Todo cambio de esquema es una migración de Alembic.
- Los textos que ve el usuario van en español llano, sin términos técnicos.

## Prohibido sin aprobación

- Agregar algo listado como excluido o pospuesto en `docs/product/mvp-scope.md`.
- Cambiar el modelo de datos, un contrato de API o una regla de negocio sin actualizar su documento en el mismo cambio.
- Agregar dependencias que la tarea no pida.
- Refactorizar código que la tarea no toca.
- Subir secretos o el archivo `.env`.
- Hacer commits o push sin que alguien lo pida.

## Convenciones de código

- Los términos del dominio van en español y sin acentos: `vale`, `movimiento`, `trabajador_id`, `/api/vales`.
- Los nombres técnicos siguen al framework: `router.py`, `service.py`, `models.py`, `schemas.py`.
- Los `id` son UUID versión 7 generados por el servidor. El folio de un vale sale del contador `serie_folio`, nunca del `id`.
- Fechas en UTC en la base; se muestran en la hora del centro de México.
- Una prueba por regla de negocio; el guion del PDF es una prueba de integración.

## Autenticación, autorización y secretos

- Sesión por cookie `HttpOnly`; identifica al usuario, y de él salen su rol, sus permisos y su almacén.
- Cada `router.py` declara qué permiso exige cada endpoint. Excepción documentada: ocho rutas lo verifican en el servicio porque depende del tipo de vale o del usuario, o porque aceptan uno de dos permisos (`POST /api/vales`, `POST /api/vales/evaluar`, `GET /api/escaneo/{codigo}`, `GET /api/busqueda`, `GET /api/autorizaciones/{id}`, `POST /api/autorizaciones/{id}/resolucion`, y `GET /api/solicitudes-compra` y `GET /api/solicitudes-compra/{id}`, que piden `compras.solicitar` o `compras.atender`); en ellas el router solo exige sesión.
- Los roles y sus permisos son datos. Los cinco iniciales los carga el script de datos de prueba.
- El PIN del supervisor es distinto de su contraseña.
- Los secretos están en `.env`; `.env.example` documenta las variables.

## Comandos

Frontend, dentro de `frontend/`:

| Acción | Comando |
|---|---|
| Instalar | `pnpm install` |
| Servidor de desarrollo (puerto `21010`; reenvía `/api` a `API_DESTINO`, por defecto `http://127.0.0.1:21011`) | `pnpm dev` |
| Verificar tipos | `pnpm typecheck` |
| Construir | `pnpm build` |

Backend, dentro de `backend/` (comprobados en la Fase 0). Copiar antes `.env.example` a `.env` en la raíz:

| Acción | Comando |
|---|---|
| Levantar la base (raíz del repo) | `docker compose up -d db` |
| Instalar | `uv sync` |
| Migraciones | `uv run alembic upgrade head` (y `uv run alembic downgrade base`) |
| Datos de prueba (repetible) | `uv run python -m app.datos_prueba` |
| Servidor de desarrollo | `uv run fastapi dev app/main.py --port 21002` |
| Pruebas | `uv run pytest` |
| Lint | `uv run ruff check .` |
| Formato | `uv run ruff format .` |
| Verificar consistencia de la base (solo lectura; sale 0 si cuadra, 1 si no) | `uv run python -m app.mantenimiento verificar` |
| Existencias que deberían valer según la bitácora (no escribe) | `uv run python -m app.mantenimiento reconstruir-existencias --simular` |

Puertos: MySQL en el host `21001` (`MYSQL_PUERTO`), servidor de desarrollo `21002`; la aplicación desplegada `21040`; el resto desde `21003` está reservado. Las pruebas usan la base `{MYSQL_DATABASE}_test_{TEST_DB_SUFFIX}`: quien corra pruebas en paralelo contra el mismo MySQL usa un `TEST_DB_SUFFIX` distinto.

Producción (un solo desplegable, ADR-002), en la raíz del repo; comprobados en TASK-F0-04:

| Acción | Comando |
|---|---|
| Construir la imagen | `docker compose build` |
| Levantar base + aplicación (API e interfaz en `http://127.0.0.1:21040`, `APP_PUERTO`) | `docker compose up -d --build` |
| Además, publicar por el túnel de Cloudflare (requiere `TUNNEL_TOKEN`) | `docker compose --profile tunel up -d --build` |
| Datos de prueba al arrancar | `CARGAR_DATOS_PRUEBA=true` en `.env` |
| Estado y bitácora | `docker compose ps` / `docker compose logs app` |
| Apagar (con `-v` borra los datos) | `docker compose down` |
| Respaldo de la base y de los archivos (`respaldos/`) | `./scripts/respaldo.sh` (bash) o `scripts/respaldo.ps1` (PowerShell) |
| Restaurar (`--base NOMBRE` para probar en otra base) | `./scripts/restaurar.sh` o `scripts/restaurar.ps1` |

El contenedor `app` aplica `alembic upgrade head` al arrancar y sirve con `uvicorn` en el puerto 8000 interno. FastAPI entrega la interfaz desde `INTERFAZ_DIR` (en la imagen, `/app/interfaz`; si no existe, solo la API). Con el túnel, `COOKIE_SEGURA=true` y `ENTORNO=produccion` (con `produccion` la aplicación no arranca con una clave de sesión de ejemplo o corta; ver `backend/README.md`). El túnel real no se ha probado (requiere token).

## Definition of Done

- Todos los criterios de aceptación de la historia se pueden demostrar.
- Pruebas, lint, verificación de tipos y construcción pasan.
- Permisos y validaciones están en el servidor.
- El cambio no amplía el alcance.
- Los documentos afectados están actualizados.
- Otra persona u otro agente revisó el cambio.

## Cuándo actualizar documentación

| Cambió… | Se actualiza… |
|---|---|
| Una regla de negocio | `docs/product/reglas-de-negocio.md` |
| Un permiso o lo que trae un rol inicial | `docs/product/reglas-de-negocio.md`, sección 8 |
| Una tabla, campo o invariante | `docs/architecture/data-model.md` |
| Un endpoint, cuerpo o error | `docs/architecture/api-contracts.md` |
| Una ruta, pantalla o transición | `docs/product/app-flow.md` |
| Un patrón visual reutilizable | `docs/product/ui-ux.md` |
| Una decisión costosa o discutible | Un ADR nuevo en `docs/architecture/decisions/` |
| El alcance | `docs/product/mvp-scope.md`, con aprobación |

## Formato del reporte final

El de `docs/templates/reporte.md`: tarea realizada, archivos modificados, decisiones y supuestos, validaciones ejecutadas con su resultado, riesgos o deuda, documentación actualizada y siguiente acción.
