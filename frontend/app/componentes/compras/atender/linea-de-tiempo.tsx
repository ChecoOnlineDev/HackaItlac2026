import { cn } from "cn";
import {
  BanIcon,
  CircleCheckBigIcon,
  FilePlus2Icon,
  PackageCheckIcon,
  ShoppingCartIcon,
  XCircleIcon,
  type LucideIcon,
} from "lucide-react";

import { formatearFechaHora } from "~/componentes/dominio/fechas";
import { instanteUtc } from "~/componentes/consulta/formato";
import type { EstadoSolicitud, EventoSolicitud } from "./tipos";

const ICONOS: Record<EstadoSolicitud, LucideIcon> = {
  PENDIENTE: FilePlus2Icon,
  EN_COMPRA: ShoppingCartIcon,
  COMPRADA: PackageCheckIcon,
  INGRESADA: CircleCheckBigIcon,
  RECHAZADA: XCircleIcon,
  CANCELADA: BanIcon,
};

/** Qué pasó, en una frase. El primer evento (nace pendiente) es el de la solicitud. */
const TITULOS: Record<EstadoSolicitud, string> = {
  PENDIENTE: "Se levantó la solicitud",
  EN_COMPRA: "Compras la tomó",
  COMPRADA: "Se marcó como comprada",
  INGRESADA: "Se ingresó al almacén",
  RECHAZADA: "Compras la rechazó",
  CANCELADA: "Se canceló la solicitud",
};

/**
 * Lo que le ha pasado a la solicitud, del más antiguo al más reciente: qué pasó, quién, cuándo (hora de
 * México) y su nota. Los eventos no se editan ni se borran (SC-08).
 */
export function LineaDeTiempoSolicitud({ eventos }: { eventos: EventoSolicitud[] }) {
  if (eventos.length === 0) {
    return <p className="text-sm text-muted-foreground">Esta solicitud todavía no tiene movimientos.</p>;
  }
  return (
    <ol aria-label="Línea de tiempo de la solicitud" className="flex flex-col">
      {eventos.map((e, i) => {
        const Icono = ICONOS[e.estado_nuevo];
        const ultimo = i === eventos.length - 1;
        return (
          <li key={e.id ?? `${e.estado_nuevo}-${e.creado_en}-${i}`} className="flex gap-3">
            <div className="flex flex-col items-center">
              <span
                className={cn(
                  "flex size-10 shrink-0 items-center justify-center rounded-full border-2 bg-card",
                  ultimo && "border-primary",
                )}
              >
                <Icono aria-hidden="true" className="size-5 text-marino" />
              </span>
              {!ultimo ? <span aria-hidden="true" className="w-0.5 flex-1 bg-border" /> : null}
            </div>
            <div className={cn("flex min-w-0 flex-1 flex-col gap-0.5 pb-5", ultimo && "pb-0")}>
              <p className="text-sm font-medium text-muted-foreground">{formatearFechaHora(instanteUtc(e.creado_en))}</p>
              <p className="text-base font-semibold wrap-break-word">{TITULOS[e.estado_nuevo]}</p>
              <p className="text-sm text-muted-foreground">Por {e.usuario.nombre}</p>
              {e.nota ? (
                <p className="mt-1 rounded-xl border bg-muted/60 p-3 text-sm wrap-break-word">
                  <span className="font-medium text-muted-foreground">Nota: </span>
                  {e.nota}
                </p>
              ) : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
