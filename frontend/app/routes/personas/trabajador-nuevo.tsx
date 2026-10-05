import { UserPlus } from "lucide-react";

import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";

// Pantalla pendiente: quien la construya reemplaza el estado vacío. No toca `routes.ts` ni los layouts.
export const handle: ManejadorRuta = { permiso: "trabajadores.administrar" };

export default function AltaTrabajador() {
  return (
    <Pantalla titulo="Alta de trabajador" descripcion="Registra a una persona nueva o reingresa a una anterior.">
      <EstadoVacio
        icono={UserPlus}
        titulo="Esta pantalla todavía no está lista"
        descripcion="Estamos construyéndola. Por ahora, regresa al inicio."
      />
    </Pantalla>
  );
}
