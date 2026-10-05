import { PackageCheck } from "lucide-react";

import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";

// Pantalla pendiente: quien la construya reemplaza el estado vacío. No toca `routes.ts` ni los layouts.
export const handle: ManejadorRuta = { permiso: "entregas.crear" };

export default function Entregar() {
  return (
    <Pantalla titulo="Entregar" descripcion="Entrega equipo o material a un trabajador y emite su vale.">
      <EstadoVacio
        icono={PackageCheck}
        titulo="Esta pantalla todavía no está lista"
        descripcion="Estamos construyéndola. Por ahora, regresa al inicio."
      />
    </Pantalla>
  );
}
