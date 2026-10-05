import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { apiGet, descargarCsv } from "~/api/cliente";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { FiltroLista, NotaAlcance, textoDeOpcion, useAlcance } from "~/componentes/reportes/filtros-comunes";
import { useAlmacenesFiltro, useCategoriasFiltro } from "~/componentes/reportes/listas";
import { MarcoReporte } from "~/componentes/reportes/marco-reporte";
import {
  TAMANO_REPORTE,
  unidadConNumero,
  type ExistenciaReporte,
  type FiltroActivo,
  type PaginaReporte,
} from "~/componentes/reportes/tipos";
import { useFiltrosUrl } from "~/componentes/reportes/usar-filtros";
import { Insignia } from "~/componentes/ui/insignia";

export const handle: ManejadorRuta = { permiso: "reportes.existencias" };

const CLAVES = ["almacen_id", "categoria_id"] as const;

function Cifras({ e }: { e: ExistenciaReporte }) {
  return (
    <>
      <span className="font-bold tabular-nums">{e.cantidad}</span>
      <span className="text-sm text-muted-foreground"> {unidadConNumero(e.unidad, e.cantidad)}</span>
    </>
  );
}

export default function ReporteExistencias() {
  const { valores, pagina, cambiar, cambiarPagina, quitarTodos } = useFiltrosUrl(CLAVES);
  const alcance = useAlcance();
  const almacenes = useAlmacenesFiltro();
  const categorias = useCategoriasFiltro();

  const parametros = {
    almacen_id: alcance.todos ? valores.almacen_id : "",
    categoria_id: valores.categoria_id,
  };
  const consulta = useConsulta(
    (signal) =>
      apiGet<PaginaReporte<ExistenciaReporte>>("/reportes/existencias", { ...parametros, pagina, tamano: TAMANO_REPORTE }, signal),
    JSON.stringify([parametros, pagina]),
  );

  const activos: FiltroActivo[] = [];
  if (alcance.todos && valores.almacen_id) {
    activos.push({ clave: "almacen_id", texto: `Almacén: ${textoDeOpcion(almacenes.opciones, valores.almacen_id) ?? "elegido"}` });
  }
  if (valores.categoria_id) {
    activos.push({ clave: "categoria_id", texto: `Categoría: ${textoDeOpcion(categorias.opciones, valores.categoria_id) ?? "elegida"}` });
  }

  const filtros = (v: Record<string, string>, c: (parcial: Record<string, string | null>) => void) => (
    <>
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
      {!(alcance.todos && almacenes.disponible) && !categorias.disponible ? (
        <p className="text-muted-foreground">Este reporte no tiene filtros para tu usuario.</p>
      ) : null}
    </>
  );

  return (
    <Pantalla titulo="Reporte de existencias" descripcion="Cuánto hay de cada artículo en cada almacén.">
      <MarcoReporte<ExistenciaReporte>
        unidad="existencias"
        valores={valores}
        alAplicar={(v) => cambiar(v)}
        filtros={filtros}
        activos={activos}
        alQuitar={(clave) => cambiar({ [clave]: null } as Record<(typeof CLAVES)[number], null>)}
        alQuitarTodos={quitarTodos}
        consulta={consulta}
        pagina={pagina}
        alCambiarPagina={cambiarPagina}
        alDescargar={() => descargarCsv("/reportes/existencias", parametros, "existencias.csv")}
        nota={
          <>
            <NotaAlcance almacen={alcance.almacen} />
            <p>Disponible es lo que se puede entregar ahora: no cuenta las piezas no aptas ni las que están en mantenimiento o calibración.</p>
          </>
        }
        tabla={(elementos) => (
          <Table>
              <TableCaption className="sr-only">Existencias por almacén</TableCaption>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">Almacén</TableHead>
                  <TableHead scope="col">Artículo</TableHead>
                  <TableHead scope="col">Categoría</TableHead>
                  <TableHead scope="col" className="text-right">Existencia</TableHead>
                  <TableHead scope="col" className="text-right">Disponible</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {elementos.map((e) => (
                  <TableRow key={`${e.almacen_id}-${e.articulo_id}`} className="align-top">
                    <TableCell>{e.almacen}</TableCell>
                    <TableHead scope="row">
                      {e.articulo}
                      {!e.activo ? <Insignia estado="neutra" className="ml-2">Inactivo</Insignia> : null}
                      <span className="block text-sm font-normal text-muted-foreground">{e.codigo}</span>
                    </TableHead>
                    <TableCell>{e.categoria}</TableCell>
                    <TableCell className="text-right">
                      <Cifras e={e} />
                    </TableCell>
                    <TableCell className="text-right font-semibold">{e.disponible}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
        )}
        tarjetas={(elementos) => (
          <ul className="flex flex-col gap-3">
            {elementos.map((e) => (
              <li key={`${e.almacen_id}-${e.articulo_id}`} className="flex flex-col gap-1.5 rounded-2xl border bg-card p-4 shadow-xs">
                <p className="flex flex-wrap items-center gap-2 text-base leading-tight font-semibold">
                  {e.articulo}
                  {!e.activo ? <Insignia estado="neutra">Inactivo</Insignia> : null}
                </p>
                <p className="text-sm text-muted-foreground">
                  {e.codigo} · {e.categoria}
                </p>
                <p className="text-sm">{e.almacen}</p>
                <dl className="mt-1 grid grid-cols-2 gap-3">
                  <div>
                    <dt className="text-sm text-muted-foreground">Existencia</dt>
                    <dd className="text-lg">
                      <Cifras e={e} />
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground">Disponible</dt>
                    <dd className="text-lg font-semibold tabular-nums">{e.disponible}</dd>
                  </div>
                </dl>
              </li>
            ))}
          </ul>
        )}
      />
    </Pantalla>
  );
}
