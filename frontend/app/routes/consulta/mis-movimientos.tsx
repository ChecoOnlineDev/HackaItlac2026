import { History } from "lucide-react";

import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";

// Pantalla pendiente: quien la construya reemplaza el estado vacío. No toca `routes.ts` ni los layouts.
export const handle: ManejadorRuta = { permiso: "vales.ver" };

export default function MisMovimientos() {
  return (
    <Pantalla titulo="Mis movimientos de hoy" descripcion="Los vales que hiciste hoy, para corregir un error sin buscarlo.">
      <EstadoVacio
        icono={History}
        titulo="Esta pantalla todavía no está lista"
        descripcion="Estamos construyéndola. Por ahora, regresa al inicio."
      />
    </Pantalla>
  );
}
