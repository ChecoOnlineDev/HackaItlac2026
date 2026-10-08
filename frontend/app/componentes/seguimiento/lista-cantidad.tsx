import { Link } from "react-router";

import { instanteUtc } from "~/componentes/consulta/formato";
import { formatearFecha, formatearFechaHora } from "~/componentes/dominio/fechas";
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { textoHace } from "./lista";
import type { CantidadSeguimiento } from "./tipos";

interface PropiedadesCantidad {
  renglones: CantidadSeguimiento[];
  /** Puede abrir la ficha del trabajador (`trabajadores.ver`). */
  puedeVerTrabajador: boolean;
  /** Puede abrir la ficha del artículo (`catalogo.ver`). */
  puedeVerArticulo: boolean;
  /** Puede abrir el vale (`vales.ver`). */
  puedeVerVale: boolean;
}

function Trabajador({ r, puede }: { r: CantidadSeguimiento; puede: boolean }) {
  return (
    <>
      {puede ? (
        <Link to={`/trabajadores/${r.trabajador.id}`} className="inline-flex min-h-10 items-center font-semibold text-primary underline underline-offset-2">
          {r.trabajador.nombre}
        </Link>
      ) : (
        <span className="font-semibold">{r.trabajador.nombre}</span>
      )}
      <span className="block text-xs text-muted-foreground">Número {r.trabajador.numero_empleado}</span>
    </>
  );
}

function Articulo({ r, puede }: { r: CantidadSeguimiento; puede: boolean }) {
  return (
    <>
      {puede ? (
        <Link to={`/articulos/${r.articulo.id}`} className="inline-flex min-h-10 items-center font-medium text-primary underline underline-offset-2">
          {r.articulo.nombre}
        </Link>
      ) : (
        <span className="font-medium">{r.articulo.nombre}</span>
      )}
      <span className="block text-xs text-muted-foreground">{[r.articulo.codigo, r.articulo.marca].filter(Boolean).join(" · ")}</span>
    </>
  );
}

function Desde({ r }: { r: CantidadSeguimiento }) {
  if (!r.desde) return <span className="text-muted-foreground">—</span>;
  const iso = instanteUtc(r.desde);
  return (
    <>
      <span>{formatearFecha(iso)}</span>
      <span className="block text-xs text-muted-foreground">
        {textoHace(r.desde)} · {formatearFechaHora(iso).slice(11)}
      </span>
    </>
  );
}

function Folio({ r, puede }: { r: CantidadSeguimiento; puede: boolean }) {
  if (!r.vale) return <span className="text-muted-foreground">—</span>;
  if (!puede) return <span className="font-medium">{r.vale.folio}</span>;
  return (
    <Link to={`/vales/${r.vale.id}`} className="inline-flex min-h-10 items-center font-medium text-primary underline underline-offset-2">
      {r.vale.folio}
    </Link>
  );
}

function Cantidad({ r }: { r: CantidadSeguimiento }) {
  return (
    <span className="tabular-nums">
      <span className="text-lg font-semibold">{r.cantidad}</span> <span className="text-xs text-muted-foreground">{r.unidad}</span>
    </span>
  );
}

/** Computadora y tableta: tabla con trabajador, artículo, cantidad, desde cuándo y el folio de la entrega. */
export function TablaCantidad({ renglones, puedeVerTrabajador, puedeVerArticulo, puedeVerVale }: PropiedadesCantidad) {
  return (
    <div className="hidden md:block">
      <Table className="[&_td]:px-2 [&_th]:px-2 lg:[&_td]:px-3 lg:[&_th]:px-3">
        <TableCaption className="sr-only">Lo que tiene cada trabajador por cantidad</TableCaption>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead scope="col">Trabajador</TableHead>
            <TableHead scope="col">Artículo</TableHead>
            <TableHead scope="col">Cantidad</TableHead>
            <TableHead scope="col">Desde</TableHead>
            <TableHead scope="col">Vale</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {renglones.map((r) => (
            <TableRow key={`${r.trabajador.id}-${r.articulo.id}`} className="align-top">
              <TableCell className="whitespace-normal">
                <Trabajador r={r} puede={puedeVerTrabajador} />
              </TableCell>
              <TableCell className="whitespace-normal">
                <Articulo r={r} puede={puedeVerArticulo} />
              </TableCell>
              <TableCell>
                <Cantidad r={r} />
              </TableCell>
              <TableCell className="whitespace-normal">
                <Desde r={r} />
              </TableCell>
              <TableCell>
                <Folio r={r} puede={puedeVerVale} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

/** Celular: una tarjeta por trabajador y artículo. */
export function TarjetasCantidad({ renglones, puedeVerTrabajador, puedeVerArticulo, puedeVerVale }: PropiedadesCantidad) {
  return (
    <ul className="flex flex-col gap-3 md:hidden">
      {renglones.map((r) => (
        <li key={`${r.trabajador.id}-${r.articulo.id}`} className="flex flex-col gap-2.5 rounded-2xl border bg-card p-4 shadow-xs">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <Trabajador r={r} puede={puedeVerTrabajador} />
            </div>
            <Cantidad r={r} />
          </div>
          <div className="min-w-0">
            <Articulo r={r} puede={puedeVerArticulo} />
          </div>
          <dl className="grid grid-cols-2 gap-3 border-t pt-2.5 text-sm">
            <div>
              <dt className="text-xs text-muted-foreground">Desde</dt>
              <dd>
                <Desde r={r} />
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Vale</dt>
              <dd>
                <Folio r={r} puede={puedeVerVale} />
              </dd>
            </div>
          </dl>
        </li>
      ))}
    </ul>
  );
}
