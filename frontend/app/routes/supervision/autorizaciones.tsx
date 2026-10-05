import { ShieldCheck } from "lucide-react";

import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";

// Pantalla pendiente: quien la construya reemplaza el estado vacío. No toca `routes.ts` ni los layouts.
export const handle: ManejadorRuta = { permiso: "autorizaciones.resolver" };

export default function Autorizaciones() {
  return (
    <Pantalla titulo="Autorizaciones" descripcion="Solicitudes que esperan tu decisión.">
      <EstadoVacio
        icono={ShieldCheck}
        titulo="Esta pantalla todavía no está lista"
        descripcion="Estamos construyéndola. Por ahora, regresa al inicio."
      />
    </Pantalla>
  );
}
