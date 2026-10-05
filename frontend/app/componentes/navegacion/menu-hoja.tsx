import { Link } from "react-router";

import { Hoja } from "~/componentes/ui/hoja";
import { agruparMenu, menuPermitido } from "~/sesion/menu";
import { useSesion } from "~/sesion/sesion";

/** Menú completo en una hoja (celular y tableta): todas las secciones que permiten los permisos. */
export function MenuHoja({ abierta, alCambiar }: { abierta: boolean; alCambiar: (abierta: boolean) => void }) {
  const { puedeAlguno } = useSesion();
  const grupos = agruparMenu(menuPermitido(puedeAlguno));
  return (
    <Hoja abierta={abierta} alCambiar={alCambiar} titulo="Menú">
      <nav aria-label="Secciones" className="flex flex-col gap-5">
        {grupos.map(({ grupo, elementos }) => (
          <div key={grupo} className="flex flex-col gap-1">
            <h2 className="text-sm font-semibold tracking-wide text-muted-foreground uppercase">{grupo}</h2>
            {elementos.map((e) => (
              <Link
                key={e.id}
                to={e.ruta}
                onClick={() => alCambiar(false)}
                className="flex min-h-12 items-center gap-3 rounded-lg px-3 text-base font-medium hover:bg-accent"
              >
                <e.icono aria-hidden="true" className="size-5 text-primary" />
                {e.titulo}
              </Link>
            ))}
          </div>
        ))}
      </nav>
    </Hoja>
  );
}
