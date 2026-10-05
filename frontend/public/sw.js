/*
 * Service worker de IMHOTEP. Solo sirve para dos cosas:
 *   1. Cumplir el requisito de instalación (aplicación instalable).
 *   2. Acelerar la carga de los archivos estáticos con huella (/assets/*, caché primero).
 *
 * NO hay modo sin conexión: no guarda la API ni datos de negocio, y no sincroniza nada.
 * Las navegaciones y todo lo demás van siempre a la red. Si la red falla al abrir una pantalla,
 * se muestra /offline.html (guardado al instalar), nunca una página de error del navegador.
 *
 * Al cambiar este archivo, subir VERSION: el navegador instala la versión nueva y la activa al
 * siguiente cierre y apertura de la aplicación; los cachés de versiones viejas se borran.
 */
const VERSION = "v1";
const CACHE_ESTATICOS = `imhotep-estaticos-${VERSION}`;
const CACHE_BASE = `imhotep-base-${VERSION}`;
const PAGINA_SIN_CONEXION = "/offline.html";
const ARCHIVOS_BASE = [PAGINA_SIN_CONEXION, "/icono-192.png"];

self.addEventListener("install", (evento) => {
  evento.waitUntil(caches.open(CACHE_BASE).then((cache) => cache.addAll(ARCHIVOS_BASE)));
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    caches
      .keys()
      .then((nombres) =>
        Promise.all(
          nombres
            .filter((n) => n.startsWith("imhotep-") && n !== CACHE_ESTATICOS && n !== CACHE_BASE)
            .map((n) => caches.delete(n)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

async function cachePrimero(peticion) {
  const cache = await caches.open(CACHE_ESTATICOS);
  const guardado = await cache.match(peticion);
  if (guardado) return guardado;
  const respuesta = await fetch(peticion);
  // Solo respuestas completas y correctas; nunca errores ni respuestas parciales.
  if (respuesta.status === 200 && respuesta.type === "basic") {
    cache.put(peticion, respuesta.clone()).catch(() => {});
  }
  return respuesta;
}

self.addEventListener("fetch", (evento) => {
  const peticion = evento.request;
  if (peticion.method !== "GET") return;
  const url = new URL(peticion.url);
  if (url.origin !== self.location.origin) return;
  // La API y cualquier dato de negocio: siempre a la red, sin tocarlos.
  if (url.pathname === "/api" || url.pathname.startsWith("/api/")) return;

  if (peticion.mode === "navigate") {
    evento.respondWith(
      fetch(peticion).catch(async () => {
        const pagina = await caches.match(PAGINA_SIN_CONEXION);
        return pagina || Response.error();
      }),
    );
    return;
  }

  // Archivos con huella en el nombre (incluye la fuente): cambian de nombre si cambian de contenido.
  if (url.pathname.startsWith("/assets/")) {
    evento.respondWith(cachePrimero(peticion));
  }
});
