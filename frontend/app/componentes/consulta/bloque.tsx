import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

/** Recuadro con icono y título corto: "Dónde está", "Quién lo tiene". */
export function Bloque({ titulo, icono: Icono, children }: { titulo: string; icono: LucideIcon; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-1 rounded-xl border p-4">
      <h2 className="flex items-center gap-2 text-base font-semibold text-marino">
        <Icono aria-hidden="true" className="size-5" />
        {titulo}
      </h2>
      {children}
    </section>
  );
}
