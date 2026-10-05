import { cn } from "cn";

type VarianteCargando = "pantalla" | "boton" | "en-linea";

interface PropiedadesCargando {
  /**
   * - `pantalla`: logotipo de IMHOTEP con tres puntos que brincan; ocupa toda la pantalla.
   * - `boton`: solo los tres puntos, del color del texto; para dentro de un botón.
   * - `en-linea`: puntos y, si se da, un texto corto; para una sección que carga.
   */
  variante?: VarianteCargando;
  texto?: string;
  className?: string;
}

function Puntos({ className }: { className?: string }) {
  return (
    <span aria-hidden="true" className={cn("inline-flex items-end gap-[0.35em]", className)}>
      <span className="punto-cargando" />
      <span className="punto-cargando" />
      <span className="punto-cargando" />
    </span>
  );
}

/** Indicador de carga de IMHOTEP. Respeta `prefers-reduced-motion` con un parpadeo suave. */
export function Cargando({ variante = "en-linea", texto, className }: PropiedadesCargando) {
  if (variante === "boton") {
    return (
      <span role="status" aria-label={texto ?? "Cargando"} className={cn("inline-flex items-center", className)}>
        <Puntos className="text-[0.5rem]" />
      </span>
    );
  }

  if (variante === "pantalla") {
    return (
      <div
        role="status"
        aria-label={texto ?? "Cargando"}
        className={cn("flex min-h-dvh flex-col items-center justify-center gap-8 bg-background p-6", className)}
      >
        <img src="/logo-imhotep.png" alt="" width={160} height={151} className="h-auto w-40" />
        <Puntos className="text-primary text-[0.9rem]" />
        {texto ? <p className="text-muted-foreground">{texto}</p> : null}
      </div>
    );
  }

  return (
    <div
      role="status"
      aria-label={texto ?? "Cargando"}
      className={cn("flex items-center justify-center gap-3 p-6 text-muted-foreground", className)}
    >
      <Puntos className="text-primary text-[0.7rem]" />
      {texto ? <span>{texto}</span> : null}
    </div>
  );
}
