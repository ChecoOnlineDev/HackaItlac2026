import { Seleccion } from "~/componentes/catalogo/campos";
import { RangoDeFechas, textoDeRango, type RangoFechas } from "~/componentes/dominio/rango-de-fechas";
import { hoyMexico } from "~/componentes/dominio/fechas";
import { Label } from "~/components/ui/label";
import { useSesion } from "~/sesion/sesion";
import type { OpcionLista } from "./listas";
import type { FiltroActivo } from "./tipos";

/** Qué almacenes ve quien mira el reporte: todos (`almacenes.todos`) o solo el suyo. */
export function useAlcance() {
  const { sesion, puede } = useSesion();
  const todos = puede("almacenes.todos");
  return { todos, almacen: todos ? null : (sesion?.almacen ?? null) };
}

export function NotaAlcance({ almacen }: { almacen: { nombre: string; clave: string } | null }) {
  if (!almacen) return null;
  return (
    <p>
      Solo ves los datos de tu almacén: <span className="font-semibold text-foreground">{almacen.nombre} ({almacen.clave})</span>.
    </p>
  );
}

export function FiltroPeriodo({ desde, hasta, alCambiar }: { desde: string; hasta: string; alCambiar: (rango: RangoFechas) => void }) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label className="text-sm font-medium text-foreground">Periodo</Label>
      <RangoDeFechas
        etiqueta="Periodo"
        valor={{ desde: desde || null, hasta: hasta || null }}
        onCambio={alCambiar}
        hastaMaximo={hoyMexico()}
        className="h-11 w-full rounded-xl px-3 text-base"
      />
    </div>
  );
}

/** Lista desplegable con "Todos…" como primera opción. */
export function FiltroLista({
  etiqueta,
  vacio,
  valor,
  opciones,
  alCambiar,
}: {
  etiqueta: string;
  vacio: string;
  valor: string;
  opciones: OpcionLista[];
  alCambiar: (valor: string) => void;
}) {
  return (
    <Seleccion
      etiqueta={etiqueta}
      vacio={vacio}
      value={valor}
      opciones={opciones}
      alCambiar={(v) => alCambiar(v)}
    />
  );
}

/** Chip del periodo con el texto del selector ("Hoy", "5 oct 2026 – 8 oct 2026"). */
export function chipPeriodo(desde: string, hasta: string): FiltroActivo | null {
  if (!desde && !hasta) return null;
  return { clave: "periodo", texto: `Periodo: ${textoDeRango({ desde: desde || null, hasta: hasta || null })}` };
}

export function textoDeOpcion(opciones: OpcionLista[], valor: string): string | null {
  return opciones.find((o) => o.valor === valor)?.texto ?? null;
}
