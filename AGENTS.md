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
backend/app/modulos/<dominio>/   router.py, service.py, models.py, schemas.py
backend/alembic/                 migraciones
backend/tests/                   pruebas
frontend/app/routes/             una ruta por pantalla
frontend/app/componentes/        escáner, renglón con semáforo, fichas
docs/                            documentación; el índice es docs/README.md
```

La estructura de `backend/app/` se crea en la Fase 0. Hoy el backend es `backend/main.py` y el frontend es la plantilla.

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
- Cada `router.py` declara qué permiso exige cada endpoint.
- Los roles y sus permisos son datos. Los cinco iniciales los carga el script de datos de prueba.
- El PIN del supervisor es distinto de su contraseña.
- Los secretos están en `.env`; `.env.example` documenta las variables.

## Comandos

Funcionan hoy:

| Acción | Comando |
|---|---|
| Instalar el frontend | `pnpm install` dentro de `frontend/` |
| Servidor de desarrollo del frontend | `pnpm dev` dentro de `frontend/` |
| Verificar tipos | `pnpm typecheck` dentro de `frontend/` |
| Construir el frontend | `pnpm build` dentro de `frontend/` |
| Instalar el backend | `uv sync` dentro de `backend/` |

Quedan disponibles al cerrar la Fase 0; hasta entonces son el objetivo, no un hecho:

| Acción | Comando |
|---|---|
| Servidor de desarrollo del backend | `uv run fastapi dev app/main.py` dentro de `backend/` |
| Pruebas | `uv run pytest` dentro de `backend/` |
| Lint | `uv run ruff check .` dentro de `backend/` |
| Migraciones | `uv run alembic upgrade head` dentro de `backend/` |
| Levantar todo | `docker compose up -d --build` en la raíz |

Quien cierre la Fase 0 actualiza esta sección con los comandos comprobados.

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
