import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { FolderIcon, PlusIcon } from "lucide-react";
import { apiGet } from "~/api/cliente";
import { cerrarProyecto, crearProyecto, editarProyecto, listarProyectos, reabrirProyecto, SITUACIONES, type DatosProyecto, type Proyecto } from "~/api/proyectos";
import { mensajeDeError } from "~/api/errores";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { Label } from "~/components/ui/label";
import { useConsulta, useRetraso } from "~/componentes/catalogo/usar-consulta";
import { fechaCorta, hoyMx } from "~/componentes/personas/formato";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { CampoFecha } from "~/componentes/ui/campo-fecha";
import { CampoBusqueda } from "~/componentes/ui/campo-busqueda";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { Hoja } from "~/componentes/ui/hoja";
import { Insignia } from "~/componentes/ui/insignia";
import { ListaDesplegable } from "~/componentes/ui/lista-desplegable";
import { aviso } from "~/componentes/ui/aviso";
import { useSesion } from "~/sesion/sesion";

export const handle: ManejadorRuta = { dispositivo: "computadora", permisosAlguno: ["proyectos.ver", "proyectos.asignar"] };
type Almacen = { id: string; nombre: string; clave: string; tipo: string; estado: string };
type Panel = { tipo: "nuevo" | "editar" | "ver" | "cerrar" | "reabrir"; proyecto?: Proyecto };
const VACIO: DatosProyecto = { clave: "", nombre: "", almacen_id: "", inicio: hoyMx(), fin_estimado: "" };

export default function Proyectos() {
  const { puede } = useSesion();
  const [parametros, setParametros] = useSearchParams();
  const porVencer = parametros.get("por_vencer") === "true";
  const proyectoId = parametros.get("proyecto_id") ?? "";
  const administrar = puede("proyectos.administrar");
  const [texto, setTexto] = useState("");
  const q = useRetraso(texto);
  const [situacion, setSituacion] = useState(parametros.get("situacion") ?? "");
  const [almacenId, setAlmacenId] = useState(parametros.get("almacen_id") ?? "");
  const [pagina, setPagina] = useState(0);
  const lista = useConsulta((signal) => listarProyectos({ q, situacion, almacen_id: almacenId, por_vencer: porVencer || undefined, tamano: 30, pagina: pagina + 1 }, signal), JSON.stringify([q, situacion, almacenId, pagina, porVencer]));
  const almacenes = useConsulta((signal) => apiGet<Almacen[]>("/almacenes", undefined, signal), "almacenes-proyectos");
  const [panel, setPanel] = useState<Panel | null>(null);
  const [datos, setDatos] = useState(VACIO);
  const [motivo, setMotivo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const fichaPedida = useConsulta((signal) => proyectoId ? apiGet<Proyecto>(`/proyectos/${proyectoId}`, undefined, signal) : Promise.resolve(null), proyectoId);
  useEffect(() => { if (fichaPedida.datos) setPanel({ tipo: "ver", proyecto: fichaPedida.datos }); }, [fichaPedida.datos]);
  function abrir(tipo: Panel["tipo"], proyecto?: Proyecto) {
    setPanel({ tipo, proyecto }); setError(null); setMotivo("");
    setDatos(proyecto ? { clave: proyecto.clave, nombre: proyecto.nombre, almacen_id: proyecto.almacen.id, inicio: proyecto.inicio, fin_estimado: proyecto.fin_estimado } : { ...VACIO, inicio: hoyMx() });
  }
  async function guardar() {
    if (!panel || guardando) return;
    const limpio = { ...datos, clave: datos.clave.trim(), nombre: datos.nombre.trim() };
    if (["nuevo", "editar"].includes(panel.tipo) && (!limpio.clave || !limpio.nombre || !limpio.almacen_id || !limpio.inicio || !limpio.fin_estimado)) { setError("Completa la clave, el nombre, el almacén y las fechas."); return; }
    if (panel.tipo === "cerrar" && !motivo.trim()) { setError("Escribe el motivo del cierre."); return; }
    setGuardando(true); setError(null);
    try {
      let resultado: Proyecto;
      if (panel.tipo === "nuevo") resultado = await crearProyecto(limpio);
      else if (panel.tipo === "editar") resultado = await editarProyecto(panel.proyecto!.id, limpio);
      else if (panel.tipo === "cerrar") {
        const cierre = await cerrarProyecto(panel.proyecto!.id, motivo.trim()); resultado = cierre;
        aviso({ titulo: "Proyecto cerrado.", descripcion: `${cierre.asignaciones_terminadas} asignaciones terminadas; ${cierre.trabajadores_sin_proyecto} personas quedaron sin proyecto.`, tipo: "exito" });
      } else resultado = await reabrirProyecto(panel.proyecto!.id, datos.fin_estimado);
      if (panel.tipo !== "cerrar") aviso({ titulo: "Proyecto guardado.", tipo: "exito" });
      lista.recargar(); abrir("ver", resultado);
    } catch (causa) { setError(mensajeDeError(causa)); } finally { setGuardando(false); }
  }
  const formulario = panel?.tipo === "nuevo" || panel?.tipo === "editar";
  const actual = panel?.proyecto;
  return <Pantalla titulo="Proyectos" descripcion="Organiza el trabajo por proyecto y almacén." acciones={administrar ? <Boton variante="normal" onClick={() => abrir("nuevo")}><PlusIcon aria-hidden="true" />Nuevo proyecto</Boton> : null}>
    <div className="grid gap-3 sm:grid-cols-3">
      <CampoBusqueda etiqueta="Buscar proyecto" value={texto} alCambiar={(v) => { setTexto(v); setPagina(0); }} placeholder="Clave o nombre" />
      <div className="flex flex-col gap-1.5"><Label htmlFor="almacen-proyectos">Almacén</Label><ListaDesplegable id="almacen-proyectos" valor={almacenId} alCambiar={(v) => { setAlmacenId(v); setPagina(0); }} vacio="Todos tus almacenes" opciones={(almacenes.datos ?? []).map((a) => ({ valor: a.id, texto: a.nombre }))} /></div>
      <div className="flex flex-col gap-1.5"><Label htmlFor="situacion-proyectos">Situación</Label><ListaDesplegable id="situacion-proyectos" valor={situacion} alCambiar={(v) => { setSituacion(v); setPagina(0); }} vacio="Todas" opciones={Object.entries(SITUACIONES).map(([valor, texto]) => ({ valor, texto }))} /></div>
    </div>
    {porVencer ? <div className="flex items-center gap-3 text-sm"><p>Viendo proyectos con fin estimado vencido o dentro de 7 días.</p><Boton onClick={() => { parametros.delete("por_vencer"); setParametros(parametros); setPagina(0); }}>Quitar filtro</Boton></div> : null}
    {fichaPedida.error ? <EstadoError error={fichaPedida.error} alReintentar={fichaPedida.recargar} /> : null}
    {lista.error ? <EstadoError error={lista.error} alReintentar={lista.recargar} /> : null}
    {lista.cargando && !lista.datos ? <Esqueleto tipo="tabla" cantidad={5} /> : null}
    {lista.datos?.elementos.length === 0 ? <EstadoVacio icono={FolderIcon} titulo="No hay proyectos con estos filtros" descripcion="Crea un proyecto o cambia los filtros." /> : null}
    {lista.datos?.elementos.length ? <Table><TableHeader><TableRow>{["Proyecto", "Almacén", "Fechas", "Situación", "Trabajadores", "Acciones"].map((t) => <TableHead key={t}>{t}</TableHead>)}</TableRow></TableHeader><TableBody>{lista.datos.elementos.map((p) => <TableRow key={p.id}><TableCell className="whitespace-normal"><strong>{p.nombre}</strong><p className="text-sm text-muted-foreground">{p.clave}</p></TableCell><TableCell>{p.almacen.nombre}</TableCell><TableCell>{fechaCorta(p.inicio)} al {fechaCorta(p.fin_estimado)}</TableCell><TableCell><Insignia estado={p.estado === "ACTIVO" ? "info" : "neutra"}>{SITUACIONES[p.situacion]}</Insignia></TableCell><TableCell>{p.trabajadores_asignados}</TableCell><TableCell><Boton variante="contorno" onClick={() => abrir("ver", p)}>Ver ficha</Boton></TableCell></TableRow>)}</TableBody></Table> : null}
    {lista.datos && lista.datos.total > 30 ? <nav aria-label="Páginas de proyectos" className="flex items-center gap-3"><Boton disabled={!pagina || lista.cargando} onClick={() => setPagina((p) => p - 1)}>Anterior</Boton><span>Página {pagina + 1}</span><Boton disabled={(pagina + 1) * 30 >= lista.datos.total || lista.cargando} onClick={() => setPagina((p) => p + 1)}>Siguiente</Boton></nav> : null}
    <Hoja abierta={Boolean(panel)} alCambiar={(a) => !a && !guardando && setPanel(null)} titulo={panel?.tipo === "nuevo" ? "Nuevo proyecto" : panel?.tipo === "editar" ? "Editar proyecto" : panel?.tipo === "cerrar" ? "Cerrar proyecto" : panel?.tipo === "reabrir" ? "Reabrir proyecto" : actual?.nombre ?? "Proyecto"} pie={panel && panel.tipo !== "ver" ? <Boton variante={panel.tipo === "cerrar" ? "peligro" : "normal"} cargando={guardando} onClick={() => void guardar()}>{panel.tipo === "cerrar" ? "Confirmar cierre" : "Guardar"}</Boton> : null}>
      {formulario ? <div className="flex flex-col gap-4">
        <Campo etiqueta="Clave" value={datos.clave} maxLength={30} disabled={guardando} onChange={(e) => setDatos({ ...datos, clave: e.target.value })} />
        <Campo etiqueta="Nombre" value={datos.nombre} maxLength={100} disabled={guardando} onChange={(e) => setDatos({ ...datos, nombre: e.target.value })} />
        <div className="flex flex-col gap-1.5"><Label htmlFor="almacen-del-proyecto">Almacén</Label><ListaDesplegable id="almacen-del-proyecto" valor={datos.almacen_id} alCambiar={(v) => setDatos({ ...datos, almacen_id: v })} deshabilitado={guardando} opciones={(almacenes.datos ?? []).filter((a) => a.estado === "ACTIVO").sort((a, b) => Number(b.tipo === "PROYECTO") - Number(a.tipo === "PROYECTO")).map((a) => ({ valor: a.id, texto: a.nombre, grupo: a.tipo === "PROYECTO" ? "Almacenes de proyectos" : "Para personal general" }))} /></div>
        <CampoFecha etiqueta="Inicio" value={datos.inicio} alCambiar={(v) => setDatos({ ...datos, inicio: v })} />
        <CampoFecha etiqueta="Fin estimado" value={datos.fin_estimado} alCambiar={(v) => setDatos({ ...datos, fin_estimado: v })} />
      </div> : null}
      {panel?.tipo === "cerrar" ? <div className="flex flex-col gap-4"><p>Se terminarán las asignaciones de {actual?.trabajadores_asignados} trabajadores. Sus contratos y lo que tienen en resguardo se conservan.</p><Campo etiqueta="Motivo del cierre" value={motivo} maxLength={500} disabled={guardando} onChange={(e) => setMotivo(e.target.value)} /></div> : null}
      {panel?.tipo === "reabrir" ? <div className="flex flex-col gap-4"><p>Las asignaciones anteriores no se restauran. RH debe volver a asignar a los trabajadores.</p><CampoFecha etiqueta="Fin estimado" value={datos.fin_estimado} alCambiar={(v) => setDatos({ ...datos, fin_estimado: v })} /></div> : null}
      {panel?.tipo === "ver" && actual ? <div className="flex flex-col gap-4"><p>{actual.clave} · {actual.almacen.nombre}</p><Insignia estado={actual.estado === "ACTIVO" ? "info" : "neutra"}>{SITUACIONES[actual.situacion]}</Insignia><p>{fechaCorta(actual.inicio)} al {fechaCorta(actual.fin_estimado)}</p><p>{actual.trabajadores_asignados} trabajadores asignados</p>{actual.motivo_cierre ? <p>Motivo del cierre: {actual.motivo_cierre}</p> : null}{actual.aviso ? <p>{actual.aviso}</p> : null}{puede("trabajadores.ver") ? <Link to={`/trabajadores?proyecto_id=${actual.id}`} className="underline">Ver trabajadores del proyecto</Link> : null}{administrar ? <div className="flex flex-wrap gap-2">{actual.estado === "ACTIVO" ? <><Boton variante="contorno" onClick={() => abrir("editar", actual)}>{actual.situacion === "FIN_VENCIDO" ? "Extender o editar" : "Editar"}</Boton><Boton variante="peligro" onClick={() => abrir("cerrar", actual)}>Cerrar proyecto</Boton></> : <Boton variante="contorno" onClick={() => abrir("reabrir", actual)}>Reabrir proyecto</Boton>}</div> : null}</div> : null}
      {error ? <p role="alert" className="mt-3 text-destructive">{error}</p> : null}
    </Hoja>
  </Pantalla>;
}
