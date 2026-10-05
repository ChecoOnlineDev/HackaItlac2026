import { Package } from "lucide-react";

import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";

// Pantalla pendiente: quien la construya reemplaza el estado vacío. No toca `routes.ts` ni los layouts.
export const handle: ManejadorRuta = { permiso: "catalogo.ver" };

export default function FichaArticulo() {
  return (
    <Pantalla titulo="Ficha de artículo" descripcion="Existencias por almacén y quién lo tiene.">
      <EstadoVacio
        icono={Package}
        titulo="Esta pantalla todavía no está lista"
        descripcion="Estamos construyéndola. Por ahora, regresa al inicio."
      />
    </Pantalla>
  );
}
