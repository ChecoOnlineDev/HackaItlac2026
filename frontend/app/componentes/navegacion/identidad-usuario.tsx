import { Avatar } from "~/componentes/ui/avatar";
import { useSesionActiva } from "~/sesion/sesion";
import { useId, useState } from "react";
import { ListaDesplegable } from "~/componentes/ui/lista-desplegable";
import { mensajeDeError } from "~/api/errores";

/** Identidad de la sesión, independiente del almacén elegido en filtros. */
export function IdentidadUsuario() {
  const { sesion, puede, cambiarAlmacen } = useSesionActiva();
  const [cambiando, setCambiando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const id = useId();
  async function elegirAlmacen(valor: string) {
    if (cambiando || valor === sesion.almacen?.id) return;
    setCambiando(true); setError(null);
    try { await cambiarAlmacen(valor); } catch (causa) { setError(mensajeDeError(causa)); } finally { setCambiando(false); }
  }
  const marcaDemo = " · DEMOSTRACIÓN LOCAL";
  const demostracion = sesion.usuario.nombre.endsWith(marcaDemo);
  const nombre = demostracion ? sesion.usuario.nombre.slice(0, -marcaDemo.length) : sesion.usuario.nombre;
  const ambito = sesion.almacen?.nombre || (puede("almacenes.todos") ? "Todos los almacenes" : "Ámbito no indicado");
  return (
    <div className="identidad-usuario flex items-start gap-3">
      <div className="shrink-0 pt-0.5"><Avatar nombre={nombre} tamano="sm" /></div>
      <div className="flex min-w-0 flex-1 flex-col gap-1.5 break-words">
        <p className="text-sm leading-snug font-semibold">{nombre || "Usuario"}</p>
        <p className="text-xs leading-relaxed text-muted-foreground">{sesion.rol.nombre || "Rol no indicado"}</p>
        <p className="text-xs leading-relaxed text-muted-foreground">{ambito}</p>
        {!puede("almacenes.todos") && (sesion.almacenes?.length ?? 0) > 1 ? <div className="flex flex-col gap-1.5">
          <label htmlFor={id} className="text-xs">Almacén donde operas</label>
          <ListaDesplegable id={id} valor={sesion.almacen_activo?.id ?? sesion.almacen?.id ?? ""} alCambiar={(v) => void elegirAlmacen(v)} deshabilitado={cambiando} opciones={(sesion.almacenes ?? []).map((a) => ({ valor: a.id, texto: a.nombre }))} />
          {error ? <p role="alert" className="text-xs">{error}</p> : null}
        </div> : null}
        {demostracion ? <span className="etiqueta-demo inline-block max-w-full rounded-md border px-2 py-1 text-[10px] leading-relaxed font-medium tracking-wide">DEMOSTRACIÓN LOCAL</span> : null}
      </div>
    </div>
  );
}
