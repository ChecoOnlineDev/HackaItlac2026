import type { ValorTablero } from "~/api/tablero";
import { ChartColumnIcon, MapPinIcon } from "lucide-react";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { TarjetaIndicador } from "./tarjetas-indicadores";

import { formatearMoneda as pesos } from "~/componentes/dominio/formato";

const APOYO = "Pesos mexicanos, sin IVA, al costo registrado";

/** Pestaña «Valor»: importes que calcula el servidor, por categoría y (para quien ve todos los almacenes) por almacén. */
export function PestanaValor({ valor, administrativo = false }: { valor: ValorTablero; administrativo?: boolean }) {
  const importe = (v: string) => `${pesos(v)}${administrativo ? " MXN" : ""}`;
  const sinNada = valor.unidades_total !== undefined ? valor.unidades_total === 0 : Number(valor.total) === 0 && valor.articulos_sin_costo === 0;
  if (sinNada) {
    return <EstadoVacio titulo="Todavía no hay valor que mostrar" descripcion="No hay existencias con costo registrado en este alcance." />;
  }
  const categorias = valor.por_categoria.slice(0, 7);
  const maximo = Math.max(...categorias.map((c) => Number(c.valor)), 1);

  return (
    <div className="valor-tablero flex flex-col gap-5">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <TarjetaIndicador titulo="Valor total del inventario" valor={importe(valor.total)} detalle={valor.unidades_total !== undefined ? `${valor.unidades_total} unidades · ${APOYO}` : APOYO} />
        <TarjetaIndicador titulo="Valor en almacén" valor={importe(valor.en_almacen)} detalle={valor.unidades_en_almacen !== undefined ? `${valor.unidades_en_almacen} unidades · ${APOYO}` : APOYO} />
        <TarjetaIndicador titulo="Valor en resguardo de trabajadores" valor={importe(valor.en_resguardo)} detalle={valor.unidades_en_resguardo !== undefined ? `${valor.unidades_en_resguardo} unidades · ${APOYO}` : APOYO} />
        {valor.en_transito !== null ? <TarjetaIndicador titulo="Valor en tránsito" valor={importe(valor.en_transito)} detalle={administrativo ? undefined : APOYO} /> : null}
      </div>
      {administrativo ? <p className="text-xs leading-relaxed text-muted-foreground">Importes expresados en pesos mexicanos (MXN), sin IVA y al costo registrado.</p> : null}

      {valor.articulos_sin_costo > 0 ? (
        <div className="sm:max-w-sm">
          <TarjetaIndicador
            titulo="Artículos sin costo"
            valor={valor.articulos_sin_costo}
            detalle="El valor total es parcial"
            ruta="/catalogo/articulos?sin_costo=true"
          />
        </div>
      ) : null}

      {categorias.length ? (
        <Card size="sm" className="bloque-categorias">
          <CardHeader>
            <CardTitle className="titulo-bloque text-base text-marino">{administrativo ? <ChartColumnIcon aria-hidden="true" size={20} /> : null}Por categoría</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="flex flex-col gap-3">
              {categorias.map((c) => (
                <li key={c.categoria} className="flex flex-col gap-1">
                  <div className={administrativo ? "flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 text-sm" : "flex items-baseline justify-between gap-3 text-sm"}>
                    <span className={administrativo ? "min-w-0 break-words" : "min-w-0 truncate"}>{c.categoria}</span>
                    <span className="shrink-0 font-semibold tabular-nums">{importe(c.valor)}{c.unidades !== undefined ? <span className="ml-2 text-xs font-normal">· {c.unidades} unidades</span> : null}</span>
                  </div>
                  <div className="h-2 rounded-full bg-muted" aria-hidden="true">
                    <div className="h-2 rounded-full bg-marino" style={{ width: `${Math.max(2, (Number(c.valor) / maximo) * 100)}%` }} />
                  </div>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}

      {valor.por_almacen.length ? (
        <Card size="sm" className="bloque-almacenes">
          <CardHeader>
            <CardTitle className="titulo-bloque text-base text-marino">{administrativo ? <MapPinIcon aria-hidden="true" size={20} /> : null}Por almacén</CardTitle>
          </CardHeader>
          <CardContent>
            {administrativo ? <p className="nota-moneda">Importes en MXN</p> : null}
            {administrativo ? (
              <dl className="almacenes-movil">
                {valor.por_almacen.map((a) => (
                  <div key={a.almacen_id} className="almacen-movil">
                    <dt>{a.nombre}</dt>
                    <dd>
                      <dl>
                        <div><dt>En almacén</dt><dd>{pesos(a.en_almacen)}{a.unidades_en_almacen !== undefined ? ` · ${a.unidades_en_almacen} unidades` : ""}</dd></div>
                        <div><dt>En resguardo</dt><dd>{pesos(a.en_resguardo)}{a.unidades_en_resguardo !== undefined ? ` · ${a.unidades_en_resguardo} unidades` : ""}</dd></div>
                        <div><dt>Total</dt><dd>{pesos(a.total)}{a.unidades_total !== undefined ? ` · ${a.unidades_total} unidades` : ""}</dd></div>
                      </dl>
                    </dd>
                  </div>
                ))}
              </dl>
            ) : null}
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">Almacén</TableHead>
                  <TableHead scope="col" className="text-right">En almacén</TableHead>
                  <TableHead scope="col" className="text-right">En resguardo</TableHead>
                  <TableHead scope="col" className="text-right">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {valor.por_almacen.map((a) => (
                  <TableRow key={a.almacen_id}>
                    <TableHead scope="row" className="whitespace-normal">{a.nombre}</TableHead>
                    <TableCell className="text-right tabular-nums">{pesos(a.en_almacen)}{a.unidades_en_almacen !== undefined ? <p className="text-xs font-normal">{a.unidades_en_almacen} unidades</p> : null}</TableCell>
                    <TableCell className="text-right tabular-nums">{pesos(a.en_resguardo)}{a.unidades_en_resguardo !== undefined ? <p className="text-xs font-normal">{a.unidades_en_resguardo} unidades</p> : null}</TableCell>
                    <TableCell className="text-right font-semibold tabular-nums">{pesos(a.total)}{a.unidades_total !== undefined ? <p className="text-xs font-normal">{a.unidades_total} unidades</p> : null}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
