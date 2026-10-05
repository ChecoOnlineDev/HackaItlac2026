import { useParams } from "react-router";

import { DetalleVale } from "~/componentes/entrega/detalle-vale";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";

// Con sesión en el MVP: si no la hay, el layout lleva a Entrar y regresa aquí al entrar.
export const handle: ManejadorRuta = { permiso: "vales.ver" };

export default function ValeDesdeQr() {
  const { token = "" } = useParams();
  return (
    <Pantalla titulo="Vale" descripcion="Vale abierto desde su código QR.">
      <DetalleVale ruta={`/vales/por-token/${encodeURIComponent(token)}`} />
    </Pantalla>
  );
}
