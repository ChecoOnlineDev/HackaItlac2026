import { cn } from "cn";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { aviso } from "~/componentes/ui/aviso";
import { RenglonSemaforo, type EstadoAutorizacion, type PropiedadesRenglonSemaforo } from "./renglon-semaforo";
import type { RenglonEvaluado } from "./tipos";

/** Tiempo que un renglón nuevo queda resaltado. La transición dura 150 ms. */
const RESALTADO_MS = 1200;

export interface PropiedadesListaRenglones {
  renglones: RenglonEvaluado[];
  /** Identifica un renglón entre cambios de la lista. Por omisión, su código. */
  claveDe?: (renglon: RenglonEvaluado) => string;
  onQuitar: (renglon: RenglonEvaluado) => void;
  onCantidad?: (renglon: RenglonEvaluado, cantidad: number) => void;
  onPedirAutorizacion?: (renglon: RenglonEvaluado) => void;
  onObservacion?: (renglon: RenglonEvaluado) => void;
  /** Lleva a la ficha de la pieza para inspeccionarla (renglón rojo por E-05 o E-06). */
  onInspeccionar?: (renglon: RenglonEvaluado) => void;
  /** Estado de autorización de cada renglón naranja. */
  estadoAutorizacion?: (renglon: RenglonEvaluado) => EstadoAutorizacion;
  /** Observación capturada de cada renglón. */
  observacionDe?: (renglon: RenglonEvaluado) => string | null | undefined;
  /** Notas por clave de renglón (por ejemplo los que cambiaron al revalidar). */
  notas?: Record<string, string>;
  /**
   * Muestra "Se agregó <artículo>. Deshacer" 5 segundos cuando aparece un renglón nuevo. Los renglones
   * que ya estaban en el primer pintado no se anuncian. Por omisión `true`.
   */
  anunciarAgregados?: boolean;
  /** Qué mostrar cuando no hay renglones. */
  vacio?: ReactNode;
  /** Bloquea los botones mientras el servidor responde. */
  deshabilitado?: boolean;
  textos?: PropiedadesRenglonSemaforo["textos"];
  className?: string;
}

/**
 * Lista de renglones del borrador. Cada renglón nuevo entra con una transición corta (150 ms), queda
 * resaltado un instante y avisa "Se agregó <artículo>. Deshacer" durante 5 segundos; tocar "Deshacer"
 * llama a `onQuitar`. Escanear solo agrega al borrador (E-28): esta lista no escribe nada.
 *
 * ```tsx
 * <ListaRenglones renglones={evaluacion.renglones} onQuitar={quitar} onCantidad={cambiarCantidad} />
 * ```
 */
export function ListaRenglones({
  renglones,
  claveDe = (r) => r.codigo,
  onQuitar,
  onCantidad,
  onPedirAutorizacion,
  onObservacion,
  onInspeccionar,
  estadoAutorizacion,
  observacionDe,
  notas,
  anunciarAgregados = true,
  vacio,
  deshabilitado,
  textos,
  className,
}: PropiedadesListaRenglones) {
  const [resaltados, setResaltados] = useState<ReadonlySet<string>>(new Set());
  const previas = useRef<Set<string> | null>(null);
  const temporizadores = useRef<Map<string, number>>(new Map());

  // Siempre la última versión, para que "Deshacer" quite el renglón tal como está ahora.
  const ultima = useRef({ renglones, claveDe, onQuitar });
  useEffect(() => {
    ultima.current = { renglones, claveDe, onQuitar };
  });

  const claves = renglones.map(claveDe);
  const firma = claves.join("\u0000");

  useEffect(() => {
    const actuales = new Set(claves);
    if (previas.current === null) {
      previas.current = actuales;
      return;
    }
    const nuevos = claves.filter((c) => !previas.current!.has(c));
    previas.current = actuales;
    if (nuevos.length === 0) return;

    setResaltados((prev) => new Set([...prev, ...nuevos]));
    for (const clave of nuevos) {
      window.clearTimeout(temporizadores.current.get(clave));
      temporizadores.current.set(
        clave,
        window.setTimeout(() => {
          setResaltados((prev) => {
            const copia = new Set(prev);
            copia.delete(clave);
            return copia;
          });
          temporizadores.current.delete(clave);
        }, RESALTADO_MS),
      );
    }
    // Un solo aviso por lote (p. ej. al agregar la dotación sugerida) en vez de uno por renglón.
    if (anunciarAgregados) {
      const anunciables = nuevos
        .map((c) => ({ clave: c, renglon: renglones.find((r) => claveDe(r) === c) }))
        .filter((x) => x.renglon?.articulo);
      if (anunciables.length > 0) {
        const quitarNuevos = () => {
          const { renglones: actualesRenglones, claveDe: clave_de, onQuitar: quitar } = ultima.current;
          for (const { clave } of anunciables) {
            const actual = actualesRenglones.find((r) => clave_de(r) === clave);
            if (actual) quitar(actual);
          }
        };
        aviso({
          titulo:
            anunciables.length === 1
              ? `Se agregó ${anunciables[0].renglon!.articulo!.nombre}`
              : `Se agregaron ${anunciables.length} artículos`,
          tipo: "info",
          duracionMs: 5000,
          accion: { etiqueta: "Deshacer", alHacerClic: quitarNuevos },
        });
      }
    }
    // Solo cuando cambia el conjunto de renglones, no su cantidad.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [firma]);

  useEffect(() => {
    const mapa = temporizadores.current;
    return () => mapa.forEach((id) => window.clearTimeout(id));
  }, []);

  if (renglones.length === 0) return vacio ? <>{vacio}</> : null;

  return (
    <ul className={cn("flex flex-col gap-3", className)} aria-label="Renglones del vale">
      {renglones.map((renglon) => {
        const clave = claveDe(renglon);
        return (
          <li
            key={clave}
            className="animate-in fade-in slide-in-from-top-2 duration-150 motion-reduce:animate-none"
          >
            <RenglonSemaforo
              renglon={renglon}
              resaltado={resaltados.has(clave)}
              nota={notas?.[clave]}
              textos={textos}
              deshabilitado={deshabilitado}
              estadoAutorizacion={estadoAutorizacion?.(renglon) ?? null}
              observacion={observacionDe?.(renglon) ?? null}
              onQuitar={() => onQuitar(renglon)}
              onCantidad={onCantidad ? (n) => onCantidad(renglon, n) : undefined}
              onPedirAutorizacion={onPedirAutorizacion ? () => onPedirAutorizacion(renglon) : undefined}
              onObservacion={onObservacion ? () => onObservacion(renglon) : undefined}
              onInspeccionar={onInspeccionar ? () => onInspeccionar(renglon) : undefined}
            />
          </li>
        );
      })}
    </ul>
  );
}
