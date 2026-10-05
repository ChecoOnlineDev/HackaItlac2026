import { Wrench } from "lucide-react";

import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";

// Pantalla pendiente: quien la construya reemplaza el estado vacío. No toca `routes.ts` ni los layouts.
export const handle: ManejadorRuta = { permiso: "catalogo.ver" };

export default function FichaPieza() {
  return (
    <Pantalla titulo="Ficha de pieza" descripcion="Estado, inspección, ubicación e historial de la pieza.">
      <EstadoVacio
        icono={Wrench}
        titulo="Esta pantalla todavía no está lista"
        descripcion="Estamos construyéndola. Por ahora, regresa al inicio."
      />
    </Pantalla>
  );
}
