import { cn } from "cn";
import { CheckIcon, LockIcon, TriangleAlertIcon, XIcon } from "lucide-react";
import type { ReactNode } from "react";

/**
 * Los cuatro niveles del semáforo tienen icono y texto además de color (SM-02).
 * Son colores reservados: úsalos solo para el nivel de un renglón o una pieza.
 * Para estados generales (Activo, Inactivo, En tránsito...) usa `neutra` o `info`.
 */
export type EstadoInsignia = "verde" | "amarillo" | "naranja" | "rojo" | "neutra" | "info";

const SEMAFORO = {
  verde: { texto: "Listo", icono: CheckIcon, clases: "border-semaforo-verde bg-semaforo-verde/10", iconoClase: "text-semaforo-verde" },
  amarillo: { texto: "Aviso", icono: TriangleAlertIcon, clases: "border-semaforo-amarillo bg-semaforo-amarillo/10", iconoClase: "text-semaforo-amarillo" },
  naranja: { texto: "Requiere autorización", icono: LockIcon, clases: "border-semaforo-naranja bg-semaforo-naranja/10", iconoClase: "text-semaforo-naranja" },
  rojo: { texto: "No se puede entregar", icono: XIcon, clases: "border-semaforo-rojo bg-semaforo-rojo/10", iconoClase: "text-semaforo-rojo" },
} as const;

interface PropiedadesInsignia {
  estado: EstadoInsignia;
  /** Texto a mostrar. En el semáforo, por omisión el de la tabla de ui-ux.md. */
  children?: ReactNode;
  className?: string;
}

export function Insignia({ estado, children, className }: PropiedadesInsignia) {
  const base = "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold text-foreground";
  if (estado === "neutra" || estado === "info") {
    return (
      <span
        className={cn(
          base,
          estado === "neutra" ? "border-border bg-muted" : "border-primary/40 bg-accent text-marino",
          className,
        )}
      >
        {children}
      </span>
    );
  }
  const nivel = SEMAFORO[estado];
  const Icono = nivel.icono;
  return (
    <span className={cn(base, nivel.clases, className)}>
      <Icono aria-hidden="true" className={cn("size-3.5 shrink-0", nivel.iconoClase)} strokeWidth={3} />
      {children ?? nivel.texto}
    </span>
  );
}
