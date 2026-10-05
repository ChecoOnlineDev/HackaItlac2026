import { User } from "lucide-react";

import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";

// Pantalla pendiente: quien la construya reemplaza el estado vacío. No toca `routes.ts` ni los layouts.
export const handle: ManejadorRuta = { permiso: "trabajadores.ver" };

export default function FichaTrabajador() {
  return (
    <Pantalla titulo="Ficha del trabajador" descripcion="Datos, vigencia, lo que tiene en resguardo y sus pendientes.">
      <EstadoVacio
        icono={User}
        titulo="Esta pantalla todavía no está lista"
        descripcion="Estamos construyéndola. Por ahora, regresa al inicio."
      />
    </Pantalla>
  );
}
