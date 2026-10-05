# Control de herramientas y EPP (Reto IMHOTEP)

Sistema web para controlar herramientas y equipo de protección personal: vales de entrega y devolución, existencias por almacén, inspecciones, autorizaciones y consulta. Proyecto del Hacka ITLAC 2026, Track 3.

Un solo desplegable (ADR-002): FastAPI entrega la API bajo `/api` y la interfaz ya construida (React, aplicación de una sola página). La documentación está en [`docs/README.md`](docs/README.md); las instrucciones para agentes, en [`AGENTS.md`](AGENTS.md).

## Levantar todo con Docker

Requiere Docker Desktop.

```bash
cp .env.example .env            # y cambia las contraseñas y CLAVE_SESION
docker compose up -d --build    # base de datos + aplicación
docker compose ps               # espera a que `app` diga (healthy)
```

La aplicación queda en `http://127.0.0.1:21040` (la interfaz) y `http://127.0.0.1:21040/api/salud` responde `{"estado":"ok","base":"ok"}`. Al arrancar, el contenedor aplica las migraciones solo.

Para entrar por `http://` (sin túnel), deja `COOKIE_SEGURA=false`.

### Datos de prueba

Pon `CARGAR_DATOS_PRUEBA=true` en `.env` y vuelve a levantar (`docker compose up -d`): se cargan los seis almacenes, los cinco roles y un usuario por rol, artículos, trabajadores y las entradas iniciales de Kepler y Contratistas. Es repetible. Déjalo en `false` en producción. Sin Docker: `uv run python -m app.datos_prueba` dentro de `backend/`.

#### Usuarios de prueba

**Son datos de prueba, no reales.** Los diez usuarios usan la misma contraseña: el valor de `CLAVE_DATOS_PRUEBA` de tu `.env` (el equipo la comparte por fuera del repositorio; nunca es una contraseña real). El PIN de autorización de `admin` y `supervisor` es el valor de `PIN_DATOS_PRUEBA` del `.env`. El PIN es distinto de la contraseña y solo sirve para autorizar excepciones en el momento.

| Usuario | Rol | Almacén | Para qué sirve en la demostración |
|---|---|---|---|
| `admin` | Administrador | todos | Todos los permisos; PIN de prueba |
| `supervisor` | Supervisor | todos | Autoriza excepciones (desde su celular o con PIN), ajusta vigencias, administra el catálogo; PIN de prueba |
| `compras` | Compras | todos | Entradas de inventario, importación, catálogo y costos |
| `rh` | Recursos Humanos | ninguno | Alta de trabajadores, datos personales, adeudos |
| `almacenista` | Almacenista | Kepler (KEP) | Entregar, devolver, trasladar y recibir |
| `alm_con` | Almacenista | Contratistas (CON) | Igual, en su almacén |
| `alm_mid` | Almacenista | Midrex (MID) | Igual, en su almacén |
| `alm_hyl` | Almacenista | HYL (HYL) | Igual, en su almacén |
| `alm_lam` | Almacenista | Laminador (LAM) | Igual, en su almacén |
| `alm_min` | Almacenista | Minas (MIN) | Igual, en su almacén |

Para saber cuál es la contraseña de prueba de tu copia: `grep CLAVE_DATOS_PRUEBA .env` (o `grep PIN_DATOS_PRUEBA .env` para el PIN). Para una demostración, cámbialas en `.env` y vuelve a cargar los datos de prueba (el script las actualiza). La guía de uso está en [`docs/guia-almacenista.md`](docs/guia-almacenista.md).

### Publicar con HTTPS (túnel de Cloudflare)

La cámara del celular exige HTTPS. Con el token de un túnel creado en Cloudflare (guía completa en [`docs/architecture/despliegue-local-cloudflare.md`](docs/architecture/despliegue-local-cloudflare.md)):

```bash
# en .env: TUNNEL_TOKEN=...   y   COOKIE_SEGURA=true
docker compose --profile tunel up -d --build
docker compose logs tunel
```

El servicio `tunel` no arranca sin el perfil `tunel`, así que el comando normal funciona aunque no haya token. En Cloudflare, el destino del subdominio es `http://app:8000`.

### Otros comandos

| Acción | Comando |
|---|---|
| Ver la bitácora de la aplicación | `docker compose logs -f app` |
| Apagar (conserva los datos) | `docker compose down` |
| Apagar y borrar los datos | `docker compose down -v` |

## Respaldo y restauración

Dos archivos con la misma marca de fecha: el volcado de la base (`bd-AAAAMMDD-HHMMSS.sql.gz`) y las firmas y fotos (`archivos-AAAAMMDD-HHMMSS.tar.gz`). Van a `respaldos/` (o a `RESPALDOS_DIR`), que no se sube al repositorio. Hay versión para bash (Git Bash, Linux) y para PowerShell; necesitan Docker y la base arriba.

```bash
./scripts/respaldo.sh                          # o: .\scripts\respaldo.ps1
./scripts/restaurar.sh                         # el más reciente, sobre la base de producción (pide confirmación)
./scripts/restaurar.sh --base imhotep_prueba   # en OTRA base, para probar sin tocar producción
cd backend && MYSQL_DATABASE=imhotep_prueba uv run python -m app.mantenimiento verificar
```

- `RESPALDOS_CONSERVAR=14` conserva solo los 14 más recientes. La contraseña de MySQL nunca va en la línea de comandos.
- `verificar` es de solo lectura: comprueba que las existencias sean la suma de los movimientos, que cada pieza esté donde dejó su último movimiento, que los folios sean consecutivos, que los vales cancelados tengan su cancelación, que los códigos no se repitan y que quien está de baja no deba equipo. Sale con `0` si todo cuadra y con `1` listando las diferencias. `reconstruir-existencias --simular` muestra lo que deberían valer las existencias sin escribir (`--aplicar`, solo con confirmación, queda en la auditoría).

### Programarlo cada día

- **Windows (Programador de tareas):** `schtasks /Create /SC DAILY /ST 02:00 /TN "Imhotep respaldo" /TR "powershell -NoProfile -ExecutionPolicy Bypass -File C:\ruta\al\repositorio\scripts\respaldo.ps1" /F`. Docker Desktop debe estar abierto.
- **Linux (cron, `crontab -e`):** `0 2 * * * cd /opt/imhotep && RESPALDOS_CONSERVAR=14 ./scripts/respaldo.sh >> respaldos/respaldo.log 2>&1`

Los respaldos se quedan en la misma máquina: copia `respaldos/` a otro equipo. Detalle, variables y cómo se probó: [`docs/architecture/despliegue-local-cloudflare.md`](docs/architecture/despliegue-local-cloudflare.md#respaldo-y-restauración).

## Desarrollo

Backend (dentro de `backend/`; necesita `.env` y la base: `docker compose up -d db`):

```bash
uv sync
uv run alembic upgrade head
uv run python -m app.datos_prueba
uv run fastapi dev app/main.py --port 21002
```

Frontend (dentro de `frontend/`): `pnpm install`, `pnpm dev` (puerto 21010; reenvía `/api` al backend; con el backend en 21002: `API_DESTINO=http://127.0.0.1:21002 pnpm dev`), `pnpm typecheck` y `pnpm build`.

## Pruebas y verificación

```bash
# backend/ (usa MySQL real; el sufijo evita choques entre copias de trabajo)
TEST_DB_SUFFIX=main uv run pytest
uv run ruff check .
# frontend/
pnpm typecheck && pnpm build
```

## Puertos

| Puerto | Qué es |
|---|---|
| `21001` | MySQL en el host (`MYSQL_PUERTO`), solo `127.0.0.1` |
| `21002` | Servidor de desarrollo del backend |
| `21010` | Servidor de desarrollo del frontend |
| `21040` | Aplicación desplegada con Docker (`APP_PUERTO`), solo `127.0.0.1` |

Dentro de Docker, la aplicación escucha en el `8000` y la base en el `3306`.
