import { useCallback, useEffect, useRef, useState } from "react";

export type EstadoBusqueda = "inactivo" | "corto" | "buscando" | "listo" | "vacio" | "error" | "sin_conexion";

export function normalizarBusqueda(texto: string): string {
  return texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim().toLocaleLowerCase("es-MX");
}

export function coincideBusqueda(texto: string, busqueda: string): boolean {
  const palabras = normalizarBusqueda(busqueda).split(/\s+/).filter(Boolean).slice(0, 5);
  const significativas = palabras.filter((p) => p.length > 1);
  return (significativas.length ? significativas : palabras).every((p) => normalizarBusqueda(texto).includes(p));
}

export function useRetraso(valor: string, ms = 300): string {
  const [retrasado, setRetrasado] = useState(valor);
  useEffect(() => {
    const id = setTimeout(() => setRetrasado(valor), ms);
    return () => clearTimeout(id);
  }, [valor, ms]);
  return retrasado;
}

/** UX-01/02: cambiar el texto invalida inmediatamente la respuesta anterior, aunque la API ignore el aborto. */
export function useBusquedaDiferida<T>(texto: string, pedir: (texto: string, signal: AbortSignal) => Promise<T>, opciones: { minimo?: number; espera?: number; clave?: string; vacio?: (resultado: T) => boolean } = {}) {
  const minimo = opciones.minimo ?? 2;
  const espera = opciones.espera ?? 300;
  const [resultado, setResultado] = useState<T | null>(null);
  const [textoDelResultado, setTextoDelResultado] = useState("");
  const [estado, setEstado] = useState<EstadoBusqueda>("inactivo");
  const [error, setError] = useState<unknown>(null);
  const [version, setVersion] = useState(0);
  const ref = useRef({ pedir, vacio: opciones.vacio });
  ref.current = { pedir, vacio: opciones.vacio };
  const control = useRef<AbortController | null>(null);
  const inmediato = useRef(false);
  const vigente = useRef(texto.trim());
  vigente.current = texto.trim();
  const buscarYa = useCallback(() => { control.current?.abort(); inmediato.current = true; setVersion((v) => v + 1); }, []);
  const limpiar = useCallback(() => { control.current?.abort(); setResultado(null); setTextoDelResultado(""); setError(null); setEstado("inactivo"); }, []);

  useEffect(() => {
    const q = texto.trim();
    const actual = new AbortController();
    control.current = actual;
    setError(null);
    if (q.length < minimo) {
      inmediato.current = false;
      setResultado(null);
      setEstado(q ? "corto" : "inactivo");
      return () => actual.abort();
    }
    setEstado("buscando");
    const ejecutar = async () => {
      try {
        const respuesta = await ref.current.pedir(q, actual.signal);
        if (actual.signal.aborted || vigente.current !== q) return;
        setResultado(respuesta);
        setTextoDelResultado(q);
        setEstado(ref.current.vacio?.(respuesta) ? "vacio" : "listo");
      } catch (causa) {
        if (actual.signal.aborted || vigente.current !== q) return;
        setError(causa);
        setEstado(typeof navigator !== "undefined" && !navigator.onLine ? "sin_conexion" : "error");
      }
    };
    const temporizador = setTimeout(() => void ejecutar(), inmediato.current ? 0 : espera);
    inmediato.current = false;
    return () => { actual.abort(); clearTimeout(temporizador); };
  }, [texto, minimo, espera, version, opciones.clave]);
  return { estado, resultado, textoDelResultado, error, buscarYa, limpiar };
}
