import { cn } from "cn";
import { InboxIcon, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "~/components/ui/empty";

interface PropiedadesEstadoVacio {
  titulo: string;
  descripcion?: string;
  icono?: LucideIcon;
  /** Acción sugerida, por ejemplo un `<Boton>`. */
  accion?: ReactNode;
  className?: string;
}

/** Lista o pantalla sin contenido: mensaje y acción sugerida ("No hay traspasos por recibir"). */
export function EstadoVacio({ titulo, descripcion, icono: Icono = InboxIcon, accion, className }: PropiedadesEstadoVacio) {
  return (
    <Empty className={cn("border py-10", className)}>
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <Icono aria-hidden="true" />
        </EmptyMedia>
        <EmptyTitle className="text-lg font-semibold text-marino">{titulo}</EmptyTitle>
        {descripcion ? <EmptyDescription className="text-base">{descripcion}</EmptyDescription> : null}
      </EmptyHeader>
      {accion ? <EmptyContent>{accion}</EmptyContent> : null}
    </Empty>
  );
}
