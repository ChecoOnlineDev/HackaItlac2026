import { Navigate, Outlet, useLocation, useMatches } from "react-router";

import { SinPermiso } from "~/componentes/navegacion/sin-permiso";
import { ArmazonEscritorio } from "~/componentes/navegacion/armazon-escritorio";
import { ArmazonMovil } from "~/componentes/navegacion/armazon-movil";
import { manejadorDe } from "~/componentes/pantalla";
import { Cargando } from "~/componentes/ui/cargando";
import { useEsEscritorio } from "~/hooks/use-escritorio";
import { ContadoresProvider } from "~/sesion/contadores";
import { useSesion } from "~/sesion/sesion";

/**
 * Layout de toda la aplicación con sesión. Aquí viven la guardia de rutas y el armazón de navegación:
 * las pantallas no lo tocan. Cada pantalla declara su permiso con `export const handle`.
 */
export default function LayoutApp() {
  const { estado, motivoSinSesion, puede, puedeAlguno } = useSesion();
  const ubicacion = useLocation();
  const coincidencias = useMatches();
  const esEscritorio = useEsEscritorio();

  if (estado === "cargando") return <Cargando variante="pantalla" />;

  if (estado === "anonima") {
    const volver = ubicacion.pathname + ubicacion.search;
    const destino =
      motivoSinSesion === "salio" || volver === "/" ? "/entrar" : `/entrar?volver=${encodeURIComponent(volver)}`;
    return <Navigate to={destino} replace />;
  }

  const permitido = coincidencias.every((c) => {
    const m = manejadorDe(c);
    if (!m) return true;
    if (m.permiso && !puede(m.permiso)) return false;
    if (m.permisosAlguno && !puedeAlguno(m.permisosAlguno)) return false;
    return true;
  });
  const contenido = permitido ? <Outlet /> : <SinPermiso />;

  return (
    <ContadoresProvider>
      {esEscritorio ? <ArmazonEscritorio>{contenido}</ArmazonEscritorio> : <ArmazonMovil contenido={contenido} />}
    </ContadoresProvider>
  );
}
