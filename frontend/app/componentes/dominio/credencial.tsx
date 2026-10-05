import { cn } from "cn";
import { DownloadIcon, IdCardIcon, PrinterIcon, QrCodeIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { CodigoQR } from "./codigo-qr";
import { ALTO_MM, ANCHO_MM, ajustarNombre, type DatosCredencial } from "./credencial-medidas";
import { credencialComoPng, descargarBlob, etiquetaQrComoPng, nombreDeArchivo } from "./credencial-png";
import { CLASE_IMPRESION, EstiloImpresion, ImpresionAparte } from "./estilo-impresion";
import { HojaEtiquetas } from "./hoja-etiquetas";

export type { DatosCredencial } from "./credencial-medidas";

/** Credenciales por hoja carta: 2 columnas × 4 filas. */
export const CREDENCIALES_POR_HOJA = 8;

/** Qué se imprime de un trabajador: la tarjeta completa o solo el código QR (la etiqueta de siempre). */
export type ModoCredencial = "completa" | "qr";

const MARINO = "#1b1f8a";
const AZUL = "#0054a6";

/** Texto legible de la etiqueta de solo QR: el mismo que manda el servidor (`nombre · número`). */
export function textoDeEtiqueta(d: DatosCredencial): string {
  return `${d.nombre} · ${d.numero_empleado}`;
}

/**
 * Credencial de trabajador, tamaño tarjeta (85.6 × 54 mm): banda azul marino con el logo, nombre completo,
 * puesto, número de empleado (único por trabajador), QR y el código en texto legible; sin pie. El QR contiene exactamente el código
 * registrado. Nunca lleva CURP ni NSS (RG-13). Las medidas van en milímetros: en papel sale a su
 * tamaño real; para verla más grande en pantalla se escala el contenedor.
 *
 * ```tsx
 * <TarjetaCredencial datos={{ codigo: "TRB-1001", nombre: "Ana Pérez", puesto: "Soldadora", numero_empleado: "E-1001" }} />
 * ```
 */
export function TarjetaCredencial({ datos, className }: { datos: DatosCredencial; className?: string }) {
  const { tamano, interlinea, lineas } = ajustarNombre(datos.nombre);
  const mm = (n: number) => `${n}mm`;
  return (
    <div
      role="img"
      aria-label={`Credencial de ${datos.nombre}, número de empleado ${datos.numero_empleado}, código ${datos.codigo}`}
      className={cn("relative shrink-0 overflow-hidden bg-white text-black ring-1 ring-slate-300 [font-family:var(--font-sans)]", className)}
      style={{ width: mm(ANCHO_MM), height: mm(ALTO_MM), borderRadius: mm(3) }}
    >
      {/* Banda superior */}
      <div className="absolute inset-x-0 top-0" style={{ height: mm(13.5), background: MARINO }} />
      <div className="absolute inset-x-0" style={{ top: mm(13.5), height: mm(0.7), background: AZUL }} />
      <div className="absolute flex items-center justify-center rounded-full bg-white" style={{ left: mm(4.1), top: mm(1.65), width: mm(10.2), height: mm(10.2) }}>
        <img src="/logo-imhotep.png" alt="" draggable={false} style={{ width: mm(9), height: "auto" }} />
      </div>
      <p className="absolute m-0 font-bold leading-none text-white" style={{ left: mm(16.2), top: mm(2.9), fontSize: mm(4.6) }}>
        IMHOTEP
      </p>
      <p className="absolute m-0 leading-none" style={{ left: mm(16.2), top: mm(8.6), fontSize: mm(2.1), color: "#c7d2fe" }}>
        Mantenimiento Industrial
      </p>

      {/* Datos */}
      <p
        className="absolute m-0 overflow-hidden font-bold wrap-break-word"
        style={{ left: mm(5), top: mm(17.1), width: mm(46.5), height: mm(interlinea * lineas), fontSize: mm(tamano), lineHeight: mm(interlinea), color: "#111827" }}
      >
        {datos.nombre}
      </p>
      <p className="absolute m-0 truncate font-semibold leading-none" style={{ left: mm(5), top: mm(31.9), width: mm(46.5), fontSize: mm(3.1), color: AZUL, lineHeight: mm(4) }}>
        {datos.puesto?.trim() || "Sin puesto registrado"}
      </p>
      <p className="absolute m-0 leading-none" style={{ left: mm(5), top: mm(38.4), fontSize: mm(2.2), color: "#4b5563" }}>
        Número de empleado
      </p>
      <p className="absolute m-0 truncate font-bold leading-none" style={{ left: mm(5), top: mm(41.4), width: mm(46.5), fontSize: mm(3.9), lineHeight: mm(4.6), color: "#111827" }}>
        {datos.numero_empleado}
      </p>

      {/* QR: contiene exactamente el código registrado. */}
      <div className="absolute rounded-[1.4mm] border border-slate-300 bg-white" style={{ left: mm(54.6), top: mm(18.4), width: mm(27.2), height: mm(27.2) }}>
        <CodigoQR valor={datos.codigo} tamano={104} nivel="M" titulo={`Código QR de ${datos.codigo}`} className="absolute top-[0.6mm] left-[0.6mm] size-[26mm]!" />
      </div>
      <p className="absolute m-0 truncate text-center font-bold leading-none" style={{ left: mm(54.6), top: mm(46.4), width: mm(27.2), fontSize: mm(2.9), lineHeight: mm(3.4), color: "#111827" }}>
        {datos.codigo}
      </p>
    </div>
  );
}

/** Etiqueta de solo el código QR de un trabajador (la de la hoja de etiquetas). */
function EtiquetaQrUnica({ datos }: { datos: DatosCredencial }) {
  return (
    <div className="flex h-[36mm] w-[60mm] items-center gap-[3mm] overflow-hidden border border-dashed border-neutral-500 bg-white p-[3mm] text-black">
      <CodigoQR valor={datos.codigo} tamano={104} nivel="M" titulo={`Código QR de ${datos.codigo}`} className="size-[28mm]!" />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <p className="line-clamp-3 text-[11pt] leading-tight font-bold wrap-break-word">{textoDeEtiqueta(datos)}</p>
        <p className="text-[10pt] font-semibold tracking-wide break-all">{datos.codigo}</p>
      </div>
    </div>
  );
}

/** Ancho útil de la hoja carta con márgenes de 12 mm: 192 mm (≈ 726 px a 96 ppp). */
const ANCHO_HOJA_PX = 726;

/** Escala que hace caber un ancho fijo en su contenedor (nunca más de `maximo`). */
function useEscala(anchoPx: number, maximo = 1) {
  const contenedor = useRef<HTMLDivElement>(null);
  const [escala, setEscala] = useState(1);
  useEffect(() => {
    const el = contenedor.current;
    if (!el) return;
    const medir = () => setEscala(Math.min(maximo, Math.max(0.2, el.clientWidth / anchoPx)));
    medir();
    const observador = new ResizeObserver(medir);
    observador.observe(el);
    return () => observador.disconnect();
  }, [anchoPx, maximo]);
  return { contenedor, escala };
}

interface PropiedadesHojaCredenciales {
  credenciales: DatosCredencial[];
  className?: string;
}

/**
 * Hoja carta con credenciales: 2 columnas × 4 filas, cada tarjeta en su recuadro de guía de corte.
 * En pantalla es una vista previa a escala; al imprimir solo sale la hoja, sin menús. Los colores
 * de fondo se imprimen (el navegador debe permitir «gráficos de fondo»; ya lo pide la hoja).
 *
 * ```tsx
 * <HojaCredenciales credenciales={seleccionadas} />
 * ```
 */
export function HojaCredenciales({ credenciales, className }: PropiedadesHojaCredenciales) {
  const { contenedor, escala } = useEscala(ANCHO_HOJA_PX);
  return (
    <div ref={contenedor} className={cn("w-full", className)}>
      <EstiloImpresion />
      <ol
        aria-label="Hoja de credenciales"
        style={{ zoom: escala }}
        className={cn(
          CLASE_IMPRESION,
          "mx-auto grid w-[726px] grid-cols-2 content-start gap-0 bg-white shadow-md ring-1 ring-black/10 print:w-full print:ring-0",
          "print:[zoom:1]!",
        )}
      >
        {credenciales.map((c) => (
          <li key={c.codigo} className="flex h-[58mm] break-inside-avoid items-center justify-center border border-dashed border-neutral-400 bg-white">
            <TarjetaCredencial datos={c} />
          </li>
        ))}
      </ol>
    </div>
  );
}

interface PropiedadesSelectorModo {
  modo: ModoCredencial;
  alCambiar: (modo: ModoCredencial) => void;
  className?: string;
}

const OPCIONES_MODO: { modo: ModoCredencial; nombre: string; ayuda: string; icono: typeof IdCardIcon }[] = [
  { modo: "completa", nombre: "Credencial completa", ayuda: "Nombre, puesto, número y QR", icono: IdCardIcon },
  { modo: "qr", nombre: "Solo el código QR", ayuda: "La etiqueta con el QR", icono: QrCodeIcon },
];

/** Dos opciones grandes para elegir qué imprimir de un trabajador. */
export function SelectorModoCredencial({ modo, alCambiar, className }: PropiedadesSelectorModo) {
  return (
    <div role="radiogroup" aria-label="Qué imprimir" className={cn("grid gap-3 sm:grid-cols-2", className)}>
      {OPCIONES_MODO.map(({ modo: m, nombre, ayuda, icono: Icono }) => {
        const activo = modo === m;
        return (
          <button
            key={m}
            type="button"
            role="radio"
            aria-checked={activo}
            onClick={() => alCambiar(m)}
            className={cn(
              "flex min-h-14 items-center gap-3 rounded-xl border-2 p-3 text-left transition-colors duration-150",
              activo ? "border-primary bg-accent" : "border-border bg-card hover:bg-muted",
            )}
          >
            <Icono aria-hidden="true" className="size-6 shrink-0 text-marino" />
            <span className="flex flex-col">
              <span className="text-base leading-tight font-semibold">{nombre}</span>
              <span className="text-sm text-muted-foreground">{ayuda}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

/** Baja la imagen PNG de un trabajador (credencial completa o solo QR) y avisa si algo falla. */
export async function descargarImagen(datos: DatosCredencial, modo: ModoCredencial): Promise<void> {
  try {
    const imagen =
      modo === "completa"
        ? await credencialComoPng(datos)
        : await etiquetaQrComoPng({ codigo: datos.codigo, texto: textoDeEtiqueta(datos) });
    descargarBlob(imagen, nombreDeArchivo(modo === "completa" ? "credencial" : "codigo-qr", datos.codigo));
  } catch {
    aviso({ titulo: "No pudimos generar la imagen", descripcion: "Intenta de nuevo; si sigue igual, usa Imprimir y guarda como PDF.", tipo: "error" });
  }
}

interface PropiedadesVistaCredencial {
  datos: DatosCredencial;
  /** Modo con el que empieza. Por omisión, la credencial completa. */
  modoInicial?: ModoCredencial;
  className?: string;
}

/**
 * Vista de una sola credencial con sus acciones: elegir qué imprimir, descargar la imagen (PNG) e
 * imprimir o guardar como PDF. Es lo que se ofrece al dar de alta a alguien y en su ficha. El
 * llamador decide si la muestra: solo con el permiso `etiquetas.imprimir`.
 *
 * ```tsx
 * {puede("etiquetas.imprimir") ? <VistaCredencial datos={datos} /> : null}
 * ```
 */
export function VistaCredencial({ datos, modoInicial = "completa", className }: PropiedadesVistaCredencial) {
  const [modo, setModo] = useState<ModoCredencial>(modoInicial);
  const [descargando, setDescargando] = useState(false);
  const anchoVista = modo === "completa" ? (ANCHO_MM * 96) / 25.4 : (60 * 96) / 25.4;
  const { contenedor, escala } = useEscala(anchoVista, 1.4);

  async function descargar() {
    setDescargando(true);
    try {
      await descargarImagen(datos, modo);
    } finally {
      setDescargando(false);
    }
  }

  return (
    <div className={cn("flex flex-col gap-4", className)}>
      <SelectorModoCredencial modo={modo} alCambiar={setModo} />
      <div ref={contenedor} className="rounded-xl border bg-muted p-3">
        <div className="flex justify-center" style={{ zoom: escala }}>
          {modo === "completa" ? <TarjetaCredencial datos={datos} /> : <EtiquetaQrUnica datos={datos} />}
        </div>
      </div>
      <div className="flex flex-col gap-3">
        <Boton variante="normal" onClick={() => window.print()}>
          <PrinterIcon aria-hidden="true" />
          Imprimir / guardar como PDF
        </Boton>
        <Boton variante="contorno" cargando={descargando} onClick={() => void descargar()}>
          <DownloadIcon aria-hidden="true" />
          Descargar imagen (PNG)
        </Boton>
      </div>
      {/* Lo que sale en papel: la hoja carta; en pantalla no se ve. */}
      <ImpresionAparte>
        <EstiloImpresion />
        {modo === "completa" ? (
          <HojaCredenciales credenciales={[datos]} />
        ) : (
          <HojaEtiquetas etiquetas={[{ codigo: datos.codigo, texto: textoDeEtiqueta(datos) }]} />
        )}
      </ImpresionAparte>
    </div>
  );
}
