import { ArchiveXIcon, TruckIcon, UserRoundIcon, WarehouseIcon, type LucideIcon } from "lucide-react";

import { Insignia, type EstadoInsignia } from "~/componentes/ui/insignia";
import type { DondeEsta, PiezaSeguimiento, TipoUbicacion } from "./tipos";

/**
 * Estado de la pieza: el semáforo solo se usa para su estado. Una pieza apta con la inspección vencida
 * no se puede entregar todavía, así que se marca como aviso.
 */
export function InsigniaEstadoPieza({
  pieza,
}: {
  pieza: Pick<PiezaSeguimiento, "estado" | "estado_texto" | "inspeccion_vigente" | "inspeccion_vigente_hasta">;
}) {
  let nivel: EstadoInsignia = "neutra";
  let texto = pieza.estado_texto;
  if (pieza.estado === "APTO") {
    const vencida = pieza.inspeccion_vigente_hasta !== null && !pieza.inspeccion_vigente;
    nivel = vencida ? "amarillo" : "verde";
    if (vencida) texto = `${pieza.estado_texto}, inspección vencida`;
  } else if (pieza.estado !== "BAJA") {
    nivel = "rojo";
  }
  return (
    <Insignia estado={nivel} className="max-w-full rounded-2xl text-left whitespace-normal">
      {texto}
    </Insignia>
  );
}

const ICONOS: Partial<Record<TipoUbicacion, LucideIcon>> = {
  ALMACEN: WarehouseIcon,
  TRABAJADOR: UserRoundIcon,
  TRANSITO: TruckIcon,
  BAJA: ArchiveXIcon,
};

/** Dónde está o quién la tiene, con el texto que arma el servidor y un icono (nunca solo color). */
export function InsigniaDonde({ donde }: { donde: DondeEsta }) {
  const Icono = ICONOS[donde.tipo];
  const estado: EstadoInsignia = donde.tipo === "TRABAJADOR" || donde.tipo === "TRANSITO" ? "info" : "neutra";
  return (
    <Insignia estado={estado} className="max-w-full rounded-2xl whitespace-normal">
      {Icono ? <Icono aria-hidden="true" className="size-3.5 shrink-0" /> : null}
      <span className="min-w-0 text-left">{donde.texto}</span>
    </Insignia>
  );
}
