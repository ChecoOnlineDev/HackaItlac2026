import { useSyncExternalStore } from "react";

// Estado de la conexión: lo alimentan los eventos del navegador y el cliente de la API.

let enLinea = typeof navigator === "undefined" ? true : navigator.onLine;
const oyentes = new Set<() => void>();

function emitir() {
  oyentes.forEach((oyente) => oyente());
}

export function marcarConexion(valor: boolean) {
  if (enLinea === valor) return;
  enLinea = valor;
  emitir();
}

if (typeof window !== "undefined") {
  window.addEventListener("online", () => marcarConexion(true));
  window.addEventListener("offline", () => marcarConexion(false));
}

function suscribir(oyente: () => void) {
  oyentes.add(oyente);
  return () => {
    oyentes.delete(oyente);
  };
}

/** `true` si hay conexión con el servidor (hasta donde se sabe). */
export function useEnLinea(): boolean {
  return useSyncExternalStore(
    suscribir,
    () => enLinea,
    () => true,
  );
}
