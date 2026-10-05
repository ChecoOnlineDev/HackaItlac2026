import { ArrowLeftIcon } from "lucide-react";
import { createContext, useContext, useEffect, useRef, type ReactNode, type MutableRefObject } from "react";

import { Boton } from "~/componentes/ui/boton";
import { useEsEscritorio } from "~/hooks/use-escritorio";

type ManejadorAtras = () => void;

const ContextoAtras = createContext<MutableRefObject<ManejadorAtras | null> | null>(null);

/** Guarda el "Atrás" que una pantalla de pasos le pide a la barra de arriba (celular y tableta). */
export function ProveedorAtras({ children }: { children: ReactNode }) {
  const ref = useRef<ManejadorAtras | null>(null);
  return <ContextoAtras.Provider value={ref}>{children}</ContextoAtras.Provider>;
}

/** Lo lee la barra de arriba: si hay un manejador de la pantalla, "Atrás" regresa un paso en vez de salir. */
export function useManejadorAtras(): MutableRefObject<ManejadorAtras | null> | null {
  return useContext(ContextoAtras);
}

/**
 * Una pantalla de pasos registra aquí qué hace "Atrás". En celular y tableta lo usa la barra de arriba;
 * en computadora, donde no hay barra, `BotonAtrasPaso` lo muestra dentro de la pantalla. Así nunca hay dos.
 */
export function usarAtrasDePasos(manejador: ManejadorAtras | null) {
  const ref = useContext(ContextoAtras);
  // Se actualiza en cada render para que el manejador siempre vea el paso actual.
  useEffect(() => {
    if (ref) ref.current = manejador;
  });
  useEffect(
    () => () => {
      if (ref) ref.current = null;
    },
    [ref],
  );
}

/** "Atrás" dentro de la pantalla: solo en computadora, porque en celular y tableta ya está en la barra. */
export function BotonAtrasPaso({ alVolver, deshabilitado }: { alVolver: () => void; deshabilitado?: boolean }) {
  const esEscritorio = useEsEscritorio();
  if (!esEscritorio) return null;
  return (
    <Boton variante="texto" className="-ml-3 self-start" disabled={deshabilitado} onClick={alVolver}>
      <ArrowLeftIcon aria-hidden="true" />
      Atrás
    </Boton>
  );
}
