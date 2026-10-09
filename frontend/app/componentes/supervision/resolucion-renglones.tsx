import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";

export interface DecisionRenglon { renglon: number; decision: "APROBAR" | "RECHAZAR"; motivo?: string }
export interface RenglonParaResolver { renglon: number; codigo: string; articulo?: string | null; cantidad: number; clase?: string; observacion?: string | null }

/** Presenta las clases y posiciones que entregó el servidor; no determina qué requiere autorización. */
export function ResolucionRenglones({ renglones, decisiones, alCambiar, bloqueado = false }: {
  renglones: RenglonParaResolver[]; decisiones: DecisionRenglon[]; alCambiar: (valor: DecisionRenglon[]) => void; bloqueado?: boolean;
}) {
  const cambiar = (renglon: number, valor: Partial<DecisionRenglon>) => {
    const anterior = decisiones.find((d) => d.renglon === renglon);
    alCambiar([...decisiones.filter((d) => d.renglon !== renglon), { renglon, decision: anterior?.decision ?? "APROBAR", ...anterior, ...valor }]);
  };
  return <div className="flex flex-col gap-3">{renglones.map((r) => {
    const decision = decisiones.find((d) => d.renglon === r.renglon);
    return <div key={r.renglon} className="rounded-xl border bg-background p-3">
      <p className="font-semibold">{r.cantidad} × {r.articulo ?? r.codigo}</p>
      <p className="text-sm text-muted-foreground">{r.clase === "CONTEXTO" ? "Solo como contexto" : r.clase === "EPP" ? "Equipo de protección" : "Requiere autorización"}</p>
      {r.observacion ? <p className="mt-1 text-sm">{r.observacion}</p> : null}
      {r.clase !== "CONTEXTO" ? <>
        <div role="group" aria-label={`Decisión para ${r.articulo ?? r.codigo}`} className="mt-2 grid grid-cols-2 gap-2">
          <Boton type="button" variante={decision?.decision === "APROBAR" ? "principal" : "contorno"} disabled={bloqueado} onClick={() => cambiar(r.renglon, { decision: "APROBAR" })}>Aprobar</Boton>
          <Boton type="button" variante={decision?.decision === "RECHAZAR" ? "principal" : "contorno"} disabled={bloqueado} onClick={() => cambiar(r.renglon, { decision: "RECHAZAR" })}>Rechazar</Boton>
        </div>
        {decision?.decision === "RECHAZAR" ? <Campo etiqueta="Motivo del rechazo" value={decision.motivo ?? ""} onChange={(e) => cambiar(r.renglon, { motivo: e.target.value })} maxLength={500} required disabled={bloqueado} /> : null}
      </> : null}
    </div>;
  })}</div>;
}

export function decisionesCompletas(renglones: RenglonParaResolver[], decisiones: DecisionRenglon[]): boolean {
  return renglones.filter((r) => r.clase !== "CONTEXTO").every((r) => {
    const d = decisiones.find((x) => x.renglon === r.renglon);
    return d && (d.decision === "APROBAR" || Boolean(d.motivo?.trim()));
  });
}
