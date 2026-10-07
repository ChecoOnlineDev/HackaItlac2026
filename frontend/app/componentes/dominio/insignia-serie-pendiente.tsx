import { cn } from "cn";
import { TriangleAlertIcon } from "lucide-react";

/**
 * Píldora amarilla «Serie pendiente» (ADR-010, E-29): la pieza todavía no tiene número de serie.
 * Es un aviso que no bloquea. Lleva icono y texto además del color.
 */
export function InsigniaSeriePendiente({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border border-semaforo-amarillo bg-semaforo-amarillo/10 px-2.5 py-0.5 text-xs font-semibold text-foreground",
        className,
      )}
    >
      <TriangleAlertIcon aria-hidden="true" className="size-3.5 shrink-0 text-semaforo-amarillo" strokeWidth={3} />
      Serie pendiente
    </span>
  );
}
