import { PackagePlus } from "lucide-react";

import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";

// Pantalla pendiente: quien la construya reemplaza el estado vacío. No toca `routes.ts` ni los layouts.
export const handle: ManejadorRuta = { permiso: "inventario.entradas" };

export default function EntradaNueva() {
  return (
    <Pantalla titulo="Nueva entrada" descripcion="Registra lo que llega al almacén.">
      <EstadoVacio
        icono={PackagePlus}
        titulo="Esta pantalla todavía no está lista"
        descripcion="Estamos construyéndola. Por ahora, regresa al inicio."
      />
    </Pantalla>
  );
}
