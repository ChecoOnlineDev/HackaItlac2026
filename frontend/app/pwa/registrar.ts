/**
 * Aplicación instalable (PWA), sin modo sin conexión.
 *
 * - Registra el service worker solo en producción y en un contexto seguro (HTTPS o localhost).
 * - Guarda el aviso `beforeinstallprompt` del navegador para ofrecer el botón "Instalar aplicación".
 * Si algo falla, la aplicación arranca igual: nada de esto es necesario para trabajar.
 */

import { esAppNativa } from "~/movil/plataforma";

interface EventoInstalacion extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

let aviso: EventoInstalacion | null = null;
let instalada = false;
const oyentes = new Set<() => void>();

function avisar() {
  oyentes.forEach((f) => f());
}

if (typeof window !== "undefined") {
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    aviso = e as EventoInstalacion;
    avisar();
  });
  window.addEventListener("appinstalled", () => {
    aviso = null;
    instalada = true;
    avisar();
  });
}

/** Suscripción para `useSyncExternalStore`. */
export function suscribirInstalacion(f: () => void) {
  oyentes.add(f);
  return () => {
    oyentes.delete(f);
  };
}

/** `true` si el navegador ofrece instalar y la aplicación aún no está instalada. */
export function puedeInstalar(): boolean {
  return !esAppNativa() && aviso !== null && !instalada;
}

/** Muestra el cuadro de instalación del navegador. */
export async function instalarAplicacion(): Promise<void> {
  const a = aviso;
  if (!a) return;
  try {
    await a.prompt();
    const { outcome } = await a.userChoice;
    // Si la persona descarta el cuadro, el evento se conserva y el botón sigue disponible: solo se
    // retira cuando el navegador avisa que la aplicación quedó instalada (`appinstalled`).
    if (outcome === "accepted") avisar();
  } catch {
    // El navegador puede rechazar un segundo intento; no es un error para quien usa la aplicación.
  }
}

/** `true` si la aplicación ya corre como instalada (ventana propia). */
export function yaEstaInstalada(): boolean {
  if (esAppNativa()) return true;
  if (typeof window === "undefined") return false;
  const standalone = (navigator as Navigator & { standalone?: boolean }).standalone === true;
  return instalada || standalone || window.matchMedia("(display-mode: standalone)").matches;
}

/** `true` en iPhone y iPad (Safari no ofrece el botón; se explica cómo agregarla al inicio). */
export function esDispositivoApple(): boolean {
  if (typeof navigator === "undefined") return false;
  const iPadNuevo = navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1;
  return /iPhone|iPad|iPod/.test(navigator.userAgent) || iPadNuevo;
}

/** Registra el service worker. Solo en producción y en contexto seguro; nunca lanza error. */
export function registrarServiceWorker(): void {
  if (esAppNativa()) return;
  if (!import.meta.env.PROD) return;
  if (typeof window === "undefined" || !window.isSecureContext) return;
  if (!("serviceWorker" in navigator)) return;
  const registrar = () => {
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {
      // Sin service worker la aplicación funciona igual, solo que no se puede instalar.
    });
  };
  if (document.readyState === "complete") registrar();
  else window.addEventListener("load", registrar, { once: true });
}
