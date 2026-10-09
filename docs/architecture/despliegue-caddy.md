# Despliegue con Caddy (HTTPS propio)

Alternativa al túnel de Cloudflare para un servidor con IP pública. Caddy (`caddy:2`) recibe el tráfico en los puertos 80 y 443, obtiene y renueva solo el certificado de Let's Encrypt y lo reenvía a `app:8000`. Solo arranca con el perfil `caddy`; `docker compose up` normal no cambia.

## Qué hace

- `deploy/Caddyfile` atiende el dominio de la variable `DOMINIO` y usa `ACME_EMAIL` para los avisos de Let's Encrypt.
- Comprime con zstd y gzip, añade HSTS, `X-Content-Type-Options` y `Referrer-Policy`, y escribe los registros en la salida estándar (`docker compose logs caddy`).
- No define `Permissions-Policy`, a propósito: bloquearía la cámara del celular que usa el escáner.
- Acepta cuerpos de hasta 25 MB (holgura sobre `ARCHIVO_TAMANO_MAXIMO`, que valida la app, y para importar Excel). Los websockets pasan sin configuración extra.
- El certificado y su configuración viven en los volúmenes `caddy_data` y `caddy_config`: no los borres, o se pedirá un certificado nuevo y Let's Encrypt limita las emisiones.

## DNS en Cloudflare

1. Crear un registro **A** con el nombre elegido (por ejemplo `app`) hacia `179.236.250.103`.
2. Dejarlo en **nube gris (solo DNS)** para la primera emisión del certificado: Let's Encrypt debe llegar directo al servidor.
3. Abrir los puertos **80 y 443** (TCP; 443 también UDP para HTTP/3) en el firewall y en el router del servidor.
4. Cuando el certificado ya esté emitido, se puede pasar a **nube naranja** (proxy) con el modo SSL/TLS en **Full (strict)**. Con otro modo habrá bucles de redirección o conexiones sin cifrar hacia el servidor.

## Variables en `.env`

```
DOMINIO=app.midominio.com
ACME_EMAIL=correo@midominio.com
ENTORNO=produccion
COOKIE_SEGURA=true
FORWARDED_ALLOW_IPS=172.28.0.0/24
```

`172.28.0.0/24` es la subred fija de la red `imhotep` que define `docker-compose.yml`: así la app solo cree las cabeceras `X-Forwarded-*` que vienen de Caddy. Si esa subred choca con otra del servidor, cámbiala en el compose y en esta variable a la vez.

## Arranque y revisión

```bash
docker compose --profile caddy up -d --build
docker compose logs -f caddy      # busca "certificate obtained successfully"
```

Si la emisión falla, revisar que el registro A apunte a la IP, que esté en nube gris y que los puertos 80 y 443 sean alcanzables desde internet. No usar este perfil junto con `--profile tunel` para el mismo dominio.
