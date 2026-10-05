import { apiGet, descargarCsv } from "~/api/cliente";
import { FilaInterruptor } from "~/componentes/catalogo/campos";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { formatearFecha } from "~/componentes/dominio/fechas";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { FiltroLista, NotaAlcance, textoDeOpcion, useAlcance } from "~/componentes/reportes/filtros-comunes";
import { useAlmacenesFiltro } from "~/componentes/reportes/listas";
import { MarcoReporte } from "~/componentes/reportes/marco-reporte";
import { comoUtc, TAMANO_REPORTE, type AdeudoReporte, type FiltroActivo, type PaginaReporte } from "~/componentes/reportes/tipos";
import { useFiltrosUrl } from "~/componentes/reportes/usar-filtros";
import { Insignia } from "~/componentes/ui/insignia";

export const handle: ManejadorRuta = { permiso: "reportes.adeudos" };

const CLAVES = ["almacen_id", "solo_no_vigentes"] as const;

function Trabajador({ a }: { a: AdeudoReporte }) {
  return (
    <>
      <span className="font-semibold">{a.trabajador}</span>
      <span className="block text-sm text-muted-foreground">{a.numero_empleado}</span>
      {!a.vigente ? (
        <span className="mt-1 flex flex-col items-start gap-1">
          <Insignia estado="amarillo">No vigente</Insignia>
          {a.motivo_no_vigente ? <span className="text-sm">{a.motivo_no_vigente}</span> : null}
        </span>
      ) : null}
    </>
  );
}

function Articulo({ a }: { a: AdeudoReporte }) {
  return (
    <>
      <span className="font-semibold">{a.articulo}</span>
      <span className="block text-sm text-muted-foreground">
        {a.codigo}
        {a.numero_serie ? ` · Serie ${a.numero_serie}` : ""}
      </span>
    </>
  );
}

export default function ReporteAdeudos() {
  const { valores, pagina, cambiar, cambiarPagina, quitarTodos } = useFiltrosUrl(CLAVES);
  const alcance = useAlcance();
  const almacenes = useAlmacenesFiltro();
  const soloNoVigentes = valores.solo_no_vigentes === "1";

  const parametros = {
    almacen_id: alcance.todos ? valores.almacen_id : "",
    solo_no_vigentes: soloNoVigentes ? "true" : "",
  };
  const consulta = useConsulta(
    (signal) => apiGet<PaginaReporte<AdeudoReporte>>("/reportes/adeudos", { ...parametros, pagina, tamano: TAMANO_REPORTE }, signal),
    JSON.stringify([parametros, pagina]),
  );

  const activos: FiltroActivo[] = [];
  if (alcance.todos && valores.almacen_id) {
    activos.push({ clave: "almacen_id", texto: `Almacén: ${textoDeOpcion(almacenes.opciones, valores.almacen_id) ?? "elegido"}` });
  }
  if (soloNoVigentes) activos.push({ clave: "solo_no_vigentes", texto: "Solo trabajadores no vigentes" });

  const filtros = (
    <>
      {alcance.todos && almacenes.disponible ? (
        <FiltroLista
          etiqueta="Almacén"
          vacio="Todos los almacenes"
          valor={valores.almacen_id}
          opciones={almacenes.opciones}
          alCambiar={(v) => cambiar({ almacen_id: v })}
        />
      ) : null}
      <div className="sm:col-span-2">
        <FilaInterruptor
          titulo="Solo trabajadores no vigentes"
          ayuda="Quienes ya no forman parte de la plantilla y siguen con equipo."
          activo={soloNoVigentes}
          alCambiar={(activo) => cambiar({ solo_no_vigentes: activo ? "1" : null })}
        />
      </div>
    </>
  );

  return (
    <Pantalla titulo="Reporte de adeudos" descripcion="Qué equipo tiene pendiente cada trabajador, desde cuándo y de qué almacén.">
      <MarcoReporte<AdeudoReporte>
        unidad="adeudos"
        filtros={filtros}
        activos={activos}
        alQuitar={(clave) => cambiar({ [clave]: null } as Record<(typeof CLAVES)[number], null>)}
        alQuitarTodos={quitarTodos}
        consulta={consulta}
        pagina={pagina}
        alCambiarPagina={cambiarPagina}
        alDescargar={() => descargarCsv("/reportes/adeudos", parametros, "adeudos.csv")}
        nota={<NotaAlcance almacen={alcance.almacen} />}
        tabla={(elementos) => (
          <div className="overflow-x-auto rounded-xl border">
            <table className="w-full text-left">
              <caption className="sr-only">Equipo pendiente por trabajador</caption>
              <thead className="bg-muted text-sm">
                <tr>
                  <th scope="col" className="p-3 font-semibold">Trabajador</th>
                  <th scope="col" className="p-3 font-semibold">Lo que tiene</th>
                  <th scope="col" className="p-3 text-right font-semibold">Cantidad</th>
                  <th scope="col" className="p-3 font-semibold">Desde</th>
                  <th scope="col" className="p-3 font-semibold">Vale</th>
                  <th scope="col" className="p-3 font-semibold">Almacén</th>
                </tr>
              </thead>
              <tbody>
                {elementos.map((a, i) => (
                  <tr key={`${a.trabajador_id}-${a.articulo_id}-${a.numero_serie ?? i}-${a.folio ?? ""}`} className="border-t align-top">
                    <th scope="row" className="p-3">
                      <Trabajador a={a} />
                    </th>
                    <td className="p-3">
                      <Articulo a={a} />
                    </td>
                    <td className="p-3 text-right font-bold tabular-nums">{a.cantidad}</td>
                    <td className="p-3 whitespace-nowrap tabular-nums">{a.desde ? formatearFecha(comoUtc(a.desde)) : "—"}</td>
                    <td className="p-3">{a.folio ?? "—"}</td>
                    <td className="p-3">{a.almacen ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        tarjetas={(elementos) => (
          <ul className="flex flex-col gap-3">
            {elementos.map((a, i) => (
              <li key={`${a.trabajador_id}-${a.articulo_id}-${a.numero_serie ?? i}-${a.folio ?? ""}`} className="flex flex-col gap-2 rounded-xl border p-4">
                <p className="text-lg leading-tight">
                  <Trabajador a={a} />
                </p>
                <p>
                  <Articulo a={a} />
                </p>
                <p className="text-lg">
                  Cantidad: <span className="font-bold tabular-nums">{a.cantidad}</span>
                </p>
                <p className="text-sm text-muted-foreground">
                  Desde {a.desde ? formatearFecha(comoUtc(a.desde)) : "—"} · Vale {a.folio ?? "—"} · {a.almacen ?? "Sin almacén"}
                </p>
              </li>
            ))}
          </ul>
        )}
      />
    </Pantalla>
  );
}
