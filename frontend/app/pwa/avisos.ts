import { api, apiGet, apiPost } from "~/api/cliente";
import { practicaActiva } from "~/api/practica";
import { esAppNativa } from "~/movil/plataforma";

const CLAVE = "imhotep.push.suscripcion";
const PREFERENCIA = "imhotep.push.activados";
let registroEnCurso: Promise<void> | null = null;

export function admiteAvisos(): boolean {
  return !practicaActiva() && typeof window !== "undefined" && window.isSecureContext && !esAppNativa() && "Notification" in window && "serviceWorker" in navigator && "PushManager" in window;
}
function claveBytes(clave: string): Uint8Array<ArrayBuffer> {
  const texto = atob(clave.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(clave.length / 4) * 4, "="));
  const bytes = new Uint8Array(new ArrayBuffer(texto.length));
  for (let i = 0; i < texto.length; i++) bytes[i] = texto.charCodeAt(i);
  return bytes;
}
function coincide(a: ArrayBuffer | null, b: Uint8Array<ArrayBuffer>): boolean {
  const bytes = a ? new Uint8Array(a) : null;
  return Boolean(bytes && bytes.length === b.length && bytes.every((valor, i) => valor === b[i]));
}
async function registrar(): Promise<void> {
  if (!admiteAvisos() || Notification.permission !== "granted") return;
  try { if (localStorage.getItem(PREFERENCIA) === "false") return; } catch { /* Continuar sin recordar preferencias. */ }
  const { clave_publica } = await apiGet<{ clave_publica: string }>("/notificaciones/clave-publica");
  const clave = claveBytes(clave_publica);
  const registro = await navigator.serviceWorker.getRegistration("/") ?? await navigator.serviceWorker.register("/sw.js", { scope: "/" });
  if (!registro.active) {
    await new Promise<void>((resolve, reject) => {
      const worker = registro.installing ?? registro.waiting;
      if (!worker) { reject(new Error("Vuelve a abrir la aplicación para activar los avisos.")); return; }
      const timer = window.setTimeout(() => reject(new Error("Vuelve a intentar activar los avisos.")), 10000);
      worker.addEventListener("statechange", () => { if (worker.state === "activated") { clearTimeout(timer); resolve(); } });
    });
  }
  let suscripcion = await registro.pushManager.getSubscription();
  if (suscripcion && !coincide(suscripcion.options.applicationServerKey, clave)) { await suscripcion.unsubscribe(); suscripcion = null; }
  suscripcion ??= await registro.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: clave });
  const datos = suscripcion.toJSON();
  if (!datos.keys?.auth || !datos.keys.p256dh) throw new Error("No pudimos registrar los avisos en este dispositivo.");
  const respuesta = await apiPost<{ id: string }>("/notificaciones/suscripciones", { endpoint: suscripcion.endpoint, keys: datos.keys });
  try { localStorage.setItem(CLAVE, respuesta.id); } catch { /* La familia de sesión sigue protegida por el servidor. */ }
}
/** La carga de la aplicación nunca pide permiso al navegador (NT-01). */
export function registrarAvisosConPermiso(): Promise<void> {
  registroEnCurso ??= registrar().finally(() => { registroEnCurso = null; });
  return registroEnCurso;
}
/** Solo se invoca desde el toque explícito en Activar avisos. */
export async function activarAvisos(): Promise<void> {
  if (!admiteAvisos()) throw new Error("Este navegador no admite avisos. Puedes revisar la bandeja de autorizaciones.");
  // La pantalla comprueba la configuración antes de mostrar este botón.
  // Pedir permiso antes del primer await mantiene el gesto explícito en Safari.
  const permiso = await Notification.requestPermission();
  if (permiso !== "granted") throw new Error("No activaste los avisos. Puedes habilitarlos en los ajustes del navegador.");
  try { localStorage.setItem(PREFERENCIA, "true"); } catch { /* Sin almacenamiento. */ }
  await registrarAvisosConPermiso();
}
/** Revoca en el servidor antes de cerrar la sesión de este dispositivo (NT-01). */
export async function cancelarAvisos(desactivar = false): Promise<void> {
  if (practicaActiva()) return;
  if (desactivar) { try { localStorage.setItem(PREFERENCIA, "false"); } catch { /* Sin almacenamiento. */ } }
  if (registroEnCurso) await registroEnCurso.catch(() => undefined);
  try {
    const id = localStorage.getItem(CLAVE);
    if (id) await api(`/notificaciones/suscripciones/${id}`, { metodo: "DELETE", sinRedirigir: true });
  } finally {
    try { localStorage.removeItem(CLAVE); } catch { /* Sin almacenamiento. */ }
    if (admiteAvisos()) {
      const registro = await navigator.serviceWorker.getRegistration("/");
      await (await registro?.pushManager.getSubscription())?.unsubscribe();
    }
  }
}
