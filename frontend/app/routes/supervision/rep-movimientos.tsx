import { FileBarChart } from "lucide-react";

import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";

// Pantalla pendiente: quien la construya reemplaza el estado vacío. No toca `routes.ts` ni los layouts.
export const handle: ManejadorRuta = { permiso: "reportes.movimientos" };

export default function ReporteMovimientos() {
  return (
    <Pantalla titulo="Reporte de movimientos" descripcion="Qué se movió, cuándo y quién lo hizo.">
      <EstadoVacio
        icono={FileBarChart}
        titulo="Esta pantalla todavía no está lista"
        descripcion="Estamos construyéndola. Por ahora, regresa al inicio."
      />
    </Pantalla>
  );
}
