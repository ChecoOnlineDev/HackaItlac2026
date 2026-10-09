import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { apiGet } from "~/api/cliente";
import { esErrorApi } from "~/api/errores";
import { esTraslado, type SolicitudCualquiera } from "~/componentes/consulta/tipos";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { TarjetaSolicitud } from "~/componentes/supervision/tarjeta-solicitud";
import { TarjetaTraslado } from "~/componentes/supervision/tarjeta-traslado";
import type { SolicitudCerrada } from "~/componentes/supervision/use-solicitudes";
import { Cargando } from "~/componentes/ui/cargando";
import { EstadoError } from "~/componentes/ui/estado-error";
import { useSesion } from "~/sesion/sesion";

export const handle: ManejadorRuta = { dispositivo: "celular", permisosAlguno: ["autorizaciones.resolver", "entregas.crear", "traspasos.operar"] };
type Detalle = SolicitudCualquiera & { resuelta_por?: { nombre: string } | null };
export default function DetalleAutorizacion() {
  const { id = "" } = useParams();
  const { puede, sesion } = useSesion();
  const [solicitud, setSolicitud] = useState<Detalle | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [ahora, setAhora] = useState(Date.now());
  const cargar = useCallback(async (signal?: AbortSignal) => {
    try { const r = await apiGet<Detalle>(`/autorizaciones/${encodeURIComponent(id)}`, undefined, signal); if (!signal?.aborted) { setSolicitud({ ...r, recibido_en: Date.now() }); setError(null); } }
    catch (e) { if (!signal?.aborted) setError(e); }
  }, [id]);
  useEffect(() => { const control = new AbortController(); setSolicitud(null); void cargar(control.signal); const t = window.setInterval(() => { setAhora(Date.now()); if (document.visibilityState === "visible") void cargar(control.signal); }, 3000); return () => { control.abort(); clearInterval(t); }; }, [cargar]);
  const cierre: SolicitudCerrada | undefined = solicitud && solicitud.estado !== "PENDIENTE" ? { solicitud, estado: solicitud.estado, por: solicitud.resuelta_por?.nombre ?? null } : undefined;
  return <Pantalla titulo="Solicitud de autorización" ancho="formulario">
    <Link to={puede("autorizaciones.resolver") ? "/autorizaciones" : puede("entregas.crear") ? "/entregar" : "/trasladar"} className="text-sm underline">{puede("autorizaciones.resolver") ? "Volver a autorizaciones" : "Volver a la captura"}</Link>
    {error ? esErrorApi(error) && error.status === 404 ? <p role="alert">Ya no puedes ver esta solicitud.</p> : <EstadoError error={error} alReintentar={() => void cargar()} /> : null}
    {!solicitud && !error ? <Cargando /> : null}
    {solicitud ? esTraslado(solicitud) ? <TarjetaTraslado solicitud={solicitud} ahora={ahora} cierre={cierre} esPropia={!puede("autorizaciones.resolver") || solicitud.solicitada_por.id === sesion?.usuario.id} alResolver={() => void cargar()} alRefrescar={() => void cargar()} /> : <TarjetaSolicitud solicitud={solicitud} ahora={ahora} cierre={cierre} puedeVerTrabajador={puede("trabajadores.ver")} esPropia={!puede("autorizaciones.resolver") || solicitud.solicitada_por.id === sesion?.usuario.id} alResolver={() => void cargar()} alRefrescar={() => void cargar()} /> : null}
  </Pantalla>;
}
