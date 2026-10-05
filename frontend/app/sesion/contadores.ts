import { createContext, createElement, useContext, useEffect, useState, type ReactNode } from "react";

import { apiGet } from "~/api/cliente";
import { useSesion } from "./sesion";

export interface Contadores {
  /** Traspasos en tránsito hacia el almacén de la sesión. */
  porRecibir?: number;
  /** Solicitudes de autorización pendientes. */
  porAutorizar?: number;
}

function contar(datos: unknown): number | undefined {
  if (Array.isArray(datos)) return datos.length;
  if (datos && typeof datos === "object") {
    const d = datos as { total?: unknown; elementos?: unknown };
    if (typeof d.total === "number") return d.total;
    if (Array.isArray(d.elementos)) return d.elementos.length;
  }
  return undefined;
}

const EVENTO_CONTADORES = "imhotep:contadores";

/** Pide al inicio y al menú volver a contar ya (por ejemplo, tras confirmar una recepción). */
export function refrescarContadores(): void {
  if (typeof window !== "undefined") window.dispatchEvent(new Event(EVENTO_CONTADORES));
}

/**
 * Cuentas que muestran los botones del inicio. Si un endpoint aún no existe o falla,
 * la cuenta simplemente no aparece (sin traspasos, "Recibir" va sin contador).
 */
function useCargarContadores(): Contadores {
  const { puede } = useSesion();
  const [contadores, setContadores] = useState<Contadores>({});
  const verTraspasos = puede("traspasos.operar");
  const verAutorizaciones = puede("autorizaciones.resolver");

  useEffect(() => {
    const control = new AbortController();
    const cargar = async () => {
      const [porRecibir, porAutorizar] = await Promise.all([
        verTraspasos
          ? apiGet("/traspasos/por-recibir", undefined, control.signal).then(contar, () => undefined)
          : undefined,
        verAutorizaciones
          ? apiGet("/autorizaciones", { estado: "PENDIENTE" }, control.signal).then(contar, () => undefined)
          : undefined,
      ]);
      if (!control.signal.aborted) setContadores({ porRecibir, porAutorizar });
    };
    void cargar();
    const alRefrescar = () => void cargar();
    window.addEventListener(EVENTO_CONTADORES, alRefrescar);
    // Quien resuelve autorizaciones ve el número subir casi al instante; los demás, cada 30 s.
    // Con la pestaña oculta no se pregunta.
    const intervalo = window.setInterval(
      () => {
        if (document.visibilityState === "visible") void cargar();
      },
      verAutorizaciones ? 5_000 : 30_000,
    );
    return () => {
      control.abort();
      window.removeEventListener(EVENTO_CONTADORES, alRefrescar);
      window.clearInterval(intervalo);
    };
  }, [verTraspasos, verAutorizaciones]);

  return contadores;
}

const ContextoContadores = createContext<Contadores>({});

/** Lo monta el layout de la aplicación una sola vez; las pantallas leen con `useContadores`. */
export function ContadoresProvider({ children }: { children: ReactNode }) {
  const contadores = useCargarContadores();
  return createElement(ContextoContadores.Provider, { value: contadores }, children);
}

export function useContadores(): Contadores {
  return useContext(ContextoContadores);
}
