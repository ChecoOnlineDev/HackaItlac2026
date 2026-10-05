import { cn } from "cn";

import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue } from "~/components/ui/select";

export interface OpcionLista {
  valor: string;
  texto: string;
  /** Si lo trae, la opción se muestra bajo ese encabezado. */
  grupo?: string;
}

interface PropiedadesLista {
  id?: string;
  /** Valor elegido; "" es "ninguno" (se muestra `vacio` o `marcador`). */
  valor: string;
  alCambiar: (valor: string) => void;
  opciones: OpcionLista[];
  /** Texto de la opción vacía (valor ""), que también se puede volver a elegir. */
  vacio?: string;
  /** Texto cuando no hay nada elegido y no hay opción vacía. */
  marcador?: string;
  deshabilitado?: boolean;
  invalido?: boolean;
  descritoPor?: string;
  className?: string;
}

/** Lista desplegable de 48 px sobre el `Select` de shadcn: en el celular se abre como panel táctil. */
export function ListaDesplegable({
  id,
  valor,
  alCambiar,
  opciones,
  vacio,
  marcador,
  deshabilitado,
  invalido,
  descritoPor,
  className,
}: PropiedadesLista) {
  const todas: OpcionLista[] = vacio !== undefined ? [{ valor: "", texto: vacio }, ...opciones] : opciones;
  // `items` le dice al selector qué texto mostrar para cada valor, aunque la lista esté cerrada.
  const items = todas.map((o) => ({ value: o.valor, label: o.texto }));
  const grupos = [...new Set(opciones.map((o) => o.grupo).filter((g): g is string => Boolean(g)))];
  const sinGrupo = opciones.filter((o) => !o.grupo);

  const item = (o: OpcionLista) => (
    <SelectItem key={o.valor} value={o.valor} className="min-h-11 text-base">
      {o.texto}
    </SelectItem>
  );

  return (
    <Select
      value={valor === "" && vacio === undefined ? null : valor}
      onValueChange={(v) => alCambiar(v ?? "")}
      items={items}
      disabled={deshabilitado}
    >
      <SelectTrigger
        id={id}
        aria-invalid={invalido ? true : undefined}
        aria-describedby={descritoPor}
        className={cn("w-full min-w-0 rounded-lg px-3 text-base data-[size=default]:h-12", className)}
      >
        <SelectValue placeholder={marcador ?? vacio ?? "Elige una opción"} />
      </SelectTrigger>
      <SelectContent alignItemWithTrigger={false} className="max-h-72">
        {vacio !== undefined ? item({ valor: "", texto: vacio }) : null}
        {sinGrupo.map(item)}
        {grupos.map((g) => (
          <SelectGroup key={g}>
            <SelectLabel className="px-2 py-1.5 text-sm">{g}</SelectLabel>
            {opciones.filter((o) => o.grupo === g).map(item)}
          </SelectGroup>
        ))}
      </SelectContent>
    </Select>
  );
}
