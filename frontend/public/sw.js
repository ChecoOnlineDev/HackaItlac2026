/*
 * Service worker de IMHOTEP. Sirve para:
 *   1. Cumplir el requisito de instalación (aplicación instalable).
 *   3. Mostrar avisos de solicitudes del supervisor.
 *   2. Acelerar la carga de los archivos estáticos con huella (/assets/*, caché primero).
 *
 * NO hay modo sin conexión: no guarda la API ni datos de negocio, y no sincroniza nada.
 * Las navegaciones y todo lo demás van siempre a la red. Si la red falla al abrir una pantalla,
 * se muestra /offline.html (guardado al instalar), nunca una página de error del navegador.
 *
 * Al cambiar este archivo, subir VERSION: el navegador instala la versión nueva y la activa al
 * siguiente cierre y apertura de la aplicación; los cachés de versiones viejas se borran.
 */
const VERSION = "v3";
/** Tope de archivos en la caché de estáticos: al pasarlo se borran los más viejos. */
const MAX_ESTATICOS = 120;
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
      .then(() => caches.open(CACHE_ESTATICOS).then(recortar))
      .then(() => self.clients.claim()),
  );
});

/** Quita las entradas más antiguas (las primeras guardadas) cuando se pasa el tope. */
async function recortar(cache) {
  const claves = await cache.keys();
  const sobran = claves.length - MAX_ESTATICOS;
  for (let i = 0; i < sobran; i++) await cache.delete(claves[i]);
}

async function cachePrimero(peticion) {
  const cache = await caches.open(CACHE_ESTATICOS);
  const guardado = await cache.match(peticion);
  if (guardado) return guardado;
  const respuesta = await fetch(peticion);
  // Solo respuestas completas y correctas; nunca errores ni respuestas parciales.
  if (respuesta.status === 200 && respuesta.type === "basic") {
    cache
      .put(peticion, respuesta.clone())
      .then(() => recortar(cache))
      .catch(() => {});
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


// NT-03/NT-06: toda entrega push muestra un aviso; los reemplazos conservan su etiqueta.
self.addEventListener("push", (event) => {
  let datos = {};
  try { datos = event.data?.json() ?? {}; } catch { /* Aviso legible aun si el mensaje es inválido. */ }
  event.waitUntil(self.registration.showNotification(datos.titulo || "IMHOTEP", {
    body: datos.cuerpo || "Revisa tus autorizaciones pendientes.",
    icon: "/icono-192.png",
    tag: datos.etiqueta || "imhotep-autorizaciones",
    renotify: !datos.silencioso,
    silent: Boolean(datos.silencioso),
    data: { url: datos.url || "/autorizaciones" },
  }));
});
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil((async () => {
    let destino = new URL("/autorizaciones", self.location.origin);
    try {
      const propuesta = new URL(event.notification.data?.url || "/autorizaciones", self.location.origin);
      if (propuesta.origin === self.location.origin) destino = propuesta;
    } catch { /* Ir a la bandeja. */ }
    const ventanas = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    for (const ventana of ventanas) {
      if (new URL(ventana.url).origin === destino.origin && "navigate" in ventana) {
        await ventana.navigate(destino.href);
        await ventana.focus();
        return;
      }
    }
    await self.clients.openWindow(destino.href);
  })());
});
self.addEventListener("pushsubscriptionchange", (event) => {
  event.waitUntil((async () => {
    try {
      const respuesta = await fetch("/api/notificaciones/clave-publica", { credentials: "include" });
      if (!respuesta.ok) return;
      const { clave_publica } = await respuesta.json();
      const texto = atob(clave_publica.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(clave_publica.length / 4) * 4, "="));
      const clave = Uint8Array.from(texto, (c) => c.charCodeAt(0));
      const suscripcion = event.newSubscription || await self.registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: clave });
      const datos = suscripcion.toJSON();
      await fetch("/api/notificaciones/suscripciones", { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ endpoint: suscripcion.endpoint, keys: datos.keys }) });
    } catch { /* Se volverá a registrar al abrir una sesión válida; no se pide permiso aquí. */ }
  })());
});
