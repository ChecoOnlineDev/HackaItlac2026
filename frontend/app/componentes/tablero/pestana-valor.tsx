import type { ValorTablero } from "~/api/tablero";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { TarjetaIndicador } from "./tarjetas-indicadores";

const moneda = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });
const pesos = (importe: string) => moneda.format(Number(importe));

const APOYO = "Pesos mexicanos, sin IVA, al costo registrado";

/** Pestaña «Valor»: importes que calcula el servidor, por categoría y (para quien ve todos los almacenes) por almacén. */
export function PestanaValor({ valor }: { valor: ValorTablero }) {
  const sinNada = Number(valor.total) === 0 && valor.articulos_sin_costo === 0;
  if (sinNada) {
    return <EstadoVacio titulo="Todavía no hay valor que mostrar" descripcion="No hay existencias con costo registrado en este alcance." />;
  }
  const categorias = valor.por_categoria.slice(0, 6);
  const maximo = Math.max(...categorias.map((c) => Number(c.valor)), 1);

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <TarjetaIndicador titulo="Valor total del inventario" valor={pesos(valor.total)} detalle={APOYO} />
        <TarjetaIndicador titulo="Valor en almacén" valor={pesos(valor.en_almacen)} detalle={APOYO} />
        <TarjetaIndicador titulo="Valor en resguardo de trabajadores" valor={pesos(valor.en_resguardo)} detalle={APOYO} />
        {valor.en_transito !== null ? <TarjetaIndicador titulo="Valor en tránsito" valor={pesos(valor.en_transito)} detalle={APOYO} /> : null}
      </div>

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
        <Card size="sm">
          <CardHeader>
            <CardTitle className="text-base text-marino">Por categoría</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="flex flex-col gap-3">
              {categorias.map((c) => (
                <li key={c.categoria} className="flex flex-col gap-1">
                  <div className="flex items-baseline justify-between gap-3 text-sm">
                    <span className="min-w-0 truncate">{c.categoria}</span>
                    <span className="shrink-0 font-semibold tabular-nums">{pesos(c.valor)}</span>
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

      {valor.alcance.todos && valor.por_almacen.length ? (
        <Card size="sm">
          <CardHeader>
            <CardTitle className="text-base text-marino">Por almacén</CardTitle>
          </CardHeader>
          <CardContent>
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
                    <TableCell className="text-right tabular-nums">{pesos(a.en_almacen)}</TableCell>
                    <TableCell className="text-right tabular-nums">{pesos(a.en_resguardo)}</TableCell>
                    <TableCell className="text-right font-semibold tabular-nums">{pesos(a.total)}</TableCell>
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
