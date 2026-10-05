import { ArrowRightIcon, ChevronRightIcon } from "lucide-react";
import { Link } from "react-router";

import type { TraspasoPorRecibirApi } from "./tipos";
import { desdeCuando, textoRenglones } from "./formato";
import { Insignia } from "~/componentes/ui/insignia";

/**
 * Un traspaso en camino: folio, de dónde viene, cuántos renglones trae y desde cuándo. Toda la tarjeta es el
 * botón para abrir su recepción (más de 48 px de alto).
 */
export function TarjetaTraspaso({ traspaso, mostrarDestino }: { traspaso: TraspasoPorRecibirApi; mostrarDestino: boolean }) {
  const conDiferencias = traspaso.estado === "RECIBIDO_CON_DIFERENCIAS";
  const pendientes = traspaso.renglones.filter((r) => r.cantidad_pendiente > 0).length;
  return (
    <li>
      <Link
        to={`/recibir/${traspaso.id}`}
        className="flex min-h-12 items-center gap-3 rounded-2xl border bg-card p-4 transition-colors hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
      >
        <span className="flex min-w-0 flex-1 flex-col gap-1">
          <span className="flex flex-wrap items-center gap-2">
            <span className="text-lg font-semibold tracking-wide text-marino">{traspaso.folio}</span>
            {conDiferencias ? <Insignia estado="amarillo">Recibido en parte</Insignia> : <Insignia estado="info">En camino</Insignia>}
          </span>
          <span className="flex flex-wrap items-center gap-1.5 text-base font-semibold">
            {traspaso.origen.nombre}
            <ArrowRightIcon aria-label="hacia" className="size-4 shrink-0" />
            {mostrarDestino ? traspaso.destino.nombre : "este almacén"}
          </span>
          <span className="text-sm text-muted-foreground">
            {conDiferencias
              ? `Faltan ${textoRenglones(pendientes)} por llegar`
              : `${textoRenglones(traspaso.renglones.length)} · ${traspaso.pendiente_total} por recibir`}
            {" · enviado "}
            {desdeCuando(traspaso.creado_en)}
          </span>
        </span>
        <span className="flex shrink-0 items-center gap-1 text-base font-semibold text-primary">
          <span className="hidden sm:inline">Recibir</span>
          <ChevronRightIcon aria-hidden="true" className="size-6" />
        </span>
      </Link>
    </li>
  );
}
