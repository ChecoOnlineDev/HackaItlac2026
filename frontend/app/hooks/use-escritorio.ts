import { useSyncExternalStore } from "react";

const CONSULTA = "(min-width: 1024px)";

function suscribir(oyente: () => void) {
  const lista = window.matchMedia(CONSULTA);
  lista.addEventListener("change", oyente);
  return () => lista.removeEventListener("change", oyente);
}

/** `true` en computadora (1024 px o más). Celular y tableta usan la navegación de botones grandes. */
export function useEsEscritorio(): boolean {
  return useSyncExternalStore(
    suscribir,
    () => window.matchMedia(CONSULTA).matches,
    () => false,
  );
}
