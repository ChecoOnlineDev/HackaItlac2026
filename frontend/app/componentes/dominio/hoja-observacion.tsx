import { cn } from "cn";
import { CircleAlertIcon, InfoIcon } from "lucide-react";
import { useEffect, useId, useState } from "react";

import { Boton } from "~/componentes/ui/boton";
import { Hoja } from "~/componentes/ui/hoja";

interface PropiedadesHojaObservacion {
  abierta: boolean;
  alCambiar: (abierta: boolean) => void;
  /** Por qué se pide, con las palabras del servidor: "Pide observación: equipo de alturas." */
  motivo: string;
  /** ID de la regla que la pide (por ejemplo `E-19`), opcional. */
  regla?: string;
  /** Texto con el que abre (para editar una observación ya capturada). */
  valorInicial?: string;
  /** Respuestas frecuentes; al tocar una se escribe en el campo. */
  respuestasRapidas?: string[];
  /** `true` por omisión: no se puede guardar vacía. */
  obligatoria?: boolean;
  titulo?: string;
  etiquetaGuardar?: string;
  /** Recibe el texto ya sin espacios sobrantes. */
  alGuardar: (texto: string) => void;
  maxLargo?: number;
}

/**
 * Hoja que sube desde abajo con el motivo que la pide, un campo de texto y respuestas rápidas.
 *
 * ```tsx
 * <HojaObservacion abierta={abierta} alCambiar={setAbierta} motivo={motivo.mensaje} alGuardar={guardar} />
 * ```
 */
export function HojaObservacion({
  abierta,
  alCambiar,
  motivo,
  regla,
  valorInicial = "",
  respuestasRapidas,
  obligatoria = true,
  titulo = "Observación",
  etiquetaGuardar = "Guardar observación",
  alGuardar,
  maxLargo = 300,
}: PropiedadesHojaObservacion) {
  const [texto, setTexto] = useState(valorInicial);
  const [intento, setIntento] = useState(false);
  const id = useId();

  useEffect(() => {
    if (abierta) {
      setTexto(valorInicial);
      setIntento(false);
    }
  }, [abierta, valorInicial]);

  const limpio = texto.trim();
  const error = obligatoria && intento && !limpio ? "Escribe la observación para continuar." : null;

  const guardar = () => {
    setIntento(true);
    if (obligatoria && !limpio) return;
    alGuardar(limpio);
    alCambiar(false);
  };

  return (
    <Hoja
      abierta={abierta}
      alCambiar={alCambiar}
      titulo={titulo}
      pie={
        <Boton variante="principal" onClick={guardar}>
          {etiquetaGuardar}
        </Boton>
      }
    >
      <div className="flex flex-col gap-4">
        <p className="flex items-start gap-2 rounded-lg border bg-muted p-3 text-base">
          <InfoIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-marino" />
          <span>
            {motivo}
            {regla ? <span className="ml-1.5 text-xs font-medium whitespace-nowrap text-muted-foreground">({regla})</span> : null}
          </span>
        </p>

        <div className="flex flex-col gap-1.5">
          <label htmlFor={`${id}-texto`} className="text-base font-medium">
            ¿Qué debemos anotar?
          </label>
          <textarea
            id={`${id}-texto`}
            value={texto}
            maxLength={maxLargo}
            rows={4}
            onChange={(e) => setTexto(e.target.value)}
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? `${id}-error` : undefined}
            placeholder="Escribe aquí"
            className={cn(
              "min-h-28 w-full resize-y rounded-lg border border-input bg-background px-3 py-2 text-base outline-none placeholder:text-muted-foreground",
              "focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50",
              error && "border-destructive",
            )}
          />
          <p className="text-right text-xs text-muted-foreground">
            {texto.length} de {maxLargo}
          </p>
          {error ? (
            <p id={`${id}-error`} role="alert" className="flex items-start gap-1.5 text-sm font-medium text-destructive">
              <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
              {error}
            </p>
          ) : null}
        </div>

        {respuestasRapidas && respuestasRapidas.length > 0 ? (
          <div className="flex flex-col gap-2">
            <p className="text-sm font-medium text-muted-foreground">Respuestas rápidas</p>
            <div className="flex flex-wrap gap-2">
              {respuestasRapidas.map((r) => (
                <Boton key={r} variante="contorno" className="h-10 px-3 text-sm" onClick={() => setTexto(r)}>
                  {r}
                </Boton>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </Hoja>
  );
}
