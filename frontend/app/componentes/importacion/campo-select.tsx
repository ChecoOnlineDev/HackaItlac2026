import { cn } from "cn";
import { useId, type ReactNode } from "react";

import { ListaDesplegable } from "~/componentes/ui/lista-desplegable";

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
      <ListaDesplegable
        id={id}
        valor={valor}
        alCambiar={alCambiar}
        opciones={opciones}
        vacio={vacio}
        deshabilitado={deshabilitado}
        descritoPor={ayuda ? `${id}-ayuda` : undefined}
      />
      {ayuda ? (
        <p id={`${id}-ayuda`} className="text-sm text-muted-foreground">
          {ayuda}
        </p>
      ) : null}
    </div>
  );
}
