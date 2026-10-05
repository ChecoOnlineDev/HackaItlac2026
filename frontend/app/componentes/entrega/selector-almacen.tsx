import { WarehouseIcon } from "lucide-react";
import { useEffect, useId, useState } from "react";

import { apiGet } from "~/api/cliente";
import { mensajeDeError } from "~/api/errores";
import type { AlmacenResumen } from "./tipos";

interface AlmacenLista extends AlmacenResumen {
  tipo: string;
  estado: string;
}

interface PropiedadesSelectorAlmacen {
  /** Almacén elegido, o null si todavía no se elige. */
  valor: string | null;
  alCambiar: (almacen: AlmacenResumen) => void;
  /** Bloquea el cambio (por ejemplo cuando ya hay renglones capturados). */
  deshabilitado?: boolean;
  className?: string;
}

/**
 * "Almacén que opera": solo lo usa quien tiene `almacenes.todos` (supervisor, Compras, administrador).
 * El resto opera el almacén de su sesión. Se manda `almacen_id` al evaluar y al confirmar.
 */
export function SelectorAlmacen({ valor, alCambiar, deshabilitado, className }: PropiedadesSelectorAlmacen) {
  const id = useId();
  const [almacenes, setAlmacenes] = useState<AlmacenLista[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let vivo = true;
    apiGet<AlmacenLista[]>("/almacenes")
      .then((lista) => {
        if (vivo) setAlmacenes(lista.filter((a) => a.estado === "ACTIVO"));
      })
      .catch((causa: unknown) => {
        if (vivo) setError(mensajeDeError(causa));
      });
    return () => {
      vivo = false;
    };
  }, []);

  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1.5 flex items-center gap-2 text-base font-medium">
        <WarehouseIcon aria-hidden="true" className="size-5 text-marino" />
        Almacén que opera
      </label>
      <select
        id={id}
        value={valor ?? ""}
        disabled={deshabilitado || almacenes === null}
        onChange={(e) => {
          const elegido = almacenes?.find((a) => a.id === e.target.value);
          if (elegido) alCambiar({ id: elegido.id, clave: elegido.clave, nombre: elegido.nombre });
        }}
        className="h-12 w-full rounded-lg border border-input bg-background px-3 text-base disabled:opacity-60"
      >
        <option value="" disabled>
          {almacenes === null && !error ? "Cargando almacenes…" : "Elige un almacén"}
        </option>
        {(almacenes ?? []).map((a) => (
          <option key={a.id} value={a.id}>
            {a.nombre} ({a.clave})
          </option>
        ))}
      </select>
      {error ? (
        <p role="alert" className="mt-1.5 text-sm font-medium text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}
