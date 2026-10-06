import { CircleAlertIcon, PackageIcon, PencilLineIcon, SearchIcon } from "lucide-react";

import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { BuscadorArticuloCompra } from "./buscador-articulo";
import { LARGO_MAXIMO_TEXTO, type ArticuloElegido } from "./tipos";

interface Propiedades {
  sinCatalogo: boolean;
  articulo: ArticuloElegido | null;
  descripcion: string;
  deshabilitado?: boolean;
  error?: string | null;
  alCambiar: (parcial: { sinCatalogo?: boolean; articulo?: ArticuloElegido | null; descripcion?: string }) => void;
}

/**
 * "¿Qué hace falta?": un artículo del catálogo o, si el equipo no existe en el catálogo, su descripción con
 * texto libre (SC-02). Elegir uno de los dos modos no borra lo escrito en el otro hasta que se envía.
 */
export function QueHaceFalta({ sinCatalogo, articulo, descripcion, deshabilitado, error, alCambiar }: Propiedades) {
  if (sinCatalogo) {
    return (
      <div className="flex flex-col gap-3">
        <Campo
          etiqueta="Describe lo que necesitas"
          placeholder="Por ejemplo: Llave métrica 24 mm"
          value={descripcion}
          maxLength={LARGO_MAXIMO_TEXTO}
          disabled={deshabilitado}
          error={error}
          autoComplete="off"
          onChange={(e) => alCambiar({ descripcion: e.target.value })}
          ayuda="Escribe el nombre, la medida o la marca, como lo dirías en el almacén."
        />
        <div>
          <Boton variante="texto" disabled={deshabilitado} onClick={() => alCambiar({ sinCatalogo: false })}>
            <SearchIcon aria-hidden="true" />
            Mejor buscarlo en el catálogo
          </Boton>
        </div>
      </div>
    );
  }

  if (articulo) {
    return (
      <div className="flex flex-col gap-2">
        <div className="flex items-start gap-3 rounded-2xl border-2 border-primary bg-accent p-3">
          <PackageIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-marino" />
          <div className="min-w-0 flex-1">
            <p className="text-base leading-tight font-semibold">{articulo.nombre}</p>
            <p className="text-sm text-muted-foreground">{[articulo.codigo, articulo.marca].filter(Boolean).join(" · ")}</p>
          </div>
          <Boton variante="contorno" disabled={deshabilitado} onClick={() => alCambiar({ articulo: null })}>
            Cambiar
          </Boton>
        </div>
        {error ? (
          <p role="alert" className="flex items-start gap-1.5 text-sm font-medium text-destructive">
            <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
            {error}
          </p>
        ) : null}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <BuscadorArticuloCompra deshabilitado={deshabilitado} alElegir={(a) => alCambiar({ articulo: a })} />
      {error ? (
        <p role="alert" className="flex items-start gap-1.5 text-sm font-medium text-destructive">
          <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          {error}
        </p>
      ) : null}
      <div>
        <Boton variante="contorno" disabled={deshabilitado} onClick={() => alCambiar({ sinCatalogo: true })}>
          <PencilLineIcon aria-hidden="true" />
          No está en el catálogo
        </Boton>
      </div>
    </div>
  );
}
