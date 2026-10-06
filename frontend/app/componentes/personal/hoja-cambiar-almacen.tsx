import { ArrowRightIcon, CircleAlertIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { apiPatch } from "~/api/cliente";
import { mensajeDeError } from "~/api/errores";
import { Boton } from "~/componentes/ui/boton";
import { aviso } from "~/componentes/ui/aviso";
import { Hoja } from "~/componentes/ui/hoja";
import { ListaDesplegable } from "~/componentes/ui/lista-desplegable";
import { Label } from "~/components/ui/label";
import { TEXTO_SIN_ALMACEN, type AlmacenOpcion, type PersonaAlmacen } from "./tipos";

interface Propiedades {
  persona: PersonaAlmacen | null;
  almacenes: AlmacenOpcion[];
  alCerrar: () => void;
  /** Recibe el renglón que responde el servidor, para actualizar la lista sin recargar. */
  alGuardar: (persona: PersonaAlmacen) => void;
}

/** Hoja para asignar o mover a una persona de almacén. El servidor decide si se puede; aquí solo se muestra su respuesta. */
export function HojaCambiarAlmacen({ persona, almacenes, alCerrar, alGuardar }: Propiedades) {
  const [valor, setValor] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setValor(persona?.almacen?.id ?? "");
    setError(null);
    setGuardando(false);
  }, [persona]);

  const actual = persona?.almacen?.nombre ?? TEXTO_SIN_ALMACEN;
  const nuevo = valor === "" ? TEXTO_SIN_ALMACEN : (almacenes.find((a) => a.id === valor)?.nombre ?? "");
  const sinCambio = (persona?.almacen?.id ?? "") === valor;

  async function guardar() {
    if (!persona || sinCambio) return;
    setGuardando(true);
    setError(null);
    try {
      const actualizada = await apiPatch<PersonaAlmacen>(`/usuarios/${persona.id}/almacen`, { almacen_id: valor === "" ? null : valor });
      aviso({
        tipo: "exito",
        titulo: actualizada.almacen
          ? `${persona.nombre} ahora trabaja en ${actualizada.almacen.nombre}`
          : `${persona.nombre} quedó sin almacén`,
      });
      alGuardar(actualizada);
    } catch (causa) {
      setError(mensajeDeError(causa));
      setGuardando(false);
    }
  }

  return (
    <Hoja
      abierta={persona !== null}
      alCambiar={(abierta) => {
        if (!abierta && !guardando) alCerrar();
      }}
      titulo="Cambiar almacén"
      descripcion={persona ? `${persona.nombre} · ${persona.rol.nombre}` : undefined}
      pie={
        <div className="grid grid-cols-2 gap-2">
          <Boton variante="contorno" onClick={alCerrar} disabled={guardando}>
            Cancelar
          </Boton>
          <Boton variante="normal" onClick={guardar} cargando={guardando} disabled={sinCambio}>
            Guardar
          </Boton>
        </div>
      }
    >
      {persona ? (
        <div className="flex flex-col gap-4">
          <p className="text-sm text-muted-foreground">
            Almacén actual: <span className="font-semibold text-foreground">{actual}</span>
          </p>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="almacen-nuevo" className="text-sm font-medium text-foreground">
              Almacén donde trabajará
            </Label>
            <ListaDesplegable
              id="almacen-nuevo"
              valor={valor}
              alCambiar={(v) => {
                setValor(v);
                setError(null);
              }}
              vacio={TEXTO_SIN_ALMACEN}
              opciones={almacenes.map((a) => ({ valor: a.id, texto: a.nombre }))}
              invalido={error !== null}
              descritoPor={error ? "almacen-error" : undefined}
            />
          </div>
          {!sinCambio ? (
            <p className="flex items-start gap-1.5 rounded-2xl border bg-accent p-3 text-sm text-marino">
              <ArrowRightIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-primary" />
              <span>
                {persona.nombre} pasará de <strong>{actual}</strong> a <strong>{nuevo}</strong>. Aplica en cuanto vuelva
                a usar el sistema; lo que ya hizo no cambia.
              </span>
            </p>
          ) : null}
          {error ? (
            <p id="almacen-error" role="alert" className="flex items-start gap-1.5 text-sm font-medium text-destructive">
              <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
              {error}
            </p>
          ) : null}
        </div>
      ) : null}
    </Hoja>
  );
}
