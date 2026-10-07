import { cn } from "cn";
import { FilterXIcon } from "lucide-react";
import { useId } from "react";

import { CampoFecha } from "~/componentes/ui/campo-fecha";
import { hoyMexico } from "~/componentes/dominio/fechas";
import { Boton } from "~/componentes/ui/boton";
import { ListaDesplegable, type OpcionLista } from "~/componentes/ui/lista-desplegable";
import { Switch } from "~/components/ui/switch";
import { ATAJOS_PERIODO, rangoDePeriodo, type ClavePeriodo, type Periodo } from "./periodos";

export interface FiltrosConsumo {
  /** "" = todos los almacenes (administrador) o el propio (los demás). */
  almacen: string;
  periodo: Periodo;
  /** "" = todas las categorías. */
  categoria: string;
  separar: boolean;
}

interface PropiedadesFiltros {
  valor: FiltrosConsumo;
  alCambiar: (cambio: Partial<FiltrosConsumo>) => void;
  alLimpiar: () => void;
  hayCambios: boolean;
  /** Solo con `alcance.puede_elegir`. */
  almacenes: OpcionLista[] | null;
  categorias: OpcionLista[];
  /** Interruptor «Separar por almacén»: solo el administrador viendo todos los almacenes. */
  puedeSeparar: boolean;
  /** Mensaje bajo las fechas cuando el rango no es válido. */
  errorFechas: string | null;
}

/** Los tres filtros de la gráfica (almacén, periodo, categoría) y el interruptor de separar por almacén. */
export function FiltrosConsumoBarra({ valor, alCambiar, alLimpiar, hayCambios, almacenes, categorias, puedeSeparar, errorFechas }: PropiedadesFiltros) {
  const id = useId();
  const hoy = hoyMexico();

  const elegirPeriodo = (clave: ClavePeriodo) => {
    if (clave === "fechas") alCambiar({ periodo: { ...valor.periodo, clave: "fechas" } });
    else alCambiar({ periodo: { clave, ...rangoDePeriodo(clave) } });
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-3 sm:grid-cols-2">
        {almacenes ? (
          <div className="flex flex-col gap-1.5">
            <label htmlFor={`${id}-almacen`} className="text-sm font-medium">
              Almacén
            </label>
            <ListaDesplegable id={`${id}-almacen`} valor={valor.almacen} alCambiar={(a) => alCambiar({ almacen: a })} opciones={almacenes} vacio="Todos los almacenes" />
          </div>
        ) : null}
        <div className="flex flex-col gap-1.5">
          <label htmlFor={`${id}-categoria`} className="text-sm font-medium">
            Categoría
          </label>
          <ListaDesplegable id={`${id}-categoria`} valor={valor.categoria} alCambiar={(c) => alCambiar({ categoria: c })} opciones={categorias} vacio="Todas las categorías" />
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <span id={`${id}-periodo`} className="text-sm font-medium">
          Periodo
        </span>
        <div role="group" aria-labelledby={`${id}-periodo`} className="flex flex-wrap gap-2">
          {ATAJOS_PERIODO.map((a) => (
            <Boton
              key={a.clave}
              variante={valor.periodo.clave === a.clave ? "normal" : "contorno"}
              aria-pressed={valor.periodo.clave === a.clave}
              className="min-h-11 px-3.5 text-sm"
              onClick={() => elegirPeriodo(a.clave)}
            >
              {a.texto}
            </Boton>
          ))}
        </div>
        {valor.periodo.clave === "fechas" ? (
          <div className="mt-1 grid gap-3 sm:grid-cols-2">
            <CampoFecha etiqueta="Desde" value={valor.periodo.desde} max={hoy} alCambiar={(d) => alCambiar({ periodo: { clave: "fechas", desde: d, hasta: valor.periodo.hasta } })} />
            <CampoFecha etiqueta="Hasta" value={valor.periodo.hasta} max={hoy} alCambiar={(h) => alCambiar({ periodo: { clave: "fechas", desde: valor.periodo.desde, hasta: h } })} error={errorFechas} />
          </div>
        ) : null}
      </div>

      <div className={cn("flex flex-wrap items-center gap-x-6 gap-y-3", !puedeSeparar && !hayCambios && "hidden")}>
        {puedeSeparar ? (
          <label className="flex min-h-11 cursor-pointer items-center gap-3 text-sm font-medium">
            <Switch checked={valor.separar} onCheckedChange={(v) => alCambiar({ separar: v })} aria-label="Separar por almacén" />
            Separar por almacén
          </label>
        ) : null}
        {hayCambios ? (
          <Boton variante="texto" className="min-h-11 text-sm" onClick={alLimpiar}>
            <FilterXIcon aria-hidden="true" />
            Limpiar filtros
          </Boton>
        ) : null}
      </div>
    </div>
  );
}
