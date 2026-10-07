import { TruckIcon } from "lucide-react";
import { useId } from "react";

import { apiGet } from "~/api/cliente";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import type { AlmacenResumen } from "~/componentes/entrega/tipos";
import { ListaDesplegable } from "~/componentes/ui/lista-desplegable";
import { EstadoError } from "~/componentes/ui/estado-error";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import type { AlmacenRedApi } from "./tipos";

interface PropiedadesSelectorDestino {
  /** Almacén del que sale el traspaso; no se ofrece como destino. */
  origenId: string | null;
  valor: string | null;
  alCambiar: (almacen: AlmacenResumen) => void;
  deshabilitado?: boolean;
  /** Solo ofrece las rutas habituales: las demás las hace únicamente quien tiene `almacenes.todos` (X-03). */
  soloHabituales?: boolean;
  className?: string;
}

/**
 * "¿A dónde se envía?": las rutas habituales primero (Kepler con Contratistas y Contratistas con las áreas,
 * en los dos sentidos) y después las demás, que el servidor avisa como poco habituales (X-03). Solo ordena la
 * lista; quien decide el nivel de la ruta es el servidor.
 */
export function SelectorDestino({ origenId, valor, alCambiar, deshabilitado, soloHabituales = false, className }: PropiedadesSelectorDestino) {
  const id = useId();
  const consulta = useConsulta((signal) => apiGet<AlmacenRedApi[]>("/almacenes", undefined, signal), "almacenes-red");

  if (consulta.error) return <EstadoError error={consulta.error} alReintentar={consulta.recargar} />;
  if (!consulta.datos) return <Esqueleto tipo="renglon" />;

  const activos = consulta.datos.filter((a) => a.estado === "ACTIVO" && a.id !== origenId);
  const origen = consulta.datos.find((a) => a.id === origenId);
  const esHabitual = (a: AlmacenRedApi) => Boolean(origen) && (origen!.padre_id === a.id || a.padre_id === origen!.id);
  const habituales = activos.filter(esHabitual);
  const otros = soloHabituales ? [] : activos.filter((a) => !esHabitual(a));
  const opcion = (grupo: string) => (a: AlmacenRedApi) => ({ valor: a.id, texto: `${a.nombre} (${a.clave})`, grupo });
  const opciones = [
    ...habituales.map(opcion("Rutas habituales")),
    ...otros.map(opcion("Otras rutas (piden una observación)")),
  ];

  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1.5 flex items-center gap-2 text-base font-medium">
        <TruckIcon aria-hidden="true" className="size-5 text-marino" />
        ¿A qué almacén se envía?
      </label>
      <ListaDesplegable
        id={id}
        valor={valor ?? ""}
        deshabilitado={deshabilitado || !origenId}
        marcador={origenId ? "Elige el destino" : "Primero elige el almacén que opera"}
        opciones={opciones}
        alCambiar={(elegido) => {
          const a = activos.find((x) => x.id === elegido);
          if (a) alCambiar({ id: a.id, clave: a.clave, nombre: a.nombre });
        }}
      />
    </div>
  );
}
