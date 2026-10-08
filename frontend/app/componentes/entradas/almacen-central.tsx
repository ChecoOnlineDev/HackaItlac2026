import { apiGet } from "~/api/cliente";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";

export interface AlmacenCentral {
  id: string;
  nombre: string;
  tipo: string;
}

/**
 * Nombre del almacén central, que es donde entra todo (EK-01). Sale de la API de almacenes, no se escribe fijo.
 * Si quien mira no puede ver la lista, queda en `null` y el texto dice «el almacén central».
 */
export function useNombreAlmacenCentral(): string | null {
  return useAlmacenCentral()?.nombre ?? null;
}

/** El almacén central completo (para filtrar listas por él), o `null` si no se pudo leer. */
export function useAlmacenCentral(): AlmacenCentral | null {
  const consulta = useConsulta((signal) => apiGet<AlmacenCentral[]>("/almacenes", undefined, signal), "almacen-central");
  return consulta.datos?.find((a) => a.tipo === "CENTRAL") ?? null;
}

/** «Entra a Kepler» y la salida para llevarlo a otro almacén (EK-03). */
export function AvisoEntradaCentral({ nombre }: { nombre: string | null }) {
  return (
    <div className="flex flex-col gap-0.5 rounded-2xl border bg-muted p-3">
      <p className="text-base font-semibold">Entra a {nombre ?? "el almacén central"}</p>
      <p className="text-sm text-muted-foreground">Para llevarlo a otro almacén, usa un traspaso.</p>
    </div>
  );
}
