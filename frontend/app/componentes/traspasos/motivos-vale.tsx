import { cn } from "cn";
import { CheckIcon, TriangleAlertIcon, XIcon } from "lucide-react";

import type { MotivoRegla, NivelSemaforo } from "~/componentes/dominio/tipos";

const ICONO = { VERDE: CheckIcon, AMARILLO: TriangleAlertIcon, NARANJA: TriangleAlertIcon, ROJO: XIcon } as const;
const TEXTO: Record<NivelSemaforo, string> = { VERDE: "Listo", AMARILLO: "Aviso", NARANJA: "Aviso", ROJO: "No se puede continuar" };
const COLOR_ICONO: Record<NivelSemaforo, string> = {
  VERDE: "text-semaforo-verde",
  AMARILLO: "text-semaforo-amarillo",
  NARANJA: "text-semaforo-naranja",
  ROJO: "text-semaforo-rojo",
};
const BORDE: Record<NivelSemaforo, string> = {
  VERDE: "border",
  AMARILLO: "border-2 border-semaforo-amarillo bg-semaforo-amarillo/10",
  NARANJA: "border-2 border-semaforo-amarillo bg-semaforo-amarillo/10",
  ROJO: "border-2 border-semaforo-rojo bg-semaforo-rojo/10",
};

/**
 * Los motivos que valen para todo el traspaso o la recepción (por ejemplo la ruta, X-03, o que el traspaso
 * es de otro almacén, X-10). Cada uno con icono y texto además del color, y el ID de su regla.
 */
export function MotivosDelVale({ motivos, className }: { motivos: MotivoRegla[]; className?: string }) {
  if (motivos.length === 0) return null;
  return (
    <ul aria-label="Avisos del traspaso" className={cn("flex flex-col gap-2", className)}>
      {motivos.map((m, i) => {
        const Icono = ICONO[m.nivel];
        return (
          <li key={`${m.regla}-${i}`} className={cn("flex items-start gap-2 rounded-xl p-3 text-sm", BORDE[m.nivel])}>
            <Icono aria-hidden="true" strokeWidth={3} className={cn("mt-1 size-4 shrink-0", COLOR_ICONO[m.nivel])} />
            <span className="min-w-0 flex-1">
              <span className="sr-only">{TEXTO[m.nivel]}: </span>
              {m.mensaje} <span className="text-xs font-medium whitespace-nowrap text-muted-foreground">({m.regla})</span>
            </span>
          </li>
        );
      })}
    </ul>
  );
}
