import { cn } from "cn";
import { QRCodeSVG } from "qrcode.react";
import type { ReactNode } from "react";

interface PropiedadesCodigoQR {
  /** Lo que contiene el QR, exactamente (por ejemplo el código de una pieza o la dirección de un vale). */
  valor: string;
  /** Lado en píxeles de pantalla. Por omisión 160. En papel se escala con el contenedor. */
  tamano?: number;
  /** Corrección de errores: `M` aguanta un poco de suciedad; `Q` más, a costa de un QR más denso. */
  nivel?: "L" | "M" | "Q" | "H";
  /** Texto para lectores de pantalla. */
  titulo?: string;
  className?: string;
}

/**
 * QR en SVG, nítido a cualquier tamaño y al imprimir. Siempre negro sobre blanco con margen blanco
 * (los lectores lo necesitan, aunque el fondo de la pantalla sea de otro color).
 *
 * ```tsx
 * <CodigoQR valor="ALT-024" tamano={128} />
 * ```
 */
export function CodigoQR({ valor, tamano = 160, nivel = "M", titulo, className }: PropiedadesCodigoQR) {
  return (
    <QRCodeSVG
      value={valor}
      size={tamano}
      level={nivel}
      bgColor="#ffffff"
      fgColor="#000000"
      marginSize={2}
      title={titulo ?? `Código QR: ${valor}`}
      className={cn("block h-auto max-w-full shrink-0 bg-white", className)}
      style={{ width: tamano }}
    />
  );
}

interface PropiedadesFolioQR {
  folio: string;
  /** Contenido del QR; para un vale, su dirección (`urlDeVale(token)`). */
  valor: string;
  /** Texto legible bajo el folio (por ejemplo "Vale de entrega · 05/10/2026 14:32"). */
  texto?: ReactNode;
  tamano?: number;
  className?: string;
}

/**
 * Folio en grande (20 px, negritas), el QR y un texto legible. Es el resultado de una entrega,
 * un traspaso o una devolución.
 *
 * ```tsx
 * <FolioQR folio="KEP-ENT-000123" valor={urlDeVale(vale.token)} texto="Vale de entrega" />
 * ```
 */
export function FolioQR({ folio, valor, texto, tamano = 176, className }: PropiedadesFolioQR) {
  return (
    <figure className={cn("flex flex-col items-center gap-3 text-center", className)}>
      <figcaption className="flex flex-col items-center gap-0.5">
        <span className="text-xl font-bold tracking-wide text-marino">{folio}</span>
        {texto ? <span className="text-base text-muted-foreground">{texto}</span> : null}
      </figcaption>
      <div className="rounded-xl border bg-white p-2">
        <CodigoQR valor={valor} tamano={tamano} titulo={`Código QR del folio ${folio}`} />
      </div>
      <p className="text-sm text-muted-foreground">Escanéalo para abrir el vale.</p>
    </figure>
  );
}

/** Dirección que abre el vale al escanear su QR (ruta `/v/:token`). */
export function urlDeVale(token: string): string {
  const origen = typeof window === "undefined" ? "" : window.location.origin;
  return `${origen}/v/${token}`;
}
