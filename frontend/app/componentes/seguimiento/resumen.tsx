import { cn } from "cn";

import { Skeleton } from "~/components/ui/skeleton";
import type { ResumenSeguimiento } from "./tipos";

/** Qué filtro de la lista representa cada tarjeta. */
export type ClaveResumen = "total" | "ALMACEN" | "TRABAJADOR" | "TRANSITO" | "NO_APTO";

const TARJETAS: { clave: ClaveResumen; titulo: string; valor: (r: ResumenSeguimiento) => number }[] = [
  { clave: "total", titulo: "Total", valor: (r) => r.total },
  { clave: "ALMACEN", titulo: "En almacén", valor: (r) => r.en_almacen },
  { clave: "TRABAJADOR", titulo: "En resguardo", valor: (r) => r.en_resguardo },
  { clave: "TRANSITO", titulo: "En tránsito", valor: (r) => r.en_transito },
  { clave: "NO_APTO", titulo: "No aptas", valor: (r) => r.no_aptas },
];

interface PropiedadesResumen {
  resumen: ResumenSeguimiento | null;
  /** Qué tarjeta está activa según los filtros de la pantalla. */
  activa: ClaveResumen;
  alElegir: (clave: ClaveResumen) => void;
  cargando?: boolean;
}

/**
 * Cinco tarjetas con los conteos de lo que se busca. Tocar una filtra la lista (otra vez, quita ese
 * filtro). Son botones con el número y el nombre juntos, para que un lector de pantalla los lea completos.
 */
export function ResumenSeguimientoTarjetas({ resumen, activa, alElegir, cargando }: PropiedadesResumen) {
  if (!resumen) {
    return (
      <div role="status" aria-label="Cargando el resumen" className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {TARJETAS.map((t) => (
          <Skeleton key={t.clave} className="h-16 rounded-2xl sm:h-20" />
        ))}
      </div>
    );
  }
  return (
    <ul
      aria-label="Resumen por lugar"
      className={cn("grid grid-cols-2 gap-3 transition-opacity sm:grid-cols-3 lg:grid-cols-5", cargando && "opacity-60")}
    >
      {TARJETAS.map((t, i) => {
        const esActiva = activa === t.clave;
        return (
          <li key={t.clave} className={cn(i === 0 && "col-span-2 sm:col-span-1")}>
            <button
              type="button"
              aria-pressed={esActiva}
              onClick={() => alElegir(t.clave)}
              className={cn(
                "flex min-h-16 w-full flex-col items-start justify-center gap-0.5 rounded-2xl border bg-card px-4 py-2.5 sm:min-h-20 sm:py-3 text-left shadow-xs transition-colors",
                "hover:bg-muted/40 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none",
                esActiva && "border-primary bg-accent ring-1 ring-primary",
              )}
            >
              <span className="text-xl leading-none font-semibold text-marino tabular-nums sm:text-2xl">{t.valor(resumen)}</span>
              <span className="text-sm text-muted-foreground">{t.titulo}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
