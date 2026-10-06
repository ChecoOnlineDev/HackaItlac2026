import { ListFilterIcon } from "lucide-react";
import { useState, type ReactNode } from "react";

import { Boton } from "./boton";
import { Hoja } from "./hoja";

interface PropiedadesHojaFiltros<T extends Record<string, string>> {
  /** Filtros que ya se aplican (cada valor es texto; "" es "sin filtro"). */
  valores: T;
  /** Cuántos filtros están activos: es el número del botón. */
  activos: number;
  /** Se llama con el borrador completo al tocar "Aplicar". */
  alAplicar: (valores: T) => void;
  /** Se llama al tocar "Limpiar": quita todos los filtros. */
  alLimpiar: () => void;
  /** Los campos. Reciben el borrador y una función para cambiarlo; nada se aplica hasta "Aplicar". */
  children: (borrador: T, cambiar: (parcial: Partial<T>) => void) => ReactNode;
  titulo?: string;
}

/**
 * Botón "Filtros" con el contador de filtros activos y la hoja lateral con sus campos: entra por la
 * derecha en computadora y sube desde abajo en celular. La búsqueda por texto no va aquí: queda fuera,
 * siempre visible. Al pie, "Limpiar" y "Aplicar".
 */
export function HojaFiltros<T extends Record<string, string>>({
  valores,
  activos,
  alAplicar,
  alLimpiar,
  children,
  titulo = "Filtros",
}: PropiedadesHojaFiltros<T>) {
  const [abierta, setAbierta] = useState(false);
  const [borrador, setBorrador] = useState<T>(valores);

  const abrir = () => {
    setBorrador(valores);
    setAbierta(true);
  };

  return (
    <>
      <Boton variante="contorno" onClick={abrir} aria-haspopup="dialog" className="shrink-0">
        <ListFilterIcon aria-hidden="true" />
        Filtros
        {activos > 0 ? (
          <span className="inline-flex min-w-5 items-center justify-center rounded-full bg-primary px-1.5 text-xs font-semibold text-primary-foreground tabular-nums">
            {activos}
            <span className="sr-only">{activos === 1 ? " filtro activo" : " filtros activos"}</span>
          </span>
        ) : null}
      </Boton>
      <Hoja
        abierta={abierta}
        alCambiar={setAbierta}
        titulo={titulo}
        pie={
          <div className="grid grid-cols-2 gap-2">
            <Boton
              variante="contorno"
              onClick={() => {
                alLimpiar();
                setAbierta(false);
              }}
            >
              Limpiar
            </Boton>
            <Boton
              variante="normal"
              onClick={() => {
                alAplicar(borrador);
                setAbierta(false);
              }}
            >
              Aplicar
            </Boton>
          </div>
        }
      >
        <div className="flex flex-col gap-4">{children(borrador, (parcial) => setBorrador((b) => ({ ...b, ...parcial })))}</div>
      </Hoja>
    </>
  );
}
