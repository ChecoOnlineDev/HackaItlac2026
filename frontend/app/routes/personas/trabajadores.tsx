import { Users } from "lucide-react";

import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";

// Pantalla pendiente: quien la construya reemplaza el estado vacío. No toca `routes.ts` ni los layouts.
export const handle: ManejadorRuta = { permiso: "trabajadores.ver" };

export default function Trabajadores() {
  return (
    <Pantalla titulo="Trabajadores" descripcion="Busca por nombre o número y revisa su situación.">
      <EstadoVacio
        icono={Users}
        titulo="Esta pantalla todavía no está lista"
        descripcion="Estamos construyéndola. Por ahora, regresa al inicio."
      />
    </Pantalla>
  );
}
