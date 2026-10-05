import { cn } from "cn";
import { useEffect, useRef, useState } from "react";

import { CodigoQR } from "./codigo-qr";
import { CLASE_IMPRESION, EstiloImpresion } from "./estilo-impresion";
import type { EtiquetaElemento } from "./tipos";

/** Ancho útil de la hoja carta con márgenes de 12 mm: 216 − 24 = 192 mm (≈ 726 px a 96 ppp). */
const ANCHO_HOJA_PX = 726;

/** Etiquetas por hoja carta: 3 columnas × 6 filas. Solo para informar cuántas hojas saldrán. */
export const ETIQUETAS_POR_HOJA = 18;

interface PropiedadesHojaEtiquetas {
  etiquetas: EtiquetaElemento[];
  className?: string;
}

function Etiqueta({ etiqueta }: { etiqueta: EtiquetaElemento }) {
  return (
    <li className="flex h-[36mm] break-inside-avoid items-center gap-[3mm] overflow-hidden border border-dashed border-neutral-500 bg-white p-[3mm] text-black">
      {/* El QR contiene exactamente el código registrado. */}
      <CodigoQR valor={etiqueta.codigo} tamano={104} nivel="M" titulo={`Código QR de ${etiqueta.codigo}`} className="size-[28mm]!" />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <p className="line-clamp-3 text-[11pt] leading-tight font-bold wrap-break-word">{etiqueta.texto}</p>
        <p className="tabular-nums text-[10pt] font-semibold tracking-wide break-all">{etiqueta.codigo}</p>
      </div>
    </li>
  );
}

/**
 * Hoja de etiquetas lista para imprimir en carta: cuadrícula de 3 columnas, cada etiqueta con su QR
 * (que contiene exactamente el código) y el nombre y el código en texto legible. En pantalla se
 * muestra como una vista previa a escala; al imprimir solo sale la hoja, sin menús.
 *
 * ```tsx
 * <HojaEtiquetas etiquetas={seleccionadas} />
 * ```
 */
export function HojaEtiquetas({ etiquetas, className }: PropiedadesHojaEtiquetas) {
  const contenedor = useRef<HTMLDivElement>(null);
  const [escala, setEscala] = useState(1);

  useEffect(() => {
    const el = contenedor.current;
    if (!el) return;
    const medir = () => setEscala(Math.min(1, el.clientWidth / ANCHO_HOJA_PX));
    medir();
    const observador = new ResizeObserver(medir);
    observador.observe(el);
    return () => observador.disconnect();
  }, []);

  return (
    <div ref={contenedor} className={cn("w-full", className)}>
      <EstiloImpresion />
      <ol
        aria-label="Hoja de etiquetas"
        style={{ zoom: escala }}
        className={cn(
          CLASE_IMPRESION,
          "mx-auto grid w-[726px] grid-cols-3 content-start gap-0 bg-white shadow-md ring-1 ring-black/10 print:w-full print:ring-0",
          "print:[zoom:1]!",
        )}
      >
        {etiquetas.map((e) => (
          <Etiqueta key={e.codigo} etiqueta={e} />
        ))}
      </ol>
    </div>
  );
}
