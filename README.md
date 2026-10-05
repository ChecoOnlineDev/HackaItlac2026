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

Para entrar por `http://` (sin túnel), deja `COOKIE_SEGURA=false` y `ENTORNO=desarrollo` (el valor por defecto): solo AVISA en el registro de una configuración insegura.

### Producción (`ENTORNO=produccion`)

En el servidor real pon en `.env` `ENTORNO=produccion`, `COOKIE_SEGURA=true` y una `CLAVE_SESION` propia de al menos 32 caracteres (`python -c "import secrets; print(secrets.token_urlsafe(48))"`). Con `produccion` la aplicación **se niega a arrancar** si la clave de sesión es la de ejemplo o es corta, si `COOKIE_SEGURA` no es `true`, o si `CARGAR_DATOS_PRUEBA=true` con `CLAVE_DATOS_PRUEBA` vacía; además apaga `/api/docs`, `/api/redoc` y `/api/openapi.json`. `FORWARDED_ALLOW_IPS` acota de qué redes se aceptan las cabeceras `X-Forwarded-*` (por defecto, las privadas de Docker; en el servidor, la subred real de la red de compose). El valor por defecto de `ENTORNO` en el compose es `desarrollo` porque la prueba local por `http://` exige `COOKIE_SEGURA=false`.

### Datos de prueba

Pon `CARGAR_DATOS_PRUEBA=true` en `.env` y vuelve a levantar (`docker compose up -d`): se cargan almacenes, cinco roles y un usuario por rol (`admin`, `supervisor`...) con la contraseña `CLAVE_DATOS_PRUEBA` y, para `admin` y `supervisor`, el PIN `PIN_DATOS_PRUEBA`. Es repetible. Déjalo en `false` en producción. Sin Docker: `uv run python -m app.datos_prueba` dentro de `backend/`.

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
