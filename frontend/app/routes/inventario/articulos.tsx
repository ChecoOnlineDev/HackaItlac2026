import { Package } from "lucide-react";

import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";

// Pantalla pendiente: quien la construya reemplaza el estado vacío. No toca `routes.ts` ni los layouts.
export const handle: ManejadorRuta = { permiso: "catalogo.administrar" };

export default function Articulos() {
  return (
    <Pantalla titulo="Artículos" descripcion="Catálogo de herramientas y equipo de protección.">
      <EstadoVacio
        icono={Package}
        titulo="Esta pantalla todavía no está lista"
        descripcion="Estamos construyéndola. Por ahora, regresa al inicio."
      />
    </Pantalla>
  );
}
