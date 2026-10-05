import { useCallback, useEffect, useRef, useState } from "react";

import { apiGet } from "~/api/cliente";
import type { Pagina } from "~/api/tipos";
import { instanteUtc } from "~/componentes/consulta/formato";
import { prepararSonido, reproducir } from "~/componentes/dominio/sonido";
import { aviso } from "~/componentes/ui/aviso";
import type { EstadoAutorizacion, EstadoSolicitud, Solicitud } from "~/componentes/consulta/tipos";

/** Cada cuántos milisegundos se pregunta por solicitudes nuevas mientras la pantalla está abierta. */
export const INTERVALO_MS = 4000;

/** Una solicitud que dejó de estar pendiente sin que esta persona la resolviera aquí. */
export interface SolicitudCerrada {
  solicitud: Solicitud;
  estado: EstadoSolicitud;
  /** Quién la resolvió, si la resolvió alguien. */
  por: string | null;
}

export function venceEn(s: Solicitud): number {
  return new Date(instanteUtc(s.vence_en)).getTime();
}

/**
 * Lista de solicitudes por resolver que se actualiza sola: consulta cada pocos segundos, se pausa si la
 * pestaña no se ve y se detiene al salir de la pantalla. Anuncia las nuevas con un sonido discreto y un
 * aviso, y conserva (atenuadas) las que dejaron de estar pendientes para decir qué pasó con ellas.
 */
export function useSolicitudes() {
  const [pendientes, setPendientes] = useState<Solicitud[]>([]);
  const [cerradas, setCerradas] = useState<SolicitudCerrada[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [nuevas, setNuevas] = useState<Set<string>>(new Set());

  const vistas = useRef<Map<string, Solicitud> | null>(null);
  const resueltasAqui = useRef<Set<string>>(new Set());
  const enCurso = useRef(false);
  const temporizador = useRef<number | null>(null);
  const activo = useRef(true);

  const cargar = useCallback(async () => {
    if (enCurso.current) return;
    enCurso.current = true;
    try {
      const pagina = await apiGet<Pagina<Solicitud>>("/autorizaciones", { estado: "PENDIENTE" });
      if (!activo.current) return;
      const actuales = new Map(pagina.elementos.map((s) => [s.id, s]));
      const previas = vistas.current;

      if (previas) {
        const llegaron = pagina.elementos.filter((s) => !previas.has(s.id));
        if (llegaron.length > 0) {
          reproducir("aviso");
          for (const s of llegaron) {
            aviso({
              titulo: "Nueva solicitud por autorizar",
              descripcion: `${s.trabajador.nombre}: ${s.renglones.map((r) => r.articulo ?? r.codigo).join(", ")}`,
              tipo: "info",
            });
          }
          setNuevas((n) => new Set([...n, ...llegaron.map((s) => s.id)]));
          window.setTimeout(() => {
            if (activo.current) setNuevas((n) => new Set([...n].filter((id) => !llegaron.some((s) => s.id === id))));
          }, 6000);
        }

        // Las que ya no están: se averigua cómo terminaron (venció, la resolvió otra persona...).
        const idas = [...previas.values()].filter((s) => !actuales.has(s.id) && !resueltasAqui.current.has(s.id));
        if (idas.length > 0) {
          const cierres = await Promise.all(
            idas.map(async (s): Promise<SolicitudCerrada> => {
              try {
                const detalle = await apiGet<EstadoAutorizacion>(`/autorizaciones/${s.id}`);
                return { solicitud: s, estado: detalle.estado, por: detalle.resuelta_por?.nombre ?? null };
              } catch {
                return { solicitud: s, estado: "VENCIDA", por: null };
              }
            }),
          );
          if (!activo.current) return;
          setCerradas((c) => [...cierres.filter((n) => !c.some((x) => x.solicitud.id === n.solicitud.id)), ...c]);
        }
      }

      vistas.current = actuales;
      setPendientes(pagina.elementos);
      setError(null);
    } catch (causa) {
      if (activo.current) setError(causa);
    } finally {
      enCurso.current = false;
      if (activo.current) setCargando(false);
    }
  }, []);

  useEffect(() => {
    activo.current = true;
    prepararSonido();
    const alToque = () => prepararSonido();
    window.addEventListener("pointerdown", alToque, { once: true });

    const programar = () => {
      temporizador.current = window.setTimeout(async () => {
        if (document.visibilityState === "visible") await cargar();
        if (activo.current) programar();
      }, INTERVALO_MS);
    };
    // Al volver a ver la pestaña se actualiza al instante.
    const alVolver = () => {
      if (document.visibilityState === "visible") void cargar();
    };
    document.addEventListener("visibilitychange", alVolver);

    void cargar().then(() => {
      if (activo.current) programar();
    });

    return () => {
      activo.current = false;
      if (temporizador.current !== null) window.clearTimeout(temporizador.current);
      document.removeEventListener("visibilitychange", alVolver);
      window.removeEventListener("pointerdown", alToque);
    };
  }, [cargar]);

  /** Marca una solicitud como resuelta aquí (no se vuelve a mostrar como cerrada) y refresca. */
  const resuelta = useCallback(
    (id: string) => {
      resueltasAqui.current.add(id);
      setPendientes((p) => p.filter((s) => s.id !== id));
      void cargar();
    },
    [cargar],
  );

  const descartar = useCallback((id: string) => {
    setCerradas((c) => c.filter((x) => x.solicitud.id !== id));
  }, []);

  return { pendientes, cerradas, cargando, error, nuevas, recargar: cargar, resuelta, descartar };
}
