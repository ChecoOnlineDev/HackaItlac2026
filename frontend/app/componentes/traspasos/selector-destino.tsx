import { TruckIcon } from "lucide-react";
import { useId } from "react";

import { apiGet } from "~/api/cliente";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import type { AlmacenResumen } from "~/componentes/entrega/tipos";
import { EstadoError } from "~/componentes/ui/estado-error";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import type { AlmacenRedApi } from "./tipos";

interface PropiedadesSelectorDestino {
  /** Almacén del que sale el traspaso; no se ofrece como destino. */
  origenId: string | null;
  valor: string | null;
  alCambiar: (almacen: AlmacenResumen) => void;
  deshabilitado?: boolean;
  className?: string;
}

/**
 * "¿A dónde se envía?": las rutas habituales primero (Kepler con Contratistas y Contratistas con las áreas,
 * en los dos sentidos) y después las demás, que el servidor avisa como poco habituales (X-03). Solo ordena la
 * lista; quien decide el nivel de la ruta es el servidor.
 */
export function SelectorDestino({ origenId, valor, alCambiar, deshabilitado, className }: PropiedadesSelectorDestino) {
  const id = useId();
  const consulta = useConsulta((signal) => apiGet<AlmacenRedApi[]>("/almacenes", undefined, signal), "almacenes-red");

  if (consulta.error) return <EstadoError error={consulta.error} alReintentar={consulta.recargar} />;
  if (!consulta.datos) return <Esqueleto tipo="renglon" />;

  const activos = consulta.datos.filter((a) => a.estado === "ACTIVO" && a.id !== origenId);
  const origen = consulta.datos.find((a) => a.id === origenId);
  const esHabitual = (a: AlmacenRedApi) => Boolean(origen) && (origen!.padre_id === a.id || a.padre_id === origen!.id);
  const habituales = activos.filter(esHabitual);
  const otros = activos.filter((a) => !esHabitual(a));
  const opcion = (a: AlmacenRedApi) => (
    <option key={a.id} value={a.id}>
      {a.nombre} ({a.clave})
    </option>
  );

  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1.5 flex items-center gap-2 text-base font-medium">
        <TruckIcon aria-hidden="true" className="size-5 text-marino" />
        ¿A qué almacén se envía?
      </label>
      <select
        id={id}
        value={valor ?? ""}
        disabled={deshabilitado || !origenId}
        onChange={(e) => {
          const elegido = activos.find((a) => a.id === e.target.value);
          if (elegido) alCambiar({ id: elegido.id, clave: elegido.clave, nombre: elegido.nombre });
        }}
        className="h-12 w-full rounded-lg border border-input bg-background px-3 text-base disabled:opacity-60"
      >
        <option value="" disabled>
          {origenId ? "Elige el destino" : "Primero elige el almacén que opera"}
        </option>
        {habituales.length > 0 ? <optgroup label="Rutas habituales">{habituales.map(opcion)}</optgroup> : null}
        {otros.length > 0 ? <optgroup label="Otras rutas (se avisa antes de enviar)">{otros.map(opcion)}</optgroup> : null}
      </select>
    </div>
  );
}
