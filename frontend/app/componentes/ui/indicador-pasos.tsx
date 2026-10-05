import { cn } from "cn";

interface PropiedadesIndicadorPasos {
  actual: number;
  total: number;
  nombre: string;
  className?: string;
}

/** "Paso 2 de 3 · Artículos" con una barra de avance. Ocupa dos líneas bajas y no compite con el título. */
export function IndicadorPasos({ actual, total, nombre, className }: PropiedadesIndicadorPasos) {
  return (
    <div className={cn("flex flex-col gap-1.5", className)} aria-live="polite">
      <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
        Paso {actual} de {total} · {nombre}
      </p>
      <div className="flex gap-1" aria-hidden="true">
        {Array.from({ length: total }, (_, i) => (
          <span key={i} className={cn("h-1 flex-1 rounded-full", i < actual ? "bg-primary" : "bg-border")} />
        ))}
      </div>
    </div>
  );
}
