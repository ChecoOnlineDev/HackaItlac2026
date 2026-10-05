import { apiGet } from "~/api/cliente";
import { esErrorApi } from "~/api/errores";
import type { ValeDetalleApi } from "~/componentes/entrega/tipos";
import type { TraspasoPorRecibirApi } from "./tipos";

/**
 * Qué traspaso abre el QR que se leyó: primero entre los que vienen en camino, y si no está ahí (otro
 * almacén, o ya recibido) se pregunta al servidor por el vale. Devuelve `null` si el QR no es de un traspaso.
 */
export async function idDeTraspasoPorToken(token: string, enCamino: TraspasoPorRecibirApi[] | null, signal?: AbortSignal): Promise<string | null> {
  const conocido = enCamino?.find((t) => t.token === token);
  if (conocido) return conocido.id;
  try {
    const vale = await apiGet<ValeDetalleApi>(`/vales/por-token/${encodeURIComponent(token)}`, undefined, signal);
    return vale.tipo === "TRASPASO" ? vale.id : null;
  } catch (causa) {
    if (esErrorApi(causa) && causa.status === 404) return null;
    throw causa;
  }
}
