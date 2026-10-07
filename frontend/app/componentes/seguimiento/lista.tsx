import { cn } from "cn";
import { Link, useNavigate } from "react-router";

import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { formatearFecha, formatearFechaHora } from "~/componentes/dominio/fechas";
import { instanteUtc } from "~/componentes/consulta/formato";
import { InsigniaSeriePendiente } from "~/componentes/dominio/insignia-serie-pendiente";
import { InsigniaDonde, InsigniaEstadoPieza } from "./insignias";
import type { PiezaSeguimiento } from "./tipos";

/** "hoy", "hace 1 día", "hace 12 días": desde cuándo está la pieza ahí, en palabras. */
export function textoHace(iso: string, ahora: Date = new Date()): string {
  const dias = Math.floor((ahora.getTime() - new Date(instanteUtc(iso)).getTime()) / 86_400_000);
  if (dias <= 0) return "hoy";
  if (dias === 1) return "hace 1 día";
  return `hace ${dias} días`;
}

function textoInspeccion(p: PiezaSeguimiento): string | null {
  if (!p.inspeccion_vigente_hasta) return null;
  return p.inspeccion_vigente
    ? `Inspección hasta el ${formatearFecha(p.inspeccion_vigente_hasta)}`
    : `Venció el ${formatearFecha(p.inspeccion_vigente_hasta)}`;
}

interface PropiedadesLista {
  piezas: PiezaSeguimiento[];
  /** Puede abrir la ficha de la pieza (`catalogo.ver`). */
  puedeAbrir: boolean;
  /** Puede abrir el vale (`vales.ver`). */
  puedeVerVale: boolean;
}

function Folio({ pieza, puedeVerVale }: { pieza: PiezaSeguimiento; puedeVerVale: boolean }) {
  if (!pieza.vale) return <span className="text-muted-foreground">—</span>;
  if (!puedeVerVale) return <span className="font-medium">{pieza.vale.folio}</span>;
  return (
    <Link
      to={`/vales/${pieza.vale.id}`}
      onClick={(e) => e.stopPropagation()}
      className="inline-flex min-h-10 items-center font-medium text-primary underline underline-offset-2"
    >
      {pieza.vale.folio}
    </Link>
  );
}

function Desde({ pieza }: { pieza: PiezaSeguimiento }) {
  if (!pieza.desde) return <span className="text-muted-foreground">—</span>;
  const iso = instanteUtc(pieza.desde);
  return (
    <>
      <span>{formatearFecha(iso)}</span>
      <span className="block text-xs text-muted-foreground">
        {textoHace(pieza.desde)} · {formatearFechaHora(iso).slice(11)}
      </span>
    </>
  );
}

/** Computadora y tableta: tabla con la pieza, su artículo, su estado, dónde está, desde cuándo y el vale. */
export function TablaPiezas({ piezas, puedeAbrir, puedeVerVale }: PropiedadesLista) {
  const navegar = useNavigate();
  return (
    <div className="hidden md:block">
      <Table className="[&_td]:px-2 [&_th]:px-2 lg:[&_td]:px-3 lg:[&_th]:px-3">
        <TableCaption className="sr-only">Piezas y dónde está cada una</TableCaption>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead scope="col">Pieza y serie</TableHead>
            <TableHead scope="col">Artículo</TableHead>
            <TableHead scope="col">Estado</TableHead>
            <TableHead scope="col" className="whitespace-normal">Dónde está o quién la tiene</TableHead>
            <TableHead scope="col">Desde</TableHead>
            <TableHead scope="col">Vale</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {piezas.map((p) => {
            const inspeccion = textoInspeccion(p);
            return (
              <TableRow
                key={p.id}
                className={cn("align-top", puedeAbrir && "cursor-pointer")}
                onClick={puedeAbrir ? () => navegar(`/piezas/${p.id}`) : undefined}
              >
                <TableCell>
                  {puedeAbrir ? (
                    <Link
                      to={`/piezas/${p.id}`}
                      onClick={(e) => e.stopPropagation()}
                      className="inline-flex min-h-10 items-center font-semibold text-primary underline underline-offset-2"
                    >
                      {p.codigo}
                    </Link>
                  ) : (
                    <span className="font-semibold">{p.codigo}</span>
                  )}
                  {p.numero_serie ? (
                    <span className="block text-xs text-muted-foreground">{p.numero_serie}</span>
                  ) : (
                    <InsigniaSeriePendiente className="mt-1" />
                  )}
                </TableCell>
                <TableCell className="whitespace-normal">
                  <span className="font-medium">{p.articulo.nombre}</span>
                  <span className="block text-xs text-muted-foreground">
                    {[p.articulo.codigo, p.articulo.marca].filter(Boolean).join(" · ")}
                  </span>
                </TableCell>
                <TableCell className="whitespace-normal">
                  <InsigniaEstadoPieza pieza={p} />
                  {inspeccion ? (
                    <span className="mt-1 block text-xs text-muted-foreground">
                      {inspeccion}
                    </span>
                  ) : null}
                </TableCell>
                <TableCell className="max-w-44 whitespace-normal lg:max-w-64">
                  <InsigniaDonde donde={p.ubicacion} />
                  {p.ubicacion.trabajador ? (
                    <span className="mt-1 block text-xs text-muted-foreground">Número {p.ubicacion.trabajador.numero_empleado}</span>
                  ) : null}
                </TableCell>
                <TableCell className="whitespace-normal">
                  <Desde pieza={p} />
                </TableCell>
                <TableCell>
                  <Folio pieza={p} puedeVerVale={puedeVerVale} />
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

/** Celular: una tarjeta por pieza; toda la tarjeta abre su ficha. */
export function TarjetasPiezas({ piezas, puedeAbrir, puedeVerVale }: PropiedadesLista) {
  return (
    <ul className="flex flex-col gap-3 md:hidden">
      {piezas.map((p) => {
        const inspeccion = textoInspeccion(p);
        return (
          <li key={p.id} className="relative flex flex-col gap-2.5 rounded-2xl border bg-card p-4 shadow-xs">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-base leading-tight font-semibold">{p.articulo.nombre}</p>
                <p className="text-sm text-muted-foreground">
                  {puedeAbrir ? (
                    <Link
                      to={`/piezas/${p.id}`}
                      className="font-semibold text-primary underline underline-offset-2 after:absolute after:inset-0 after:content-['']"
                    >
                      {p.codigo}
                    </Link>
                  ) : (
                    <span className="font-semibold">{p.codigo}</span>
                  )}
                  {p.numero_serie ? ` · Serie ${p.numero_serie}` : null}
                </p>
                {p.numero_serie ? null : <InsigniaSeriePendiente className="mt-1" />}
              </div>
              <InsigniaEstadoPieza pieza={p} />
            </div>
            <div className="flex flex-col items-start gap-1">
              <InsigniaDonde donde={p.ubicacion} />
              {p.ubicacion.trabajador ? (
                <span className="text-xs text-muted-foreground">Número {p.ubicacion.trabajador.numero_empleado}</span>
              ) : null}
            </div>
            {inspeccion ? (
              <p className="text-xs text-muted-foreground">{inspeccion}</p>
            ) : null}
            <dl className="grid grid-cols-2 gap-3 border-t pt-2.5 text-sm">
              <div>
                <dt className="text-xs text-muted-foreground">Desde</dt>
                <dd>
                  <Desde pieza={p} />
                </dd>
              </div>
              <div className="relative z-10">
                <dt className="text-xs text-muted-foreground">Vale</dt>
                <dd>
                  <Folio pieza={p} puedeVerVale={puedeVerVale} />
                </dd>
              </div>
            </dl>
          </li>
        );
      })}
    </ul>
  );
}
