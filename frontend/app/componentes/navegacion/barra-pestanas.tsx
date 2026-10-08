import { cn } from "cn";
import { Link } from "react-router";

import type { ElementoMenu } from "~/sesion/menu";
import { useContadores } from "~/sesion/contadores";

/**
 * Barra de pestañas compartida de una sección del menú (Inventario, Catálogo, Compras...). Cada pestaña es un
 * enlace a la URL de siempre de su pantalla; en el celular se desliza de lado. Ver ui-ux.md, «Pestañas por sección».
 */
export function BarraPestanas({ titulo, pestanas, activa }: { titulo: string; pestanas: readonly ElementoMenu[]; activa: string | null }) {
  const contadores = useContadores();
  return (
    <nav aria-label={titulo} className="-mx-4 mb-5 overflow-x-auto border-b px-4 sm:mx-0 sm:px-0">
      <ul className="flex min-w-max gap-1">
        {pestanas.map((p) => {
          const esActiva = p.id === activa;
          const cuenta = p.contador ? contadores[p.contador] : undefined;
          return (
            <li key={p.id}>
              <Link
                to={p.ruta}
                aria-current={esActiva ? "page" : undefined}
                className={cn(
                  "-mb-px flex min-h-11 items-center gap-2 border-b-2 px-3 text-sm whitespace-nowrap transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  esActiva
                    ? "border-primary font-semibold text-marino"
                    : "border-transparent font-medium text-muted-foreground hover:border-border hover:text-foreground",
                )}
              >
                {p.pestana ?? p.titulo}
                {cuenta ? (
                  <span className="rounded-full bg-primary px-1.5 text-xs font-semibold text-primary-foreground">{cuenta}</span>
                ) : null}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
