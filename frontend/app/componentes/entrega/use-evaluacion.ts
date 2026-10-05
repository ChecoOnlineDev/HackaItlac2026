import { useCallback, useEffect, useRef, useState } from "react";

import { apiPost } from "~/api/cliente";
import { esErrorApi, type ErrorApi } from "~/api/errores";
import type { EvaluacionApi } from "./tipos";

/** El cuerpo de `POST /api/vales/evaluar` (el mismo que el de confirmar, sin la firma). */
export interface CuerpoEvaluar {
  tipo: "ENTREGA";
  almacen_id: string | null;
  trabajador_id: string;
  id_cliente: string;
  autorizacion_id?: string;
  renglones: { codigo: string; cantidad: number; observacion?: string }[];
}

interface Resultado {
  /** Última evaluación recibida (puede ser de un borrador anterior si llegó otro cambio). */
  evaluacion: EvaluacionApi | null;
  /** `true` si `evaluacion` corresponde al borrador tal como está ahora. */
  actual: boolean;
  /** Se está esperando la respuesta del servidor. */
  evaluando: boolean;
  /** Por qué falló la última evaluación (sin conexión, otro almacén...). */
  error: ErrorApi | null;
  /** Vuelve a evaluar el mismo borrador. */
  reintentar: () => void;
  /** Usa una evaluación que ya se tiene (la que trae `VALE_CAMBIO`) como la actual. */
  adoptar: (evaluacion: EvaluacionApi) => void;
}

const ESPERA_MS = 120;

/**
 * Evalúa el borrador completo en el servidor cada vez que cambia (E-28: no se escribe nada). Cancela la
 * evaluación anterior y descarta respuestas viejas. La pantalla muestra lo que responde; no decide nada.
 */
export function useEvaluacion(cuerpo: CuerpoEvaluar | null): Resultado {
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
    const cuerpoActual = JSON.parse(clave) as CuerpoEvaluar;
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
    }, ESPERA_MS);
    return () => {
      window.clearTimeout(temporizador);
      control.abort();
    };
  }, [clave, intento]);

  const reintentar = useCallback(() => setIntento((n) => n + 1), []);
  const adoptar = useCallback((nueva: EvaluacionApi) => {
    setEvaluacion(nueva);
    setClaveEvaluada(claveRef.current);
    setError(null);
  }, []);

  return {
    evaluacion,
    actual: clave !== null && clave === claveEvaluada,
    evaluando,
    error,
    reintentar,
    adoptar,
  };
}
