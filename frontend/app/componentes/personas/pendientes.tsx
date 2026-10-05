import { Link } from "react-router";

import { fechaHoraMx } from "./formato";
import type { Pendiente } from "./tipos";

/** Retornables en resguardo: artículo, código o serie, desde cuándo, folio y almacén. */
export function ListaPendientes({ pendientes }: { pendientes: Pendiente[] }) {
  return (
    <ul className="flex flex-col gap-3">
      {pendientes.map((p, i) => (
        <li key={`${p.pieza_id ?? p.articulo_id}-${i}`} className="flex flex-col gap-1 rounded-xl border p-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <span className="text-lg font-bold text-marino">
              {p.articulo}
              {p.cantidad > 1 ? ` × ${p.cantidad}` : ""}
            </span>
            {p.de_periodo_anterior ? (
              <span className="text-sm font-semibold text-foreground">De un periodo anterior</span>
            ) : null}
          </div>
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-base">
            <dt className="text-muted-foreground">{p.numero_serie ? "Serie" : "Código"}</dt>
            <dd>{p.numero_serie ?? p.codigo}</dd>
            <dt className="text-muted-foreground">Desde</dt>
            <dd>{fechaHoraMx(p.entregado_en)}</dd>
            <dt className="text-muted-foreground">Vale</dt>
            <dd>
              {p.vale_id && p.folio ? (
                <Link to={`/vales/${p.vale_id}`} className="font-semibold text-primary underline underline-offset-2">
                  {p.folio}
                </Link>
              ) : (
                (p.folio ?? "—")
              )}
            </dd>
            <dt className="text-muted-foreground">Almacén</dt>
            <dd>{p.almacen ?? "—"}</dd>
          </dl>
        </li>
      ))}
    </ul>
  );
}
