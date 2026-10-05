import { useCallback, useEffect, useState } from "react";

import { apiGet } from "~/api/cliente";

export interface EstadoCarga<T> {
  datos: T | null;
  error: unknown;
  /** Solo la primera carga (o tras cambiar la ruta): las recargas conservan lo que ya se muestra. */
  cargando: boolean;
  recargar: () => void;
}

/**
 * Carga un recurso con estados de carga y error. `ruta` en null no pide nada.
 * Recargar no vacía la pantalla: refresca los datos debajo del contenido que ya se ve.
 */
export function useCarga<T>(ruta: string | null, parametros?: Record<string, string | number | undefined>): EstadoCarga<T> {
  const [datos, setDatos] = useState<T | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [cargando, setCargando] = useState(ruta !== null);
  const [version, setVersion] = useState(0);
  const claveParametros = JSON.stringify(parametros ?? {});

  useEffect(() => {
    if (ruta === null) {
      setDatos(null);
      setError(null);
      setCargando(false);
      return;
    }
    const control = new AbortController();
    setError(null);
    apiGet<T>(ruta, JSON.parse(claveParametros) as Record<string, string | number>, control.signal)
      .then((respuesta) => {
        setDatos(respuesta);
        setCargando(false);
      })
      .catch((causa: unknown) => {
        if (causa instanceof DOMException && causa.name === "AbortError") return;
        setError(causa);
        setCargando(false);
      });
    return () => control.abort();
  }, [ruta, claveParametros, version]);

  // Al cambiar de recurso se vuelve a mostrar el esqueleto.
  useEffect(() => {
    if (ruta !== null) {
      setDatos(null);
      setCargando(true);
    }
  }, [ruta, claveParametros]);

  const recargar = useCallback(() => setVersion((n) => n + 1), []);
  return { datos, error, cargando, recargar };
}
