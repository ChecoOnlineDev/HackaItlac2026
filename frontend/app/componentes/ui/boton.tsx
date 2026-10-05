import { cn } from "cn";
import type { ComponentProps } from "react";

import { Button } from "~/components/ui/button";
import { Cargando } from "./cargando";

type VarianteBoton = "principal" | "normal" | "secundario" | "contorno" | "texto" | "peligro";

interface PropiedadesBoton extends Omit<ComponentProps<typeof Button>, "variant" | "size"> {
  /**
   * - `principal`: la acción de la pantalla; 48 px y a todo el ancho. Una por pantalla.
   * - `normal`: acción azul de 40 px (por ejemplo "Sí, confirmar" en una ventana).
   * - `secundario`: acción de apoyo, 40 px, azul suave.
   * - `contorno`: acción neutra, 40 px, con borde.
   * - `texto`: sin fondo, para "Atrás" o "Cancelar".
   * - `peligro`: acción que no se deshace.
   */
  variante?: VarianteBoton;
  /** Muestra los tres puntos, deshabilita el botón y evita un segundo toque. */
  cargando?: boolean;
}

const MAPA: Record<VarianteBoton, { variant: ComponentProps<typeof Button>["variant"]; size: ComponentProps<typeof Button>["size"] }> = {
  principal: { variant: "default", size: "principal" },
  normal: { variant: "default", size: "toque" },
  secundario: { variant: "secondary", size: "toque" },
  contorno: { variant: "outline", size: "toque" },
  texto: { variant: "ghost", size: "toque" },
  peligro: { variant: "destructive", size: "toque" },
};

export function Boton({ variante = "contorno", cargando = false, disabled, className, children, ...props }: PropiedadesBoton) {
  const { variant, size } = MAPA[variante];
  return (
    <Button
      variant={variant}
      size={size}
      disabled={disabled || cargando}
      aria-busy={cargando || undefined}
      className={cn(variante === "peligro" && "font-semibold", className)}
      {...props}
    >
      {cargando ? <Cargando variante="boton" /> : null}
      {children}
    </Button>
  );
}
