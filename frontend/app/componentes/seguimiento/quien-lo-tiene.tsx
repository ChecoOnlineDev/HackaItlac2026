import { useState } from "react";
import { Link } from "react-router";

import { instanteUtc } from "~/componentes/consulta/formato";
import type { Poseedor } from "~/componentes/consulta/tipos";
import { formatearFecha } from "~/componentes/dominio/fechas";
import { Boton } from "~/componentes/ui/boton";
import { Hoja } from "~/componentes/ui/hoja";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";

interface Permisos {
  /** Puede abrir la ficha del trabajador (`trabajadores.ver`). */
  puedeVerTrabajador: boolean;
  /** Puede abrir el vale (`vales.ver`). */
  puedeVerVale: boolean;
  /** Puede abrir la ficha de una pieza (`catalogo.ver`). */
  puedeVerPieza: boolean;
}

function Fecha({ iso }: { iso: string | null | undefined }) {
  return iso ? <span>{formatearFecha(instanteUtc(iso))}</span> : <span className="text-muted-foreground">—</span>;
}

function Folio({ p, puede }: { p: Poseedor; puede: boolean }) {
  if (!p.folio) return <span className="text-muted-foreground">—</span>;
  if (!puede || !p.vale_id) return <span className="font-medium">{p.folio}</span>;
  return (
    <Link to={`/vales/${p.vale_id}`} className="inline-flex min-h-10 items-center font-medium text-primary underline underline-offset-2">
      {p.folio}
    </Link>
  );
}

/** SG-02: lo que tiene un trabajador de este artículo, con su fecha, su vale y, por pieza, cada código y serie. */
function HojaPoseedor({ poseedor, permisos, alCambiar }: { poseedor: Poseedor | null; permisos: Permisos; alCambiar: (abierta: boolean) => void }) {
  return (
    <Hoja abierta={poseedor !== null} alCambiar={alCambiar} titulo={poseedor?.nombre ?? "Detalle"} descripcion={poseedor ? `Número ${poseedor.numero_empleado}` : undefined}>
      {poseedor ? (
        <div className="flex flex-col gap-4">
          <dl className="grid grid-cols-2 gap-3 text-base">
            <div>
              <dt className="text-sm text-muted-foreground">En resguardo</dt>
              <dd className="font-semibold tabular-nums">{poseedor.cantidad}</dd>
            </div>
            <div>
              <dt className="text-sm text-muted-foreground">Desde</dt>
              <dd>
                <Fecha iso={poseedor.desde} />
              </dd>
            </div>
            <div>
              <dt className="text-sm text-muted-foreground">Vale de entrega</dt>
              <dd>
                <Folio p={poseedor} puede={permisos.puedeVerVale} />
              </dd>
            </div>
          </dl>
          {poseedor.piezas && poseedor.piezas.length > 0 ? (
            <div className="flex flex-col gap-2">
              <p className="text-sm font-semibold">Piezas que tiene</p>
              <ul className="flex flex-col divide-y rounded-2xl border">
                {poseedor.piezas.map((z) => (
                  <li key={z.id} className="flex flex-col px-4 py-2.5">
                    {permisos.puedeVerPieza ? (
                      <Link to={`/piezas/${z.id}`} className="inline-flex min-h-10 items-center font-semibold text-primary underline underline-offset-2">
                        {z.codigo}
                      </Link>
                    ) : (
                      <span className="font-semibold">{z.codigo}</span>
                    )}
                    <span className="text-sm text-muted-foreground">{z.numero_serie ? `Serie ${z.numero_serie}` : "Serie pendiente"}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {permisos.puedeVerTrabajador ? (
            <Boton variante="contorno" nativeButton={false} render={<Link to={`/trabajadores/${poseedor.trabajador_id}`} />}>
              Ver al trabajador
            </Boton>
          ) : null}
        </div>
      ) : null}
    </Hoja>
  );
}

/**
 * SG-02: «Quién lo tiene» como tabla con trabajador, cantidad, fecha y folio, y un botón «Ver detalle».
 * En un artículo por pieza muestra además el código y la serie de cada pieza.
 */
export function TablaQuienLoTiene({ poseedores, ...permisos }: { poseedores: Poseedor[] } & Permisos) {
  const [abierto, setAbierto] = useState<Poseedor | null>(null);
  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead scope="col" className="px-3 py-2 font-semibold">Trabajador</TableHead>
            <TableHead scope="col" className="px-3 py-2 text-right font-semibold">Cantidad</TableHead>
            <TableHead scope="col" className="hidden px-3 py-2 font-semibold sm:table-cell">Desde</TableHead>
            <TableHead scope="col" className="hidden px-3 py-2 font-semibold sm:table-cell">Vale</TableHead>
            <TableHead scope="col" className="px-3 py-2"><span className="sr-only">Detalle</span></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody className="divide-y">
          {poseedores.map((t) => (
            <TableRow key={t.trabajador_id} className="align-top">
              <TableCell className="px-3 py-3 whitespace-normal">
                {permisos.puedeVerTrabajador ? (
                  <Link to={`/trabajadores/${t.trabajador_id}`} className="inline-flex min-h-10 items-center text-base font-semibold text-primary underline underline-offset-2">
                    {t.nombre}
                  </Link>
                ) : (
                  <span className="text-base font-semibold">{t.nombre}</span>
                )}
                <span className="block text-sm text-muted-foreground">Número {t.numero_empleado}</span>
                {t.piezas && t.piezas.length > 0 ? (
                  <ul className="mt-1 flex flex-col gap-0.5 text-sm">
                    {t.piezas.map((z) => (
                      <li key={z.id}>
                        {permisos.puedeVerPieza ? (
                          <Link to={`/piezas/${z.id}`} className="font-medium text-primary underline underline-offset-2">
                            {z.codigo}
                          </Link>
                        ) : (
                          <span className="font-medium">{z.codigo}</span>
                        )}
                        <span className="text-muted-foreground">{z.numero_serie ? ` · Serie ${z.numero_serie}` : " · Serie pendiente"}</span>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </TableCell>
              <TableCell className="px-3 py-3 text-right text-lg font-semibold tabular-nums">{t.cantidad}</TableCell>
              <TableCell className="hidden px-3 py-3 sm:table-cell">
                <Fecha iso={t.desde} />
              </TableCell>
              <TableCell className="hidden px-3 py-3 sm:table-cell">
                <Folio p={t} puede={permisos.puedeVerVale} />
              </TableCell>
              <TableCell className="px-3 py-3 text-right">
                <Boton variante="contorno" className="h-11" onClick={() => setAbierto(t)}>
                  Ver detalle
                </Boton>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <HojaPoseedor poseedor={abierto} permisos={permisos} alCambiar={(a) => (a ? null : setAbierto(null))} />
    </>
  );
}
