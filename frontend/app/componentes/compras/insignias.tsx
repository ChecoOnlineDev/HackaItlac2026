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

import { Insignia } from "~/componentes/ui/insignia";
import type { EstadoSolicitud, Urgencia } from "./solicitar/tipos";

const ESTADO_INSIGNIA: Record<EstadoSolicitud, { nivel: "neutra" | "info"; texto: string; icono: LucideIcon }> = {
  PENDIENTE: { nivel: "neutra", texto: "Pendiente", icono: ClockIcon },
  EN_COMPRA: { nivel: "info", texto: "En compra", icono: ShoppingCartIcon },
  COMPRADA: { nivel: "info", texto: "Comprada", icono: PackageCheckIcon },
  INGRESADA: { nivel: "info", texto: "Ingresada al almacén", icono: CircleCheckBigIcon },
  RECHAZADA: { nivel: "neutra", texto: "Rechazada", icono: XCircleIcon },
  CANCELADA: { nivel: "neutra", texto: "Cancelada", icono: BanIcon },
};

const BASE_URGENCIA = "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap";

/** La misma insignia y los mismos textos se usan en Mis solicitudes y en la cola de Compras. */
export function InsigniaEstadoCompra({ estado, className }: { estado: EstadoSolicitud; className?: string }) {
  const { nivel, texto, icono: Icono } = ESTADO_INSIGNIA[estado];
  return (
    <Insignia estado={nivel} className={className}>
      <Icono aria-hidden="true" className="size-3.5 shrink-0" />
      {texto}
    </Insignia>
  );
}

/** Las solicitudes urgentes se distinguen en rojo; las normales conservan el tratamiento neutro. */
export function InsigniaUrgencia({ urgencia, className }: { urgencia: Urgencia; className?: string }) {
  if (urgencia === "NORMAL") {
    return <Insignia estado="neutra" className={className}>Normal</Insignia>;
  }

  return (
    <span className={cn(BASE_URGENCIA, "border-destructive/40 bg-destructive/10 text-destructive", className)}>
      <ZapIcon aria-hidden="true" className="size-3.5 shrink-0" strokeWidth={2.5} />
      Urgente
    </span>
  );
}
