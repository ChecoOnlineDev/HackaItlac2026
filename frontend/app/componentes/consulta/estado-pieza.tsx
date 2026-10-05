import { cn } from "cn";
import { CheckIcon, TriangleAlertIcon, XIcon, MinusIcon } from "lucide-react";

import { formatearFecha } from "~/componentes/dominio/fechas";
import { diasHasta, textoDias } from "./formato";

interface DatosEstado {
  estado: string;
  estado_texto: string;
  requiere_inspeccion?: boolean;
  inspeccion_vigente_hasta: string | null;
  inspeccion_vigente: boolean;
}

type Nivel = "verde" | "amarillo" | "rojo" | "neutro";

export interface LecturaPieza {
  nivel: Nivel;
  titulo: string;
  detalle: string;
}

/** Lo que dice la ficha de la pieza arriba: estado e inspección, con su fecha y los días que faltan. */
export function leerEstadoPieza(p: DatosEstado): LecturaPieza {
  if (p.estado === "BAJA") return { nivel: "neutro", titulo: "Pieza de baja", detalle: "Ya no se entrega ni se inspecciona." };
  if (p.estado === "NO_APTO") return { nivel: "rojo", titulo: "No apta", detalle: "No se entrega. Solo una inspección nueva la regresa a apta." };
  if (p.estado === "EN_MANTENIMIENTO" || p.estado === "EN_CALIBRACION")
    return { nivel: "rojo", titulo: p.estado_texto, detalle: "No se entrega mientras tanto." };
  if (p.requiere_inspeccion === false && !p.inspeccion_vigente_hasta)
    return { nivel: "verde", titulo: "Apta", detalle: "Este artículo no pide inspección." };
  if (!p.inspeccion_vigente_hasta) return { nivel: "rojo", titulo: "Sin inspección vigente", detalle: "No se entrega hasta que se inspeccione." };
  const dias = diasHasta(p.inspeccion_vigente_hasta);
  const fecha = formatearFecha(p.inspeccion_vigente_hasta);
  if (!p.inspeccion_vigente || dias < 0)
    return { nivel: "rojo", titulo: "Inspección vencida", detalle: `Venció el ${fecha} (${textoDias(dias)}). No se entrega hasta que se inspeccione.` };
  if (dias <= 14)
    return { nivel: "amarillo", titulo: "Apta, la inspección vence pronto", detalle: `Vale hasta el ${fecha} (${textoDias(dias)}).` };
  return { nivel: "verde", titulo: "Apta, con inspección vigente", detalle: `Vale hasta el ${fecha} (${textoDias(dias)}).` };
}

const ESTILOS: Record<Nivel, { caja: string; icono: typeof CheckIcon; color: string }> = {
  verde: { caja: "border-semaforo-verde bg-semaforo-verde/10", icono: CheckIcon, color: "text-semaforo-verde" },
  amarillo: { caja: "border-semaforo-amarillo bg-semaforo-amarillo/10", icono: TriangleAlertIcon, color: "text-semaforo-amarillo" },
  rojo: { caja: "border-semaforo-rojo bg-semaforo-rojo/10", icono: XIcon, color: "text-semaforo-rojo" },
  neutro: { caja: "border-border bg-muted", icono: MinusIcon, color: "text-muted-foreground" },
};

/** Banda grande de estado: color, icono y texto (nunca solo color). */
export function BandaEstadoPieza({ lectura, className }: { lectura: LecturaPieza; className?: string }) {
  const { caja, icono: Icono, color } = ESTILOS[lectura.nivel];
  return (
    <div role={lectura.nivel === "rojo" ? "alert" : "status"} className={cn("flex items-start gap-3 rounded-xl border-2 p-4", caja, className)}>
      <Icono aria-hidden="true" className={cn("mt-0.5 size-7 shrink-0", color)} strokeWidth={3} />
      <div className="flex flex-col gap-0.5">
        <p className="text-xl leading-tight font-bold">{lectura.titulo}</p>
        <p className="text-base">{lectura.detalle}</p>
      </div>
    </div>
  );
}
