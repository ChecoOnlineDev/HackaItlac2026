import { Avatar } from "~/componentes/ui/avatar";
import { useSesionActiva } from "~/sesion/sesion";

/** Identidad de la sesión, independiente del almacén elegido en filtros. */
export function IdentidadUsuario() {
  const { sesion, puede } = useSesionActiva();
  const marcaDemo = " · DEMOSTRACIÓN LOCAL";
  const demostracion = sesion.usuario.nombre.endsWith(marcaDemo);
  const nombre = demostracion ? sesion.usuario.nombre.slice(0, -marcaDemo.length) : sesion.usuario.nombre;
  const ambito = sesion.almacen?.nombre || (puede("almacenes.todos") ? "Todos los almacenes" : "Ámbito no indicado");
  return (
    <div className="identidad-usuario flex items-start gap-3">
      <div className="shrink-0 pt-0.5"><Avatar nombre={nombre} tamano="sm" /></div>
      <div className="min-w-0 flex-1 space-y-1.5 break-words">
        <p className="text-sm leading-snug font-semibold">{nombre || "Usuario"}</p>
        <p className="text-xs leading-relaxed text-muted-foreground">{sesion.rol.nombre || "Rol no indicado"}</p>
        <p className="text-xs leading-relaxed text-muted-foreground">{ambito}</p>
        {demostracion ? <span className="etiqueta-demo inline-block max-w-full rounded-md border px-2 py-1 text-[10px] leading-relaxed font-medium tracking-wide">DEMOSTRACIÓN LOCAL</span> : null}
      </div>
    </div>
  );
}
