import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { descargarCsv } from "~/api/cliente";
import { listarDeudores, resumenDeudores, type Deudor } from "~/api/deudores";
import { listarProyectos } from "~/api/proyectos";
import { ConsumoDelTrabajador } from "~/componentes/personas/consumo-trabajador";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { FilaInterruptor } from "~/componentes/catalogo/campos";
import { formatearFecha } from "~/componentes/dominio/fechas";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { FiltroLista } from "~/componentes/reportes/filtros-comunes";
import { useAlmacenesFiltro, useCategoriasFiltro } from "~/componentes/reportes/listas";
import { useFiltrosUrl } from "~/componentes/reportes/usar-filtros";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { Hoja } from "~/componentes/ui/hoja";
import { Insignia } from "~/componentes/ui/insignia";
import { useSesion } from "~/sesion/sesion";

export const handle: ManejadorRuta = { permiso: "deudores.ver" };
const CLAVES = ["q", "almacen_id", "proyecto_id", "trabajador_id", "sin_proyecto", "categoria_id", "alto_valor", "vigencia", "antiguedad_dias"] as const;

function Detalle({ deudor, filtros }: { deudor: Deudor; filtros: Record<string, string> }) {
  const { puede, sesion } = useSesion();
  const [pestana, setPestana] = useState<"adeudo" | "consumo">("adeudo");
  const consulta = useConsulta((signal) => listarDeudores({ ...filtros, trabajador_id: deudor.trabajador.id }, signal), JSON.stringify([filtros, deudor.trabajador.id]));
  if (consulta.error) return <EstadoError error={consulta.error} alReintentar={consulta.recargar} />;
  if (consulta.cargando) return <Esqueleto tipo="lista" cantidad={3} />;
  const renglones = consulta.datos?.elementos[0]?.renglones ?? [];
  return <div className="space-y-4"><div className="flex gap-2" role="group" aria-label="Información del trabajador"><Boton variante={pestana === "adeudo" ? "principal" : "contorno"} onClick={() => setPestana("adeudo")}>Lo que debe</Boton><Boton variante={pestana === "consumo" ? "principal" : "contorno"} onClick={() => setPestana("consumo")}>Consumo</Boton></div>{pestana === "consumo" ? <ConsumoDelTrabajador id={deudor.trabajador.id} /> : <><ul className="flex flex-col gap-3">{renglones.map((r, i) => <li key={`${r.articulo.id}|${r.pieza?.id ?? i}`} className="rounded-xl border p-4">
    <p className="font-semibold">{r.articulo.nombre} · {r.cantidad}</p>
    <p className="text-sm">{r.articulo.codigo}{r.pieza ? ` · ${r.pieza.codigo} · Serie ${r.pieza.numero_serie ?? "pendiente"}` : ""}</p>
    <p className="text-sm">{r.almacen.nombre} · {r.proyecto?.nombre ?? "Sin proyecto"}{r.proyecto?.estado === "CERRADO" ? " (cerrado)" : ""}</p>
    <p className="text-sm">Desde {r.desde ? formatearFecha(r.desde) : "sin fecha"} · {r.vale.id && puede("vales.ver") ? <Link className="underline" to={`/vales/${r.vale.id}`}>{r.vale.folio}</Link> : r.vale.folio ?? "Sin vale"}</p>
    {r.alto_valor ? <Insignia estado="amarillo">Alto valor</Insignia> : null}
    {r.pieza && puede("catalogo.ver") ? <Link className="ml-3 text-sm underline" to={`/piezas/${r.pieza.id}`}>Ver pieza</Link> : null}
  </li>)}</ul>{puede("devoluciones.crear") && (puede("almacenes.todos") || renglones.some((r) => r.almacen.id === sesion?.almacen?.id)) ? <Link className="inline-flex min-h-11 items-center rounded-lg border px-4 font-medium" to={`/devolver?trabajador=${deudor.trabajador.id}`}>Recibir devolución</Link> : null}</>}</div>;
}

export default function Deudores() {
  const { sesion, puede } = useSesion();
  const { valores, pagina, cambiar, cambiarPagina, quitarTodos } = useFiltrosUrl(CLAVES);
  const [busqueda, setBusqueda] = useState(valores.q);
  const pendienteBusqueda = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    setBusqueda(valores.q);
    if (pendienteBusqueda.current) clearTimeout(pendienteBusqueda.current);
  }, [valores.q]);
  useEffect(() => () => { if (pendienteBusqueda.current) clearTimeout(pendienteBusqueda.current); }, []);
  function buscar(texto: string) {
    setBusqueda(texto);
    if (pendienteBusqueda.current) clearTimeout(pendienteBusqueda.current);
    pendienteBusqueda.current = setTimeout(() => cambiar({ q: texto }), 300);
  }
  const [seleccionado, setSeleccionado] = useState<Deudor | null>(null);
  const [verResumen, setVerResumen] = useState(false);
  const [errorDescarga, setErrorDescarga] = useState<unknown>(null);
  const categorias = useCategoriasFiltro();
  const almacenesTodos = useAlmacenesFiltro();
  const almacenes = puede("almacenes.todos") ? almacenesTodos.opciones : (sesion?.almacenes ?? []).map((a) => ({ valor: a.id, texto: a.nombre }));
  const proyectos = useConsulta((signal) => puede("proyectos.ver") ? listarProyectos({ tamano: 200, almacen_id: valores.almacen_id || undefined }, signal) : Promise.resolve({ elementos: [], total: 0 }), `deudores-proyectos|${valores.almacen_id}|${puede("proyectos.ver")}`);
  const parametros = { ...valores, sin_proyecto: valores.sin_proyecto === "true" ? "true" : "", alto_valor: valores.alto_valor === "true" ? "true" : "" };
  const consulta = useConsulta((signal) => listarDeudores({ ...parametros, pagina, tamano: 50 }, signal), JSON.stringify([parametros, pagina]));
  // DU-06: las tarjetas ignoran únicamente vigencia y antigüedad, como el servidor.
  const resumen = useConsulta((signal) => verResumen ? resumenDeudores(parametros, signal) : Promise.resolve(null), JSON.stringify([parametros, verResumen]));
  async function descargar(agrupado = false) {
    setErrorDescarga(null);
    try { await descargarCsv(agrupado ? "/deudores/resumen" : "/deudores", parametros, agrupado ? "deudores-resumen.csv" : "deudores.csv"); }
    catch (error) { setErrorDescarga(error); }
  }
  const tarjetas = consulta.datos?.resumen;
  const indicadores = tarjetas ? [
    { nombre: "Trabajadores con adeudo", cantidad: tarjetas.trabajadores_con_adeudo, filtrar: () => cambiar({ vigencia: null, antiguedad_dias: null, alto_valor: null }) },
    { nombre: "Alto valor fuera", cantidad: tarjetas.alto_valor_fuera, filtrar: () => cambiar({ alto_valor: "true", vigencia: null, antiguedad_dias: null }) },
    { nombre: "No vigentes con adeudo", cantidad: tarjetas.no_vigentes_con_adeudo, filtrar: () => cambiar({ vigencia: "NO_VIGENTES", antiguedad_dias: null }) },
    { nombre: "Más de 30 días", cantidad: tarjetas.mas_de_30_dias, filtrar: () => cambiar({ antiguedad_dias: "30", vigencia: null }) },
  ] : [];
  return <Pantalla titulo="Deudores" descripcion="Equipo que debe regresar al almacén, por trabajador y proyecto.">
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">{indicadores.map((i) => <button type="button" key={i.nombre} onClick={i.filtrar} className="rounded-xl border bg-card p-4 text-left hover:bg-accent focus-visible:outline-2 focus-visible:outline-primary"><span className="block text-sm text-muted-foreground">{i.nombre}</span><span className="block text-2xl font-bold">{i.cantidad}</span></button>)}</div>
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <Campo etiqueta="Nombre o número del trabajador" value={busqueda} maxLength={100} onChange={(e) => buscar(e.target.value)} />
      {almacenes.length > 1 ? <FiltroLista etiqueta="Almacén" vacio="Todos los de mi alcance" valor={valores.almacen_id} opciones={almacenes} alCambiar={(v) => cambiar({ almacen_id: v, proyecto_id: null })} /> : null}
      {puede("proyectos.ver") ? <FiltroLista etiqueta="Proyecto" vacio="Todos los proyectos" valor={valores.sin_proyecto === "true" ? "sin" : valores.proyecto_id} opciones={[{ valor: "sin", texto: "Sin proyecto" }, ...(proyectos.datos?.elementos ?? []).map((p) => ({ valor: p.id, texto: p.nombre }))]} alCambiar={(v) => cambiar({ proyecto_id: v === "sin" ? null : v, sin_proyecto: v === "sin" ? "true" : null })} /> : null}
      {categorias.disponible ? <FiltroLista etiqueta="Categoría" vacio="Todas las categorías" valor={valores.categoria_id} opciones={categorias.opciones} alCambiar={(v) => cambiar({ categoria_id: v })} /> : null}
      <FiltroLista etiqueta="Vigencia" vacio="Todos" valor={valores.vigencia} opciones={[{ valor: "VIGENTES", texto: "Vigentes" }, { valor: "NO_VIGENTES", texto: "No vigentes" }]} alCambiar={(v) => cambiar({ vigencia: v })} />
      <Campo etiqueta="Con más de estos días" type="number" min={0} max={36500} value={valores.antiguedad_dias} onChange={(e) => cambiar({ antiguedad_dias: e.target.value })} />
      <FilaInterruptor titulo="Solo alto valor" activo={valores.alto_valor === "true"} alCambiar={(v) => cambiar({ alto_valor: v ? "true" : null })} />
    </div>
    <div className="flex flex-wrap gap-2"><Boton variante="contorno" onClick={() => { setBusqueda(""); quitarTodos(); }}>Limpiar filtros</Boton><Boton variante="contorno" onClick={() => setVerResumen(!verResumen)}>{verResumen ? "Ocultar resumen" : "Resumen por almacén y proyecto"}</Boton><Boton variante="contorno" onClick={() => void descargar()}>Descargar CSV</Boton></div>
    {Boolean(errorDescarga) ? <EstadoError error={errorDescarga} alReintentar={() => void descargar()} /> : null}
    {verResumen ? <section className="rounded-xl border p-4"><h2 className="font-semibold">Resumen</h2>{resumen.error ? <EstadoError error={resumen.error} alReintentar={resumen.recargar} /> : resumen.cargando ? <Esqueleto tipo="lista" cantidad={2} /> : <div className="grid gap-4 md:grid-cols-2">{[{ titulo: "Por almacén", filas: (resumen.datos?.almacenes ?? []).map((r) => ({ ...r, id: r.almacen_id, nombre: r.almacen_nombre })) }, { titulo: "Por proyecto", filas: (resumen.datos?.proyectos ?? []).map((r) => ({ ...r, id: r.proyecto_id ?? "sin", nombre: r.proyecto_nombre ?? "Sin proyecto" })) }].map((grupo) => <div key={grupo.titulo}><h3 className="font-medium">{grupo.titulo}</h3>{grupo.filas.map((r) => <p className="my-2 text-sm" key={r.id}>{r.nombre}: {r.trabajadores} trabajadores · {r.piezas} piezas · {r.unidades} unidades · {r.alto_valor} de alto valor · {r.no_vigentes} no vigentes</p>)}</div>)}</div>}<Boton variante="contorno" onClick={() => void descargar(true)}>CSV del resumen</Boton></section> : null}
    {consulta.error ? <EstadoError error={consulta.error} alReintentar={consulta.recargar} /> : consulta.cargando ? <Esqueleto tipo="lista" cantidad={3} /> : !consulta.datos?.elementos.length ? <EstadoVacio titulo="No hay trabajadores con adeudo" descripcion="Prueba otros filtros para ampliar la búsqueda." /> : <ul className="grid gap-3 lg:grid-cols-2">{consulta.datos.elementos.map((d) => <li key={d.trabajador.id} className="flex flex-col gap-2 rounded-xl border bg-card p-4">
      <Link className="font-bold text-marino underline" to={`/trabajadores/${d.trabajador.id}`}>{d.trabajador.nombre} · {d.trabajador.numero_empleado}</Link>
      <Insignia estado={d.vigente ? "verde" : "rojo"}>{d.vigente ? "Vigente" : "No vigente"}</Insignia>{d.aviso ? <p role="alert" className="text-sm">{d.aviso}</p> : null}
      <p>{d.piezas} piezas · {d.unidades} unidades{d.alto_valor ? ` · ${d.alto_valor} de alto valor` : ""}</p>
      <p className="text-sm">{d.proyectos.map((p) => `${p.nombre}${p.estado === "CERRADO" ? " (cerrado)" : ""}`).join(", ") || "Sin proyecto"}</p>
      <p className="text-sm">Desde {d.desde ? formatearFecha(d.desde) : "sin fecha"}{d.otros_almacenes ? ` · Tiene ${d.otros_almacenes} pendientes en otros almacenes` : ""}</p>
      <Boton variante="contorno" onClick={() => setSeleccionado(d)}>Ver lo que debe</Boton>
    </li>)}</ul>}
    <nav aria-label="Páginas de deudores" className="flex items-center justify-between gap-3"><Boton variante="contorno" disabled={pagina <= 1 || consulta.cargando} onClick={() => cambiarPagina(pagina - 1)}>Anterior</Boton><span>Página {pagina} · {consulta.datos?.total ?? 0} trabajadores</span><Boton variante="contorno" disabled={pagina * 50 >= (consulta.datos?.total ?? 0) || consulta.cargando} onClick={() => cambiarPagina(pagina + 1)}>Siguiente</Boton></nav>
    <Hoja abierta={seleccionado !== null} alCambiar={(v) => !v && setSeleccionado(null)} titulo={seleccionado?.trabajador.nombre ?? "Detalle del adeudo"}>{seleccionado ? <Detalle deudor={seleccionado} filtros={parametros} /> : null}</Hoja>
  </Pantalla>;
}
