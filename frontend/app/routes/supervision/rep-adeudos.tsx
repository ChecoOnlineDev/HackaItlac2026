import { FileBarChart } from "lucide-react";

import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";

// Pantalla pendiente: quien la construya reemplaza el estado vacío. No toca `routes.ts` ni los layouts.
export const handle: ManejadorRuta = { permiso: "reportes.adeudos" };

export default function ReporteAdeudos() {
  return (
    <Pantalla titulo="Reporte de adeudos" descripcion="Qué tiene cada trabajador en resguardo.">
      <EstadoVacio
        icono={FileBarChart}
        titulo="Esta pantalla todavía no está lista"
        descripcion="Estamos construyéndola. Por ahora, regresa al inicio."
      />
    </Pantalla>
  );
}
