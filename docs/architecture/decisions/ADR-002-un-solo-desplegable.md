# ADR-002: Un solo desplegable: el servidor entrega la API y la interfaz

## Estado

Aceptada (4 de octubre de 2026).

## Contexto

El proyecto tiene un backend en FastAPI y un frontend en React Router que nació con renderizado en servidor. La cámara del celular exige HTTPS, no hay servidor todavía y el despliegue debe poder mudarse de una laptop a un servidor sin cambios.

## Fuerzas y restricciones

- El patrocinador pidió que sea web, en la nube y sin instalar.
- El `Dockerfile` de la plantilla del frontend usa npm y el proyecto usa pnpm.
- El equipo es pequeño y el tiempo, corto.

## Alternativas consideradas

1. **Dos servicios:** un servidor de Node para la interfaz y FastAPI para la API. Son dos procesos, dos imágenes y permisos entre dos orígenes.
2. **Interfaz en Cloudflare Pages y API por túnel.** Dos despliegues y dos direcciones.
3. **Un solo servicio:** la interfaz se construye como aplicación de una sola página y FastAPI entrega sus archivos junto con la API.

## Decisión

La alternativa 3. React Router pasa a modo de una sola página (`ssr: false`) y un `Dockerfile` en la raíz construye la interfaz y la copia a la imagen del servidor. Un túnel de Cloudflare publica un único subdominio.

## Justificación

Un solo origen elimina la configuración entre dominios y simplifica la sesión por cookie. Un solo contenedor de aplicación hace que mudarse de máquina sea copiar el proyecto y levantar Docker Compose.

## Consecuencias positivas

- Una dirección, un certificado, un despliegue.
- La misma configuración sirve en la laptop y en el servidor.
- Deja listo el camino para funcionar sin conexión más adelante.

## Consecuencias negativas

- Se pierde el renderizado en servidor; no hace falta para una herramienta interna.
- Cada cambio de interfaz obliga a reconstruir la imagen para probarlo en el entorno publicado. En desarrollo se usa el servidor de Vite.

## Señales para reevaluar

- Se necesita contenido público indexable.
- La interfaz y la API empiezan a desplegarse a ritmos distintos.
