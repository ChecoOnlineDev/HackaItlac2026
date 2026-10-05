import { Inbox } from "lucide-react";

import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";

// Pantalla pendiente: quien la construya reemplaza el estado vacío. No toca `routes.ts` ni los layouts.
export const handle: ManejadorRuta = { permiso: "traspasos.operar" };

export default function Recibir() {
  return (
    <Pantalla titulo="Recibir" descripcion="Traspasos que vienen en camino a este almacén.">
      <EstadoVacio
        icono={Inbox}
        titulo="Esta pantalla todavía no está lista"
        descripcion="Estamos construyéndola. Por ahora, regresa al inicio."
      />
    </Pantalla>
  );
}
