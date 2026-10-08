import { TriangleAlertIcon } from "lucide-react";

/**
 * SG-06: aviso de que una pieza de alto valor o de alturas la tiene un trabajador dado de baja o con el
 * contrato vencido. El texto lo arma el servidor; el icono y el borde evitan que dependa solo del color.
 */
export function AvisoResguardo({ texto }: { texto: string }) {
  return (
    <p role="note" className="mt-1.5 flex items-start gap-1.5 rounded-xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-2 text-sm">
      <TriangleAlertIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
      <span className="min-w-0">{texto}</span>
    </p>
  );
}
