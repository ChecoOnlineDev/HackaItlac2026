import { cn } from "cn";
import { ChevronDownIcon } from "lucide-react";
import type { ReactNode } from "react";

interface PropiedadesEncabezado {
  /** Identificador del grupo; arma el `id` del encabezado y el del panel que controla. */
  id: string;
  titulo: string;
  abierto: boolean;
  /** `true` si la sección actual está en este grupo (se nota aunque esté cerrado). */
  activo: boolean;
  alAlternar: () => void;
  className?: string;
}

export const idPanelGrupo = (id: string) => `menu-grupo-${id}`;

/**
 * Encabezado de un grupo plegable del menú: botón de 44 px con `aria-expanded` y `aria-controls`,
 * foco visible y una flecha que gira (con «reducir movimiento», sin giro). Ver ui-ux.md,
 * «Grupo de menú plegable».
 */
export function EncabezadoGrupo({ id, titulo, abierto, activo, alAlternar, className }: PropiedadesEncabezado) {
  return (
    <button
      type="button"
      id={`${idPanelGrupo(id)}-encabezado`}
      aria-expanded={abierto}
      aria-controls={idPanelGrupo(id)}
      onClick={alAlternar}
      className={cn(
        "flex min-h-11 w-full items-center justify-between gap-2 rounded-xl px-3 text-left text-xs font-semibold tracking-wide uppercase transition-colors outline-none hover:bg-accent/60 focus-visible:ring-2 focus-visible:ring-ring",
        activo ? "text-marino" : "text-muted-foreground",
        className,
      )}
    >
      <span className="flex items-center gap-2">
        {titulo}
        {activo && !abierto ? (
          <>
            <span aria-hidden="true" className="size-1.5 rounded-full bg-primary" />
            <span className="sr-only">(aquí estás)</span>
          </>
        ) : null}
      </span>
      <ChevronDownIcon
        aria-hidden="true"
        className={cn("size-4 shrink-0 motion-safe:transition-transform", abierto ? "motion-safe:rotate-180" : "")}
      />
    </button>
  );
}

/** Panel de un grupo: se oculta (no se desmonta) mientras está cerrado. */
export function PanelGrupo({ id, abierto, children, className }: { id: string; abierto: boolean; children: ReactNode; className?: string }) {
  return (
    <div id={idPanelGrupo(id)} role="group" aria-labelledby={`${idPanelGrupo(id)}-encabezado`} hidden={!abierto} className={className}>
      {children}
    </div>
  );
}
