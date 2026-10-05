import { cn } from "cn";

import { Skeleton } from "~/components/ui/skeleton";

type TipoEsqueleto = "lista" | "renglon" | "tarjeta" | "tabla";

interface PropiedadesEsqueleto {
  tipo?: TipoEsqueleto;
  /** Cuántos renglones o tarjetas dibujar. */
  cantidad?: number;
  className?: string;
}

function Renglon() {
  return (
    <div className="flex items-center gap-3 rounded-xl border p-3">
      <Skeleton className="size-12 shrink-0 rounded-full" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-2/3" />
        <Skeleton className="h-3 w-1/3" />
      </div>
      <Skeleton className="h-8 w-16" />
    </div>
  );
}

function Tarjeta() {
  return (
    <div className="space-y-3 rounded-xl border p-4">
      <Skeleton className="h-5 w-1/2" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-4/5" />
    </div>
  );
}

/** Marcador de lugar mientras carga una lista, un renglón, una tarjeta o una tabla. */
export function Esqueleto({ tipo = "lista", cantidad = 3, className }: PropiedadesEsqueleto) {
  const veces = Array.from({ length: cantidad }, (_, i) => i);
  return (
    <div role="status" aria-label="Cargando" aria-busy="true" className={cn("w-full", className)}>
      <span className="sr-only">Cargando</span>
      {tipo === "renglon" ? <Renglon /> : null}
      {tipo === "tarjeta" ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {veces.map((i) => (
            <Tarjeta key={i} />
          ))}
        </div>
      ) : null}
      {tipo === "lista" ? (
        <div className="space-y-3">
          {veces.map((i) => (
            <Renglon key={i} />
          ))}
        </div>
      ) : null}
      {tipo === "tabla" ? (
        <div className="overflow-hidden rounded-xl border">
          <div className="flex gap-4 border-b bg-muted p-3">
            <Skeleton className="h-4 w-1/4" />
            <Skeleton className="h-4 w-1/4" />
            <Skeleton className="h-4 w-1/6" />
          </div>
          {veces.map((i) => (
            <div key={i} className="flex gap-4 border-b p-3 last:border-b-0">
              <Skeleton className="h-4 w-1/4" />
              <Skeleton className="h-4 w-1/4" />
              <Skeleton className="h-4 w-1/6" />
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
