import { cn } from "cn";
import { EraserIcon } from "lucide-react";
import { useCallback, useEffect, useId, useImperativeHandle, useRef, useState, type PointerEvent, type Ref } from "react";

import { Boton } from "~/componentes/ui/boton";
import type { PuntoTrazo, Trazo } from "./tipos";

/** Tamaño lógico del lienzo; el CSS lo escala al ancho disponible, sin perder nitidez. */
const ANCHO = 900;
const ALTO = 450;
const GROSOR = 5;
/** Largo mínimo (en puntos del lienzo) para que algo cuente como firma. Un toque suelto no lo es. */
const LARGO_MINIMO = 60;

export interface FirmaExportada {
  /** PNG en `data:image/png;base64,…` sobre fondo blanco. */
  imagen: string;
  trazo: Trazo;
  ancho: number;
  alto: number;
}

export interface ManejadorFirma {
  borrar: () => void;
  /** La firma actual, o null si está vacía. */
  exportar: () => FirmaExportada | null;
}

export interface PropiedadesFirmaPad {
  /**
   * Se llama cuando termina cada trazo y al borrar. `vacia` es `true` si no hay firma;
   * entonces `imagen` es null y `trazo` queda en `[]`.
   */
  onCambio: (vacia: boolean, imagen: string | null, trazo: Trazo) => void;
  etiqueta?: string;
  deshabilitado?: boolean;
  className?: string;
  ref?: Ref<ManejadorFirma>;
}

function largoDeTrazos(trazos: Trazo): number {
  let total = 0;
  for (const t of trazos) {
    for (let i = 1; i < t.length; i++) total += Math.hypot(t[i].x - t[i - 1].x, t[i].y - t[i - 1].y);
  }
  return total;
}

/** Dibuja los trazos con curvas suaves (punto medio entre muestras). */
function dibujar(ctx: CanvasRenderingContext2D, trazos: Trazo) {
  ctx.save();
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, ANCHO, ALTO);
  ctx.strokeStyle = "#0a0a0a";
  ctx.fillStyle = "#0a0a0a";
  ctx.lineWidth = GROSOR;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  for (const t of trazos) {
    if (t.length === 0) continue;
    if (t.length < 3) {
      ctx.beginPath();
      ctx.arc(t[0].x, t[0].y, GROSOR / 2, 0, Math.PI * 2);
      ctx.fill();
      if (t.length === 2) {
        ctx.beginPath();
        ctx.moveTo(t[0].x, t[0].y);
        ctx.lineTo(t[1].x, t[1].y);
        ctx.stroke();
      }
      continue;
    }
    ctx.beginPath();
    ctx.moveTo(t[0].x, t[0].y);
    for (let i = 1; i < t.length - 1; i++) {
      const medioX = (t[i].x + t[i + 1].x) / 2;
      const medioY = (t[i].y + t[i + 1].y) / 2;
      ctx.quadraticCurveTo(t[i].x, t[i].y, medioX, medioY);
    }
    const ultimo = t[t.length - 1];
    ctx.lineTo(ultimo.x, ultimo.y);
    ctx.stroke();
  }
  ctx.restore();
}

/**
 * Recuadro para firmar con el dedo o el ratón. Exporta un PNG y el trazo. Una firma vacía (nada, o
 * solo un toque) cuenta como vacía.
 *
 * ```tsx
 * <FirmaPad onCambio={(vacia, imagen, trazo) => setFirma(vacia ? null : { imagen, trazo })} />
 * ```
 */
export function FirmaPad({ onCambio, etiqueta = "Firma del trabajador", deshabilitado = false, className, ref }: PropiedadesFirmaPad) {
  const id = useId();
  const lienzo = useRef<HTMLCanvasElement>(null);
  const trazos = useRef<Trazo>([]);
  const actual = useRef<PuntoTrazo[] | null>(null);
  const inicio = useRef(0);
  const [hayTinta, setHayTinta] = useState(false);
  const alCambiar = useRef(onCambio);
  useEffect(() => {
    alCambiar.current = onCambio;
  });

  const repintar = useCallback(() => {
    const ctx = lienzo.current?.getContext("2d");
    if (ctx) dibujar(ctx, actual.current ? [...trazos.current, actual.current] : trazos.current);
  }, []);

  useEffect(() => {
    repintar();
  }, [repintar]);

  const exportar = useCallback((): FirmaExportada | null => {
    if (largoDeTrazos(trazos.current) < LARGO_MINIMO || !lienzo.current) return null;
    return {
      imagen: lienzo.current.toDataURL("image/png"),
      trazo: trazos.current.map((t) => t.map((p) => ({ ...p }))),
      ancho: ANCHO,
      alto: ALTO,
    };
  }, []);

  const avisar = useCallback(() => {
    const firma = exportar();
    setHayTinta(trazos.current.length > 0);
    alCambiar.current(firma === null, firma?.imagen ?? null, firma?.trazo ?? []);
  }, [exportar]);

  const borrar = useCallback(() => {
    trazos.current = [];
    actual.current = null;
    repintar();
    setHayTinta(false);
    alCambiar.current(true, null, []);
  }, [repintar]);

  useImperativeHandle(ref, () => ({ borrar, exportar }), [borrar, exportar]);

  const punto = (e: PointerEvent<HTMLCanvasElement>): PuntoTrazo => {
    const caja = e.currentTarget.getBoundingClientRect();
    return {
      x: Math.round(((e.clientX - caja.left) / caja.width) * ANCHO * 10) / 10,
      y: Math.round(((e.clientY - caja.top) / caja.height) * ALTO * 10) / 10,
      t: Math.round(performance.now() - inicio.current),
    };
  };

  const alBajar = (e: PointerEvent<HTMLCanvasElement>) => {
    if (deshabilitado || (e.pointerType === "mouse" && e.button !== 0)) return;
    try {
      e.currentTarget.setPointerCapture(e.pointerId);
    } catch {
      // Sin captura el trazo sigue mientras el puntero esté dentro del recuadro.
    }
    if (trazos.current.length === 0) inicio.current = performance.now();
    actual.current = [punto(e)];
    setHayTinta(true);
    repintar();
  };
  const alMover = (e: PointerEvent<HTMLCanvasElement>) => {
    if (!actual.current) return;
    // Los navegadores agrupan muestras; se toman todas para que la curva salga suave.
    const nativos = e.nativeEvent.getCoalescedEvents?.() ?? [];
    const eventos = nativos.length > 0 ? nativos : [e.nativeEvent];
    const caja = e.currentTarget.getBoundingClientRect();
    for (const n of eventos) {
      actual.current.push({
        x: Math.round(((n.clientX - caja.left) / caja.width) * ANCHO * 10) / 10,
        y: Math.round(((n.clientY - caja.top) / caja.height) * ALTO * 10) / 10,
        t: Math.round(performance.now() - inicio.current),
      });
    }
    repintar();
  };
  const alSoltar = () => {
    const terminado = actual.current;
    if (!terminado) return;
    actual.current = null;
    trazos.current = [...trazos.current, terminado];
    repintar();
    avisar();
  };

  return (
    <div className={cn("flex flex-col gap-2", className)} data-slot="firma-pad">
      <div className="flex items-center justify-between gap-2">
        <p className="text-base font-semibold" id={`${id}-etiqueta`}>
          {etiqueta}
        </p>
        <Boton variante="contorno" onClick={borrar} disabled={deshabilitado || !hayTinta}>
          <EraserIcon aria-hidden="true" />
          Borrar
        </Boton>
      </div>
      <div className="relative w-full max-w-[640px] overflow-hidden rounded-xl border-2 border-foreground bg-white">
        <canvas
          ref={lienzo}
          width={ANCHO}
          height={ALTO}
          role="img"
          aria-labelledby={`${id}-etiqueta`}
          aria-describedby={`${id}-ayuda`}
          onPointerDown={alBajar}
          onPointerMove={alMover}
          onPointerUp={alSoltar}
          onPointerCancel={alSoltar}
          className={cn("block aspect-[2/1] w-full touch-none select-none", deshabilitado ? "cursor-not-allowed opacity-60" : "cursor-crosshair")}
        />
        {!hayTinta ? (
          <div aria-hidden="true" className="pointer-events-none absolute inset-x-6 bottom-10 flex items-end gap-2 border-b-2 border-dashed border-muted-foreground/60 pb-1">
            <span className="text-2xl font-bold text-muted-foreground/70">×</span>
            <span className="text-sm text-muted-foreground">Firma aquí</span>
          </div>
        ) : null}
      </div>
      <p id={`${id}-ayuda`} className="text-sm text-muted-foreground">
        Firma con el dedo o con el ratón dentro del recuadro. Si te equivocas, toca “Borrar”.
      </p>
    </div>
  );
}
