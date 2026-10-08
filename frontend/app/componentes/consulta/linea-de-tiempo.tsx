import { cn } from "cn";
import { ArrowRightIcon, ArrowLeftRightIcon, CalendarClockIcon, ClipboardCheckIcon, RefreshCwIcon, type LucideIcon } from "lucide-react";
import { Link } from "react-router";

import { formatearFecha, formatearFechaHora } from "~/componentes/dominio/fechas";
import { instanteUtc } from "./formato";
import type { HechoHistorial, TipoHistorial } from "./tipos";

const ICONOS: Record<TipoHistorial, { icono: LucideIcon; etiqueta: string }> = {
  MOVIMIENTO: { icono: ArrowLeftRightIcon, etiqueta: "Movimiento" },
  INSPECCION: { icono: ClipboardCheckIcon, etiqueta: "Inspección" },
  CAMBIO_ESTADO: { icono: RefreshCwIcon, etiqueta: "Cambio de estado" },
  AJUSTE_VIGENCIA: { icono: CalendarClockIcon, etiqueta: "Ajuste de vigencia" },
};

/** El detalle de un ajuste llega como "De <antes> a <ahora>. Motivo: <motivo>"; aquí solo interesa el motivo. */
function motivoDe(detalle: string | null): string | null {
  if (!detalle) return null;
  const i = detalle.indexOf("Motivo: ");
  return i >= 0 ? detalle.slice(i + "Motivo: ".length) : detalle;
}

const CONDICIONES: Record<string, string> = { BUENO: "buen estado", DESGASTE: "desgaste por uso", DANADO: "dañado" };

function Detalle({ hecho, puedeVerVales, puedeVerTrabajadores }: { hecho: HechoHistorial; puedeVerVales: boolean; puedeVerTrabajadores: boolean }) {
  switch (hecho.tipo) {
    case "MOVIMIENTO":
      return (
        <>
          {hecho.origen && hecho.destino ? (
            <p className="flex flex-wrap items-center gap-x-1.5 text-base">
              <span>{hecho.origen}</span>
              <ArrowRightIcon aria-label="a" className="size-4 shrink-0" />
              <span>{hecho.destino}</span>
            </p>
          ) : null}
          {hecho.trabajador ? (
            <p className="text-base">
              {hecho.destino?.startsWith(hecho.trabajador) ? "Se la dieron a " : "La devolvió "}
              {puedeVerTrabajadores && hecho.trabajador_id ? (
                <Link to={`/trabajadores/${hecho.trabajador_id}`} className="inline-flex min-h-10 items-center font-semibold text-primary underline underline-offset-2">
                  {hecho.trabajador}
                </Link>
              ) : (
                <span className="font-semibold">{hecho.trabajador}</span>
              )}
            </p>
          ) : null}
          {hecho.almacen ? <p className="text-sm text-muted-foreground">Almacén: {hecho.almacen}</p> : null}
          {hecho.folio ? (
            <p className="text-sm text-muted-foreground">
              Vale{" "}
              {puedeVerVales && hecho.vale_id ? (
                <Link to={`/vales/${hecho.vale_id}`} className="inline-flex min-h-10 items-center font-semibold text-primary underline underline-offset-2">
                  {hecho.folio}
                </Link>
              ) : (
                <span className="font-semibold">{hecho.folio}</span>
              )}
              {hecho.condicion ? ` · Condición: ${CONDICIONES[hecho.condicion] ?? hecho.condicion.toLowerCase()}` : ""}
            </p>
          ) : null}
        </>
      );
    case "INSPECCION":
      return (
        <>
          {hecho.vigente_hasta ? (
            <p className="text-base">Vale hasta el {formatearFecha(hecho.vigente_hasta)}.</p>
          ) : null}
          {hecho.observacion ? <p className="text-base">Observación: {hecho.observacion}</p> : null}
        </>
      );
    case "CAMBIO_ESTADO":
      return (
        <>
          {hecho.observacion ? <p className="text-base">Observación: {hecho.observacion}</p> : null}
        </>
      );
    case "AJUSTE_VIGENCIA":
      return (
        <>
          <p className="text-base">
            {hecho.vigente_hasta_anterior ? `Antes: ${formatearFecha(hecho.vigente_hasta_anterior)}. ` : ""}
            {hecho.vigente_hasta ? `Ahora: ${formatearFecha(hecho.vigente_hasta)}.` : ""}
          </p>
          {motivoDe(hecho.detalle) ? <p className="text-base">Motivo: {motivoDe(hecho.detalle)}</p> : null}
        </>
      );
  }
}

interface PropiedadesLineaDeTiempo {
  historial: HechoHistorial[];
  /** Si puede abrir el vale de cada movimiento (`vales.ver`). */
  puedeVerVales?: boolean;
  /** Si puede abrir la ficha del trabajador de cada movimiento (`trabajadores.ver`). */
  puedeVerTrabajadores?: boolean;
}

/** Hechos de la vida de una pieza, del más reciente al más antiguo: quién y cuándo (hora de México). */
export function LineaDeTiempo({ historial, puedeVerVales = false, puedeVerTrabajadores = false }: PropiedadesLineaDeTiempo) {
  if (historial.length === 0) {
    return <p className="text-sm text-muted-foreground">Esta pieza todavía no tiene historial.</p>;
  }
  return (
    <ol className="flex flex-col">
      {historial.map((hecho, i) => {
        const { icono: Icono, etiqueta } = ICONOS[hecho.tipo];
        const ultimo = i === historial.length - 1;
        return (
          <li key={`${hecho.tipo}-${hecho.fecha}-${i}`} className="flex gap-3">
            <div className="flex flex-col items-center">
              <span className="flex size-10 shrink-0 items-center justify-center rounded-full border-2 bg-card">
                <Icono aria-hidden="true" className="size-5 text-marino" />
              </span>
              {!ultimo ? <span aria-hidden="true" className="w-0.5 flex-1 bg-border" /> : null}
            </div>
            <div className={cn("flex min-w-0 flex-1 flex-col gap-0.5 pb-5", ultimo && "pb-0")}>
              <p className="text-sm font-medium text-muted-foreground">
                {etiqueta} · {formatearFechaHora(instanteUtc(hecho.fecha))}
              </p>
              <p className="text-base font-semibold wrap-break-word">{hecho.titulo}</p>
              <Detalle hecho={hecho} puedeVerVales={puedeVerVales} puedeVerTrabajadores={puedeVerTrabajadores} />
              {hecho.usuario ? <p className="text-sm text-muted-foreground">{hecho.tipo === "MOVIMIENTO" ? "Lo registró" : "Por"} {hecho.usuario}</p> : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
