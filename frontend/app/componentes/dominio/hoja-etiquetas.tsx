import { cn } from "cn";
import { useEffect, useRef, useState } from "react";

import { CodigoQR } from "./codigo-qr";
import { CLASE_IMPRESION, EstiloImpresion } from "./estilo-impresion";
import type { EtiquetaElemento } from "./tipos";
import { CARTA, FORMATOS_ETIQUETA, type FormatoEtiqueta } from "./etiquetas-medidas";

/** Ancho útil de la hoja carta con márgenes de 12 mm: 216 − 24 = 192 mm (≈ 726 px a 96 ppp). */
const ANCHO_HOJA_PX = CARTA.ancho * 96 / 25.4;

/** Etiquetas por hoja carta: 3 columnas × 6 filas. Solo para informar cuántas hojas saldrán. */
export const ETIQUETAS_POR_HOJA = 18;

interface PropiedadesHojaEtiquetas {
  etiquetas: EtiquetaElemento[];
  className?: string;
  formato?: FormatoEtiqueta;
  inicio?: number;
}

function Etiqueta({ etiqueta, formato }: { etiqueta: EtiquetaElemento; formato: FormatoEtiqueta }) {
  const m = FORMATOS_ETIQUETA[formato];
  return (
    <li style={{ width: `${m.ancho}mm`, height: `${m.alto}mm` }} className={cn("flex break-inside-avoid gap-[2mm] overflow-hidden bg-white p-[2mm] text-black", formato === 9 ? "flex-col items-center" : "items-start", formato !== 30 && "border border-dashed border-neutral-500")}>
      {/* El QR contiene exactamente el código registrado. */}
      <div style={{ width: `${m.qr}mm`, height: `${m.qr}mm` }} className="shrink-0"><CodigoQR valor={etiqueta.codigo} tamano={m.qr * 96 / 25.4} nivel="M" margen={4} titulo={`Código QR de ${etiqueta.codigo}`} className="size-full!" /></div>
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <p style={{ fontSize: `${m.nombrePt}pt`, WebkitLineClamp: m.lineas }} className="line-clamp-3 leading-tight wrap-break-word">{etiqueta.texto}</p>
        <p style={{ fontSize: `${m.codigoPt}pt` }} className="tabular-nums leading-tight break-all">{etiqueta.codigo}</p>
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
export function HojaEtiquetas({ etiquetas, className, formato = 18, inicio = 1 }: PropiedadesHojaEtiquetas) {
  const m = FORMATOS_ETIQUETA[formato];
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
        style={{ zoom: escala, width: `${CARTA.ancho}mm`, minHeight: `${CARTA.alto}mm`, padding: `${m.margenY}mm ${m.margenX}mm`, columnGap: `${m.separacion}mm` }}
        className={cn(
          CLASE_IMPRESION,
          "mx-auto grid grid-cols-3 content-start bg-white shadow-md ring-1 ring-black/10 print:ring-0",
          "print:[zoom:1]!",
        )}
      >
        {Array.from({ length: inicio - 1 }, (_, i) => <li key={`blanco-${i}`} style={{ height: `${m.alto}mm` }} aria-hidden="true" />)}
        {etiquetas.slice(0, formato - inicio + 1).map((e) => (
          <Etiqueta key={e.codigo} etiqueta={e} formato={formato} />
        ))}
      </ol>
    </div>
  );
}
