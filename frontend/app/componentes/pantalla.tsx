import { cn } from "cn";
import { useEffect, type ReactNode } from "react";
import type { UIMatch } from "react-router";

import type { Permiso } from "~/api/tipos";

/**
 * Lo que cada pantalla declara en `export const handle`. La guardia de rutas lo lee:
 * si el usuario no tiene el permiso, ve "Tu rol no puede hacer esto". El servidor
 * vuelve a verificar el permiso en cada endpoint; esto solo evita mostrar lo que no aplica.
 */
export interface ManejadorRuta {
  /** Debe tener este permiso. */
  permiso?: Permiso;
  /** Basta con tener uno de estos. */
  permisosAlguno?: readonly Permiso[];
}

export function manejadorDe(match: UIMatch): ManejadorRuta | undefined {
  return match.handle as ManejadorRuta | undefined;
}

interface PropiedadesPantalla {
  titulo: string;
  descripcion?: string;
  /** Botones junto al título (en computadora) como "Nuevo". */
  acciones?: ReactNode;
  /** `formulario` limita el ancho a 720 px; `completo` ocupa todo el ancho (tablas). */
  ancho?: "formulario" | "completo";
  children?: ReactNode;
}

/** Marco de una pantalla: título de 24 px, descripción corta y contenido. */
export function Pantalla({ titulo, descripcion, acciones, ancho = "completo", children }: PropiedadesPantalla) {
  useEffect(() => {
    document.title = `${titulo} · IMHOTEP`;
  }, [titulo]);

  return (
    <section className={cn("flex flex-col gap-6", ancho === "formulario" && "max-w-[720px]")}>
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 flex-col gap-1">
          <h1>{titulo}</h1>
          {descripcion ? <p className="text-muted-foreground">{descripcion}</p> : null}
        </div>
        {acciones ? <div className="flex items-center gap-2">{acciones}</div> : null}
      </header>
      {children}
    </section>
  );
}

/**
 * Barra con la acción principal de un flujo ("Continuar", "Confirmar entrega").
 * En celular queda fija en la parte baja; en computadora va al final del contenido.
 */
export function AccionPrincipal({ children, nota }: { children: ReactNode; nota?: ReactNode }) {
  return (
    <div className="fixed inset-x-0 bottom-0 z-30 flex flex-col gap-2 border-t bg-background p-4 pb-[max(1rem,env(safe-area-inset-bottom))] lg:static lg:mt-2 lg:border-0 lg:p-0">
      {nota ? <p className="text-center text-sm text-muted-foreground">{nota}</p> : null}
      {children}
    </div>
  );
}
