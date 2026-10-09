import { cn } from "cn";
import { CircleAlertIcon, TriangleAlertIcon } from "lucide-react";
import { useId } from "react";

import { Textarea } from "~/components/ui/textarea";
import { Boton } from "~/componentes/ui/boton";

/** Respuestas frecuentes para explicar un traslado entre proyectos que autoriza quien lo envía (X-16). */
export const RESPUESTAS_RAPIDAS_TRASLADO = ["Les sobra a nosotros y les hace falta", "Para una obra que arranca", "Para devolver prestado", "Otro motivo"] as const;

/** Respuestas frecuentes para explicar un traspaso por una ruta poco habitual (X-03). */
export const RESPUESTAS_RAPIDAS_RUTA = ["Para surtir una urgencia", "Para regresar sobrante", "Se corrige una ruta anterior", "Otro motivo"] as const;

const LARGO_MAXIMO = 300;

interface PropiedadesObservacionRuta {
  valor: string;
  alCambiar: (texto: string) => void;
  /** Error del servidor junto al campo (422 con la regla X-03). */
  error?: string | null;
  deshabilitado?: boolean;
  className?: string;
  /** Por omisión, el texto de la ruta poco habitual (X-03). El servidor decide cuándo se pide y por qué regla. */
  titulo?: string;
  descripcion?: string;
  respuestas?: readonly string[];
}

/**
 * «¿Por qué se envía por esta ruta?»: la pide el servidor cuando el traspaso no es de un almacén a su padre ni
 * a su hijo y quien lo hace es un administrador (X-03). Solo captura el texto; no evalúa nada.
 */
export function ObservacionRuta({
  valor,
  alCambiar,
  error,
  deshabilitado,
  className,
  titulo = "¿Por qué se envía por esta ruta?",
  descripcion = "Este envío no va entre un almacén y el que lo surte o el que depende de él. Anota el motivo para poder confirmarlo.",
  respuestas = RESPUESTAS_RAPIDAS_RUTA,
}: PropiedadesObservacionRuta) {
  const id = useId();
  const vacia = valor.trim().length === 0;
  return (
    <section aria-labelledby={`${id}-titulo`} className={cn("flex flex-col gap-3 rounded-2xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-4", className)}>
      <div className="flex flex-col gap-1">
        <h2 id={`${id}-titulo`} className="flex items-center gap-2 text-lg">
          <TriangleAlertIcon aria-hidden="true" className="size-5 shrink-0 text-semaforo-amarillo" strokeWidth={2.5} />
          <label htmlFor={`${id}-texto`}>{titulo}</label>
        </h2>
        <p className="text-sm text-muted-foreground">{descripcion}</p>
      </div>
      <div className="flex flex-col gap-1.5">
        <Textarea
          id={`${id}-texto`}
          value={valor}
          maxLength={LARGO_MAXIMO}
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
        {error ? (
          <p id={`${id}-error`} role="alert" className="flex items-start gap-1.5 text-sm font-medium text-destructive">
            <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
            {error}
          </p>
        ) : null}
      </div>
      <div className="flex flex-wrap gap-2" aria-label="Respuestas rápidas">
        {respuestas.map((r) => (
          <Boton key={r} type="button" variante="contorno" disabled={deshabilitado} onClick={() => alCambiar(r)}>
            {r}
          </Boton>
        ))}
      </div>
    </section>
  );
}
