import { cn } from "cn";
import { ChevronDownIcon } from "lucide-react";
import { Fragment, useState } from "react";

import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { apiGet, descargarCsv } from "~/api/cliente";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import {
  chipPeriodo,
  FiltroLista,
  FiltroPeriodo,
  NotaAlcance,
  textoDeOpcion,
  useAlcance,
} from "~/componentes/reportes/filtros-comunes";
import { useAlmacenesFiltro, useCategoriasFiltro, useEtiqueta } from "~/componentes/reportes/listas";
import { MarcoReporte } from "~/componentes/reportes/marco-reporte";
import { SelectorBusqueda } from "~/componentes/reportes/selector-busqueda";
import { TAMANO_REPORTE, unidadConNumero, type ConsumoReporte, type FiltroActivo, type PaginaReporte } from "~/componentes/reportes/tipos";
import { useFiltrosUrl } from "~/componentes/reportes/usar-filtros";

export const handle: ManejadorRuta = { dispositivo: "computadora", permiso: "reportes.consumo" };

const CLAVES = ["desde", "hasta", "almacen_id", "categoria_id", "articulo_id", "trabajador_id"] as const;

/** Consumo de un artículo por trabajador, de mayor a menor. */
function Desglose({ c, id }: { c: ConsumoReporte; id: string }) {
  return (
    <div id={id} className="flex flex-col gap-2">
      <p className="text-sm font-semibold text-muted-foreground">Consumo por trabajador, de mayor a menor</p>
      {c.trabajadores.length === 0 ? (
        <p className="text-muted-foreground">No hay detalle por trabajador.</p>
      ) : (
        <ol className="flex flex-col divide-y rounded-xl border bg-background">
          {c.trabajadores.map((t, i) => (
            <li key={`${t.trabajador_id ?? "sin"}-${i}`} className="flex items-center justify-between gap-3 p-3">
              <span className="min-w-0">
                <span className="font-semibold">{t.trabajador}</span>
                {t.numero_empleado ? <span className="block text-sm text-muted-foreground">{t.numero_empleado}</span> : null}
              </span>
              <span className="shrink-0 text-base font-semibold tabular-nums">
                {t.cantidad} <span className="text-sm font-normal text-muted-foreground">{unidadConNumero(c.unidad, t.cantidad)}</span>
              </span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

function Total({ c }: { c: ConsumoReporte }) {
  return (
    <span className="text-lg font-semibold tabular-nums">
      {c.total} <span className="text-sm font-normal text-muted-foreground">{unidadConNumero(c.unidad, c.total)}</span>
    </span>
  );
}

export default function ReporteConsumo() {
  const { valores, pagina, cambiar, cambiarPagina, quitarTodos } = useFiltrosUrl(CLAVES);
  const alcance = useAlcance();
  const almacenes = useAlmacenesFiltro();
  const categorias = useCategoriasFiltro();
  const etiquetaTrabajador = useEtiqueta("trabajador", valores.trabajador_id);
  const etiquetaArticulo = useEtiqueta("articulo", valores.articulo_id);
  const [abiertos, setAbiertos] = useState<ReadonlySet<string>>(new Set());

  const parametros = {
    desde: valores.desde,
    hasta: valores.hasta,
    almacen_id: alcance.todos ? valores.almacen_id : "",
    categoria_id: valores.categoria_id,
    articulo_id: valores.articulo_id,
    trabajador_id: valores.trabajador_id,
  };
  const consulta = useConsulta(
    (signal) => apiGet<PaginaReporte<ConsumoReporte>>("/reportes/consumo", { ...parametros, pagina, tamano: TAMANO_REPORTE }, signal),
    JSON.stringify([parametros, pagina]),
  );

  const activos: FiltroActivo[] = [];
  const periodo = chipPeriodo(valores.desde, valores.hasta);
  if (periodo) activos.push(periodo);
  if (alcance.todos && valores.almacen_id) {
    activos.push({ clave: "almacen_id", texto: `Almacén: ${textoDeOpcion(almacenes.opciones, valores.almacen_id) ?? "elegido"}` });
  }
  if (valores.categoria_id) {
    activos.push({ clave: "categoria_id", texto: `Categoría: ${textoDeOpcion(categorias.opciones, valores.categoria_id) ?? "elegida"}` });
  }
  if (valores.articulo_id) activos.push({ clave: "articulo_id", texto: `Artículo: ${etiquetaArticulo ?? "elegido"}` });
  if (valores.trabajador_id) activos.push({ clave: "trabajador_id", texto: `Trabajador: ${etiquetaTrabajador ?? "elegido"}` });

  function quitar(clave: string) {
    if (clave === "periodo") cambiar({ desde: null, hasta: null });
    else cambiar({ [clave]: null } as Record<(typeof CLAVES)[number], null>);
  }

  function alternar(id: string) {
    setAbiertos((previos) => {
      const nuevos = new Set(previos);
      if (nuevos.has(id)) nuevos.delete(id);
      else nuevos.add(id);
      return nuevos;
    });
  }

  const filtros = (v: Record<string, string>, c: (parcial: Record<string, string | null>) => void) => (
    <>
      <FiltroPeriodo desde={v.desde} hasta={v.hasta} alCambiar={(r) => c({ desde: r.desde, hasta: r.hasta })} />
      {alcance.todos && almacenes.disponible ? (
        <FiltroLista
          etiqueta="Almacén"
          vacio="Todos los almacenes"
          valor={v.almacen_id}
          opciones={almacenes.opciones}
          alCambiar={(v) => c({ almacen_id: v })}
        />
      ) : null}
      {categorias.disponible ? (
        <FiltroLista
          etiqueta="Categoría"
          vacio="Todas las categorías"
          valor={v.categoria_id}
          opciones={categorias.opciones}
          alCambiar={(v) => c({ categoria_id: v })}
        />
      ) : null}
      <SelectorBusqueda tipo="articulo" valor={v.articulo_id} alCambiar={(id) => c({ articulo_id: id })} />
      <SelectorBusqueda tipo="trabajador" valor={v.trabajador_id} alCambiar={(id) => c({ trabajador_id: id })} />
    </>
  );

  return (
    <Pantalla titulo="Reporte de consumo" descripcion="Cuánto se consumió de cada artículo y quién lo recibió.">
      <MarcoReporte<ConsumoReporte>
        unidad="artículos"
        valores={valores}
        alAplicar={(v) => cambiar(v)}
        filtros={filtros}
        activos={activos}
        alQuitar={quitar}
        alQuitarTodos={quitarTodos}
        consulta={consulta}
        pagina={pagina}
        alCambiarPagina={cambiarPagina}
        alDescargar={() => descargarCsv("/reportes/consumo", parametros, "consumo.csv")}
        nota={
          <>
            <NotaAlcance almacen={alcance.almacen} />
            <p>Toca un artículo para ver cuánto consumió cada trabajador.</p>
          </>
        }
        tabla={(elementos) => (
          <Table>
              <TableCaption className="sr-only">Consumo por artículo</TableCaption>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">Artículo</TableHead>
                  <TableHead scope="col">Categoría</TableHead>
                  <TableHead scope="col" className="text-right">Total consumido</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {elementos.map((c) => {
                  const abierto = abiertos.has(c.articulo_id);
                  const idDetalle = `consumo-${c.articulo_id}`;
                  return (
                    <Fragment key={c.articulo_id}>
                      <TableRow className={cn("border-t", abierto && "bg-muted/40")}>
                        <TableHead scope="row" className="p-0 font-semibold">
                          <button
                            type="button"
                            aria-expanded={abierto}
                            aria-controls={idDetalle}
                            onClick={() => alternar(c.articulo_id)}
                            className="flex min-h-12 w-full items-center gap-2 px-3 py-2 text-left hover:bg-muted/60"
                          >
                            <ChevronDownIcon aria-hidden="true" className={cn("size-4 shrink-0 transition-transform duration-150", !abierto && "-rotate-90")} />
                            <span>
                              {c.articulo}
                              <span className="block text-sm font-normal text-muted-foreground">{c.codigo}</span>
                            </span>
                          </button>
                        </TableHead>
                        <TableCell>{c.categoria}</TableCell>
                        <TableCell className="text-right">
                          <Total c={c} />
                        </TableCell>
                      </TableRow>
                      {abierto ? (
                        <TableRow className="bg-muted/40">
                          <TableCell colSpan={3} className="px-3 pb-4 pl-10">
                            <Desglose c={c} id={idDetalle} />
                          </TableCell>
                        </TableRow>
                      ) : null}
                    </Fragment>
                  );
                })}
              </TableBody>
            </Table>
        )}
        tarjetas={(elementos) => (
          <ul className="flex flex-col gap-3">
            {elementos.map((c) => {
              const abierto = abiertos.has(c.articulo_id);
              const idDetalle = `consumo-${c.articulo_id}`;
              return (
                <li key={c.articulo_id} className="overflow-hidden rounded-2xl border bg-card shadow-xs">
                  <button
                    type="button"
                    aria-expanded={abierto}
                    aria-controls={idDetalle}
                    onClick={() => alternar(c.articulo_id)}
                    className="flex min-h-12 w-full items-center gap-3 p-4 text-left"
                  >
                    <ChevronDownIcon aria-hidden="true" className={cn("size-4 shrink-0 transition-transform duration-150", !abierto && "-rotate-90")} />
                    <span className="flex min-w-0 flex-1 flex-col">
                      <span className="text-base leading-tight font-semibold">{c.articulo}</span>
                      <span className="text-sm text-muted-foreground">
                        {c.codigo} · {c.categoria}
                      </span>
                    </span>
                    <Total c={c} />
                  </button>
                  {abierto ? (
                    <div className="border-t p-4">
                      <Desglose c={c} id={idDetalle} />
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
      />
    </Pantalla>
  );
}
