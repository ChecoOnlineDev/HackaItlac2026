import { FileBarChart } from "lucide-react";

import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";

// Pantalla pendiente: quien la construya reemplaza el estado vacío. No toca `routes.ts` ni los layouts.
export const handle: ManejadorRuta = { permiso: "reportes.consumo" };

export default function ReporteConsumo() {
  return (
    <Pantalla titulo="Reporte de consumo" descripcion="Cuánto se ha consumido por artículo.">
      <EstadoVacio
        icono={FileBarChart}
        titulo="Esta pantalla todavía no está lista"
        descripcion="Estamos construyéndola. Por ahora, regresa al inicio."
      />
    </Pantalla>
  );
}
