import { SearchXIcon } from "lucide-react";
import { Link } from "react-router";

import { Pantalla } from "~/componentes/pantalla";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { buttonVariants } from "~/components/ui/button";

export default function NoEncontrada() {
  return (
    <Pantalla titulo="No encontramos esa pantalla">
      <EstadoVacio
        icono={SearchXIcon}
        titulo="Esa dirección no existe"
        descripcion="Revisa que esté bien escrita o regresa al inicio."
        accion={
          <Link to="/" className={buttonVariants({ size: "toque" })}>
            Ir al inicio
          </Link>
        }
      />
    </Pantalla>
  );
}
