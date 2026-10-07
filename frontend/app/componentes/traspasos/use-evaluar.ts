import { useCallback, useEffect, useRef, useState } from "react";

import { apiPost } from "~/api/cliente";
import { esErrorApi, type ErrorApi } from "~/api/errores";
import type { EvaluacionApi } from "~/componentes/entrega/tipos";

/** El cuerpo de `POST /api/vales/evaluar` para un traspaso o una recepción (el mismo que el de confirmar). */
export interface CuerpoTraspaso {
  tipo: "TRASPASO" | "RECEPCION";
  almacen_id?: string | null;
  destino_almacen_id?: string;
  vale_origen_id?: string;
  id_cliente: string;
  renglones: { codigo: string; cantidad: number }[];
}

interface Resultado {
  evaluacion: EvaluacionApi | null;
  /** `true` si `evaluacion` corresponde al cuerpo tal como está ahora. */
  actual: boolean;
  evaluando: boolean;
  error: ErrorApi | null;
  reintentar: () => void;
  adoptar: (evaluacion: EvaluacionApi) => void;
}

const ESPERA_MS = 120;

/**
 * Evalúa el borrador de un traspaso o una recepción en el servidor cada vez que cambia (E-28: no se
 * escribe nada). Cancela la evaluación anterior y descarta respuestas viejas.
 */
export function useEvaluar(cuerpo: CuerpoTraspaso | null, esperaMs: number = ESPERA_MS): Resultado {
  const [evaluacion, setEvaluacion] = useState<EvaluacionApi | null>(null);
  const [claveEvaluada, setClaveEvaluada] = useState<string | null>(null);
  const [evaluando, setEvaluando] = useState(false);
  const [error, setError] = useState<ErrorApi | null>(null);
  const [intento, setIntento] = useState(0);

  const clave = cuerpo ? JSON.stringify(cuerpo) : null;
  const claveRef = useRef(clave);
  claveRef.current = clave;

  useEffect(() => {
    if (!clave) {
      setEvaluando(false);
      return;
    }
    const control = new AbortController();
    const cuerpoActual = JSON.parse(clave) as CuerpoTraspaso;
    setEvaluando(true);
    const temporizador = window.setTimeout(() => {
      apiPost<EvaluacionApi>("/vales/evaluar", cuerpoActual, control.signal)
        .then((respuesta) => {
          setEvaluacion(respuesta);
          setClaveEvaluada(clave);
          setError(null);
          setEvaluando(false);
        })
        .catch((causa: unknown) => {
          if (control.signal.aborted || (causa instanceof DOMException && causa.name === "AbortError")) return;
          setError(esErrorApi(causa) ? causa : null);
          setEvaluando(false);
        });
    }, esperaMs);
    return () => {
      window.clearTimeout(temporizador);
      control.abort();
    };
  }, [clave, intento, esperaMs]);

  const reintentar = useCallback(() => setIntento((n) => n + 1), []);
  const adoptar = useCallback((nueva: EvaluacionApi) => {
    setEvaluacion(nueva);
    setClaveEvaluada(claveRef.current);
    setError(null);
  }, []);

  return { evaluacion, actual: clave !== null && clave === claveEvaluada, evaluando, error, reintentar, adoptar };
}
