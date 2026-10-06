import { useEffect, useState } from "react";

import { apiGet } from "~/api/cliente";
import type { Pagina } from "~/api/tipos";
import type { OpcionLista } from "~/componentes/ui/lista-desplegable";
import { useSesion } from "~/sesion/sesion";
import type { SolicitudCompra } from "./tipos";

/**
 * Almacenes para el filtro de la cola. Compras ve las solicitudes de todos los almacenes pero no su inventario,
 * y la lista de almacenes solo trae el suyo; por eso se suman los almacenes que ya aparecen en las solicitudes.
 * Si algo falla, el filtro simplemente trae menos opciones.
 */
export function useAlmacenesDeLaCola(): OpcionLista[] {
  const { puede } = useSesion();
  const verAlmacenes = puede("inventario.ver");
  const [opciones, setOpciones] = useState<OpcionLista[]>([]);

  useEffect(() => {
    const control = new AbortController();
    const pedidos = [
      apiGet<Pagina<SolicitudCompra>>("/solicitudes-compra", { tamano: 200 }, control.signal).then((p) =>
        p.elementos.map((s) => s.almacen),
      ),
      verAlmacenes
        ? apiGet<{ id: string; clave: string; nombre: string }[]>("/almacenes", undefined, control.signal)
        : Promise.resolve([] as { id: string; clave: string; nombre: string }[]),
    ];
    void Promise.allSettled(pedidos).then((resultados) => {
      if (control.signal.aborted) return;
      const porId = new Map<string, OpcionLista>();
      for (const r of resultados) {
        if (r.status !== "fulfilled") continue;
        for (const a of r.value) porId.set(a.id, { valor: a.id, texto: a.nombre === a.clave ? a.nombre : `${a.nombre} (${a.clave})` });
      }
      setOpciones([...porId.values()].sort((a, b) => a.texto.localeCompare(b.texto, "es")));
    });
    return () => control.abort();
  }, [verAlmacenes]);

  return opciones;
}
