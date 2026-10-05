import { PackageCheckIcon, Undo2Icon, UserRoundIcon, WrenchIcon } from "lucide-react";
import { Link } from "react-router";

import { FichaTrabajador } from "~/componentes/dominio/ficha-trabajador";
import type { Ficha } from "~/componentes/personas/tipos";
import { Boton } from "~/componentes/ui/boton";
import { EstadoError } from "~/componentes/ui/estado-error";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { useSesion } from "~/sesion/sesion";
import { Seccion } from "./bloques";
import { useCarga } from "./use-carga";

/** Quién es y qué tiene: ficha breve con vigencia y resguardo, y los atajos a la acción siguiente. */
export function ResultadoTrabajador({ id }: { id: string }) {
  const { puede } = useSesion();
  const { datos, error, cargando, recargar } = useCarga<Ficha>(`/trabajadores/${id}`);

  if (cargando) return <Esqueleto tipo="tarjeta" cantidad={1} />;
  if (error || !datos) return <EstadoError error={error ?? undefined} alReintentar={recargar} />;

  const piezas = datos.resguardo.filter((r) => r.pieza_id);
  return (
    <div className="flex flex-col gap-4">
      <FichaTrabajador trabajador={datos} variante="completa" />

      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
        {puede("entregas.crear") && datos.vigencia.vigente ? (
          <Boton variante="normal" nativeButton={false} render={<Link to="/entregar" />}>
            <PackageCheckIcon aria-hidden="true" />
            Entregarle
          </Boton>
        ) : null}
        {puede("devoluciones.crear") && datos.resguardo.length > 0 ? (
          <Boton variante="contorno" nativeButton={false} render={<Link to="/devolver" />}>
            <Undo2Icon aria-hidden="true" />
            Devolver
          </Boton>
        ) : null}
        {puede("trabajadores.ver") ? (
          <Boton variante="contorno" nativeButton={false} render={<Link to={`/trabajadores/${datos.id}`} />}>
            <UserRoundIcon aria-hidden="true" />
            Ver su ficha completa
          </Boton>
        ) : null}
      </div>

      {piezas.length > 0 && puede("catalogo.ver") ? (
        <Seccion titulo="Abrir la ficha de una pieza">
          <ul className="flex flex-col divide-y rounded-2xl border">
            {piezas.map((p) => (
              <li key={p.pieza_id}>
                <Link
                  to={`/piezas/${p.pieza_id}`}
                  className="flex min-h-12 items-center gap-3 px-3 py-2 text-base font-semibold hover:bg-muted"
                >
                  <WrenchIcon aria-hidden="true" className="size-5 text-marino" />
                  {p.articulo} · {p.codigo}
                </Link>
              </li>
            ))}
          </ul>
        </Seccion>
      ) : null}
    </div>
  );
}
