import { cn } from "cn";
import { CircleAlertIcon, TriangleAlertIcon } from "lucide-react";
import { useId } from "react";

import { Textarea } from "~/components/ui/textarea";
import { Boton } from "~/componentes/ui/boton";

/** Respuestas frecuentes para explicar una entrega fuera de la dotación (E-09). */
export const RESPUESTAS_RAPIDAS_ENTREGA = ["Se mojaron", "Se llenaron de grasa", "Se perdieron", "Desgaste por uso", "Otro motivo"] as const;

/** Largo máximo de la observación de una entrega (el servidor admite hasta 1000). */
export const LARGO_OBSERVACION_ENTREGA = 200;

interface PropiedadesObservacionEntrega {
  valor: string;
  alCambiar: (texto: string) => void;
  /** Por qué se pide, con las palabras del servidor. */
  motivos?: string[];
  /** Error del servidor junto al campo (422 con la regla E-09). */
  error?: string | null;
  deshabilitado?: boolean;
  className?: string;
}

/**
 * "¿Por qué se entrega esto?": campo corto y obligatorio cuando el servidor pide observación (E-09).
 * Las respuestas rápidas rellenan el campo y se pueden editar. No evalúa nada: solo captura el texto.
 */
export function ObservacionEntrega({ valor, alCambiar, motivos, error, deshabilitado, className }: PropiedadesObservacionEntrega) {
  const id = useId();
  const vacia = valor.trim().length === 0;
  return (
    <section aria-labelledby={`${id}-titulo`} className={cn("flex flex-col gap-3 rounded-2xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-4", className)}>
      <div className="flex flex-col gap-1">
        <h2 id={`${id}-titulo`} className="flex items-center gap-2 text-lg">
          <TriangleAlertIcon aria-hidden="true" className="size-5 shrink-0 text-semaforo-amarillo" strokeWidth={2.5} />
          <label htmlFor={`${id}-texto`}>¿Por qué se entrega esto?</label>
        </h2>
        <p className="text-sm text-muted-foreground">
          {motivos && motivos.length > 0 ? `${motivos[0]} ` : "Se entrega algo que no está en su dotación o pasa de lo recomendado. "}
          Anota el motivo para poder confirmar.
        </p>
      </div>

      <div className="flex flex-col gap-1.5">
        <Textarea
          id={`${id}-texto`}
          value={valor}
          maxLength={LARGO_OBSERVACION_ENTREGA}
          rows={2}
          disabled={deshabilitado}
          onChange={(e) => alCambiar(e.target.value)}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${id}-error` : undefined}
          placeholder="Escribe el motivo"
          className={cn(
            "min-h-20 w-full resize-y rounded-xl border border-input bg-background px-3 py-2 text-base outline-none placeholder:text-muted-foreground",
            "focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50",
            (error || vacia) && "border-semaforo-amarillo",
            error && "border-destructive",
          )}
        />
        <p className="text-right text-xs text-muted-foreground tabular-nums">
          {valor.length} de {LARGO_OBSERVACION_ENTREGA}
        </p>
        {error ? (
          <p id={`${id}-error`} role="alert" className="flex items-start gap-1.5 text-sm font-medium text-destructive">
            <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
            {error}
          </p>
        ) : null}
      </div>

      <div className="flex flex-col gap-2">
        <p className="text-sm font-medium text-muted-foreground">Respuestas rápidas</p>
        <div className="flex flex-wrap gap-2">
          {RESPUESTAS_RAPIDAS_ENTREGA.map((r) => (
            <Boton
              key={r}
              variante="contorno"
              disabled={deshabilitado}
              aria-pressed={valor === r}
              className={cn("h-10 rounded-full px-4 text-sm", valor === r && "border-primary bg-accent")}
              onClick={() => alCambiar(r)}
            >
              {r}
            </Boton>
          ))}
        </div>
      </div>
    </section>
  );
}
