import { useMemo } from "react";

import { apiGet } from "~/api/cliente";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import type { OpcionLista } from "~/componentes/ui/lista-desplegable";

const CLAVE_ALMACEN_OPERANDO = "imhotep.almacen.operando";

/** El almacén que esta persona operó por última vez en este dispositivo (lo comparten Entregar, Devolver y Trasladar). */
export function almacenRecordado(): string | null {
  try {
    return window.localStorage.getItem(CLAVE_ALMACEN_OPERANDO);
  } catch {
    return null;
  }
}

export function recordarAlmacen(id: string) {
  try {
    window.localStorage.setItem(CLAVE_ALMACEN_OPERANDO, id);
  } catch {
    // Sin almacenamiento, simplemente no se recuerda.
  }
}

/** Almacenes activos para el selector de quien opera todos (`almacenes.todos`). Los demás no lo piden. */
export function useAlmacenesParaPedir(activo: boolean) {
  const consulta = useConsulta(
    (signal) =>
      activo
        ? apiGet<{ id: string; clave: string; nombre: string; estado: string }[]>("/almacenes", undefined, signal)
        : Promise.resolve([]),
    `almacenes-compra|${activo}`,
  );
  const opciones = useMemo<OpcionLista[]>(
    () =>
      (consulta.datos ?? [])
        .filter((a) => a.estado === "ACTIVO")
        .map((a) => ({ valor: a.id, texto: `${a.nombre} (${a.clave})` })),
    [consulta.datos],
  );
  return { opciones, cargando: consulta.cargando, error: consulta.error, recargar: consulta.recargar };
}
