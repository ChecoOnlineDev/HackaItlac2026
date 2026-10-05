import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router";

/**
 * Filtros de un reporte guardados en la dirección (`?almacen_id=…&desde=…`), para compartirlos y
 * recargar sin perderlos. Cambiar un filtro vuelve a la página 1.
 */
export function useFiltrosUrl<K extends string>(claves: readonly K[]) {
  const [params, setParams] = useSearchParams();

  const valores = useMemo(() => {
    const salida = {} as Record<K, string>;
    for (const clave of claves) salida[clave] = params.get(clave) ?? "";
    return salida;
    // `claves` es una constante de la pantalla.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  const pagina = Math.max(1, Number.parseInt(params.get("pagina") ?? "1", 10) || 1);

  const cambiar = useCallback(
    (parcial: Partial<Record<K, string | null>>) => {
      setParams(
        (previos) => {
          const nuevos = new URLSearchParams(previos);
          for (const [clave, valor] of Object.entries(parcial) as [K, string | null][]) {
            if (valor) nuevos.set(clave, valor);
            else nuevos.delete(clave);
          }
          nuevos.delete("pagina");
          return nuevos;
        },
        { replace: true },
      );
    },
    [setParams],
  );

  const cambiarPagina = useCallback(
    (nueva: number) => {
      setParams(
        (previos) => {
          const nuevos = new URLSearchParams(previos);
          if (nueva > 1) nuevos.set("pagina", String(nueva));
          else nuevos.delete("pagina");
          return nuevos;
        },
        { replace: true },
      );
    },
    [setParams],
  );

  const quitarTodos = useCallback(() => {
    setParams(new URLSearchParams(), { replace: true });
  }, [setParams]);

  return { valores, pagina, cambiar, cambiarPagina, quitarTodos };
}
