import { BanIcon, HandIcon, PackageCheckIcon, ShoppingCartIcon, XIcon, type LucideIcon } from "lucide-react";

import { Boton } from "~/componentes/ui/boton";
import { TEXTO_ACCION, type AccionSolicitud } from "./tipos";

const ICONOS: Record<AccionSolicitud, LucideIcon> = {
  tomar: HandIcon,
  rechazar: XIcon,
  comprar: ShoppingCartIcon,
  ingresar: PackageCheckIcon,
  cancelar: BanIcon,
};

/** La acción que hace avanzar la solicitud, si el servidor la ofrece. Las demás son secundarias. */
const PRINCIPALES: readonly AccionSolicitud[] = ["tomar", "comprar", "ingresar"];

export function accionPrincipal(acciones: readonly AccionSolicitud[]): AccionSolicitud | null {
  return PRINCIPALES.find((a) => acciones.includes(a)) ?? null;
}

interface PropiedadesBotonesAccion {
  /** Lo que dice el servidor en `acciones`: se muestra tal cual, sin deducir nada del rol. */
  acciones: readonly AccionSolicitud[];
  alElegir: (accion: AccionSolicitud) => void;
  /** Solo la acción principal (para el renglón de la lista). */
  soloPrincipal?: boolean;
  /** Etiquetas cortas ("Comprada" en vez de "Marcar como comprada"). */
  compacto?: boolean;
  className?: string;
}

const CORTAS: Partial<Record<AccionSolicitud, string>> = {
  comprar: "Comprada",
  ingresar: "Ingresar",
  cancelar: "Cancelar",
};

/**
 * Botones de las acciones que el servidor ofrece para una solicitud. Una sola es la principal (azul, a la
 * derecha); las demás van con contorno. "Rechazar" y "Cancelar" nunca son la principal.
 */
export function BotonesAccion({ acciones, alElegir, soloPrincipal = false, compacto = false, className }: PropiedadesBotonesAccion) {
  const principal = accionPrincipal(acciones);
  const secundarias = soloPrincipal ? [] : acciones.filter((a) => a !== principal);
  const texto = (a: AccionSolicitud) => (compacto ? (CORTAS[a] ?? TEXTO_ACCION[a]) : TEXTO_ACCION[a]);
  if (acciones.length === 0 || (soloPrincipal && !principal)) return null;

  const dibujar = (a: AccionSolicitud, esPrincipal: boolean) => {
    const Icono = ICONOS[a];
    return (
      <Boton
        key={a}
        variante={esPrincipal ? "normal" : "contorno"}
        className={esPrincipal ? undefined : a === "rechazar" || a === "cancelar" ? "text-destructive" : undefined}
        onClick={(e) => {
          // Dentro de una fila o tarjeta que también abre el detalle.
          e.stopPropagation();
          alElegir(a);
        }}
      >
        {compacto ? null : <Icono aria-hidden="true" />}
        {texto(a)}
      </Boton>
    );
  };

  return (
    <div className={className ?? "flex flex-wrap items-center justify-end gap-2"}>
      {secundarias.map((a) => dibujar(a, false))}
      {principal ? dibujar(principal, true) : null}
    </div>
  );
}
