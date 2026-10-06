import { cn } from "cn";
import { BanIcon, ClockIcon, PackageCheckIcon, ReceiptTextIcon, ShoppingCartIcon, XIcon, ZapIcon, type LucideIcon } from "lucide-react";

import { TEXTO_ESTADO, TEXTO_URGENCIA, type EstadoSolicitud, type Urgencia } from "./tipos";

const BASE = "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap";

/**
 * Cada estado lleva icono y texto además del color. No se usa el semáforo (verde, amarillo, naranja y rojo
 * son solo para el nivel de un renglón o una pieza): los estados de la solicitud tienen sus propios tonos.
 */
const ESTILOS: Record<EstadoSolicitud, { icono: LucideIcon; clases: string }> = {
  PENDIENTE: { icono: ClockIcon, clases: "border-primary/40 bg-accent text-marino" },
  EN_COMPRA: { icono: ShoppingCartIcon, clases: "border-sky-300 bg-sky-50 text-sky-900" },
  COMPRADA: { icono: ReceiptTextIcon, clases: "border-violet-300 bg-violet-50 text-violet-900" },
  INGRESADA: { icono: PackageCheckIcon, clases: "border-teal-300 bg-teal-50 text-teal-900" },
  RECHAZADA: { icono: BanIcon, clases: "border-destructive/40 bg-destructive/5 text-destructive" },
  CANCELADA: { icono: XIcon, clases: "border-border bg-muted text-muted-foreground" },
};

export function InsigniaEstadoCompra({ estado, className }: { estado: EstadoSolicitud; className?: string }) {
  const { icono: Icono, clases } = ESTILOS[estado];
  return (
    <span className={cn(BASE, clases, className)}>
      <Icono aria-hidden="true" className="size-3.5 shrink-0" strokeWidth={2.5} />
      {TEXTO_ESTADO[estado]}
    </span>
  );
}

export function InsigniaUrgencia({ urgencia, className }: { urgencia: Urgencia; className?: string }) {
  const urgente = urgencia === "URGENTE";
  return (
    <span className={cn(BASE, urgente ? "border-marino bg-marino text-white" : "border-border bg-muted text-foreground", className)}>
      {urgente ? <ZapIcon aria-hidden="true" className="size-3.5 shrink-0" strokeWidth={2.5} /> : null}
      {TEXTO_URGENCIA[urgencia]}
    </span>
  );
}
