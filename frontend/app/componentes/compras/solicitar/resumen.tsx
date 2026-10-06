import { cn } from "cn";

import { InsigniaUrgencia } from "./insignias";
import { textoCantidad, type Urgencia } from "./tipos";

interface Propiedades {
  /** Lo que se pide: el nombre del artículo o la descripción. */
  que: string;
  /** Código del artículo del catálogo, si lo hay. */
  codigo?: string | null;
  cantidad: number;
  motivo: string;
  urgencia: Urgencia;
  almacen?: string | null;
  className?: string;
}

/** Lo que se va a pedir (o ya se pidió), en una tarjeta corta. */
export function ResumenSolicitud({ que, codigo, cantidad, motivo, urgencia, almacen, className }: Propiedades) {
  const vacio = <span className="text-muted-foreground">Falta este dato</span>;
  return (
    <dl className={cn("grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 rounded-2xl border bg-card p-4 text-sm", className)}>
      <dt className="text-muted-foreground">Qué</dt>
      <dd className="min-w-0 font-semibold break-words">
        {que || vacio}
        {codigo ? <span className="block text-xs font-normal text-muted-foreground">{codigo}</span> : null}
      </dd>
      <dt className="text-muted-foreground">Cantidad</dt>
      <dd className="font-semibold tabular-nums">{textoCantidad(cantidad)}</dd>
      <dt className="text-muted-foreground">Para</dt>
      <dd className="min-w-0 break-words">{motivo || vacio}</dd>
      <dt className="text-muted-foreground">Urgencia</dt>
      <dd>
        <InsigniaUrgencia urgencia={urgencia} />
      </dd>
      {almacen ? (
        <>
          <dt className="text-muted-foreground">Almacén</dt>
          <dd>{almacen}</dd>
        </>
      ) : null}
    </dl>
  );
}
