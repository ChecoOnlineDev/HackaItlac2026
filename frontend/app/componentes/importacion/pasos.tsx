import { cn } from "cn";
import { CheckIcon } from "lucide-react";

const NOMBRES = ["Qué hacer", "Pegar o subir", "Relacionar columnas", "Revisar y confirmar"] as const;

/**
 * Los cuatro pasos de la importación, siempre visibles: el actual con su número resaltado, los anteriores con
 * palomita. Nada se comunica solo con color: cada paso lleva número o icono y su nombre.
 */
export function PasosImportacion({ actual }: { actual: 1 | 2 | 3 | 4 | 5 }) {
  return (
    <nav aria-label="Pasos de la importación">
      <ol className="grid grid-cols-4 gap-2">
        {NOMBRES.map((nombre, i) => {
          const numero = i + 1;
          const hecho = actual > numero;
          const esActual = actual === numero;
          return (
            <li
              key={nombre}
              aria-current={esActual ? "step" : undefined}
              className={cn(
                "flex min-h-12 flex-col items-center justify-center gap-1 rounded-2xl border p-2 text-center sm:flex-row sm:gap-2",
                esActual && "border-primary bg-accent",
                hecho && "bg-muted",
              )}
            >
              <span
                aria-hidden="true"
                className={cn(
                  "flex size-7 shrink-0 items-center justify-center rounded-full border text-sm font-semibold",
                  esActual && "border-primary bg-primary text-primary-foreground",
                  hecho && "border-semaforo-verde bg-semaforo-verde text-white",
                )}
              >
                {hecho ? <CheckIcon className="size-4" strokeWidth={3} /> : numero}
              </span>
              <span className={cn("text-xs leading-tight sm:text-sm", esActual ? "font-semibold text-marino" : "font-medium")}>
                <span className="sr-only">
                  Paso {numero}
                  {hecho ? " (hecho): " : esActual ? " (actual): " : ": "}
                </span>
                {nombre}
              </span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
