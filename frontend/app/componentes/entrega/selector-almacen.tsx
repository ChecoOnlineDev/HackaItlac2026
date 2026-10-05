import { WarehouseIcon } from "lucide-react";
import { useEffect, useId, useState } from "react";

import { apiGet } from "~/api/cliente";
import { mensajeDeError } from "~/api/errores";
import { ListaDesplegable } from "~/componentes/ui/lista-desplegable";
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
      <ListaDesplegable
        id={id}
        valor={valor ?? ""}
        deshabilitado={deshabilitado || almacenes === null}
        marcador={almacenes === null && !error ? "Cargando almacenes…" : "Elige un almacén"}
        opciones={(almacenes ?? []).map((a) => ({ valor: a.id, texto: `${a.nombre} (${a.clave})` }))}
        alCambiar={(elegido) => {
          const a = almacenes?.find((x) => x.id === elegido);
          if (a) alCambiar({ id: a.id, clave: a.clave, nombre: a.nombre });
        }}
      />
      {error ? (
        <p role="alert" className="mt-1.5 text-sm font-medium text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}
