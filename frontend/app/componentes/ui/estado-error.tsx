import { cn } from "cn";
import { RefreshCwIcon, TriangleAlertIcon } from "lucide-react";

import { mensajeDeError } from "~/api/errores";
import { Boton } from "./boton";

interface PropiedadesEstadoError {
  /** El error tal cual llegó; se muestra su mensaje en español llano. */
  error?: unknown;
  /** Si no hay `error`, el texto a mostrar. */
  mensaje?: string;
  alReintentar?: () => void;
  className?: string;
}

/** Algo falló: mensaje en lenguaje llano y botón "Reintentar". */
export function EstadoError({ error, mensaje, alReintentar, className }: PropiedadesEstadoError) {
  const texto = mensaje ?? (error === undefined ? "No pudimos cargar esto." : mensajeDeError(error));
  return (
    <div
      role="alert"
      className={cn("flex flex-col items-center gap-3 rounded-2xl border bg-card p-6 text-center", className)}
    >
      <TriangleAlertIcon aria-hidden="true" className="size-7 text-marino" />
      <p className="max-w-sm text-base font-semibold text-marino">{texto}</p>
      {alReintentar ? (
        <Boton variante="secundario" onClick={alReintentar}>
          <RefreshCwIcon aria-hidden="true" />
          Reintentar
        </Boton>
      ) : null}
    </div>
  );
}
