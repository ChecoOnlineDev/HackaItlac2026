import { Navigate, useParams } from "react-router";

import { apiGet } from "~/api/cliente";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { DetalleVale } from "~/componentes/entrega/detalle-vale";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import type { PorRecibirApi } from "~/componentes/traspasos/tipos";
import { Cargando } from "~/componentes/ui/cargando";
import { useSesionActiva } from "~/sesion/sesion";

// Con sesión en el MVP: si no la hay, el layout lleva a Entrar y regresa aquí al entrar.
export const handle: ManejadorRuta = { permiso: "vales.ver" };

export default function ValeDesdeQr() {
  const { token = "" } = useParams();
  const { puede } = useSesionActiva();
  const operaTraspasos = puede("traspasos.operar");
  return operaTraspasos ? <ConRecepcion token={token} /> : <Vale token={token} />;
}

function Vale({ token }: { token: string }) {
  return (
    <Pantalla titulo="Vale" descripcion="Vale abierto desde su código QR.">
      <DetalleVale ruta={`/vales/por-token/${encodeURIComponent(token)}`} />
    </Pantalla>
  );
}

/**
 * Quien opera traspasos y escanea el QR de un traspaso que viene en camino a su almacén va directo a su
 * recepción. Con cualquier otro vale (o si la lista no carga) se abre el vale de siempre.
 */
function ConRecepcion({ token }: { token: string }) {
  const consulta = useConsulta((signal) => apiGet<PorRecibirApi>("/traspasos/por-recibir", undefined, signal), "por-recibir-qr");
  if (consulta.cargando && !consulta.datos) return <Cargando variante="en-linea" texto="Abriendo el vale…" />;
  const traspaso = consulta.datos?.elementos.find((t) => t.token === token);
  if (traspaso) return <Navigate to={`/recibir/${traspaso.id}`} replace />;
  return <Vale token={token} />;
}
