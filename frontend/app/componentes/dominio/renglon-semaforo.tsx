import { cn } from "cn";
import { CheckIcon, LockIcon, MinusIcon, PlusIcon, TrashIcon, TriangleAlertIcon, XIcon, MessageSquareTextIcon } from "lucide-react";
import { useState } from "react";

import { Boton } from "~/componentes/ui/boton";
import { Insignia } from "~/componentes/ui/insignia";
import { TecladoNumerico } from "./teclado-numerico";
import type { MotivoRegla, NivelSemaforo, RenglonEvaluado, TitularPieza } from "./tipos";

export const TEXTO_NIVEL: Record<NivelSemaforo, string> = {
  VERDE: "Listo",
  AMARILLO: "Aviso",
  NARANJA: "Requiere autorización",
  ROJO: "No se puede entregar",
};

const ICONO_NIVEL = {
  VERDE: CheckIcon,
  AMARILLO: TriangleAlertIcon,
  NARANJA: LockIcon,
  ROJO: XIcon,
} as const;

/** Colores reservados del semáforo (clases completas para que Tailwind las encuentre). */
const COLOR_FRANJA: Record<NivelSemaforo, string> = {
  VERDE: "bg-semaforo-verde",
  AMARILLO: "bg-semaforo-amarillo",
  NARANJA: "bg-semaforo-naranja",
  ROJO: "bg-semaforo-rojo",
};
const COLOR_FONDO: Record<NivelSemaforo, string> = {
  VERDE: "bg-card",
  AMARILLO: "bg-card",
  NARANJA: "bg-card",
  ROJO: "bg-semaforo-rojo/5",
};
const COLOR_TEXTO_ICONO: Record<NivelSemaforo, string> = {
  VERDE: "text-semaforo-verde",
  AMARILLO: "text-semaforo-amarillo",
  NARANJA: "text-semaforo-naranja",
  ROJO: "text-semaforo-rojo",
};

/** Nombre del titular, venga como texto o como objeto. */
export function nombreDeTitular(titular: TitularPieza): string | null {
  if (!titular) return null;
  return typeof titular === "string" ? titular : titular.nombre;
}

export type EstadoAutorizacion = "autorizado" | "en_espera" | null;

export interface PropiedadesRenglonSemaforo {
  /** El renglón tal como lo devuelve `evaluar`. */
  renglon: RenglonEvaluado;
  /** Si la cantidad se puede cambiar con − y +, o tecleándola. Sin esto solo se muestra. */
  onCantidad?: (cantidad: number) => void;
  /** "Quitar" siempre está disponible, sin importar el nivel. */
  onQuitar?: () => void;
  /** Muestra "Pedir autorización" en un renglón naranja que se puede autorizar. */
  onPedirAutorizacion?: () => void;
  /** Muestra "Agregar observación" cuando el servidor la pide (`pide_observacion`). */
  onObservacion?: () => void;
  /** Observación ya capturada, para mostrarla. */
  observacion?: string | null;
  /** `autorizado` pinta el renglón naranja como autorizado; `en_espera` indica que se espera al supervisor. */
  estadoAutorizacion?: EstadoAutorizacion;
  /** Resalta el renglón un instante (al agregarse). */
  resaltado?: boolean;
  /** Nota de la pantalla sobre este renglón (por ejemplo "Cambió; revísalo" tras revalidar). */
  nota?: string;
  /** Cantidad máxima al teclear. Por omisión 9999. */
  cantidadMaxima?: number;
  /** Cambia los textos de los niveles (por ejemplo "No se puede devolver"). */
  textos?: Partial<Record<NivelSemaforo, string>>;
  /** Bloquea los botones (mientras el servidor responde). */
  deshabilitado?: boolean;
  className?: string;
}

function Motivo({ motivo, textos }: { motivo: MotivoRegla; textos?: PropiedadesRenglonSemaforo["textos"] }) {
  const Icono = ICONO_NIVEL[motivo.nivel];
  return (
    <li className="flex items-start gap-2 text-sm leading-snug">
      <Icono aria-hidden="true" strokeWidth={3} className={cn("mt-1 size-4 shrink-0", COLOR_TEXTO_ICONO[motivo.nivel])} />
      <span className="min-w-0 flex-1">
        <span className="sr-only">{textos?.[motivo.nivel] ?? TEXTO_NIVEL[motivo.nivel]}: </span>
        {motivo.mensaje}
        {motivo.regla ? <span className="ml-1.5 text-xs font-medium whitespace-nowrap text-muted-foreground">({motivo.regla})</span> : null}
      </span>
    </li>
  );
}

/**
 * Un renglón de la lista de captura: franja de color, icono y texto del nivel, artículo con marca,
 * código o serie, cantidad con − y + (o teclado numérico al tocar el número) y los motivos que dio el
 * servidor. No evalúa nada: pinta lo que dice `renglon.nivel`.
 *
 * ```tsx
 * <RenglonSemaforo renglon={r} onQuitar={() => quitar(r)} onCantidad={(n) => cambiar(r, n)} />
 * ```
 */
export function RenglonSemaforo({
  renglon,
  onCantidad,
  onQuitar,
  onPedirAutorizacion,
  onObservacion,
  observacion,
  estadoAutorizacion = null,
  resaltado = false,
  nota,
  cantidadMaxima = 9999,
  textos,
  deshabilitado = false,
  className,
}: PropiedadesRenglonSemaforo) {
  const [teclado, setTeclado] = useState(false);
  const { nivel, articulo, pieza, cantidad } = renglon;
  const Icono = ICONO_NIVEL[nivel];
  const textoNivel = textos?.[nivel] ?? TEXTO_NIVEL[nivel];
  const nombre = articulo?.nombre ?? "Código desconocido";
  const detalleNombre = [articulo?.marca, articulo?.talla ? `Talla ${articulo.talla}` : null].filter(Boolean).join(" · ");
  const titular = nombreDeTitular(renglon.titular);
  const porCantidad = articulo?.control === "CANTIDAD";
  const autorizado = nivel === "NARANJA" && estadoAutorizacion === "autorizado";
  const enEspera = nivel === "NARANJA" && estadoAutorizacion === "en_espera";
  const puedePedir = nivel === "NARANJA" && renglon.autorizable && !autorizado && !enEspera && onPedirAutorizacion;
  const editable = porCantidad && Boolean(onCantidad);

  return (
    <div
      role="group"
      aria-label={`${nombre}. ${textoNivel}`}
      data-nivel={nivel}
      className={cn(
        "flex overflow-hidden rounded-2xl border transition-colors duration-150 motion-reduce:transition-none",
        resaltado ? "bg-accent ring-2 ring-primary" : COLOR_FONDO[nivel],
        nota && "ring-2 ring-semaforo-rojo",
        className,
      )}
    >
      <div aria-hidden="true" className={cn("w-2 shrink-0", COLOR_FRANJA[nivel])} />
      <div className="flex min-w-0 flex-1 flex-col gap-2 p-3">
        <div className="flex items-start gap-3">
          <span
            aria-hidden="true"
            className={cn("mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full text-white", COLOR_FRANJA[nivel])}
          >
            <Icono className="size-4" strokeWidth={3} />
          </span>
          <div className="flex min-w-0 flex-1 flex-col">
            <p className="text-base leading-tight font-semibold wrap-break-word">{nombre}</p>
            {detalleNombre ? <p className="text-sm text-muted-foreground">{detalleNombre}</p> : null}
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground">{renglon.codigo}</span>
              {pieza?.numero_serie ? ` · Serie ${pieza.numero_serie}` : ""}
              {porCantidad && renglon.disponible !== null ? ` · Hay ${renglon.disponible}` : ""}
            </p>
            {titular ? <p className="text-sm">La tiene: <span className="font-semibold">{titular}</span></p> : null}
          </div>
        </div>

        <p className="flex flex-wrap items-center gap-2 text-sm font-semibold">
          <span className={cn(nivel === "ROJO" && "text-semaforo-rojo")}>{textoNivel}</span>
          {autorizado ? <Insignia estado="verde">Autorizado</Insignia> : null}
          {enEspera ? <Insignia estado="neutra">Esperando al supervisor</Insignia> : null}
        </p>

        {renglon.motivos.length > 0 ? (
          <ul className="flex flex-col gap-1">
            {renglon.motivos.map((m, i) => (
              <Motivo key={`${m.regla}-${i}`} motivo={m} textos={textos} />
            ))}
          </ul>
        ) : null}

        {observacion ? (
          <p className="rounded-xl bg-muted p-2 text-sm">
            <span className="font-semibold">Observación: </span>
            {observacion}
          </p>
        ) : null}
        {nota ? (
          <p role="alert" className="text-sm font-semibold text-semaforo-rojo">
            {nota}
          </p>
        ) : null}

        <div className="mt-1 flex flex-wrap items-center justify-between gap-2">
          {editable ? (
            <div className="flex items-center gap-1" role="group" aria-label="Cantidad">
              <Boton
                variante="contorno"
                className="w-10 px-0"
                aria-label="Quitar una"
                disabled={deshabilitado || cantidad <= 1}
                onClick={() => onCantidad?.(Math.max(1, cantidad - 1))}
              >
                <MinusIcon aria-hidden="true" />
              </Boton>
              <button
                type="button"
                aria-label={`Cantidad ${cantidad}. Toca para teclearla`}
                disabled={deshabilitado}
                onClick={() => setTeclado(true)}
                className="h-10 min-w-12 rounded-xl border border-input bg-background px-3 text-base font-semibold tabular-nums hover:bg-muted disabled:opacity-50"
              >
                {cantidad}
              </button>
              <Boton
                variante="contorno"
                className="w-10 px-0"
                aria-label="Agregar una"
                disabled={deshabilitado || cantidad >= cantidadMaxima}
                onClick={() => onCantidad?.(Math.min(cantidadMaxima, cantidad + 1))}
              >
                <PlusIcon aria-hidden="true" />
              </Boton>
            </div>
          ) : (
            <p className="text-base">
              Cantidad: <span className="text-lg font-semibold tabular-nums">{cantidad}</span>
            </p>
          )}

          <div className="flex flex-wrap items-center gap-2">
            {renglon.pide_observacion && onObservacion ? (
              <Boton variante="secundario" disabled={deshabilitado} onClick={onObservacion}>
                <MessageSquareTextIcon aria-hidden="true" />
                {observacion ? "Cambiar observación" : "Agregar observación"}
              </Boton>
            ) : null}
            {puedePedir ? (
              <Boton
                variante="contorno"
                disabled={deshabilitado}
                onClick={onPedirAutorizacion}
                className="border border-semaforo-naranja bg-semaforo-naranja/10 font-semibold hover:bg-semaforo-naranja/20"
              >
                <LockIcon aria-hidden="true" />
                Pedir autorización
              </Boton>
            ) : null}
            {onQuitar ? (
              <Boton variante="texto" disabled={deshabilitado} onClick={onQuitar} aria-label={`Quitar ${nombre}`}>
                <TrashIcon aria-hidden="true" />
                Quitar
              </Boton>
            ) : null}
          </div>
        </div>
      </div>

      {editable ? (
        <TecladoNumerico
          abierto={teclado}
          alCambiar={setTeclado}
          valorInicial={cantidad}
          maximo={cantidadMaxima}
          titulo="¿Cuántas piezas?"
          descripcion={nombre}
          alAceptar={(n) => onCantidad?.(n)}
        />
      ) : null}
    </div>
  );
}
