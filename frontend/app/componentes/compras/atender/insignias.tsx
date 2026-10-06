import { cn } from "cn";
import {
  BanIcon,
  CircleCheckBigIcon,
  ClockIcon,
  PackageCheckIcon,
  ShoppingCartIcon,
  XCircleIcon,
  ZapIcon,
  type LucideIcon,
} from "lucide-react";

import { Insignia, type EstadoInsignia } from "~/componentes/ui/insignia";
import { TEXTO_ESTADO, TEXTO_URGENCIA, type EstadoSolicitud, type UrgenciaSolicitud } from "./tipos";

const ESTADOS: Record<EstadoSolicitud, { icono: LucideIcon; nivel: EstadoInsignia }> = {
  PENDIENTE: { icono: ClockIcon, nivel: "neutra" },
  EN_COMPRA: { icono: ShoppingCartIcon, nivel: "info" },
  COMPRADA: { icono: PackageCheckIcon, nivel: "info" },
  INGRESADA: { icono: CircleCheckBigIcon, nivel: "info" },
  RECHAZADA: { icono: XCircleIcon, nivel: "neutra" },
  CANCELADA: { icono: BanIcon, nivel: "neutra" },
};

/**
 * Estado de la solicitud, siempre con icono y texto. Los colores del semáforo no se usan aquí: están
 * reservados para el nivel de un renglón o de una pieza.
 */
export function InsigniaEstadoSolicitud({ estado, className }: { estado: EstadoSolicitud; className?: string }) {
  const { icono: Icono, nivel } = ESTADOS[estado];
  return (
    <Insignia estado={nivel} className={className}>
      <Icono aria-hidden="true" className="size-3.5 shrink-0" />
      {TEXTO_ESTADO[estado]}
    </Insignia>
  );
}

/** URGENTE va en rojo y con icono de rayo; NORMAL, en gris. */
export function InsigniaUrgencia({ urgencia, className }: { urgencia: UrgenciaSolicitud; className?: string }) {
  if (urgencia === "URGENTE") {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1 rounded-full border border-destructive/40 bg-destructive/10 px-2.5 py-0.5 text-xs font-semibold text-destructive",
          className,
        )}
      >
        <ZapIcon aria-hidden="true" className="size-3.5 shrink-0" strokeWidth={2.5} />
        {TEXTO_URGENCIA.URGENTE}
      </span>
    );
  }
  return (
    <Insignia estado="neutra" className={className}>
      {TEXTO_URGENCIA.NORMAL}
    </Insignia>
  );
}
