import { cn } from "cn";
import { XIcon } from "lucide-react";
import { Link, useNavigate } from "react-router";

import { formatearFechaHora } from "~/componentes/dominio/fechas";
import { Boton } from "~/componentes/ui/boton";
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { InsigniaEstadoCompra, InsigniaUrgencia } from "./insignias";
import { textoCantidad, type SolicitudCompra } from "./tipos";

interface PropiedadesLista {
  solicitudes: SolicitudCompra[];
  /** Muestra de qué almacén es cada una (solo quien ve varios almacenes). */
  conAlmacen: boolean;
  alCancelar: (solicitud: SolicitudCompra) => void;
}

const puedeCancelar = (s: SolicitudCompra) => s.acciones.includes("cancelar");
const queSePide = (s: SolicitudCompra) => s.articulo?.nombre ?? s.descripcion;

function Que({ solicitud: s }: { solicitud: SolicitudCompra }) {
  return (
    <>
      <span className="font-medium">{queSePide(s)}</span>
      <span className="block text-xs text-muted-foreground">
        {s.articulo ? s.articulo.codigo : "No está en el catálogo"}
        {` · Para ${s.motivo}`}
      </span>
    </>
  );
}

/** Lo que Compras dijo al rechazar o al avanzar: quien pidió lo lee aquí (SC-05). */
function NotaDeCompras({ solicitud: s, className }: { solicitud: SolicitudCompra; className?: string }) {
  if (!s.nota_compras) return null;
  return (
    <p className={cn("text-xs text-muted-foreground", className)}>
      <span className="font-semibold text-foreground">Compras: </span>
      {s.nota_compras}
    </p>
  );
}

function BotonCancelar({ solicitud, alCancelar, className }: { solicitud: SolicitudCompra; alCancelar: (s: SolicitudCompra) => void; className?: string }) {
  if (!puedeCancelar(solicitud)) return null;
  return (
    <Boton
      variante="contorno"
      className={className}
      aria-label={`Cancelar la solicitud ${solicitud.folio}`}
      onClick={(e) => {
        e.stopPropagation();
        alCancelar(solicitud);
      }}
    >
      <XIcon aria-hidden="true" />
      Cancelar
    </Boton>
  );
}

/** Tableta y computadora: una tabla; toda la fila abre el detalle y el folio es un enlace. */
export function TablaSolicitudes({ solicitudes, conAlmacen, alCancelar }: PropiedadesLista) {
  const navegar = useNavigate();
  return (
    <div className="hidden md:block">
      <Table className="[&_td]:px-2 [&_th]:px-2 lg:[&_td]:px-3 lg:[&_th]:px-3">
        <TableCaption className="sr-only">Solicitudes de compra</TableCaption>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead scope="col">Folio</TableHead>
            <TableHead scope="col">Qué se pidió</TableHead>
            <TableHead scope="col" className="text-right">
              Cantidad
            </TableHead>
            <TableHead scope="col">Urgencia</TableHead>
            <TableHead scope="col">Estado</TableHead>
            <TableHead scope="col">Quién la pidió</TableHead>
            <TableHead scope="col">Fecha</TableHead>
            <TableHead scope="col">
              <span className="sr-only">Acciones</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {solicitudes.map((s) => (
            <TableRow key={s.id} className="cursor-pointer align-top" onClick={() => navegar(`/compras/${s.id}`)}>
              <TableCell>
                <Link
                  to={`/compras/${s.id}`}
                  onClick={(e) => e.stopPropagation()}
                  className="inline-flex min-h-10 items-center font-semibold text-primary underline underline-offset-2"
                >
                  {s.folio}
                </Link>
              </TableCell>
              <TableCell className="max-w-64 whitespace-normal">
                <Que solicitud={s} />
              </TableCell>
              <TableCell className="text-right font-semibold">{s.cantidad}</TableCell>
              <TableCell>
                <InsigniaUrgencia urgencia={s.urgencia} />
              </TableCell>
              <TableCell className="whitespace-normal">
                <InsigniaEstadoCompra estado={s.estado} />
                <NotaDeCompras solicitud={s} className="mt-1 max-w-48" />
              </TableCell>
              <TableCell className="whitespace-normal">
                <span>{s.solicitante.nombre}</span>
                {conAlmacen ? <span className="block text-xs text-muted-foreground">{s.almacen.nombre}</span> : null}
              </TableCell>
              <TableCell className="whitespace-normal">{formatearFechaHora(s.creada_en)}</TableCell>
              <TableCell>
                <BotonCancelar solicitud={s} alCancelar={alCancelar} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

/** Celular: una tarjeta por solicitud; toda la tarjeta abre el detalle, "Cancelar" queda aparte. */
export function TarjetasSolicitudes({ solicitudes, conAlmacen, alCancelar }: PropiedadesLista) {
  return (
    <ul className="flex flex-col gap-3 md:hidden">
      {solicitudes.map((s) => (
        <li key={s.id} className="relative flex flex-col gap-2.5 rounded-2xl border bg-card p-4 shadow-xs">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-base leading-tight font-semibold break-words">{queSePide(s)}</p>
              <p className="text-sm text-muted-foreground">
                <Link
                  to={`/compras/${s.id}`}
                  className="font-semibold text-primary underline underline-offset-2 after:absolute after:inset-0 after:content-['']"
                >
                  {s.folio}
                </Link>
                {` · ${textoCantidad(s.cantidad)}`}
              </p>
            </div>
            <InsigniaUrgencia urgencia={s.urgencia} />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <InsigniaEstadoCompra estado={s.estado} />
            {s.articulo ? null : <span className="text-xs text-muted-foreground">No está en el catálogo</span>}
          </div>
          <p className="text-sm break-words">
            <span className="text-muted-foreground">Para: </span>
            {s.motivo}
          </p>
          <NotaDeCompras solicitud={s} className="text-sm" />
          <p className="text-xs text-muted-foreground">
            {s.solicitante.nombre}
            {conAlmacen ? ` · ${s.almacen.nombre}` : ""} · {formatearFechaHora(s.creada_en)}
          </p>
          {puedeCancelar(s) ? (
            <div className="relative z-10">
              <BotonCancelar solicitud={s} alCancelar={alCancelar} />
            </div>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
