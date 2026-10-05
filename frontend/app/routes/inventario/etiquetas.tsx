import { Printer } from "lucide-react";

import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";

// Pantalla pendiente: quien la construya reemplaza el estado vacío. No toca `routes.ts` ni los layouts.
export const handle: ManejadorRuta = { permiso: "etiquetas.imprimir" };

export default function Etiquetas() {
  return (
    <Pantalla titulo="Etiquetas" descripcion="Hojas de códigos QR para imprimir.">
      <EstadoVacio
        icono={Printer}
        titulo="Esta pantalla todavía no está lista"
        descripcion="Estamos construyéndola. Por ahora, regresa al inicio."
      />
    </Pantalla>
  );
}
