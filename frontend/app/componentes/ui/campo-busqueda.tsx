import { cn } from "cn";
import { SearchIcon } from "lucide-react";
import type { ComponentProps } from "react";

import { Input } from "~/components/ui/input";

interface PropiedadesCampoBusqueda extends Omit<ComponentProps<typeof Input>, "type" | "onChange" | "value"> {
  /** Lo que lee un lector de pantalla; el campo no muestra etiqueta, el icono y el texto de ayuda bastan. */
  etiqueta: string;
  value: string;
  alCambiar: (texto: string) => void;
  claseContenedor?: string;
}

/**
 * Búsqueda por texto: lupa, 44 px, siempre visible junto a los filtros. Es controlado: la pantalla guarda
 * el texto y lo pasa por `useRetraso` (300 ms) para consultar al dejar de escribir.
 */
export function CampoBusqueda({ etiqueta, value, alCambiar, claseContenedor, className, ...props }: PropiedadesCampoBusqueda) {
  return (
    <div className={cn("relative min-w-0 flex-1", claseContenedor)}>
      <SearchIcon aria-hidden="true" className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        type="search"
        aria-label={etiqueta}
        value={value}
        onChange={(e) => alCambiar(e.target.value)}
        autoComplete="off"
        className={cn("pl-9", className)}
        {...props}
      />
    </div>
  );
}
