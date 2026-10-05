import { cn } from "cn";
import { useId, type ReactNode } from "react";

interface PropiedadesCampoSelect {
  etiqueta: ReactNode;
  ayuda?: string;
  valor: string;
  alCambiar: (valor: string) => void;
  opciones: { valor: string; texto: string }[];
  /** Texto de la opción vacía (valor ""). */
  vacio?: string;
  deshabilitado?: boolean;
  className?: string;
}

/** Etiqueta + lista desplegable de 48 px, del mismo estilo que el selector de almacén. */
export function CampoSelect({ etiqueta, ayuda, valor, alCambiar, opciones, vacio, deshabilitado, className }: PropiedadesCampoSelect) {
  const id = useId();
  return (
    <div className={cn("flex min-w-0 flex-col gap-1.5", className)}>
      <label htmlFor={id} className="text-base font-medium">
        {etiqueta}
      </label>
      <select
        id={id}
        value={valor}
        disabled={deshabilitado}
        aria-describedby={ayuda ? `${id}-ayuda` : undefined}
        onChange={(e) => alCambiar(e.target.value)}
        className="h-12 w-full min-w-0 rounded-lg border border-input bg-background px-3 text-base disabled:opacity-60"
      >
        {vacio !== undefined ? <option value="">{vacio}</option> : null}
        {opciones.map((o) => (
          <option key={o.valor} value={o.valor}>
            {o.texto}
          </option>
        ))}
      </select>
      {ayuda ? (
        <p id={`${id}-ayuda`} className="text-sm text-muted-foreground">
          {ayuda}
        </p>
      ) : null}
    </div>
  );
}
