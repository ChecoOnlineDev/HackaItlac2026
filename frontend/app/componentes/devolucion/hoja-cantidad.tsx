import { MinusIcon, PlusIcon } from "lucide-react";
import { useEffect, useState } from "react";

import type { Condicion } from "~/componentes/dominio/tipos";
import { Boton } from "~/componentes/ui/boton";
import { Hoja } from "~/componentes/ui/hoja";
import { ControlCondicion } from "./control-condicion";

interface PropiedadesHojaCantidad {
  abierta: boolean;
  alCambiar: (abierta: boolean) => void;
  articulo: string;
  /** Lo que el trabajador todavía tiene por devolver de este artículo (ya sin lo agregado). */
  disponible: number;
  /** Cantidad con la que abre. */
  inicial?: number;
  alAgregar: (cantidad: number, condicion: Condicion) => void;
}

/**
 * Hoja para devolver un artículo por cantidad desde la lista del trabajador: cuánto (no más de lo que
 * tiene) y cómo regresa. Al agregar, el renglón entra a la devolución y el servidor lo vuelve a revisar.
 */
export function HojaCantidad({ abierta, alCambiar, articulo, disponible, inicial = 1, alAgregar }: PropiedadesHojaCantidad) {
  const [cantidad, setCantidad] = useState(inicial);
  const [condicion, setCondicion] = useState<Condicion | null>(null);
  const [intento, setIntento] = useState(false);

  useEffect(() => {
    if (abierta) {
      setCantidad(Math.min(Math.max(1, inicial), Math.max(1, disponible)));
      setCondicion(null);
      setIntento(false);
    }
  }, [abierta, inicial, disponible]);

  const agregar = () => {
    setIntento(true);
    if (!condicion) return;
    alAgregar(cantidad, condicion);
    alCambiar(false);
  };

  return (
    <Hoja
      abierta={abierta}
      alCambiar={alCambiar}
      titulo={`Devolver ${articulo}`}
      descripcion={`Todavía tiene ${disponible} por devolver.`}
      pie={
        <Boton variante="principal" onClick={agregar}>
          Agregar a la devolución
        </Boton>
      }
    >
      <div className="flex flex-col gap-5">
        <div className="flex flex-col gap-2">
          <p className="text-base font-medium">¿Cuántas regresa?</p>
          <div className="flex items-center gap-3" role="group" aria-label="Cantidad">
            <Boton variante="contorno" className="w-14 px-0" aria-label="Quitar una" disabled={cantidad <= 1} onClick={() => setCantidad((n) => Math.max(1, n - 1))}>
              <MinusIcon aria-hidden="true" />
            </Boton>
            <span className="min-w-16 text-center text-3xl font-bold tabular-nums" aria-live="polite">
              {cantidad}
            </span>
            <Boton variante="contorno" className="w-14 px-0" aria-label="Agregar una" disabled={cantidad >= disponible} onClick={() => setCantidad((n) => Math.min(disponible, n + 1))}>
              <PlusIcon aria-hidden="true" />
            </Boton>
          </div>
        </div>
        <div className="flex flex-col gap-2">
          <p className="text-base font-medium">¿Cómo regresa?</p>
          <ControlCondicion valor={condicion} alCambiar={setCondicion} />
          {intento && !condicion ? (
            <p role="alert" className="text-sm font-semibold text-destructive">
              Elige cómo regresa para continuar.
            </p>
          ) : null}
        </div>
      </div>
    </Hoja>
  );
}
