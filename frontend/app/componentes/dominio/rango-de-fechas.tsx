import { cn } from "cn";
import { format } from "date-fns";
import { es } from "date-fns/locale/es";
import { CalendarDaysIcon } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { DateRange } from "react-day-picker";

import { Boton } from "~/componentes/ui/boton";
import { Calendar } from "~/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "~/components/ui/popover";
import { useIsMobile } from "~/hooks/use-mobile";
import { Hoja } from "~/componentes/ui/hoja";
import { aFechaLocal, aTextoFecha, hoyMexico, sumarDias } from "./fechas";

/** Fechas `YYYY-MM-DD` del calendario de México. El servidor las convierte a UTC. */
export interface RangoFechas {
  desde: string | null;
  hasta: string | null;
}

type Atajo = "hoy" | "ayer" | "siete" | "mes" | "personalizado";

const ETIQUETA_ATAJO: Record<Atajo, string> = {
  hoy: "Hoy",
  ayer: "Ayer",
  siete: "Últimos 7 días",
  mes: "Este mes",
  personalizado: "Rango personalizado",
};

/** Rango de cada atajo, calculado con el día de hoy en México (no el del dispositivo). */
export function rangoDeAtajo(atajo: Exclude<Atajo, "personalizado">, hoy: string = hoyMexico()): RangoFechas {
  switch (atajo) {
    case "hoy":
      return { desde: hoy, hasta: hoy };
    case "ayer": {
      const ayer = sumarDias(hoy, -1);
      return { desde: ayer, hasta: ayer };
    }
    case "siete":
      return { desde: sumarDias(hoy, -6), hasta: hoy };
    case "mes":
      return { desde: `${hoy.slice(0, 8)}01`, hasta: hoy };
  }
}

function atajoActual(valor: RangoFechas, hoy: string): Atajo | null {
  if (!valor.desde || !valor.hasta) return null;
  for (const a of ["hoy", "ayer", "siete", "mes"] as const) {
    const r = rangoDeAtajo(a, hoy);
    if (r.desde === valor.desde && r.hasta === valor.hasta) return a;
  }
  return null;
}

function formatoCorto(valor: string): string {
  return format(aFechaLocal(valor), "d MMM yyyy", { locale: es }).replace(".", "");
}

/** Texto del botón: el atajo, o las fechas, o la invitación a elegirlas. */
export function textoDeRango(valor: RangoFechas, hoy: string = hoyMexico()): string {
  if (!valor.desde || !valor.hasta) return "Elegir fechas";
  const atajo = atajoActual(valor, hoy);
  if (atajo) return ETIQUETA_ATAJO[atajo];
  return valor.desde === valor.hasta ? formatoCorto(valor.desde) : `${formatoCorto(valor.desde)} – ${formatoCorto(valor.hasta)}`;
}

/** Pone el rango en orden: nunca queda "hasta" antes de "desde". */
function ordenar(desde: string, hasta: string): RangoFechas {
  return desde <= hasta ? { desde, hasta } : { desde: hasta, hasta: desde };
}

interface PropiedadesRangoDeFechas {
  valor: RangoFechas;
  onCambio: (rango: RangoFechas) => void;
  /** Etiqueta para lectores de pantalla y para el título de la hoja. */
  etiqueta?: string;
  /** Última fecha que se puede elegir (`YYYY-MM-DD`). Por ejemplo el día de hoy. */
  hastaMaximo?: string;
  deshabilitado?: boolean;
  className?: string;
}

/**
 * Selector de periodo: un botón que abre un calendario de rango con atajos (Hoy, Ayer, Últimos 7 días,
 * Este mes, Rango personalizado). En celular se abre en una hoja. Semana desde el lunes, en español.
 * Entrega fechas `YYYY-MM-DD` del calendario de México; el rango nunca queda invertido.
 *
 * ```tsx
 * <RangoDeFechas valor={rango} onCambio={setRango} />
 * ```
 */
export function RangoDeFechas({ valor, onCambio, etiqueta = "Periodo", hastaMaximo, deshabilitado, className }: PropiedadesRangoDeFechas) {
  const esMovil = useIsMobile();
  const [abierto, setAbierto] = useState(false);
  const [borrador, setBorrador] = useState<DateRange | undefined>(undefined);
  const [mes, setMes] = useState<Date>(() => aFechaLocal(valor.hasta ?? hoyMexico()));
  const [personalizado, setPersonalizado] = useState(false);
  const hoy = hoyMexico();

  // Al abrir, el borrador parte del valor actual.
  useEffect(() => {
    if (!abierto) return;
    setBorrador(valor.desde && valor.hasta ? { from: aFechaLocal(valor.desde), to: aFechaLocal(valor.hasta) } : undefined);
    setMes(aFechaLocal(valor.hasta ?? hoyMexico()));
    setPersonalizado(false);
    // Solo al abrir.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [abierto]);

  const entregar = (rango: RangoFechas) => {
    if (!rango.desde || !rango.hasta) return;
    const ordenado = ordenar(rango.desde, rango.hasta);
    onCambio(ordenado);
    setAbierto(false);
  };

  const aplicarAtajo = (atajo: Atajo) => {
    if (atajo === "personalizado") {
      setPersonalizado(true);
      setBorrador(undefined);
      return;
    }
    const rango = rangoDeAtajo(atajo, hoy);
    entregar(rango);
  };

  const seleccion = useMemo(() => atajoActual(valor, hoy), [valor, hoy]);
  const texto = textoDeRango(valor, hoy);

  const panel = (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-2" role="group" aria-label="Atajos">
        {(Object.keys(ETIQUETA_ATAJO) as Atajo[]).map((a) => (
          <Boton
            key={a}
            variante={(a === "personalizado" ? personalizado : seleccion === a && !borrador?.from) ? "normal" : "contorno"}
            className="h-10 px-3 text-sm"
            aria-pressed={a === "personalizado" ? personalizado : seleccion === a}
            onClick={() => aplicarAtajo(a)}
          >
            {ETIQUETA_ATAJO[a]}
          </Boton>
        ))}
      </div>

      <p className="text-sm text-muted-foreground" role="status">
        {!borrador?.from
          ? "Toca el primer día y luego el último."
          : !borrador.to
            ? `Desde el ${formatoCorto(aTextoFecha(borrador.from))}. Toca el último día.`
            : aTextoFecha(borrador.from) === aTextoFecha(borrador.to)
              ? formatoCorto(aTextoFecha(borrador.from))
              : `${formatoCorto(aTextoFecha(borrador.from))} – ${formatoCorto(aTextoFecha(borrador.to))}`}
      </p>

      <div className="flex justify-center">
        <Calendar
          mode="range"
          locale={es}
          weekStartsOn={1}
          month={mes}
          onMonthChange={setMes}
          selected={borrador}
          onSelect={(rango, dia) => {
            // Con un rango ya completo, un nuevo toque empieza otro rango desde ese día.
            if (borrador?.from && borrador.to) setBorrador({ from: dia, to: undefined });
            // El calendario acomoda el orden; aun así se ordena por si llegara invertido.
            else if (rango?.from && rango.to && rango.from > rango.to) setBorrador({ from: rango.to, to: rango.from });
            else setBorrador(rango);
          }}
          disabled={hastaMaximo ? { after: aFechaLocal(hastaMaximo) } : undefined}
          labels={{
            labelPrevious: () => "Mes anterior",
            labelNext: () => "Mes siguiente",
          }}
          className="p-0 [--cell-size:--spacing(11)] md:[--cell-size:--spacing(10)]"
        />
      </div>

      <div className="flex gap-2">
        <Boton variante="texto" className="flex-1" onClick={() => setAbierto(false)}>
          Cancelar
        </Boton>
        <Boton
          variante="normal"
          className="flex-1"
          disabled={!borrador?.from}
          onClick={() => {
            if (!borrador?.from) return;
            const d = aTextoFecha(borrador.from);
            entregar({ desde: d, hasta: borrador.to ? aTextoFecha(borrador.to) : d });
          }}
        >
          Aplicar
        </Boton>
      </div>
    </div>
  );

  const disparador = (
    <Boton
      variante="contorno"
      disabled={deshabilitado}
      aria-label={`${etiqueta}: ${texto}`}
      aria-haspopup="dialog"
      aria-expanded={abierto}
      onClick={esMovil ? () => setAbierto(true) : undefined}
      className={cn("justify-start font-normal", className)}
    >
      <CalendarDaysIcon aria-hidden="true" />
      <span>{texto}</span>
    </Boton>
  );

  if (esMovil) {
    return (
      <>
        {disparador}
        <Hoja abierta={abierto} alCambiar={setAbierto} titulo={etiqueta} descripcion="Elige un atajo o los días en el calendario.">
          {panel}
        </Hoja>
      </>
    );
  }

  return (
    <Popover open={abierto} onOpenChange={setAbierto}>
      <PopoverTrigger render={disparador} />
      <PopoverContent align="start" className="w-[22rem] max-w-[95vw] gap-3 p-4">
        {panel}
      </PopoverContent>
    </Popover>
  );
}
