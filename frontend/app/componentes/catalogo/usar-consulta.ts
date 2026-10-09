import { useCallback, useEffect, useRef, useState } from "react";

interface EstadoConsulta<T> {
  datos: T | null;
  cargando: boolean;
  error: unknown;
  recargar: () => void;
}

/**
 * Carga datos de la API y los vuelve a pedir cuando cambia `clave`.
 * Mientras llega la respuesta nueva conserva la anterior (`cargando` es verdadero).
 */
export function useConsulta<T>(pedir: (signal: AbortSignal) => Promise<T>, clave: string): EstadoConsulta<T> {
  const [datos, setDatos] = useState<T | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [version, setVersion] = useState(0);
  const pedirRef = useRef(pedir);
  pedirRef.current = pedir;

  useEffect(() => {
    const control = new AbortController();
    setCargando(true);
    setError(null);
    pedirRef
      .current(control.signal)
      .then((respuesta) => {
        if (control.signal.aborted) return;
        setDatos(respuesta);
        setCargando(false);
      })
      .catch((causa: unknown) => {
        if (control.signal.aborted) return;
        setError(causa);
        setCargando(false);
      });
    return () => control.abort();
  }, [clave, version]);

  const recargar = useCallback(() => setVersion((v) => v + 1), []);
  return { datos, cargando, error, recargar };
}

export { useRetraso } from "~/componentes/ui/busqueda-diferida";
