import { cn } from "cn";
import { CheckIcon, HammerIcon, HourglassIcon, ThumbsUpIcon } from "lucide-react";

import type { Condicion } from "~/componentes/dominio/tipos";

export const NOMBRE_CONDICION: Record<Condicion, string> = {
  BUENO: "Bueno",
  DESGASTE: "Desgaste por uso",
  DANADO: "Dañado",
};

const ICONO = { BUENO: ThumbsUpIcon, DESGASTE: HourglassIcon, DANADO: HammerIcon } as const;
const ORDEN: Condicion[] = ["BUENO", "DESGASTE", "DANADO"];

interface PropiedadesControlCondicion {
  valor: Condicion | null;
  alCambiar: (condicion: Condicion) => void;
  deshabilitado?: boolean;
  /** Texto que nombra el grupo para quien usa lector de pantalla. */
  etiqueta?: string;
  className?: string;
  /** Valor de `data-tutorial` (FEAT-010). */
  ancla?: string;
}

/**
 * Los tres botones grandes de cómo regresa lo devuelto: Bueno, Desgaste por uso y Dañado (V-04).
 * La elegida lleva palomita y color de relleno, no solo color. No usa los colores del semáforo.
 */
export function ControlCondicion({ valor, alCambiar, deshabilitado = false, etiqueta = "Cómo regresa", className, ancla }: PropiedadesControlCondicion) {
  return (
    <div role="group" aria-label={etiqueta} data-tutorial={ancla} className={cn("grid grid-cols-3 gap-2", className)}>
      {ORDEN.map((condicion) => {
        const Icono = ICONO[condicion];
        const elegida = valor === condicion;
        return (
          <button
            key={condicion}
            type="button"
            aria-pressed={elegida}
            disabled={deshabilitado}
            onClick={() => alCambiar(condicion)}
            className={cn(
              "flex min-h-12 flex-col items-center justify-center gap-1 rounded-xl border-2 px-1.5 py-2 text-center text-base leading-tight font-semibold transition-colors duration-150 motion-reduce:transition-none",
              "focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:opacity-50",
              elegida ? "border-primary bg-primary text-primary-foreground" : "border-input bg-background hover:bg-muted",
            )}
          >
            <span className="flex items-center gap-1">
              {elegida ? <CheckIcon aria-hidden="true" className="size-5" strokeWidth={3} /> : <Icono aria-hidden="true" className="size-5" />}
            </span>
            <span>{NOMBRE_CONDICION[condicion]}</span>
          </button>
        );
      })}
    </div>
  );
}
