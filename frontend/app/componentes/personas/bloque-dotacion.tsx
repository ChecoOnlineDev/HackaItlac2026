import { apiGet } from "~/api/cliente";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import type { DotacionTrabajador } from "~/componentes/puestos/tipos";
import { EstadoError } from "~/componentes/ui/estado-error";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { Insignia } from "~/componentes/ui/insignia";

interface Propiedades {
  trabajadorId: string;
  /** Cambia cuando la ficha se vuelve a cargar (nuevo periodo, entrega...), para pedir la dotación otra vez. */
  version: string;
}

/**
 * "Dotación del puesto": cada artículo recomendado con lo que lleva el trabajador y lo que le falta (D-02).
 * Todo viene calculado por el servidor; aquí solo se muestra.
 */
export function BloqueDotacion({ trabajadorId, version }: Propiedades) {
  const consulta = useConsulta(
    (signal) => apiGet<DotacionTrabajador>(`/trabajadores/${trabajadorId}/dotacion`, undefined, signal),
    `${trabajadorId}|${version}`,
  );
  const dotacion = consulta.datos;

  if (consulta.error && !dotacion) return <EstadoError error={consulta.error} alReintentar={consulta.recargar} />;
  if (!dotacion) return <Esqueleto tipo="lista" cantidad={2} />;

  if (dotacion.puesto === null) {
    return <p className="text-base text-muted-foreground">Su puesto no está en el catálogo, así que no hay dotación que mostrar.</p>;
  }
  if (dotacion.renglones.length === 0) {
    return (
      <p className="text-base text-muted-foreground">
        El puesto {dotacion.puesto.nombre} todavía no tiene dotación: no se generan avisos al entregarle equipo.
      </p>
    );
  }

  const faltan = dotacion.renglones.filter((r) => r.falta > 0).length;
  return (
    <div className="flex flex-col gap-3">
      <p className="text-base">
        {faltan === 0
          ? `Tiene completa la dotación de ${dotacion.puesto.nombre}.`
          : `Puesto ${dotacion.puesto.nombre}: le ${faltan === 1 ? "falta 1 artículo" : `faltan ${faltan} artículos`} de su dotación.`}
      </p>
      <ul aria-label="Dotación del puesto" className="flex flex-col gap-2">
        {dotacion.renglones.map((r) => {
          const avance = r.recomendada > 0 ? Math.min(100, Math.round((r.entregada / r.recomendada) * 100)) : 100;
          return (
            <li key={r.articulo.id} className="flex flex-col gap-2 rounded-2xl border p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="flex min-w-0 flex-col">
                  <span className="text-base leading-tight font-semibold">{r.articulo.nombre}</span>
                  <span className="text-sm text-muted-foreground">{r.articulo.codigo}</span>
                </div>
                <Insignia estado={r.falta > 0 ? "info" : "neutra"}>{r.falta > 0 ? `Falta ${r.falta}` : "Completo"}</Insignia>
              </div>
              <div className="flex items-center gap-3">
                <div
                  role="progressbar"
                  aria-valuemin={0}
                  aria-valuemax={r.recomendada}
                  aria-valuenow={Math.min(r.entregada, r.recomendada)}
                  aria-label={`${r.articulo.nombre}: ${r.entregada} de ${r.recomendada}`}
                  className="h-2 flex-1 overflow-hidden rounded-full bg-muted"
                >
                  <div className="h-full rounded-full bg-primary" style={{ width: `${avance}%` }} />
                </div>
                <span className="shrink-0 text-sm font-medium tabular-nums">
                  {r.entregada} de {r.recomendada} {r.articulo.unidad}
                </span>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
