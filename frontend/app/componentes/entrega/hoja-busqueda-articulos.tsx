import { Hoja } from "~/componentes/ui/hoja";

export interface CoincidenciaArticulo {
  /** Lo que se agrega al borrador: el código del artículo o el de la pieza. */
  codigo: string;
  nombre: string;
  detalle: string;
}

interface PropiedadesHojaBusqueda {
  abierta: boolean;
  alCambiar: (abierta: boolean) => void;
  texto: string;
  coincidencias: CoincidenciaArticulo[];
  alElegir: (coincidencia: CoincidenciaArticulo) => void;
}

/** Lista de artículos y piezas que coinciden con lo que se escribió (`GET /api/busqueda`). Tocar uno lo agrega. */
export function HojaBusquedaArticulos({ abierta, alCambiar, texto, coincidencias, alElegir }: PropiedadesHojaBusqueda) {
  return (
    <Hoja abierta={abierta} alCambiar={alCambiar} titulo="¿Cuál es?" descripcion={`Resultados para “${texto}”.`}>
      <ul className="flex flex-col gap-2">
        {coincidencias.map((c) => (
          <li key={c.codigo}>
            <button
              type="button"
              onClick={() => alElegir(c)}
              className="flex min-h-14 w-full flex-col items-start rounded-xl border bg-card px-4 py-2 text-left hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
            >
              <span className="text-lg font-semibold">{c.nombre}</span>
              <span className="text-sm text-muted-foreground">{c.detalle}</span>
            </button>
          </li>
        ))}
      </ul>
    </Hoja>
  );
}
