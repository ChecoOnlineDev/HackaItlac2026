import { cn } from "cn";
import { CheckIcon, ClockIcon, MinusIcon, PlusIcon, ZapIcon } from "lucide-react";
import { useState, type ReactNode } from "react";

import { TecladoNumerico } from "~/componentes/dominio/teclado-numerico";
import { Boton } from "~/componentes/ui/boton";
import { MOTIVOS_RAPIDOS, type Urgencia } from "./tipos";

const CANTIDAD_EN_TECLADO = 9999;

/** Bloque del formulario: título de sección y su contenido. Una pregunta por bloque. */
export function Bloque({ id, titulo, ayuda, children }: { id: string; titulo: string; ayuda?: string; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className="flex flex-col gap-3">
      <div className="flex flex-col gap-0.5">
        <h2 id={id} className="text-base font-semibold text-marino">
          {titulo}
        </h2>
        {ayuda ? <p className="text-sm text-muted-foreground">{ayuda}</p> : null}
      </div>
      {children}
    </section>
  );
}

interface PropiedadesCantidad {
  valor: number;
  alCambiar: (cantidad: number) => void;
  deshabilitado?: boolean;
  /** Para el título del teclado: "Llave métrica 24 mm". */
  descripcion?: string;
  error?: string | null;
}

/** Cantidad con menos, más y el número en grande: al tocarlo abre el teclado numérico. */
export function ControlCantidad({ valor, alCambiar, deshabilitado, descripcion, error }: PropiedadesCantidad) {
  const [teclado, setTeclado] = useState(false);
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2" role="group" aria-label="Cantidad">
        <Boton
          variante="contorno"
          className="h-12 w-12 px-0"
          aria-label="Quitar una"
          disabled={deshabilitado || valor <= 1}
          onClick={() => alCambiar(Math.max(1, valor - 1))}
        >
          <MinusIcon aria-hidden="true" />
        </Boton>
        <button
          type="button"
          aria-label={`Cantidad ${valor}. Toca para teclearla`}
          aria-invalid={error ? true : undefined}
          disabled={deshabilitado}
          onClick={() => setTeclado(true)}
          className={cn(
            "h-12 min-w-24 rounded-xl border border-input bg-background px-4 text-2xl font-semibold tabular-nums hover:bg-muted disabled:opacity-50",
            error && "border-destructive",
          )}
        >
          {valor}
        </button>
        <Boton
          variante="contorno"
          className="h-12 w-12 px-0"
          aria-label="Agregar una"
          disabled={deshabilitado || valor >= CANTIDAD_EN_TECLADO}
          onClick={() => alCambiar(Math.min(CANTIDAD_EN_TECLADO, valor + 1))}
        >
          <PlusIcon aria-hidden="true" />
        </Boton>
      </div>
      {error ? (
        <p role="alert" className="text-sm font-medium text-destructive">
          {error}
        </p>
      ) : null}
      <TecladoNumerico
        abierto={teclado}
        alCambiar={setTeclado}
        valorInicial={valor}
        maximo={CANTIDAD_EN_TECLADO}
        titulo="¿Cuántas se necesitan?"
        descripcion={descripcion}
        alAceptar={alCambiar}
      />
    </div>
  );
}

interface PropiedadesMotivos {
  motivo: string;
  otro: boolean;
  deshabilitado?: boolean;
  /** Elegir una respuesta rápida llena el motivo; "Otro" lo vacía y deja escribirlo. */
  alElegir: (texto: string, otro: boolean) => void;
}

/** Respuestas rápidas de "¿Para qué trabajo?": chips táctiles de 40 px. Se puede escribir otra cosa debajo. */
export function ChipsMotivo({ motivo, otro, deshabilitado, alElegir }: PropiedadesMotivos) {
  return (
    <div role="group" aria-label="Respuestas rápidas" className="flex flex-wrap gap-2">
      {MOTIVOS_RAPIDOS.map((texto) => {
        const esOtro = texto === "Otro";
        const activo = esOtro ? otro : motivo === texto;
        return (
          <button
            key={texto}
            type="button"
            aria-pressed={activo}
            disabled={deshabilitado}
            onClick={() => alElegir(esOtro ? "" : texto, esOtro)}
            className={cn(
              "inline-flex h-10 items-center gap-1.5 rounded-full border px-4 text-sm font-semibold transition-colors disabled:opacity-50",
              activo ? "border-primary bg-primary text-primary-foreground" : "border-input bg-background hover:bg-muted",
            )}
          >
            {activo ? <CheckIcon aria-hidden="true" className="size-4" strokeWidth={3} /> : null}
            {texto}
          </button>
        );
      })}
    </div>
  );
}

interface PropiedadesUrgencia {
  valor: Urgencia;
  alCambiar: (urgencia: Urgencia) => void;
  deshabilitado?: boolean;
}

const OPCIONES_URGENCIA: { valor: Urgencia; titulo: string; ayuda: string; icono: typeof ZapIcon }[] = [
  { valor: "URGENTE", titulo: "Urgente", ayuda: "Se necesita ya", icono: ZapIcon },
  { valor: "NORMAL", titulo: "Normal", ayuda: "Puede esperar unos días", icono: ClockIcon },
];

/** Dos opciones grandes. Urgente viene elegida (SC-02). */
export function OpcionesUrgencia({ valor, alCambiar, deshabilitado }: PropiedadesUrgencia) {
  return (
    <div role="group" aria-label="Urgencia" className="grid grid-cols-2 gap-3">
      {OPCIONES_URGENCIA.map(({ valor: v, titulo, ayuda, icono: Icono }) => {
        const activo = valor === v;
        return (
          <button
            key={v}
            type="button"
            aria-pressed={activo}
            disabled={deshabilitado}
            onClick={() => alCambiar(v)}
            className={cn(
              "flex min-h-20 flex-col items-start gap-1 rounded-2xl border-2 p-3 text-left transition-colors disabled:opacity-50",
              activo ? "border-primary bg-accent" : "border-input bg-background hover:bg-muted",
            )}
          >
            <span className="flex w-full items-center justify-between gap-2">
              <span className="flex items-center gap-1.5 text-base font-semibold text-marino">
                <Icono aria-hidden="true" className="size-4" strokeWidth={2.5} />
                {titulo}
              </span>
              {activo ? <CheckIcon aria-hidden="true" className="size-5 text-primary" strokeWidth={3} /> : null}
            </span>
            <span className="text-sm text-muted-foreground">{ayuda}</span>
          </button>
        );
      })}
    </div>
  );
}
