import { cn } from "cn";
import { Link } from "react-router";

import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { apiGet, descargarCsv } from "~/api/cliente";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { formatearFechaHora } from "~/componentes/dominio/fechas";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import {
  chipPeriodo,
  FiltroLista,
  FiltroPeriodo,
  NotaAlcance,
  textoDeOpcion,
  useAlcance,
} from "~/componentes/reportes/filtros-comunes";
import { useAlmacenesFiltro, useEtiqueta, useUsuariosFiltro } from "~/componentes/reportes/listas";
import { MarcoReporte } from "~/componentes/reportes/marco-reporte";
import { SelectorBusqueda } from "~/componentes/reportes/selector-busqueda";
import {
  comoUtc,
  TAMANO_REPORTE,
  TIPOS_DE_MOVIMIENTO,
  type FiltroActivo,
  type MovimientoReporte,
  type PaginaReporte,
} from "~/componentes/reportes/tipos";
import { useFiltrosUrl } from "~/componentes/reportes/usar-filtros";
import { Insignia } from "~/componentes/ui/insignia";

export const handle: ManejadorRuta = { permiso: "reportes.movimientos" };

const CLAVES = ["desde", "hasta", "almacen_id", "tipo", "trabajador_id", "articulo_id", "usuario_id"] as const;

function Saldo({ m, enLinea = false }: { m: MovimientoReporte; enLinea?: boolean }) {
  if (m.saldo_origen === null && m.saldo_destino === null) return <span className="text-muted-foreground">—</span>;
  return (
    <span className={cn("flex text-sm whitespace-nowrap tabular-nums", enLinea ? "flex-row flex-wrap gap-x-3" : "flex-col")}>
      {m.saldo_origen !== null ? <span>Origen: {m.saldo_origen}</span> : null}
      {m.saldo_destino !== null ? <span>Destino: {m.saldo_destino}</span> : null}
    </span>
  );
}

function Articulo({ m }: { m: MovimientoReporte }) {
  return (
    <>
      <span className="font-semibold">{m.articulo}</span>
      <span className="block text-sm text-muted-foreground">
        {m.codigo_articulo}
        {m.pieza ? ` · Pieza ${m.pieza}` : ""}
      </span>
    </>
  );
}

export default function ReporteMovimientos() {
  const { valores, pagina, cambiar, cambiarPagina, quitarTodos } = useFiltrosUrl(CLAVES);
  const alcance = useAlcance();
  const almacenes = useAlmacenesFiltro();
  const usuarios = useUsuariosFiltro();
  const etiquetaTrabajador = useEtiqueta("trabajador", valores.trabajador_id);
  const etiquetaArticulo = useEtiqueta("articulo", valores.articulo_id);

  // Quien no ve todos los almacenes no manda el filtro: el servidor ya lo limita al suyo.
  const parametros = {
    desde: valores.desde,
    hasta: valores.hasta,
    almacen_id: alcance.todos ? valores.almacen_id : "",
    tipo: valores.tipo,
    trabajador_id: valores.trabajador_id,
    articulo_id: valores.articulo_id,
    usuario_id: valores.usuario_id,
  };
  const claveConsulta = JSON.stringify([parametros, pagina]);
  const consulta = useConsulta(
    (signal) =>
      apiGet<PaginaReporte<MovimientoReporte>>(
        "/reportes/movimientos",
        { ...parametros, pagina, tamano: TAMANO_REPORTE },
        signal,
      ),
    claveConsulta,
  );

  const activos: FiltroActivo[] = [];
  const periodo = chipPeriodo(valores.desde, valores.hasta);
  if (periodo) activos.push(periodo);
  if (alcance.todos && valores.almacen_id) {
    activos.push({ clave: "almacen_id", texto: `Almacén: ${textoDeOpcion(almacenes.opciones, valores.almacen_id) ?? "elegido"}` });
  }
  if (valores.tipo) {
    activos.push({ clave: "tipo", texto: `Tipo: ${textoDeOpcion(TIPOS_DE_MOVIMIENTO, valores.tipo) ?? valores.tipo}` });
  }
  if (valores.trabajador_id) activos.push({ clave: "trabajador_id", texto: `Trabajador: ${etiquetaTrabajador ?? "elegido"}` });
  if (valores.articulo_id) activos.push({ clave: "articulo_id", texto: `Artículo: ${etiquetaArticulo ?? "elegido"}` });
  if (valores.usuario_id) {
    activos.push({ clave: "usuario_id", texto: `Quién lo hizo: ${textoDeOpcion(usuarios.opciones, valores.usuario_id) ?? "elegido"}` });
  }

  function quitar(clave: string) {
    if (clave === "periodo") cambiar({ desde: null, hasta: null });
    else cambiar({ [clave]: null } as Record<(typeof CLAVES)[number], null>);
  }

  const filtros = (
    <>
      <FiltroPeriodo desde={valores.desde} hasta={valores.hasta} alCambiar={(r) => cambiar({ desde: r.desde, hasta: r.hasta })} />
      {alcance.todos && almacenes.disponible ? (
        <FiltroLista
          etiqueta="Almacén"
          vacio="Todos los almacenes"
          valor={valores.almacen_id}
          opciones={almacenes.opciones}
          alCambiar={(v) => cambiar({ almacen_id: v })}
        />
      ) : null}
      <FiltroLista
        etiqueta="Tipo de movimiento"
        vacio="Todos los tipos"
        valor={valores.tipo}
        opciones={TIPOS_DE_MOVIMIENTO}
        alCambiar={(v) => cambiar({ tipo: v })}
      />
      <FiltroLista
        etiqueta="Quién lo hizo"
        vacio="Todos los usuarios"
        valor={valores.usuario_id}
        opciones={usuarios.opciones}
        alCambiar={(v) => cambiar({ usuario_id: v })}
      />
      <SelectorBusqueda tipo="trabajador" valor={valores.trabajador_id} alCambiar={(id) => cambiar({ trabajador_id: id })} />
      <SelectorBusqueda tipo="articulo" valor={valores.articulo_id} alCambiar={(id) => cambiar({ articulo_id: id })} />
    </>
  );

  return (
    <Pantalla titulo="Reporte de movimientos" descripcion="Qué se movió, cuándo y quién lo hizo.">
      <MarcoReporte<MovimientoReporte>
        unidad="movimientos"
        filtros={filtros}
        activos={activos}
        alQuitar={quitar}
        alQuitarTodos={quitarTodos}
        consulta={consulta}
        pagina={pagina}
        alCambiarPagina={cambiarPagina}
        alDescargar={() => descargarCsv("/reportes/movimientos", parametros, "movimientos.csv")}
        nota={<NotaAlcance almacen={alcance.almacen} />}
        tabla={(elementos) => (
          <div className="overflow-x-auto rounded-xl border">
            <Table className="w-full text-left">
              <TableCaption className="sr-only">Movimientos de inventario</TableCaption>
              <TableHeader className="bg-muted text-sm">
                <TableRow>
                  <TableHead scope="col" className="p-3 font-semibold">Fecha y hora</TableHead>
                  <TableHead scope="col" className="p-3 font-semibold">Folio</TableHead>
                  <TableHead scope="col" className="p-3 font-semibold">Tipo</TableHead>
                  <TableHead scope="col" className="p-3 font-semibold">Artículo</TableHead>
                  <TableHead scope="col" className="p-3 text-right font-semibold">Cantidad</TableHead>
                  <TableHead scope="col" className="p-3 font-semibold">De</TableHead>
                  <TableHead scope="col" className="p-3 font-semibold">A</TableHead>
                  <TableHead scope="col" className="p-3 font-semibold">Responsable</TableHead>
                  <TableHead scope="col" className="p-3 font-semibold">Saldo</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {elementos.map((m) => (
                  <TableRow key={m.id} className="border-t align-top">
                    <TableCell className="p-3 whitespace-nowrap tabular-nums">{formatearFechaHora(comoUtc(m.fecha))}</TableCell>
                    <TableHead scope="row" className="p-3 font-semibold whitespace-nowrap">
                      <Link to={`/vales/${m.vale_id}`} className="inline-flex min-h-12 items-center underline underline-offset-4">
                        {m.folio}
                      </Link>
                    </TableHead>
                    <TableCell className="p-3">{m.tipo_texto}</TableCell>
                    <TableCell className="p-3">
                      <Articulo m={m} />
                    </TableCell>
                    <TableCell className="p-3 text-right font-semibold tabular-nums">{m.cantidad}</TableCell>
                    <TableCell className="p-3">{m.origen}</TableCell>
                    <TableCell className="p-3">{m.destino}</TableCell>
                    <TableCell className="p-3">{m.responsable}</TableCell>
                    <TableCell className="p-3">
                      <Saldo m={m} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
        tarjetas={(elementos) => (
          <ul className="flex flex-col gap-3">
            {elementos.map((m) => (
              <li key={m.id} className="flex flex-col gap-2 rounded-xl border p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <Link to={`/vales/${m.vale_id}`} className="inline-flex min-h-12 items-center text-lg font-bold underline underline-offset-4">
                    {m.folio}
                  </Link>
                  <Insignia estado="neutra">{m.tipo_texto}</Insignia>
                </div>
                <p className="text-sm text-muted-foreground tabular-nums">{formatearFechaHora(comoUtc(m.fecha))}</p>
                <p>
                  <Articulo m={m} />
                </p>
                <p className="text-lg">
                  Cantidad: <span className="font-bold tabular-nums">{m.cantidad}</span>
                </p>
                <p>
                  <span className="text-muted-foreground">De </span>
                  {m.origen}
                  <span className="text-muted-foreground"> a </span>
                  {m.destino}
                </p>
                <p className="text-sm">
                  <span className="text-muted-foreground">Responsable: </span>
                  {m.responsable}
                </p>
                <div className="flex flex-wrap items-center gap-x-2 text-sm">
                  <span className="text-muted-foreground">Saldo: </span>
                  <Saldo m={m} enLinea />
                </div>
              </li>
            ))}
          </ul>
        )}
      />
    </Pantalla>
  );
}
