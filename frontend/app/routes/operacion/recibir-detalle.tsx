import { Inbox } from "lucide-react";

import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";

// Pantalla pendiente: quien la construya reemplaza el estado vacío. No toca `routes.ts` ni los layouts.
export const handle: ManejadorRuta = { permiso: "traspasos.operar" };

export default function RecibirTraspaso() {
  return (
    <Pantalla titulo="Recibir un traspaso" descripcion="Revisa lo que llegó y confirma la recepción.">
      <EstadoVacio
        icono={Inbox}
        titulo="Esta pantalla todavía no está lista"
        descripcion="Estamos construyéndola. Por ahora, regresa al inicio."
      />
    </Pantalla>
  );
}
