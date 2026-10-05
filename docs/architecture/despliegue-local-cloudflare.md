# Despliegue local con Cloudflare Tunnel

Cómo publicar la aplicación desde la computadora de desarrollo (Windows) con HTTPS, usando el dominio que ya está en Cloudflare. Sirve para probar en celular desde hoy y mudarse al servidor cuando exista.

Estado: los comandos de `cloudflared` son los estándar de la herramienta. El `docker-compose.yml` que aparece aquí es la forma planeada; todavía no existe en el repositorio ni se ha probado.

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

Guardar el token en un archivo `.env` en la raíz. El `.gitignore` ya excluye `.env`, así que no se sube al repositorio.

```
TUNNEL_TOKEN=pega_aqui_el_token
MYSQL_ROOT_PASSWORD=una_contraseña_local
MYSQL_PASSWORD=otra_contraseña_local
```

Forma planeada del `docker-compose.yml`:

```yaml
services:
  db:
    image: mysql:8.4
    environment:
      MYSQL_DATABASE: imhotep
      MYSQL_USER: imhotep
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
    volumes:
      - db_data:/var/lib/mysql
    ports:
      - "127.0.0.1:3306:3306"   # solo accesible desde esta computadora

  app:
    build: .
    environment:
      DATABASE_URL: mysql+pymysql://imhotep:${MYSQL_PASSWORD}@db:3306/imhotep
    depends_on:
      - db
    ports:
      - "127.0.0.1:8000:8000"

  tunnel:
    image: cloudflare/cloudflared:latest
    command: tunnel --no-autoupdate run
    environment:
      TUNNEL_TOKEN: ${TUNNEL_TOKEN}
    depends_on:
      - app

volumes:
  db_data:
```

Puntos a cuidar:

- La base de datos no se publica por el túnel. Solo el servicio `app` tiene nombre público.
- Los puertos se ligan a `127.0.0.1` para que nadie en la misma red entre directo.
- El volumen `db_data` conserva los datos entre reinicios.

Levantar todo:

```bash
docker compose up -d --build
```

Revisar que el túnel conectó:

```bash
docker compose logs tunnel
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

## Limitaciones de usar la computadora como servidor

- **Encendida y despierta.** Desactivar la suspensión mientras se prueba; Docker Desktop debe estar abierto.
- **Depende de su Internet.** Si se cae la conexión, se cae el sitio.
- **Dos túneles con el mismo token.** Si la laptop y el servidor corren el mismo túnel a la vez, Cloudflare reparte el tráfico entre ambos. Apagar uno antes de encender el otro.
- **Caché de Cloudflare.** Si un archivo estático no se actualiza, activar Development Mode en el panel o recargar forzando.

## Paso al servidor

1. Instalar Docker en el servidor.
2. Clonar el repositorio y copiar el `.env`, con contraseñas nuevas para producción.
3. Detener el túnel en la laptop: `docker compose stop tunnel`.
4. En el servidor: `docker compose up -d --build`.
5. Pasar los datos con un respaldo de MySQL, o cargar de nuevo los datos de prueba.

El subdominio y el certificado no cambian, así que las etiquetas QR impresas siguen sirviendo. No hace falta Caddy ni abrir puertos en el servidor.

Plan de respaldo para la demo: la laptop con el mismo Compose y el túnel apagado. Si el servidor falla, se detiene su túnel y se enciende el de la laptop.
