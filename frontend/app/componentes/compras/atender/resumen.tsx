import { cn } from "cn";
import { useEffect, useState } from "react";

import { apiGet } from "~/api/cliente";
import { Skeleton } from "~/components/ui/skeleton";
import type { EstadoSolicitud } from "./tipos";

export interface ResumenCola {
  pendientes: number;
  urgentes: number;
  enCompra: number;
  compradas: number;
}

type Total = { total: number };

/**
 * Cuántas solicitudes hay en cada punto de la cola, con `solo_contar` (sin traer las filas). Se vuelve a pedir
 * cuando cambia `version` (al actuar sobre una solicitud, para que los números no se queden atrás).
 */
export function useResumenCola(version: number): { resumen: ResumenCola | null; error: boolean } {
  const [resumen, setResumen] = useState<ResumenCola | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const control = new AbortController();
    const contar = (parametros: Record<string, string>) =>
      apiGet<Total>("/solicitudes-compra", { ...parametros, solo_contar: true }, control.signal).then((r) => r.total);
    Promise.all([
      contar({ estado: "PENDIENTE" }),
      contar({ estado: "PENDIENTE", urgencia: "URGENTE" }),
      contar({ estado: "EN_COMPRA" }),
      contar({ estado: "COMPRADA" }),
    ])
      .then(([pendientes, urgentes, enCompra, compradas]) => {
        if (control.signal.aborted) return;
        setResumen({ pendientes, urgentes, enCompra, compradas });
        setError(false);
      })
      .catch(() => {
        if (!control.signal.aborted) setError(true);
      });
    return () => control.abort();
  }, [version]);

  return { resumen, error };
}

const TARJETAS: { estado: EstadoSolicitud; titulo: string; valor: (r: ResumenCola) => number }[] = [
  { estado: "PENDIENTE", titulo: "Pendientes", valor: (r) => r.pendientes },
  { estado: "EN_COMPRA", titulo: "En compra", valor: (r) => r.enCompra },
  { estado: "COMPRADA", titulo: "Compradas por ingresar", valor: (r) => r.compradas },
];

interface PropiedadesResumen {
  resumen: ResumenCola | null;
  /** El estado que filtra la lista ahora. */
  activo: string;
  alElegir: (estado: EstadoSolicitud) => void;
}

/** Tres tarjetas táctiles con lo que espera a Compras. Tocar una filtra la lista; tocarla otra vez, quita el filtro. */
export function ResumenCompras({ resumen, activo, alElegir }: PropiedadesResumen) {
  if (!resumen) {
    return (
      <div role="status" aria-label="Cargando el resumen" className="grid grid-cols-3 gap-2 sm:gap-3">
        {TARJETAS.map((t) => (
          <Skeleton key={t.estado} className="h-20 rounded-2xl" />
        ))}
      </div>
    );
  }
  return (
    <ul aria-label="Resumen de la cola" className="grid grid-cols-3 gap-2 sm:gap-3">
      {TARJETAS.map((t) => {
        const esActiva = activo === t.estado;
        return (
          <li key={t.estado}>
            <button
              type="button"
              aria-pressed={esActiva}
              onClick={() => alElegir(t.estado)}
              className={cn(
                "flex min-h-24 w-full flex-col items-start justify-between gap-1 rounded-2xl border bg-card px-3 py-3 text-left shadow-xs transition-colors sm:min-h-20 sm:flex-row-reverse sm:items-center sm:px-4",
                "hover:bg-muted/40 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none",
                esActiva && "border-primary bg-accent ring-1 ring-primary",
              )}
            >
              <span className="text-3xl leading-none font-semibold text-marino tabular-nums">{t.valor(resumen)}</span>
              <span className="flex flex-col gap-0.5">
                <span className="text-xs leading-tight text-muted-foreground sm:text-sm">{t.titulo}</span>
                {t.estado === "PENDIENTE" && resumen.urgentes > 0 ? (
                  <span className="text-xs font-semibold text-destructive">
                    {resumen.urgentes} {resumen.urgentes === 1 ? "urgente" : "urgentes"}
                  </span>
                ) : null}
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
