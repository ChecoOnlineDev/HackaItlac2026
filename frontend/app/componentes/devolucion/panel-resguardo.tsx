import { InfoIcon, PackageCheckIcon, UserRoundIcon } from "lucide-react";

import { claveDeCodigo } from "~/componentes/entrega/borrador";
import { fechaHoraMx } from "~/componentes/personas/formato";
import type { Ficha, Pendiente } from "~/componentes/personas/tipos";
import { Avatar } from "~/componentes/ui/avatar";
import { Boton } from "~/componentes/ui/boton";
import { EstadoError } from "~/componentes/ui/estado-error";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import type { TrabajadorDevolucion } from "./borrador";

interface PropiedadesPanelResguardo {
  trabajador: TrabajadorDevolucion;
  /** La ficha con el resguardo al día; `null` mientras carga. */
  ficha: Ficha | null;
  cargando: boolean;
  error: unknown;
  alReintentar: () => void;
  /** Cuánto de cada artículo por cantidad ya está en la devolución. */
  agregadoDe: (pendiente: Pendiente) => number;
  alElegirPieza: (pendiente: Pendiente) => void;
  alElegirCantidad: (pendiente: Pendiente) => void;
  alCambiarTrabajador: () => void;
  deshabilitado?: boolean;
  /** Códigos de las piezas que ya están en la devolución. */
  codigosAgregados: ReadonlySet<string>;
}

/**
 * Lo que el trabajador tiene en resguardo, para devolverlo desde la lista (V-03, V-14): se elige la
 * pieza o el artículo y la cantidad. No es la ficha con semáforo de la entrega: una devolución nunca se
 * bloquea por la vigencia del trabajador (SM-05), así que aquí no hay rojo por "no vigente".
 */
export function PanelResguardo({
  trabajador,
  ficha,
  cargando,
  error,
  alReintentar,
  agregadoDe,
  alElegirPieza,
  alElegirCantidad,
  alCambiarTrabajador,
  deshabilitado = false,
  codigosAgregados,
}: PropiedadesPanelResguardo) {
  const resguardo = ficha?.resguardo ?? [];
  const sinVigencia = ficha ? !ficha.vigencia.vigente || ficha.estado !== "ACTIVO" : false;
  return (
    <section aria-label={`Resguardo de ${trabajador.nombre}`} className="flex flex-col gap-3 rounded-xl border bg-card p-4">
      <header className="flex flex-wrap items-start gap-x-3 gap-y-2">
        <Avatar nombre={trabajador.nombre} fotoUrl={ficha?.tiene_foto ? ficha.foto_url : null} tamano="lg" className="size-14 text-xl" />
        <div className="flex min-w-44 flex-1 flex-col">
          <p className="text-[20px] leading-tight font-bold text-marino wrap-break-word">{trabajador.nombre}</p>
          <p className="text-base">Número {trabajador.numero_empleado}</p>
          <p className="text-sm text-muted-foreground">{[trabajador.puesto, trabajador.area_obra].filter(Boolean).join(" · ")}</p>
        </div>
        <Boton variante="texto" className="-ml-3 sm:-mr-2 sm:ml-0" onClick={alCambiarTrabajador} disabled={deshabilitado}>
          <UserRoundIcon aria-hidden="true" />
          Otra persona
        </Boton>
      </header>

      {sinVigencia ? (
        <p className="flex items-start gap-2 rounded-lg bg-muted p-3 text-base">
          <InfoIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-marino" />
          Esta persona ya no está activa en la empresa, pero su devolución se recibe normalmente.
        </p>
      ) : null}

      <h2 className="text-lg font-bold text-marino">Lo que tiene en resguardo</h2>
      {error && !ficha ? (
        <EstadoError error={error} alReintentar={alReintentar} className="p-4" />
      ) : cargando && !ficha ? (
        <Esqueleto tipo="lista" cantidad={2} />
      ) : resguardo.length === 0 ? (
        <p className="flex items-center gap-2 text-base">
          <PackageCheckIcon aria-hidden="true" className="size-5 shrink-0 text-marino" />
          No tiene equipo pendiente de devolver.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {resguardo.map((p, i) => {
            const porCantidad = p.pieza_id === null;
            const agregado = porCantidad ? agregadoDe(p) : codigosAgregados.has(claveDeCodigo(p.codigo)) ? 1 : 0;
            const restante = porCantidad ? p.cantidad - agregado : agregado > 0 ? 0 : 1;
            return (
              <li key={`${p.pieza_id ?? p.articulo_id}-${i}`} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border p-3">
                <div className="flex min-w-0 flex-1 flex-col">
                  <p className="text-lg leading-tight font-semibold wrap-break-word">
                    {p.articulo}
                    {porCantidad ? ` × ${p.cantidad}` : ""}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {p.numero_serie ? `Serie ${p.numero_serie}` : p.codigo}
                    {p.folio ? ` · Vale ${p.folio}` : ""}
                    {p.entregado_en ? ` · ${fechaHoraMx(p.entregado_en)}` : ""}
                  </p>
                  {agregado > 0 ? <p className="text-sm font-semibold">{porCantidad ? `Ya agregaste ${agregado}` : "Ya está en la devolución"}</p> : null}
                </div>
                <Boton
                  variante="secundario"
                  disabled={deshabilitado || restante <= 0}
                  aria-label={`Devolver ${p.articulo}`}
                  onClick={() => (porCantidad ? alElegirCantidad(p) : alElegirPieza(p))}
                >
                  Devolver
                </Boton>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
