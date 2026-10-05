import { ClipboardList } from "lucide-react";

import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";

// Pantalla pendiente: quien la construya reemplaza el estado vacío. No toca `routes.ts` ni los layouts.
export const handle: ManejadorRuta = { permiso: "reportes.existencias" };

export default function ReporteExistencias() {
  return (
    <Pantalla titulo="Reporte de existencias" descripcion="Cuánto hay de cada artículo.">
      <EstadoVacio
        icono={ClipboardList}
        titulo="Esta pantalla todavía no está lista"
        descripcion="Estamos construyéndola. Por ahora, regresa al inicio."
      />
    </Pantalla>
  );
}
