import { cn } from "cn";
import { DownloadIcon, FileBarChartIcon, XIcon } from "lucide-react";
import { useState, type ReactNode } from "react";

import { mensajeDeError } from "~/api/errores";
import { Paginador } from "~/componentes/catalogo/campos";
import { Boton } from "~/componentes/ui/boton";
import { aviso } from "~/componentes/ui/aviso";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { HojaFiltros } from "~/componentes/ui/hoja-filtros";
import { useEsEscritorio } from "~/hooks/use-escritorio";
import { TAMANO_REPORTE, type FiltroActivo, type PaginaReporte } from "./tipos";

interface Consulta<T> {
  datos: PaginaReporte<T> | null;
  cargando: boolean;
  error: unknown;
  recargar: () => void;
}

interface PropiedadesMarco<T> {
  /** Filtros que ya se aplican (los de la dirección). */
  valores: Record<string, string>;
  /** Aplica el borrador de la hoja "Filtros" completo. */
  alAplicar: (valores: Record<string, string>) => void;
  /** Los controles de filtro. Van en la hoja "Filtros"; trabajan sobre un borrador hasta tocar "Aplicar". */
  filtros: (borrador: Record<string, string>, cambiar: (parcial: Record<string, string | null>) => void) => ReactNode;
  activos: FiltroActivo[];
  alQuitar: (clave: string) => void;
  alQuitarTodos: () => void;
  consulta: Consulta<T>;
  pagina: number;
  alCambiarPagina: (pagina: number) => void;
  /** Descarga el CSV con los mismos filtros. */
  alDescargar: () => Promise<void>;
  /** Tabla para computadora. */
  tabla: (elementos: T[]) => ReactNode;
  /** Tarjetas para celular y tableta. */
  tarjetas: (elementos: T[]) => ReactNode;
  /** Nota sobre el alcance o las columnas, bajo los filtros. */
  nota?: ReactNode;
  /** Lo que se cuenta: "movimientos", "renglones"… */
  unidad?: string;
}

/**
 * Marco común de los reportes: filtros arriba (en celular, en una hoja con contador), chips de los
 * filtros activos, total de registros, "Descargar CSV" y los estados de la lista (carga, vacío,
 * error). La pantalla solo aporta sus filtros y cómo se ve cada fila.
 */
export function MarcoReporte<T>({
  valores,
  alAplicar,
  filtros,
  activos,
  alQuitar,
  alQuitarTodos,
  consulta,
  pagina,
  alCambiarPagina,
  alDescargar,
  tabla,
  tarjetas,
  nota,
  unidad = "registros",
}: PropiedadesMarco<T>) {
  const escritorio = useEsEscritorio();
  const [descargando, setDescargando] = useState(false);
  const { datos, cargando, error } = consulta;
  const elementos = datos?.elementos ?? [];
  const total = datos?.total ?? 0;

  async function descargar() {
    setDescargando(true);
    try {
      await alDescargar();
    } catch (causa) {
      aviso({ titulo: "No se pudo descargar el archivo", descripcion: mensajeDeError(causa), tipo: "error" });
    } finally {
      setDescargando(false);
    }
  }

  let contenido: ReactNode;
  if (error) {
    contenido = <EstadoError error={error} alReintentar={consulta.recargar} />;
  } else if (cargando && !datos) {
    contenido = <Esqueleto tipo={escritorio ? "tabla" : "lista"} cantidad={6} />;
  } else if (total === 0 && !cargando) {
    contenido = (
      <EstadoVacio
        icono={FileBarChartIcon}
        titulo={activos.length > 0 ? "No hay registros con esos filtros" : "No hay registros"}
        descripcion={
          activos.length > 0 ? "Prueba con otro periodo u otros filtros." : "Todavía no hay nada que mostrar en este reporte."
        }
        accion={
          activos.length > 0 ? (
            <Boton variante="contorno" onClick={alQuitarTodos}>
              Quitar filtros
            </Boton>
          ) : undefined
        }
      />
    );
  } else {
    contenido = (
      <div className={cn("flex flex-col gap-4 transition-opacity", cargando && "opacity-60")} aria-busy={cargando}>
        {/* `w-0 min-w-full`: la tabla ancha se desplaza dentro de su caja y no ensancha la página. */}
        {escritorio ? <div className="w-0 min-w-full">{tabla(elementos)}</div> : tarjetas(elementos)}
        <Paginador pagina={pagina} tamano={TAMANO_REPORTE} total={total} alCambiar={alCambiarPagina} ocupado={cargando} />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <HojaFiltros valores={valores} activos={activos.length} alAplicar={alAplicar} alLimpiar={alQuitarTodos}>
          {(borrador, cambiar) =>
            filtros(borrador, (parcial) => cambiar(Object.fromEntries(Object.entries(parcial).map(([k, v]) => [k, v ?? ""]))))
          }
        </HojaFiltros>
        <Boton variante="contorno" cargando={descargando} disabled={!datos || total === 0 || Boolean(error)} onClick={descargar}>
          {descargando ? null : <DownloadIcon aria-hidden="true" />}
          Descargar CSV
        </Boton>
      </div>

      {activos.length > 0 ? (
        <ul aria-label="Filtros activos" className="flex flex-wrap items-center gap-2">
          {activos.map((f) => (
            <li key={f.clave}>
              <button
                type="button"
                onClick={() => alQuitar(f.clave)}
                aria-label={`Quitar filtro: ${f.texto}`}
                className="inline-flex min-h-10 items-center gap-1.5 rounded-full border border-primary/30 bg-accent px-3 text-xs font-semibold text-marino hover:bg-accent/70"
              >
                {f.texto}
                <XIcon aria-hidden="true" className="size-3.5" />
              </button>
            </li>
          ))}
          <li>
            <Boton variante="texto" className="h-10 px-3 text-xs" onClick={alQuitarTodos}>
              Quitar todos
            </Boton>
          </li>
        </ul>
      ) : null}

      {nota ? <div className="flex flex-col gap-1 text-xs text-muted-foreground">{nota}</div> : null}

      <p className="text-sm font-semibold" aria-live="polite">
        {datos && !error ? `${total} ${total === 1 ? unidad.replace(/s$/, "") : unidad}` : " "}
      </p>

      {contenido}
    </div>
  );
}
