import { useEffect, useId } from "react";
import { Link } from "react-router";
import { useSesion } from "~/sesion/sesion";
import { listarProyectos } from "~/api/proyectos";
import { Label } from "~/components/ui/label";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { fechaCorta } from "~/componentes/personas/formato";
import { EstadoError } from "~/componentes/ui/estado-error";
import { ListaDesplegable } from "~/componentes/ui/lista-desplegable";

export function SelectorProyecto({ valor, alCambiar, deshabilitado, error, excluir = [], proponerUnico = true, asignables = true }: {
  valor: string; alCambiar: (valor: string) => void; deshabilitado?: boolean; error?: string | null; excluir?: string[]; proponerUnico?: boolean; asignables?: boolean;
}) {
  const id = useId();
  const { puede } = useSesion();
  const consulta = useConsulta(async (signal) => {
    const resultado = await listarProyectos({ asignables: asignables || undefined, tamano: 100 }, signal);
    for (let pagina = 2; resultado.elementos.length < resultado.total; pagina++) {
      const siguiente = await listarProyectos({ asignables: asignables || undefined, tamano: 100, pagina }, signal);
      if (!siguiente.elementos.length) break;
      resultado.elementos.push(...siguiente.elementos);
    }
    return resultado;
  }, `proyectos-selector-${asignables}`);
  const disponibles = consulta.datos?.elementos.filter((p) => !excluir.includes(p.id)) ?? [];
  const unico = disponibles.length === 1 ? disponibles[0].id : "";
  useEffect(() => { if (proponerUnico && !valor && unico) alCambiar(unico); }, [proponerUnico, valor, unico, alCambiar]);
  useEffect(() => {
    if (consulta.datos && valor && !consulta.datos.elementos.some((p) => p.id === valor)) alCambiar("");
  }, [consulta.datos, valor, alCambiar]);
  return <div className="flex flex-col gap-1.5">
    <Label htmlFor={id}>Proyecto</Label>
    <ListaDesplegable id={id} valor={valor} alCambiar={alCambiar} deshabilitado={deshabilitado || consulta.cargando || disponibles.length === 0} invalido={Boolean(error)} descritoPor={`${id}-ayuda`} marcador={consulta.cargando ? "Cargando proyectos…" : "Elige el proyecto"} opciones={disponibles.map((p) => ({ valor: p.id, texto: `${p.nombre} (${p.clave}) · ${fechaCorta(p.inicio)} al ${fechaCorta(p.fin_estimado)}`, grupo: p.almacen.nombre }))} />
    <p id={`${id}-ayuda`} className="text-sm text-muted-foreground">{!consulta.cargando && !consulta.error && disponibles.length === 0 ? "No hay proyectos disponibles. Pide al administrador que cree o extienda un proyecto." : asignables ? "El proyecto indica en qué almacén trabaja la persona." : "Incluye proyectos vigentes y cerrados."}</p>
    {error ? <p role="alert" className="text-sm text-destructive">{error}</p> : null}
    {puede("proyectos.administrar") ? <Link to="/proyectos?nuevo=1" className="w-fit text-sm underline">Dar de alta un proyecto</Link> : null}
    {consulta.error ? <EstadoError error={consulta.error} alReintentar={consulta.recargar} /> : null}
  </div>;
}
