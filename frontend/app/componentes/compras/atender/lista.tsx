import { cn } from "cn";
import { ChevronRightIcon } from "lucide-react";
import { Link, useNavigate } from "react-router";

import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { instanteUtc } from "~/componentes/consulta/formato";
import { formatearFechaHora } from "~/componentes/dominio/fechas";
import { InsigniaEstadoCompra, InsigniaUrgencia } from "~/componentes/compras/insignias";
import { BotonesAccion } from "./botones-accion";
import type { AccionSolicitud, SolicitudCompra } from "./tipos";

interface PropiedadesLista {
  solicitudes: SolicitudCompra[];
  alAccion: (solicitud: SolicitudCompra, accion: AccionSolicitud) => void;
}

/** Una urgente que Compras todavía no atiende: es lo primero que debe verse. */
export function esUrgentePendiente(s: Pick<SolicitudCompra, "estado" | "urgencia">): boolean {
  return s.estado === "PENDIENTE" && s.urgencia === "URGENTE";
}

function QuePidio({ s }: { s: SolicitudCompra }) {
  return (
    <>
      <span className="block font-semibold wrap-break-word">{s.descripcion}</span>
      <span className="block text-xs text-muted-foreground wrap-break-word">
        {s.articulo ? `Catálogo: ${s.articulo.codigo}` : "Fuera del catálogo"} · {s.motivo}
      </span>
    </>
  );
}

function Fecha({ iso }: { iso: string }) {
  return <span className="tabular-nums">{formatearFechaHora(instanteUtc(iso))}</span>;
}

/** Computadora y tableta: tabla con una solicitud por renglón; tocarla abre su detalle. */
export function TablaSolicitudes({ solicitudes, alAccion }: PropiedadesLista) {
  const navegar = useNavigate();
  return (
    <div className="hidden w-0 min-w-full md:block">
      <Table>
        <TableCaption className="sr-only">Solicitudes de compra</TableCaption>
        <TableHeader>
          <TableRow>
            <TableHead scope="col">Folio</TableHead>
            <TableHead scope="col">Qué se pidió</TableHead>
            <TableHead scope="col" className="text-right">
              Cant.
            </TableHead>
            <TableHead scope="col">Almacén</TableHead>
            <TableHead scope="col" className="whitespace-normal">
              Urgencia y estado
            </TableHead>
            <TableHead scope="col" className="hidden xl:table-cell">
              Solicitante
            </TableHead>
            <TableHead scope="col" className="hidden 2xl:table-cell">
              Fecha
            </TableHead>
            <TableHead scope="col">
              <span className="sr-only">Acción</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {solicitudes.map((s) => (
            <TableRow
              key={s.id}
              onClick={() => void navegar(`/compras/${s.id}`)}
              className={cn("cursor-pointer align-top", esUrgentePendiente(s) && "bg-destructive/5 hover:bg-destructive/10")}
            >
              <TableHead
                scope="row"
                className={cn("whitespace-nowrap", esUrgentePendiente(s) && "shadow-[inset_4px_0_0_0_var(--color-destructive)]")}
              >
                <Link
                  to={`/compras/${s.id}`}
                  onClick={(e) => e.stopPropagation()}
                  className="inline-flex min-h-10 items-center font-semibold text-primary underline underline-offset-4"
                >
                  {s.folio}
                </Link>
              </TableHead>
              <TableCell className="max-w-56 min-w-36 whitespace-normal">
                <QuePidio s={s} />
              </TableCell>
              <TableCell className="text-right font-semibold tabular-nums">{s.cantidad}</TableCell>
              <TableCell>{s.almacen.nombre}</TableCell>
              <TableCell>
                <span className="flex flex-col items-start gap-1.5">
                  <InsigniaUrgencia urgencia={s.urgencia} />
                  <InsigniaEstadoCompra estado={s.estado} />
                </span>
              </TableCell>
              <TableCell className="hidden whitespace-normal xl:table-cell">{s.solicitante.nombre}</TableCell>
              <TableCell className="hidden 2xl:table-cell">
                <Fecha iso={s.creada_en} />
              </TableCell>
              <TableCell className="text-right">
                <BotonesAccion acciones={s.acciones} alElegir={(a) => alAccion(s, a)} soloPrincipal compacto />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

/** Celular: una tarjeta por solicitud; las urgentes pendientes llevan franja y fondo rojos suaves. */
export function TarjetasSolicitudes({ solicitudes, alAccion }: PropiedadesLista) {
  return (
    <ul className="flex flex-col gap-3 md:hidden" aria-label="Solicitudes de compra">
      {solicitudes.map((s) => {
        const urgente = esUrgentePendiente(s);
        const hayAccion = s.acciones.some((a) => a === "tomar" || a === "comprar" || a === "ingresar");
        return (
          <li
            key={s.id}
            className={cn(
              "flex flex-col overflow-hidden rounded-2xl border bg-card shadow-xs",
              urgente && "border-destructive/40 border-l-4 border-l-destructive bg-destructive/5",
            )}
          >
            <Link to={`/compras/${s.id}`} className="flex min-h-12 flex-col gap-2 p-4 active:bg-accent/40">
              <span className="flex items-start justify-between gap-2">
                <span className="text-base font-semibold text-primary">{s.folio}</span>
                <ChevronRightIcon aria-hidden="true" className="size-5 shrink-0 text-muted-foreground" />
              </span>
              <span className="flex flex-wrap items-center gap-2">
                <InsigniaUrgencia urgencia={s.urgencia} />
                <InsigniaEstadoCompra estado={s.estado} />
              </span>
              <span>
                <QuePidio s={s} />
              </span>
              <span className="text-sm">
                <span className="font-semibold tabular-nums">{s.cantidad}</span>
                <span className="text-muted-foreground">
                  {" "}
                  · {s.almacen.nombre} · {s.solicitante.nombre}
                </span>
              </span>
              <span className="text-xs text-muted-foreground">
                <Fecha iso={s.creada_en} />
              </span>
            </Link>
            {hayAccion ? (
              <div className="border-t px-4 py-3">
                <BotonesAccion
                  acciones={s.acciones}
                  alElegir={(a) => alAccion(s, a)}
                  soloPrincipal
                  className="flex justify-end"
                />
              </div>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}
