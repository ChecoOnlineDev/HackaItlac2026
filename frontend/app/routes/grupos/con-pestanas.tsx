import { Outlet, useLocation } from "react-router";

import { BarraPestanas } from "~/componentes/navegacion/barra-pestanas";
import { menuPermitido, pestanasDe } from "~/sesion/menu";
import { useSesionActiva } from "~/sesion/sesion";

/**
 * Layout de las pantallas que comparten una barra de pestañas (Inventario, Catálogo, Traspasos, Compras...).
 * No cambia ninguna URL: solo pone encima la barra con las pestañas que permiten los permisos de la sesión.
 * La barra sale solo en la pantalla misma de una pestaña, no en sus detalles (`/compras/<id>`, `/roles/<id>`).
 */
export default function ConPestanas() {
  const { puedeAlguno } = useSesionActiva();
  const { pathname } = useLocation();
  const barra = pestanasDe(menuPermitido(puedeAlguno), pathname);
  return (
    <>
      {barra ? <BarraPestanas titulo={barra.seccion.titulo} pestanas={barra.pestanas} activa={barra.activa} /> : null}
      <Outlet />
    </>
  );
}
