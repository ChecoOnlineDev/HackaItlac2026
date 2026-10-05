import { cn } from "cn";
import { CircleAlertIcon } from "lucide-react";
import { useId, type ComponentProps } from "react";

import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";

interface PropiedadesCampo extends ComponentProps<typeof Input> {
  etiqueta: string;
  /** Mensaje del error, escrito junto al campo. */
  error?: string | null;
  /** Texto de apoyo bajo el campo. */
  ayuda?: string;
  /** Clases del contenedor (no del campo). */
  claseContenedor?: string;
}

/** Etiqueta + campo de 48 px + error junto al campo. */
export function Campo({ etiqueta, error, ayuda, claseContenedor, id, className, ...props }: PropiedadesCampo) {
  const idGenerado = useId();
  const idCampo = id ?? idGenerado;
  const idError = `${idCampo}-error`;
  const idAyuda = `${idCampo}-ayuda`;
  const descripcion = [error ? idError : null, ayuda ? idAyuda : null].filter(Boolean).join(" ") || undefined;

  return (
    <div className={cn("flex flex-col gap-1.5", claseContenedor)}>
      <Label htmlFor={idCampo} className="text-sm font-medium text-foreground">
        {etiqueta}
      </Label>
      <Input
        id={idCampo}
        aria-invalid={error ? true : undefined}
        aria-describedby={descripcion}
        className={cn("h-11 px-3 text-base md:text-base", className)}
        {...props}
      />
      {ayuda ? (
        <p id={idAyuda} className="text-sm text-muted-foreground">
          {ayuda}
        </p>
      ) : null}
      {error ? (
        <p id={idError} role="alert" className="flex items-start gap-1.5 text-sm font-medium text-destructive">
          <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          {error}
        </p>
      ) : null}
    </div>
  );
}
