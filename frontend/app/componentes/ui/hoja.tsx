import { XIcon } from "lucide-react";
import type { ReactNode } from "react";

import { useIsMobile } from "~/hooks/use-mobile";
import { Sheet, SheetClose, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "~/components/ui/sheet";
import { Boton } from "./boton";

interface PropiedadesHoja {
  abierta: boolean;
  alCambiar: (abierta: boolean) => void;
  titulo: string;
  descripcion?: string;
  children?: ReactNode;
  /** Botones al pie; en celular quedan fijos abajo. */
  pie?: ReactNode;
}

/** Hoja que sube desde abajo en celular y entra por la derecha en computadora. Para observaciones y formularios cortos. */
export function Hoja({ abierta, alCambiar, titulo, descripcion, children, pie }: PropiedadesHoja) {
  const esMovil = useIsMobile();
  return (
    <Sheet open={abierta} onOpenChange={alCambiar}>
      <SheetContent
        side={esMovil ? "bottom" : "right"}
        showCloseButton={false}
        className="max-h-[92dvh] gap-0 rounded-t-3xl data-[side=right]:rounded-l-3xl data-[side=right]:rounded-r-none data-[side=right]:sm:max-w-md"
      >
        <SheetHeader className="flex-row items-start justify-between gap-3 border-b p-4">
          <div className="flex flex-col gap-1">
            <SheetTitle className="text-lg font-semibold text-marino">{titulo}</SheetTitle>
            {descripcion ? <SheetDescription className="text-sm">{descripcion}</SheetDescription> : null}
          </div>
          <SheetClose render={<Boton variante="texto" aria-label="Cerrar" className="-mr-2 -mt-1" />}>
            <XIcon aria-hidden="true" />
          </SheetClose>
        </SheetHeader>
        <div className="flex-1 overflow-y-auto p-4">{children}</div>
        {pie ? <SheetFooter className="border-t p-4 pb-[max(1rem,env(safe-area-inset-bottom))]">{pie}</SheetFooter> : null}
      </SheetContent>
    </Sheet>
  );
}
