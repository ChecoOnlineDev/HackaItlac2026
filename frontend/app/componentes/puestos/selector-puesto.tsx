import { cn } from "cn";
import { CircleAlertIcon, InfoIcon } from "lucide-react";
import { useId } from "react";
import { Link } from "react-router";

import { apiGet } from "~/api/cliente";
import type { Pagina } from "~/api/tipos";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { EstadoError } from "~/componentes/ui/estado-error";
import { Label } from "~/components/ui/label";
import { ListaDesplegable } from "~/componentes/ui/lista-desplegable";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { useSesion } from "~/sesion/sesion";
import type { Puesto } from "./tipos";

interface Propiedades {
  /** `id` del puesto elegido ("" si no hay). */
  valorId: string;
  /** Texto del puesto: lo que se tecleó, cuando el usuario no puede ver el catálogo. */
  valorTexto: string;
  alCambiar: (id: string, texto: string) => void;
  error?: string | null;
  deshabilitado?: boolean;
  etiqueta?: string;
  /** Texto de la opción "ninguno". Con él, dejar el puesto sin elegir es válido (reingreso: se conserva el actual). */
  vacio?: string;
}

/** Lo que se manda al servidor: el `puesto_id` del catálogo o, sin catálogo a la vista, el nombre escrito. */
export function cuerpoDePuesto(id: string, texto: string): { puesto_id?: string; puesto?: string } {
  if (id) return { puesto_id: id };
  const limpio = texto.trim();
  return limpio ? { puesto: limpio } : {};
}

/**
 * El puesto de un trabajador: lista de los puestos activos del catálogo (con `catalogo.ver`).
 * Recursos Humanos, que no ve el catálogo, usa la lista de puestos activos del alta; quien no puede ni eso escribe el nombre y el servidor lo liga si coincide.
 */
export function SelectorPuesto({ valorId, valorTexto, alCambiar, error, deshabilitado, etiqueta = "Puesto", vacio }: Propiedades) {
  const { puede } = useSesion();
  // Quien ve el catálogo usa su lista; RH (que da de alta, sin `catalogo.ver`) usa la propia del alta.
  const veCatalogo = puede("catalogo.ver");
  const veLista = veCatalogo || puede("trabajadores.administrar");
  const puedeAdministrar = puede("catalogo.administrar");
  const id = useId();
  const consulta = useConsulta(
    (signal) =>
      veLista
        ? apiGet<Pagina<Puesto>>(veCatalogo ? "/puestos" : "/trabajadores/puestos", veCatalogo ? { activo: true, tamano: 100 } : { tamano: 100 }, signal)
        : Promise.resolve(null),
    veLista ? (veCatalogo ? "activos" : "activos-alta") : "",
  );

  if (!veLista) {
    return (
      <Campo
        etiqueta={etiqueta}
        value={valorTexto}
        onChange={(e) => alCambiar("", e.target.value)}
        error={error}
        disabled={deshabilitado}
        placeholder={vacio ? "Déjalo vacío para conservar el actual" : undefined}
      />
    );
  }

  if (consulta.error && !consulta.datos) {
    return (
      <div className="flex flex-col gap-1.5">
        <span className="text-sm font-medium">{etiqueta}</span>
        <EstadoError error={consulta.error} alReintentar={consulta.recargar} />
      </div>
    );
  }
  if (!consulta.datos) {
    return (
      <div className="flex flex-col gap-1.5">
        <span className="text-sm font-medium">{etiqueta}</span>
        <Esqueleto tipo="renglon" cantidad={1} />
      </div>
    );
  }

  const puestos = consulta.datos.elementos;
  if (puestos.length === 0 && !vacio) {
    return (
      <div className="flex flex-col gap-1.5">
        <span className="text-sm font-medium">{etiqueta}</span>
        <div role="status" className={cn("flex flex-col gap-2 rounded-2xl border p-3 text-sm", error && "border-destructive")}>
          <p className="flex items-start gap-2 font-semibold">
            <InfoIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
            {puedeAdministrar ? "Primero crea un puesto." : "Pide a Compras o al supervisor que cree el puesto."}
          </p>
          <p className="text-muted-foreground">Todavía no hay puestos activos. El puesto define la dotación que se le recomienda al trabajador.</p>
          {puedeAdministrar ? (
            <Boton variante="contorno" nativeButton={false} render={<Link to="/puestos" />} className="self-start">
              Ir a Puestos
            </Boton>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id} className="text-sm font-medium text-foreground">
        {etiqueta}
      </Label>
      <ListaDesplegable
        id={id}
        valor={valorId}
        alCambiar={(v) => alCambiar(v, puestos.find((p) => p.id === v)?.nombre ?? "")}
        opciones={puestos.map((p) => ({ valor: p.id, texto: p.nombre }))}
        vacio={vacio}
        marcador="Elige el puesto"
        deshabilitado={deshabilitado}
        invalido={Boolean(error)}
        descritoPor={error ? `${id}-error` : undefined}
      />
      {error ? (
        <p id={`${id}-error`} role="alert" className="flex items-start gap-1.5 text-sm font-medium text-destructive">
          <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          {error}
        </p>
      ) : null}
    </div>
  );
}
