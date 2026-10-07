import { CheckIcon, GraduationCapIcon } from "lucide-react";
import { useState } from "react";

import { Boton } from "~/componentes/ui/boton";
import { Hoja } from "~/componentes/ui/hoja";
import { useTutorial } from "./proveedor";

/** Interruptor «Tutorial» con la lista de recorridos que la sesión permite. */
export function InterruptorTutorial({ className, alIniciar }: { className?: string; alIniciar?: () => void }) {
  const { activo, recorrido, recorridosDisponibles, terminados, encender, apagar, iniciar } = useTutorial();

  return (
    <div className={className}>
      <Boton
        variante={activo ? "normal" : "contorno"}
        role="switch"
        aria-checked={activo}
        className="w-full"
        onClick={activo ? apagar : encender}
      >
        <GraduationCapIcon aria-hidden="true" />
        Tutorial: {activo ? "encendido" : "apagado"}
      </Boton>
      {activo ? (
        <div className="mt-2 flex flex-col gap-2">
          {recorrido ? (
            <p className="text-sm text-muted-foreground">En curso: {recorrido.titulo}</p>
          ) : recorridosDisponibles.length === 0 ? (
            <p className="text-sm text-muted-foreground">No hay recorridos para tu usuario.</p>
          ) : (
            <>
              <p className="text-sm text-muted-foreground">Elige qué quieres practicar.</p>
              {recorridosDisponibles.map((r) => {
                const hecho = terminados.includes(r.id);
                return (
                  <Boton
                    key={r.id}
                    variante="contorno"
                    className="h-12 justify-start"
                    onClick={() => {
                      iniciar(r.id);
                      alIniciar?.();
                    }}
                  >
                    {hecho ? <CheckIcon aria-hidden="true" className="text-primary" /> : null}
                    {r.titulo}
                    {hecho ? <span className="sr-only"> (ya lo hiciste)</span> : null}
                  </Boton>
                );
              })}
            </>
          )}
        </div>
      ) : null}
    </div>
  );
}

/** Versión para el encabezado móvil: un botón que abre una hoja con el interruptor y la lista. */
export function InterruptorTutorialCompacto() {
  const { activo } = useTutorial();
  const [abierta, setAbierta] = useState(false);
  return (
    <>
      <Boton variante="texto" className="text-marino" onClick={() => setAbierta(true)}>
        <GraduationCapIcon aria-hidden="true" />
        Tutorial
        {activo ? <span className="sr-only"> (encendido)</span> : null}
        {activo ? <span aria-hidden="true" className="size-2 rounded-full bg-primary" /> : null}
      </Boton>
      <Hoja abierta={abierta} alCambiar={setAbierta} titulo="Tutorial">
        <InterruptorTutorial alIniciar={() => setAbierta(false)} />
      </Hoja>
    </>
  );
}
