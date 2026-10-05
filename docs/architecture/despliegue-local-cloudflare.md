# Despliegue local con Cloudflare Tunnel

Cómo publicar la aplicación desde la computadora de desarrollo (Windows) con HTTPS, usando el dominio que ya está en Cloudflare. Sirve para probar en celular desde hoy y mudarse al servidor cuando exista.

Estado: el `docker-compose.yml`, el `Dockerfile` de la raíz y los scripts de respaldo y restauración existen y están probados (base, aplicación con API e interfaz, salud, sesión, respaldo y restauración en otra base). El servicio `tunel` está definido pero **no se ha probado con un token real**; los comandos de `cloudflared` son los estándar de la herramienta.

## Por qué hace falta

El navegador solo permite abrir la cámara en una página segura: HTTPS, o `localhost`. El celular no puede usar `localhost` de la computadora, así que necesita una dirección HTTPS real.

Cloudflare Tunnel lo resuelve sin abrir puertos: un programa (`cloudflared`) abre una conexión saliente desde la computadora hacia Cloudflare, y Cloudflare publica un subdominio con su certificado y reenvía el tráfico.

```
Celular ──HTTPS──> imhotep.tudominio.com (Cloudflare) ──túnel──> cloudflared ──> aplicación local
```

## Qué opción usar

| Opción | Cómo queda | Cuándo conviene |
|---|---|---|
| **A. Todo local, una sola dirección** (recomendada) | El backend sirve la API y el frontend ya construido. Un solo subdominio. | Pruebas en celular, ensayos y demo. Es igual a como quedará en el servidor. |
| **B. Modo desarrollo por el túnel** | El túnel apunta al servidor de desarrollo de Vite, que reenvía `/api` al backend. | Mientras se programan pantallas y se quiere ver cada cambio en el celular. |
| **C. Frontend en Cloudflare Pages, backend por túnel** | Dos direcciones: `app.tudominio.com` y `api.tudominio.com`. | No conviene ahora. |

Por qué no la opción C por ahora: son dos despliegues en lugar de uno, obliga a configurar CORS y cookies entre dos orígenes, y cada cambio de frontend pasa por una construcción en la nube. No aporta nada a la demo. Con A y B se trabaja en un solo origen y no hay CORS.

Lo práctico es usar **B mientras se programa** y **A para probar y ensayar**. Las dos usan el mismo túnel; solo cambia a qué puerto apunta.

## Requisitos en Windows

| Qué | Para qué | Estado |
|---|---|---|
| Docker Desktop | Corre MySQL, la aplicación y el túnel | Ya instalado |
| Node y pnpm | Servidor de desarrollo del frontend (opción B) | Ya instalados |
| uv | Backend en modo desarrollo | Ya instalado |
| `cloudflared` para Windows | Solo si se usa el método 2 (línea de comandos) | Por instalar, opcional |

Con el método 1 no hay que instalar nada más: `cloudflared` corre dentro de Docker.

## Método 1 (recomendado): túnel creado en el panel, corriendo en Docker Compose

### En Cloudflare

Los nombres de los menús cambian con el tiempo; se busca la sección de túneles dentro de Zero Trust.

1. Entrar al panel de Cloudflare y abrir **Zero Trust**. La primera vez pide elegir un nombre de equipo y el plan gratuito.
2. Ir a **Networks → Tunnels** y crear un túnel de tipo **Cloudflared**. Nombre sugerido: `imhotep-dev`.
3. Cloudflare muestra un comando de instalación que contiene un **token** largo. Copiar solo el token. Es un secreto: quien lo tenga puede publicar en ese túnel.
4. En la pestaña **Public Hostname** del túnel, agregar una entrada:
   - Subdomain: `imhotep` (o el que se elija)
   - Domain: el dominio propio
   - Service: tipo `HTTP`, URL `app:8000`

   `app` es el nombre del servicio dentro de Docker Compose. Cloudflare crea solo el registro DNS; no hay que tocar la sección de DNS a mano.

Usar un subdominio de un solo nivel (`imhotep.tudominio.com`). El certificado gratuito no cubre dos niveles (`a.b.tudominio.com`).

### En el proyecto

Copiar `.env.example` a `.env` en la raíz y llenarlo. El `.gitignore` ya excluye `.env`, así que no se sube al repositorio. Para el túnel importan estas variables:

```
TUNNEL_TOKEN=pega_aqui_el_token
COOKIE_SEGURA=true          # el túnel entrega HTTPS; sin esto la cookie de sesión no es segura
ENTORNO=produccion          # la aplicación no arranca con una configuración insegura (ver abajo)
MYSQL_ROOT_PASSWORD=una_contraseña_local
MYSQL_PASSWORD=otra_contraseña_local
CLAVE_SESION=una_clave_larga_y_unica   # mínimo 32 caracteres: python -c "import secrets; print(secrets.token_urlsafe(48))"
```

El `docker-compose.yml` de la raíz define tres servicios: `db` (MySQL 8.4), `app` (la imagen del `Dockerfile` de la raíz: FastAPI con la API bajo `/api` y la interfaz ya construida, puerto 8000 dentro de Docker) y `tunel` (`cloudflare/cloudflared`, `tunnel --no-autoupdate run`, token desde `TUNNEL_TOKEN`). El servicio `tunel` pertenece al perfil `tunel`: sin ese perfil no se levanta, y `docker compose up -d --build` funciona aunque no haya token.

Puntos a cuidar:

- La base de datos no se publica por el túnel. Solo el servicio `app` tiene nombre público.
- Los puertos de `db` (`MYSQL_PUERTO`, 21001) y de `app` (`APP_PUERTO`, 21040) se ligan a `127.0.0.1` para que nadie en la misma red entre directo.
- Los volúmenes `imhotep_db_datos` (base) e `imhotep_archivos` (firmas y fotos) conservan los datos entre reinicios.
- `app` aplica las migraciones al arrancar (reintenta hasta 60 s si la base no está lista) y confía en las cabeceras `X-Forwarded-*` del túnel solo desde las redes de `FORWARDED_ALLOW_IPS` (por defecto las privadas de Docker; acótala a la subred real de la red de compose, nunca `*`).
- Con `ENTORNO=produccion` la aplicación se niega a arrancar si `CLAVE_SESION` es la de ejemplo o tiene menos de 32 caracteres, si `COOKIE_SEGURA` no es `true` o si `CARGAR_DATOS_PRUEBA=true` con `CLAVE_DATOS_PRUEBA` vacía (el registro de `docker compose logs app` dice cuál), y apaga `/api/docs`. El compose usa `desarrollo` por defecto para poder probar por `http://127.0.0.1`; actívalo en el servidor real.

Levantar todo:

```bash
docker compose --profile tunel up -d --build
```

Sin el perfil `tunel` se levantan solo la base y la aplicación (`http://127.0.0.1:21040`), útil para probar sin túnel.

Revisar que el túnel conectó:

```bash
docker compose logs tunel
```

Debe aparecer que registró conexiones. Después se abre `https://imhotep.tudominio.com` desde el celular.

## Método 2: túnel por línea de comandos en Windows

Útil si se quiere el túnel sin Docker, por ejemplo para la opción B.

Instalar:

```bash
winget install --id Cloudflare.cloudflared
```

Iniciar sesión; abre el navegador para elegir el dominio:

```bash
cloudflared tunnel login
```

Crear el túnel; imprime un identificador y guarda un archivo de credenciales en `C:\Users\PC\.cloudflared\`:

```bash
cloudflared tunnel create imhotep-dev
```

Asociar el subdominio:

```bash
cloudflared tunnel route dns imhotep-dev imhotep.tudominio.com
```

Crear `C:\Users\PC\.cloudflared\config.yml`, con el identificador que imprimió el paso anterior:

```yaml
tunnel: ID-DEL-TUNEL
credentials-file: C:\Users\PC\.cloudflared\ID-DEL-TUNEL.json

ingress:
  - hostname: imhotep.tudominio.com
    service: http://localhost:8000
  - service: http_status:404
```

Correrlo:

```bash
cloudflared tunnel run imhotep-dev
```

No mezclar los dos métodos sobre el mismo subdominio. Si se usa el método 1, el destino se cambia en el panel; si se usa el 2, en `config.yml`.

## Opción B: ver cambios en vivo desde el celular

El túnel apunta al servidor de desarrollo del frontend (puerto 5173) en lugar del 8000. Con el método 1, el servicio en el panel sería `host.docker.internal:5173`; con el método 2, `http://localhost:5173`.

En `frontend/vite.config.ts` hacen falta dos ajustes:

```ts
server: {
  allowedHosts: ["imhotep.tudominio.com"],
  proxy: {
    "/api": "http://localhost:8000",
  },
},
```

- `allowedHosts`: sin esto Vite rechaza las peticiones que llegan con el dominio.
- `proxy`: manda `/api` al backend, así el celular ve un solo origen.

Si la recarga automática no llega al celular, se recarga la página a mano. No afecta la prueba de cámara.

## Instalar la aplicación en el celular o la computadora

La interfaz es una aplicación instalable (PWA). Requiere **HTTPS**: funciona por el túnel de Cloudflare (`https://imhotep.checodev.top`) o en `localhost`, pero no por `http://` con una IP de la red local. No hay modo sin conexión: sin internet solo se ve una pantalla de aviso.

- **Android (Chrome):** abrir el sitio, entrar al menú de la aplicación y tocar «Instalar aplicación» (o el menú del navegador, «Instalar aplicación»).
- **iPhone o iPad (Safari):** tocar Compartir y luego «Agregar a inicio».
- **Computadora (Chrome o Edge):** botón «Instalar aplicación» del menú lateral o el icono de instalar en la barra de direcciones.

Al publicar una versión nueva de la interfaz, la aplicación instalada la toma al cerrarla y volver a abrirla.

## Limitaciones de usar la computadora como servidor

- **Encendida y despierta.** Desactivar la suspensión mientras se prueba; Docker Desktop debe estar abierto.
- **Depende de su Internet.** Si se cae la conexión, se cae el sitio.
- **Dos túneles con el mismo token.** Si la laptop y el servidor corren el mismo túnel a la vez, Cloudflare reparte el tráfico entre ambos. Apagar uno antes de encender el otro.
- **Caché de Cloudflare.** Si un archivo estático no se actualiza, activar Development Mode en el panel o recargar forzando.

## Respaldo y restauración

La base (MySQL) y los archivos (firmas y fotos, volumen `imhotep_archivos`, `/data/archivos` dentro del contenedor `app`) se respaldan juntos. Los scripts están en `scripts/` en dos versiones con el mismo comportamiento: `.sh` (bash: Git Bash en Windows, o Linux) y `.ps1` (PowerShell). Necesitan Docker corriendo y el contenedor de la base arriba.

### Hacer un respaldo

```bash
./scripts/respaldo.sh            # Git Bash o Linux
.\scripts\respaldo.ps1           # PowerShell
```

Deja en `respaldos/` (o en `RESPALDOS_DIR`) dos archivos con la misma marca de fecha y hora:

| Archivo | Contenido |
|---|---|
| `bd-AAAAMMDD-HHMMSS.sql.gz` | Volcado de la base (`mysqldump --single-transaction --routines --triggers`, hecho dentro del contenedor, sin bloquear la operación). |
| `archivos-AAAAMMDD-HHMMSS.tar.gz` | Firmas y fotos. Se toman del contenedor `app` si corre; si no, de la carpeta local `backend/almacenamiento` (desarrollo). |

Variables, en el entorno o en `.env` (todas opcionales):

| Variable | Para qué | Por defecto |
|---|---|---|
| `RESPALDOS_DIR` | Carpeta de destino (ruta absoluta o relativa a la raíz del repositorio). Está en `.gitignore`. | `respaldos` |
| `RESPALDOS_CONSERVAR` | Cuántos respaldos guardar; los más viejos se borran. `0` guarda todos. | `0` |
| `MYSQL_DATABASE` | Base a respaldar. | `imhotep` |
| `DB_CONTENEDOR` | Nombre del contenedor de MySQL. | `imhotep_db` |
| `APP_CONTENEDOR` | Nombre del contenedor de la aplicación, si no se encuentra solo con `docker compose ps`. | (se busca) |

La contraseña de MySQL nunca aparece en la línea de comandos ni en la salida: el volcado corre dentro del contenedor y toma la clave de root del entorno del contenedor. Si no hay de dónde leer los archivos (ni contenedor `app` ni carpeta local), el script respalda la base, avisa que el respaldo quedó **incompleto** y sale con código 2.

### Restaurar

```bash
./scripts/restaurar.sh                          # el respaldo más reciente, sobre la base de producción
./scripts/restaurar.sh 20261005-021500          # el de esa marca
./scripts/restaurar.sh --base imhotep_prueba    # en OTRA base, sin tocar producción
```

En PowerShell: `.\scripts\restaurar.ps1 --base imhotep_prueba` (acepta también `-Base`).

- Sobre la base de producción pide escribir su nombre antes de sobrescribir, y devuelve los archivos al volumen de la aplicación. `--si` omite la pregunta (para automatizar; con cuidado).
- Con `--base OTRA` crea la base si no existe, restaura en ella y extrae los archivos en `respaldos/restaurado-MARCA/archivos`, sin tocar el volumen de la aplicación.
- Después de restaurar, comprobar que todo cuadra (en PowerShell, `$env:MYSQL_DATABASE='imhotep_prueba'` antes del comando):

```bash
cd backend
MYSQL_DATABASE=imhotep_prueba uv run python -m app.mantenimiento verificar   # debe decir "Todo cuadra" y salir con 0
```

### Cómo se probó

Con una base de prueba con los datos de prueba, dos entregas con firma y una cancelación: se respaldó con `respaldo.sh` y con `respaldo.ps1`, se restauró en otra base con `restaurar.sh --base` y con `restaurar.ps1 --base`, y `verificar` dio código 0 en la original y en la restaurada, con los mismos conteos de vales, movimientos y existencias. Conviene repetirlo en el servidor antes del release (casilla de la [checklist](../releases/mvp-checklist.md)).

### Programar el respaldo diario

**Windows (Programador de tareas).** Una tarea diaria a las 2:00 que corre el script en PowerShell (ajustar la ruta del repositorio):

```powershell
schtasks /Create /SC DAILY /ST 02:00 /TN "Imhotep respaldo" /TR "powershell -NoProfile -ExecutionPolicy Bypass -File C:\ruta\al\repositorio\scripts\respaldo.ps1" /F
```

Para conservar solo los últimos 14, definir antes `RESPALDOS_CONSERVAR=14` en el `.env` del repositorio. Se puede probar con `schtasks /Run /TN "Imhotep respaldo"` y revisar `respaldos/`. La tarea corre con la sesión iniciada y Docker Desktop abierto, salvo que se configure «Ejecutar tanto si el usuario inició sesión como si no» en las propiedades de la tarea.

**Linux (cron).** Con `crontab -e`, a las 2:00 y conservando 14 respaldos:

```cron
0 2 * * * cd /opt/imhotep && RESPALDOS_CONSERVAR=14 ./scripts/respaldo.sh >> respaldos/respaldo.log 2>&1
```

Los scripts no copian los respaldos fuera de la máquina: conviene sincronizar `respaldos/` a otro equipo o a la nube. Un respaldo que vive solo en el servidor no protege contra la pérdida del servidor.

### Si las existencias dejan de cuadrar

`python -m app.mantenimiento verificar` lista las diferencias. `reconstruir-existencias --simular` muestra lo que deberían valer las existencias según la bitácora sin escribir nada; `--aplicar` las corrige, pide una frase de confirmación y deja registro en la auditoría. Hacer un respaldo antes. Ver [security-model.md](security-model.md).

## Paso al servidor

1. Instalar Docker en el servidor.
2. Clonar el repositorio y copiar el `.env`, con contraseñas nuevas para producción.
3. Detener el túnel en la laptop: `docker compose stop tunel`.
4. En el servidor: `docker compose --profile tunel up -d --build`.
5. Pasar los datos con un respaldo (`scripts/respaldo.*` en la laptop y `scripts/restaurar.*` en el servidor, sección anterior), o cargar de nuevo los datos de prueba.

El subdominio y el certificado no cambian, así que las etiquetas QR impresas siguen sirviendo. No hace falta Caddy ni abrir puertos en el servidor.

Plan de respaldo para la demo: la laptop con el mismo Compose y el túnel apagado. Si el servidor falla, se detiene su túnel y se enciende el de la laptop.
