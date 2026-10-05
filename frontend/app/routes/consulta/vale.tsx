import { FileText } from "lucide-react";

import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";

// Pantalla pendiente: quien la construya reemplaza el estado vacío. No toca `routes.ts` ni los layouts.
export const handle: ManejadorRuta = { permiso: "vales.ver" };

export default function DetalleVale() {
  return (
    <Pantalla titulo="Detalle del vale" descripcion="Renglones, firma, responsable y opciones para cancelarlo.">
      <EstadoVacio
        icono={FileText}
        titulo="Esta pantalla todavía no está lista"
        descripcion="Estamos construyéndola. Por ahora, regresa al inicio."
      />
    </Pantalla>
  );
}
