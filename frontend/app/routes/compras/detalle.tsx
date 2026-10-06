import { ArrowLeftIcon, RefreshCwIcon } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link, useParams } from "react-router";

import { apiGet } from "~/api/cliente";
import { esErrorApi } from "~/api/errores";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { BotonesAccion } from "~/componentes/compras/atender/botones-accion";
import { FlujoAccion } from "~/componentes/compras/atender/flujo-accion";
import { InsigniaEstadoSolicitud, InsigniaUrgencia } from "~/componentes/compras/atender/insignias";
import { LineaDeTiempoSolicitud } from "~/componentes/compras/atender/linea-de-tiempo";
import type { AccionSolicitud, SolicitudCompra } from "~/componentes/compras/atender/tipos";
import { instanteUtc } from "~/componentes/consulta/formato";
import { formatearFechaHora } from "~/componentes/dominio/fechas";
import { AccionPrincipal, Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { Boton } from "~/componentes/ui/boton";
import { EstadoError } from "~/componentes/ui/estado-error";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { useSesion } from "~/sesion/sesion";

// La ven Compras (todas las solicitudes) y quien pide (las de su almacén); el servidor decide cuáles.
export const handle: ManejadorRuta = { permisosAlguno: ["compras.atender", "compras.solicitar"] };

function Dato({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">{titulo}</dt>
      <dd className="text-base wrap-break-word">{children}</dd>
    </div>
  );
}

function hora(iso: string): string {
  return formatearFechaHora(instanteUtc(iso));
}

export default function DetalleDeSolicitud() {
  const { id = "" } = useParams();
  const { puede } = useSesion();
  const volverA = puede("compras.atender") ? "/compras" : "/compras/mias";
  const { datos: s, cargando, error, recargar } = useConsulta(
    (signal) => apiGet<SolicitudCompra>(`/solicitudes-compra/${encodeURIComponent(id)}`, undefined, signal),
    id,
  );
  const [enAccion, setEnAccion] = useState<AccionSolicitud | null>(null);

  const volver = (
    <Boton variante="texto" nativeButton={false} render={<Link to={volverA} />} className="-ml-3 self-start max-lg:hidden">
      <ArrowLeftIcon aria-hidden="true" />
      Volver a la lista
    </Boton>
  );

  if (error && !s) {
    const noExiste = esErrorApi(error) && error.status === 404;
    return (
      <Pantalla titulo="Solicitud de compra">
        {volver}
        <EstadoError
          error={noExiste ? undefined : error}
          mensaje={noExiste ? "No encontramos esta solicitud. Puede que no sea de tu almacén o que ya no exista." : undefined}
          alReintentar={noExiste ? undefined : recargar}
        />
        {noExiste ? (
          <Boton variante="contorno" nativeButton={false} render={<Link to={volverA} />} className="self-center">
            Ir a las solicitudes
          </Boton>
        ) : null}
      </Pantalla>
    );
  }

  if (!s) {
    return (
      <Pantalla titulo="Solicitud de compra">
        {volver}
        <Esqueleto tipo="tarjeta" cantidad={2} />
      </Pantalla>
    );
  }

  const rechazada = s.estado === "RECHAZADA";

  return (
    <Pantalla
      titulo={`Solicitud ${s.folio}`}
      acciones={
        <Boton variante="contorno" onClick={recargar} disabled={cargando}>
          <RefreshCwIcon aria-hidden="true" />
          Actualizar
        </Boton>
      }
    >
      {volver}
      {error ? <EstadoError error={error} alReintentar={recargar} /> : null}

      <div className="flex flex-col gap-4" aria-busy={cargando}>
        <section aria-label="Datos de la solicitud" className="flex flex-col gap-4 rounded-2xl border bg-card p-4 shadow-xs">
          <div className="flex flex-wrap items-center gap-2">
            <InsigniaEstadoSolicitud estado={s.estado} />
            <InsigniaUrgencia urgencia={s.urgencia} />
          </div>
          <div>
            <p className="text-lg font-semibold wrap-break-word text-marino">{s.descripcion}</p>
            <p className="text-sm text-muted-foreground">
              {s.articulo ? (
                <>
                  Del catálogo:{" "}
                  {puede("catalogo.ver") ? (
                    <Link to={`/articulos/${s.articulo.id}`} className="font-semibold text-primary underline underline-offset-2">
                      {s.articulo.codigo}
                    </Link>
                  ) : (
                    <span className="font-semibold">{s.articulo.codigo}</span>
                  )}
                </>
              ) : (
                "No está en el catálogo"
              )}
            </p>
          </div>
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Dato titulo="Cantidad">
              <span className="font-semibold tabular-nums">{s.cantidad}</span>
            </Dato>
            <Dato titulo="Almacén">
              {s.almacen.nombre} ({s.almacen.clave})
            </Dato>
            <Dato titulo="Para qué se necesita">{s.motivo}</Dato>
            <Dato titulo="Quién la pidió">{s.solicitante.nombre}</Dato>
            <Dato titulo="Fecha de la solicitud">
              <span className="tabular-nums">{hora(s.creada_en)}</span>
            </Dato>
            <Dato titulo="Última actualización">
              <span className="tabular-nums">{hora(s.actualizada_en)}</span>
            </Dato>
          </dl>
          {s.nota_compras ? (
            <div className="rounded-xl border bg-muted/60 p-3">
              <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                {rechazada ? "Por qué se rechazó" : "Nota de Compras"}
              </p>
              <p className="text-base wrap-break-word">{s.nota_compras}</p>
            </div>
          ) : null}
          {s.vale_entrada ? (
            <div className="rounded-xl border bg-muted/60 p-3">
              <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">Vale de entrada</p>
              <p className="text-base">
                {puede("vales.ver") ? (
                  <Link
                    to={`/vales/${s.vale_entrada.id}`}
                    className="inline-flex min-h-10 items-center font-semibold text-primary underline underline-offset-4"
                  >
                    {s.vale_entrada.folio}
                  </Link>
                ) : (
                  <span className="font-semibold">{s.vale_entrada.folio}</span>
                )}
              </p>
            </div>
          ) : null}
        </section>

        <section aria-labelledby="titulo-linea" className="flex flex-col gap-4 rounded-2xl border bg-card p-4 shadow-xs">
          <h2 id="titulo-linea">Línea de tiempo</h2>
          <LineaDeTiempoSolicitud eventos={s.eventos ?? []} />
        </section>
      </div>

      {s.acciones.length > 0 ? (
        <AccionPrincipal>
          <BotonesAccion
            acciones={s.acciones}
            alElegir={setEnAccion}
            className="flex flex-wrap items-center justify-end gap-2 max-sm:[&>button]:flex-1"
          />
        </AccionPrincipal>
      ) : null}

      <FlujoAccion
        solicitud={s}
        accion={enAccion}
        alCerrar={() => setEnAccion(null)}
        alTerminar={recargar}
        alDesactualizar={recargar}
      />
    </Pantalla>
  );
}
