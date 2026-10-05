import { cn } from "cn";
import { ChevronLeftIcon, ChevronRightIcon, CircleAlertIcon, LockIcon } from "lucide-react";
import { useId, type ComponentProps, type ReactNode } from "react";

import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { ListaDesplegable } from "~/componentes/ui/lista-desplegable";
import { Label } from "~/components/ui/label";
import { Switch } from "~/components/ui/switch";

interface PropiedadesSeleccion {
  etiqueta: string;
  opciones: { valor: string; texto: string }[];
  value: string;
  alCambiar: (valor: string) => void;
  /** Texto de la primera opción vacía ("Todas las categorías"). Sin él no hay opción vacía. */
  vacio?: string;
  error?: string | null;
  ayuda?: string;
  claseContenedor?: string;
  /** Oculta la etiqueta a la vista (sigue disponible para lectores de pantalla). */
  etiquetaOculta?: boolean;
  id?: string;
  disabled?: boolean;
  className?: string;
}

/** Lista desplegable (`Select` de shadcn), de 44 px, con etiqueta y error junto al campo. */
export function Seleccion({
  etiqueta,
  opciones,
  vacio,
  error,
  ayuda,
  claseContenedor,
  etiquetaOculta,
  id,
  className,
  value,
  alCambiar,
  disabled,
}: PropiedadesSeleccion) {
  const generado = useId();
  const idCampo = id ?? generado;
  return (
    <div className={cn("flex flex-col gap-1.5", claseContenedor)}>
      <Label htmlFor={idCampo} className={cn("text-sm font-medium text-foreground", etiquetaOculta && "sr-only")}>
        {etiqueta}
      </Label>
      <ListaDesplegable
        id={idCampo}
        valor={value}
        alCambiar={alCambiar}
        opciones={opciones}
        vacio={vacio}
        deshabilitado={disabled}
        invalido={Boolean(error)}
        descritoPor={error ? `${idCampo}-error` : undefined}
        className={className}
      />
      {ayuda ? <p className="text-sm text-muted-foreground">{ayuda}</p> : null}
      {error ? (
        <p id={`${idCampo}-error`} role="alert" className="flex items-start gap-1.5 text-sm font-medium text-destructive">
          <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          {error}
        </p>
      ) : null}
    </div>
  );
}

/** Campo para un número entero positivo (días, cantidades). */
export function CampoEntero(props: Omit<ComponentProps<typeof Campo>, "type" | "inputMode">) {
  return <Campo type="number" inputMode="numeric" min={1} step={1} {...props} />;
}

interface PropiedadesInterruptor {
  titulo: string;
  ayuda?: string;
  activo: boolean;
  alCambiar: (activo: boolean) => void;
  disabled?: boolean;
  /** Se muestra solo cuando el interruptor está activo. */
  children?: ReactNode;
}

/**
 * Una regla con su interruptor. Dice "Sí" o "No" con texto, no solo con color.
 * Todo el renglón se puede tocar (44 px o más).
 */
export function FilaInterruptor({ titulo, ayuda, activo, alCambiar, disabled, children }: PropiedadesInterruptor) {
  return (
    <div className="rounded-2xl border bg-card p-4">
      <label className={cn("flex min-h-11 cursor-pointer items-center justify-between gap-4", disabled && "cursor-not-allowed opacity-70")}>
        <span className="flex min-w-0 flex-col">
          <span className="text-sm font-semibold">{titulo}</span>
          {ayuda ? <span className="text-xs text-muted-foreground">{ayuda}</span> : null}
        </span>
        <span className="flex shrink-0 items-center gap-2">
          <span className="w-6 text-right text-sm font-semibold" aria-hidden="true">
            {activo ? "Sí" : "No"}
          </span>
          <Switch checked={activo} onCheckedChange={alCambiar} disabled={disabled} aria-label={titulo} />
        </span>
      </label>
      {activo && children ? <div className="mt-3 flex flex-col gap-4 border-t pt-4">{children}</div> : null}
    </div>
  );
}

/** Nota con candado para lo que no se puede cambiar. */
export function NotaBloqueo({ children }: { children: ReactNode }) {
  return (
    <p className="flex items-start gap-2 rounded-2xl border bg-muted p-3 text-sm">
      <LockIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
      <span>{children}</span>
    </p>
  );
}

/** "Mostrando 1 a 20 de 53" con "Anterior" y "Siguiente". */
export function Paginador({
  pagina,
  tamano,
  total,
  alCambiar,
  ocupado,
}: {
  pagina: number;
  tamano: number;
  total: number;
  alCambiar: (pagina: number) => void;
  ocupado?: boolean;
}) {
  if (total === 0) return null;
  const desde = (pagina - 1) * tamano + 1;
  const hasta = Math.min(total, pagina * tamano);
  const ultima = Math.max(1, Math.ceil(total / tamano));
  return (
    <nav aria-label="Páginas" className="flex flex-wrap items-center justify-between gap-3">
      <p className="text-sm text-muted-foreground" aria-live="polite">
        Mostrando {desde} a {hasta} de {total}
      </p>
      <div className="flex gap-2">
        <Boton variante="contorno" disabled={pagina <= 1 || ocupado} onClick={() => alCambiar(pagina - 1)}>
          <ChevronLeftIcon aria-hidden="true" />
          Anterior
        </Boton>
        <Boton variante="contorno" disabled={pagina >= ultima || ocupado} onClick={() => alCambiar(pagina + 1)}>
          Siguiente
          <ChevronRightIcon aria-hidden="true" />
        </Boton>
      </div>
    </nav>
  );
}
