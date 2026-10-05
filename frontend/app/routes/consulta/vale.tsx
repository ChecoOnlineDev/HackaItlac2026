import { useParams } from "react-router";

import { DetalleVale } from "~/componentes/entrega/detalle-vale";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";

export const handle: ManejadorRuta = { permiso: "vales.ver" };

export default function DetalleDeVale() {
  const { id = "" } = useParams();
  return (
    <Pantalla titulo="Detalle del vale" descripcion="Renglones, responsable y código QR del vale.">
      <DetalleVale ruta={`/vales/${encodeURIComponent(id)}`} />
    </Pantalla>
  );
}
