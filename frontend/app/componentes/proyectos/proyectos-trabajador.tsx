import { useState } from "react";
import { asignarProyecto, proyectosDeTrabajador, terminarProyecto, type AsignacionProyecto } from "~/api/proyectos";
import { mensajeDeError } from "~/api/errores";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { fechaCorta } from "~/componentes/personas/formato";
import { Boton } from "~/componentes/ui/boton";
import { Confirmacion } from "~/componentes/ui/confirmacion";
import { EstadoError } from "~/componentes/ui/estado-error";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { Hoja } from "~/componentes/ui/hoja";
import { aviso } from "~/componentes/ui/aviso";
import { useSesion } from "~/sesion/sesion";
import { SelectorProyecto } from "./selector-proyecto";

export function ProyectosTrabajador({ trabajadorId, estado, alCambiar }: { trabajadorId: string; estado: string; alCambiar: () => void }) {
  const { puede } = useSesion();
  const consulta = useConsulta((signal) => proyectosDeTrabajador(trabajadorId, signal), trabajadorId);
  const [accion, setAccion] = useState<{ tipo: "agregar" | "cambiar" | "terminar"; asignacion?: AsignacionProyecto } | null>(null);
  const [proyecto, setProyecto] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const activas = consulta.datos?.filter((a) => !a.terminada_en) ?? [];
  const historial = consulta.datos?.filter((a) => a.terminada_en) ?? [];
  const editar = puede("proyectos.asignar") && estado !== "INACTIVO";
  function abrir(tipo: "agregar" | "cambiar" | "terminar", asignacion?: AsignacionProyecto) { setAccion({ tipo, asignacion }); setProyecto(""); setError(null); }
  async function guardar() {
    if (!accion || guardando) return;
    if (accion.tipo !== "terminar" && !proyecto) { setError("Elige un proyecto."); return; }
    setGuardando(true); setError(null);
    try {
      if (accion.tipo === "terminar" && accion.asignacion) {
        const resultado = await terminarProyecto(trabajadorId, accion.asignacion.asignacion_id);
        aviso({ titulo: resultado.queda_sin_proyecto ? "La persona quedó sin proyecto." : "Proyecto terminado para esta persona.", tipo: "exito" });
      } else {
        await asignarProyecto(trabajadorId, proyecto, accion.tipo === "cambiar" ? accion.asignacion?.asignacion_id : undefined);
        aviso({ titulo: "Proyecto guardado.", tipo: "exito" });
      }
      setAccion(null); consulta.recargar(); alCambiar();
    } catch (causa) { setError(mensajeDeError(causa)); } finally { setGuardando(false); }
  }
  return <section className="flex flex-col gap-3">
    <h2 className="text-lg font-bold text-marino">Proyectos</h2>
    {consulta.cargando && !consulta.datos ? <Esqueleto tipo="tabla" cantidad={2} /> : null}
    {consulta.error ? <EstadoError error={consulta.error} alReintentar={consulta.recargar} /> : null}
    {consulta.datos && activas.length === 0 ? <p>Sin proyecto.</p> : null}
    {activas.map((a) => <div key={a.asignacion_id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border p-3">
      <div><p className="font-semibold">{a.proyecto.nombre}{a.principal ? " · Principal" : ""}</p><p className="text-sm text-muted-foreground">{a.proyecto.almacen.nombre} · Desde {fechaCorta(a.inicio)}</p></div>
      {editar ? <div className="flex flex-wrap gap-2"><Boton variante="contorno" onClick={() => abrir("cambiar", a)}>Cambiar de proyecto</Boton><Boton variante="texto" onClick={() => abrir("terminar", a)}>Terminar</Boton></div> : null}
    </div>)}
    {editar ? <details><summary className="cursor-pointer text-sm font-medium">Otras acciones</summary><Boton className="mt-2" variante="contorno" onClick={() => abrir("agregar")}>{activas.length ? "Agregar otro proyecto" : "Asignar proyecto"}</Boton></details> : null}
    {historial.length ? <details><summary className="cursor-pointer text-sm font-medium">Historial de proyectos ({historial.length})</summary><ul className="mt-3 flex flex-col gap-2">{historial.map((a) => <li key={a.asignacion_id}>{a.proyecto.nombre} · {fechaCorta(a.inicio)} al {a.fin ? fechaCorta(a.fin) : "—"}</li>)}</ul></details> : null}
    <Hoja abierta={accion?.tipo === "agregar" || accion?.tipo === "cambiar"} alCambiar={(a) => !a && !guardando && setAccion(null)} titulo={accion?.tipo === "cambiar" ? "Cambiar de proyecto" : "Asignar proyecto"} descripcion="Lo que tiene en resguardo sigue siendo suyo." pie={<Boton variante="normal" cargando={guardando} disabled={!proyecto} onClick={() => void guardar()}>Guardar proyecto</Boton>}>
      <SelectorProyecto valor={proyecto} alCambiar={(id) => { setProyecto(id); setError(null); }} excluir={activas.map((a) => a.proyecto.id)} deshabilitado={guardando} error={error} />
    </Hoja>
    <Confirmacion abierta={accion?.tipo === "terminar"} alCambiar={(a) => !a && !guardando && setAccion(null)} mensaje={`¿Terminar ${accion?.asignacion?.proyecto.nombre ?? "el proyecto"} para esta persona?`} detalle={error ?? `${activas.length === 1 ? "Quedará sin proyecto. " : ""}Su contrato y el equipo que tiene en resguardo se conservan.`} cargando={guardando} alConfirmar={() => void guardar()} />
  </section>;
}
