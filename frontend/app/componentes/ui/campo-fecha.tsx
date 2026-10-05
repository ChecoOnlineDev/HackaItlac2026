import { cn } from "cn";
import { es } from "date-fns/locale/es";
import { CalendarDaysIcon, CircleAlertIcon } from "lucide-react";
import { useId, useState } from "react";

import { aFechaLocal, aTextoFecha, formatearFecha } from "~/componentes/dominio/fechas";
import { Calendar } from "~/components/ui/calendar";
import { Label } from "~/components/ui/label";
import { useIsMobile } from "~/hooks/use-mobile";
import { Popover, PopoverContent, PopoverTrigger } from "~/components/ui/popover";
import { Boton } from "./boton";
import { Hoja } from "./hoja";

interface PropiedadesCampoFecha {
  etiqueta: string;
  /** Fecha `YYYY-MM-DD` o "" si no hay. */
  value: string;
  alCambiar: (valor: string) => void;
  /** Primer día que se puede elegir (`YYYY-MM-DD`). */
  min?: string;
  /** Último día que se puede elegir (`YYYY-MM-DD`). */
  max?: string;
  error?: string | null;
  ayuda?: string;
  disabled?: boolean;
  claseContenedor?: string;
}

/** Etiqueta + botón de 44 px que abre el calendario de shadcn. Entrega y recibe `YYYY-MM-DD`. */
export function CampoFecha({ etiqueta, value, alCambiar, min, max, error, ayuda, disabled, claseContenedor }: PropiedadesCampoFecha) {
  const id = useId();
  const esMovil = useIsMobile();
  const [abierto, setAbierto] = useState(false);
  const elegida = value ? aFechaLocal(value) : undefined;
  const fueraDeRango = (dia: Date) => {
    const t = aTextoFecha(dia);
    return Boolean((min && t < min) || (max && t > max));
  };

  const disparador = (
    <Boton
      id={id}
      variante="contorno"
      disabled={disabled}
      aria-invalid={error ? true : undefined}
      onClick={esMovil ? () => setAbierto(true) : undefined}
      className={cn("h-11 w-full justify-start font-normal", !value && "text-muted-foreground", error && "border-destructive")}
    >
      <CalendarDaysIcon aria-hidden="true" />
      <span className="truncate">{value ? formatearFecha(value) : "Elige una fecha"}</span>
    </Boton>
  );

  const calendario = (clase?: string) => (
    <Calendar
      mode="single"
      locale={es}
      weekStartsOn={1}
      defaultMonth={elegida}
      selected={elegida}
      className={clase}
      disabled={min || max ? fueraDeRango : undefined}
      onSelect={(dia) => {
        if (!dia) return;
        alCambiar(aTextoFecha(dia));
        setAbierto(false);
      }}
    />
  );

  return (
    <div className={cn("flex flex-col gap-1.5", claseContenedor)}>
      <Label htmlFor={id} className="text-base font-medium text-foreground">
        {etiqueta}
      </Label>
      {esMovil ? (
        <>
          {disparador}
          <Hoja abierta={abierto} alCambiar={setAbierto} titulo={etiqueta}>
            <div className="flex justify-center pb-2">{calendario("[--cell-size:--spacing(11)]")}</div>
          </Hoja>
        </>
      ) : (
        <Popover open={abierto} onOpenChange={setAbierto}>
          <PopoverTrigger render={disparador} />
          <PopoverContent align="start" className="w-auto max-w-[95vw] p-2">
            {calendario()}
          </PopoverContent>
        </Popover>
      )}
      {ayuda ? <p className="text-sm text-muted-foreground">{ayuda}</p> : null}
      {error ? (
        <p role="alert" className="flex items-start gap-1.5 text-sm font-medium text-destructive">
          <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          {error}
        </p>
      ) : null}
    </div>
  );
}
