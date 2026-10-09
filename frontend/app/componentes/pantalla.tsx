import { cn } from "cn";
import { useEffect, type ReactNode } from "react";
import { useMatches, type UIMatch } from "react-router";

import type { Permiso } from "~/api/tipos";

/**
 * Lo que cada pantalla declara en `export const handle`. La guardia de rutas lo lee:
 * si el usuario no tiene el permiso, ve "Tu rol no puede hacer esto". El servidor
 * vuelve a verificar el permiso en cada endpoint; esto solo evita mostrar lo que no aplica.
 */
export interface ManejadorRuta {
  dispositivo?: "celular" | "computadora";
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

/** Marco de una pantalla: título, descripción corta y contenido. */
export function Pantalla({ titulo, descripcion, acciones, ancho, children }: PropiedadesPantalla) {
  const matches = useMatches();
  const dispositivo = [...matches].reverse().map(manejadorDe).find((h) => h?.dispositivo)?.dispositivo;
  const limitado = ancho === "formulario" || (ancho === undefined && dispositivo === "celular");
  useEffect(() => {
    document.title = `${titulo} · IMHOTEP`;
  }, [titulo]);

  return (
    <section className={cn("flex flex-col gap-5", limitado && "mx-auto w-full max-w-[720px]")}>
      <header className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
        <div className="flex min-w-0 flex-col gap-1 sm:flex-1">
          <h1 className="text-balance">{titulo}</h1>
          {descripcion ? <p className="text-sm text-muted-foreground">{descripcion}</p> : null}
        </div>
        {acciones ? <div className="flex flex-wrap items-center gap-2">{acciones}</div> : null}
      </header>
      {children}
    </section>
  );
}

/**
 * Barra con la acción principal de un flujo ("Continuar", "Confirmar entrega").
 * En celular y tableta queda fija en la parte baja, con el área segura del teléfono; en computadora va al final
 * del contenido. Aquí caben también las acciones secundarias ("No es esta persona"): siempre a la vista.
 */
export function AccionPrincipal({ children, nota }: { children: ReactNode; nota?: ReactNode }) {
  return (
    <div className="fixed inset-x-0 bottom-0 z-30 border-t bg-background/95 px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] shadow-[0_-4px_12px_rgb(0_0_0/0.05)] backdrop-blur lg:static lg:mt-2 lg:border-0 lg:bg-transparent lg:p-0 lg:shadow-none lg:backdrop-blur-none">
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-2">
        {nota ? <p className="text-center text-xs text-muted-foreground">{nota}</p> : null}
        {children}
      </div>
    </div>
  );
}
