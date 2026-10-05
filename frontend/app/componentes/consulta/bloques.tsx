import { ArrowLeftIcon } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";

export function Seccion({ titulo, children, accion }: { titulo: string; children: ReactNode; accion?: ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-semibold text-marino">{titulo}</h2>
        {accion}
      </div>
      {children}
    </section>
  );
}

export function Dato({ etiqueta, valor }: { etiqueta: string; valor: ReactNode }) {
  return (
    <div className="flex flex-col">
      <dt className="text-sm text-muted-foreground">{etiqueta}</dt>
      <dd className="text-base">{valor}</dd>
    </div>
  );
}

/** Enlace "Volver a Consultar" al principio de una ficha. */
export function VolverAConsultar() {
  return (
    <Link
      to="/consultar"
      className="inline-flex min-h-10 w-fit items-center gap-2 text-base font-semibold text-primary underline-offset-2 hover:underline"
    >
      <ArrowLeftIcon aria-hidden="true" className="size-5" />
      Volver a Consultar
    </Link>
  );
}
