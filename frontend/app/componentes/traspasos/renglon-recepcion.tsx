import { cn } from "cn";
import { CheckIcon, MinusIcon, PlusIcon, TriangleAlertIcon, XIcon } from "lucide-react";
import { memo, useEffect, useId, useRef } from "react";

import { Checkbox } from "~/components/ui/checkbox";
import type { MotivoRegla, NivelSemaforo } from "~/componentes/dominio/tipos";
import { Boton } from "~/componentes/ui/boton";
import type { RenglonPorRecibirApi } from "./tipos";

const SIN_MOTIVOS: MotivoRegla[] = [];

const FRANJA: Record<NivelSemaforo, string> = {
  VERDE: "bg-semaforo-verde",
  AMARILLO: "bg-semaforo-amarillo",
  NARANJA: "bg-semaforo-naranja",
  ROJO: "bg-semaforo-rojo",
};

interface PropiedadesRenglonRecepcion {
  renglon: RenglonPorRecibirApi;
  /** Cuántas piezas o unidades se marcaron como recibidas ahora (0 = sin marcar). */
  marcado: number;
  /** Estable entre dibujos (así el renglón no se redibuja si no cambió): recibe la clave del renglón y la cantidad. */
  alMarcar?: (clave: string, cantidad: number) => void;
  /** Clave con la que `alMarcar` identifica este renglón. */
  clave?: string;
  /** Cambia cada vez que se acaba de escanear este renglón: destello verde breve. */
  destello?: number;
  /** Lo que dijo el servidor de este renglón (por ejemplo X-12). */
  nivel?: NivelSemaforo;
  motivos?: MotivoRegla[];
  /** Solo se muestra: sin casilla (traspaso de otro almacén o ya recibido). */
  soloLectura?: boolean;
  deshabilitado?: boolean;
}

/**
 * Un renglón de un traspaso que se está recibiendo: casilla de recibido de 48 px (toda la fila es el botón),
 * lo enviado, lo ya recibido y lo que falta. En un artículo por cantidad, − y + dicen cuántas unidades llegaron.
 */
export const RenglonRecepcion = memo(function RenglonRecepcion({
  renglon,
  marcado,
  alMarcar: alMarcarClave,
  clave = "",
  destello = 0,
  nivel,
  motivos = SIN_MOTIVOS,
  soloLectura = false,
  deshabilitado = false,
}: PropiedadesRenglonRecepcion) {
  const alMarcar = alMarcarClave ? (cantidad: number) => alMarcarClave(clave, cantidad) : undefined;
  const raiz = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!destello) return;
    try {
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      raiz.current?.animate(
        [{ backgroundColor: "rgb(34 197 94 / 0.35)" }, { backgroundColor: "rgb(34 197 94 / 0)" }],
        { duration: 1000, easing: "ease-out" },
      );
    } catch {
      // Sin animación el renglón se marca igual.
    }
  }, [destello]);
  const idCasilla = useId();
  const porCantidad = renglon.pieza_id === null;
  const completo = renglon.cantidad_pendiente <= 0;
  const marcada = marcado > 0;
  const detalleNombre = [renglon.marca, renglon.talla ? `Talla ${renglon.talla}` : null].filter(Boolean).join(" · ");
  const identificador = porCantidad
    ? `Código ${renglon.codigo}`
    : `Pieza ${renglon.codigo}${renglon.numero_serie ? ` · Serie ${renglon.numero_serie}` : ""}`;
  const puedeMarcar = !soloLectura && !completo && Boolean(alMarcar) && !deshabilitado;

  return (
    <div
      ref={raiz}
      role="group"
      aria-label={`${renglon.articulo}. ${completo ? "Ya recibido" : marcada ? "Marcado como recibido" : "Sin marcar"}`}
      className={cn("flex overflow-hidden rounded-2xl border bg-card", nivel === "ROJO" && "bg-semaforo-rojo/5 ring-2 ring-semaforo-rojo")}
    >
      {nivel ? <span aria-hidden="true" className={cn("w-2 shrink-0", FRANJA[nivel])} /> : null}
      <div className="flex min-w-0 flex-1 flex-col gap-2 p-3">
        {(() => {
          const contenido = (
            <>
              {soloLectura ? null : (
                <span className="flex size-12 shrink-0 items-center justify-center">
                  {completo ? (
                    <CheckIcon aria-hidden="true" className="size-6 text-semaforo-verde" strokeWidth={3} />
                  ) : (
                    <Checkbox
                      id={idCasilla}
                      checked={marcada}
                      disabled={!puedeMarcar}
                      onCheckedChange={(marcar) => alMarcar?.(marcar ? renglon.cantidad_pendiente : 0)}
                      className="size-7 rounded-md [&_svg]:size-5"
                    />
                  )}
                </span>
              )}
              <span className="flex min-h-12 min-w-0 flex-1 flex-col justify-center">
                <span className="text-base leading-snug font-semibold">{renglon.articulo}</span>
                {detalleNombre ? <span className="text-sm text-muted-foreground">{detalleNombre}</span> : null}
                <span className="text-sm text-muted-foreground">{identificador}</span>
              </span>
            </>
          );
          // Toda la fila es la casilla: se acierta con guantes o con prisa.
          return puedeMarcar ? (
            <label htmlFor={idCasilla} className="flex cursor-pointer items-start gap-3">
              {contenido}
            </label>
          ) : (
            <div className="flex items-start gap-3">{contenido}</div>
          );
        })()}

        <p className="text-base">
          Enviado: <strong>{renglon.cantidad_enviada}</strong>
          {soloLectura ? null : (
            <>
              {renglon.cantidad_recibida > 0 ? (
                <>
                  {" · "}Ya recibido: <strong>{renglon.cantidad_recibida}</strong>
                </>
              ) : null}
              {" · "}
              {completo ? (
                <span className="font-semibold">Ya se recibió completo</span>
              ) : (
                <>
                  Falta: <strong>{renglon.cantidad_pendiente}</strong>
                </>
              )}
            </>
          )}
        </p>

        {porCantidad && marcada && !soloLectura && !completo && alMarcar ? (
          <div className="flex flex-wrap items-center gap-2" role="group" aria-label={`Cuántas llegaron de ${renglon.articulo}`}>
            <span className="text-base font-medium">Llegaron:</span>
            <Boton variante="contorno" className="size-12 p-0" aria-label="Una menos" disabled={deshabilitado || marcado <= 1} onClick={() => alMarcar(marcado - 1)}>
              <MinusIcon aria-hidden="true" />
            </Boton>
            <span aria-live="polite" className="min-w-10 text-center text-lg font-semibold tabular-nums">
              {marcado}
            </span>
            <Boton variante="contorno" className="size-12 p-0" aria-label="Una más" disabled={deshabilitado || marcado >= renglon.cantidad_pendiente} onClick={() => alMarcar(marcado + 1)}>
              <PlusIcon aria-hidden="true" />
            </Boton>
            <span className="text-sm text-muted-foreground">de {renglon.cantidad_pendiente}</span>
          </div>
        ) : null}

        {motivos.length > 0 ? (
          <ul className="flex flex-col gap-1">
            {motivos.map((m, i) => (
              <li key={`${m.regla}-${i}`} className="flex items-start gap-2 text-base leading-snug">
                {m.nivel === "ROJO" ? (
                  <XIcon aria-hidden="true" strokeWidth={3} className="mt-1 size-4 shrink-0 text-semaforo-rojo" />
                ) : (
                  <TriangleAlertIcon aria-hidden="true" strokeWidth={3} className="mt-1 size-4 shrink-0 text-semaforo-amarillo" />
                )}
                <span>
                  <span className="sr-only">{m.nivel === "ROJO" ? "No se puede recibir" : "Aviso"}: </span>
                  {m.mensaje}
                </span>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </div>
  );
});
