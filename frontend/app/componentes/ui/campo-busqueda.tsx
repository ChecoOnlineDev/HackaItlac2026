import { cn } from "cn";
import { SearchIcon, XIcon } from "lucide-react";
import type { ComponentProps } from "react";
import type { EstadoBusqueda } from "./busqueda-diferida";

import { Input } from "~/components/ui/input";

interface PropiedadesCampoBusqueda extends Omit<ComponentProps<typeof Input>, "type" | "onChange" | "value"> {
  /** Lo que lee un lector de pantalla; el campo no muestra etiqueta, el icono y el texto de ayuda bastan. */
  etiqueta: string;
  value: string;
  alCambiar: (texto: string) => void;
  claseContenedor?: string;
  estado?: EstadoBusqueda;
  alEnviar?: () => void;
}

/**
 * Búsqueda por texto: lupa, 44 px, siempre visible junto a los filtros. Es controlado: la pantalla guarda
 * el texto y lo pasa por `useRetraso` (300 ms) para consultar al dejar de escribir.
 */
export function CampoBusqueda({ etiqueta, value, alCambiar, claseContenedor, className, estado, alEnviar, onKeyDown, ...props }: PropiedadesCampoBusqueda) {
  return (
    <div className={cn("relative min-w-0 flex-1", claseContenedor)}>
      <SearchIcon aria-hidden="true" className="pointer-events-none absolute top-[22px] left-3 size-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        type="search"
        aria-label={etiqueta}
        value={value}
        onChange={(e) => alCambiar(e.target.value)}
        autoComplete="off"
        onKeyDown={(e) => { onKeyDown?.(e); if (e.key === "Enter" && alEnviar) { e.preventDefault(); alEnviar(); } }}
        className={cn("min-h-11 pl-9 pr-11 [&::-webkit-search-cancel-button]:appearance-none", className)}
        {...props}
      />
      {value ? <button type="button" aria-label="Borrar búsqueda" className="absolute top-0 right-0 flex size-11 items-center justify-center rounded-lg focus-visible:ring-2 focus-visible:ring-ring" onClick={(e) => { alCambiar(""); e.currentTarget.parentElement?.querySelector("input")?.focus(); }}><XIcon aria-hidden="true" className="size-4" /></button> : null}
      {estado === "corto" || estado === "buscando" || estado === "sin_conexion" ? <p role="status" className="mt-1 text-sm text-muted-foreground">{estado === "corto" ? "Escribe al menos 2 letras o números." : estado === "buscando" ? "Buscando…" : "Sin conexión. Escanea el código o inténtalo cuando vuelva la señal."}</p> : null}
    </div>
  );
}
