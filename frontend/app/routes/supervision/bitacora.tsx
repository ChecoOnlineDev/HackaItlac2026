import { ArrowRightLeftIcon, DownloadIcon, XIcon } from "lucide-react";
import { Fragment, useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { listarProyectos } from "~/api/proyectos";
import { FiltroLista } from "~/componentes/reportes/filtros-comunes";
import { useAlmacenesFiltro, useUsuariosFiltro } from "~/componentes/reportes/listas";
import { SelectorBusqueda } from "~/componentes/reportes/selector-busqueda";
import { apiGet, descargarCsv } from "~/api/cliente";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { BotonPdfVale } from "~/componentes/dominio/boton-pdf-vale";
import { formatearFechaHora } from "~/componentes/dominio/fechas";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { CampoBusqueda } from "~/componentes/ui/campo-busqueda";
import { HojaFiltros } from "~/componentes/ui/hoja-filtros";
import { Insignia } from "~/componentes/ui/insignia";
import { Tabs, TabsList, TabsTrigger } from "~/components/ui/tabs";
import { Cargando } from "~/componentes/ui/cargando";
import { EstadoError } from "~/componentes/ui/estado-error";
import { useSesionActiva } from "~/sesion/sesion";
import PorRenglon from "./rep-movimientos";

export const handle: ManejadorRuta = { permisosAlguno: ["bitacora.ver", "reportes.movimientos"] };
const CLAVES = ["desde", "hasta", "tipo", "usuario_id", "trabajador_id", "articulo_id", "proyecto_id", "almacen_id", "solo_mios"] as const;
interface ValeFila {
  clase: "VALE" | "LOTE"; id: string; folio: string; lote_id: string | null;
  creado_en: string; tipo: string; tipo_texto: string; estado_texto: string;
  renglones: number; unidades: number; coincidencias: number | null; direccion_texto: string | null;
  almacen: { nombre: string }; responsable: { nombre: string };
  trabajador: { id: string; nombre: string; numero_empleado: string } | null;
  destino: { nombre: string } | null; proyecto: { nombre: string } | null;
  cancelacion?: {id:string|null;folio:string|null} | null;
  vales?: ValeFila[]; archivo_repetido?: boolean; titulares?: number; tiene_varios_titulares?: boolean;
}
interface Respuesta { elementos: ValeFila[]; total: number; mensaje: string | null }
export default function Bitacora() {
  const navegar = useNavigate();
  const [url, setUrl] = useSearchParams(); const { puede, sesion } = useSesionActiva();
  const usuarios = useUsuariosFiltro(); const almacenes = useAlmacenesFiltro();
  const proyectos = useConsulta((signal) => puede("proyectos.ver") ? listarProyectos({ tamano: 200 }, signal) : Promise.resolve({ elementos: [], total: 0 }), "proyectos-bitacora");
  const [texto, setTexto] = useState(url.get("q") ?? "");
  const [expandidos, setExpandidos] = useState<Set<string>>(() => new Set(url.get("lote_id") ? [url.get("lote_id")!] : []));
  const [errorCsv, setErrorCsv] = useState(false);
  const vista = url.get("vista") ?? "vales"; const pagina = Math.max(1, Number(url.get("pagina") ?? "1") || 1);
  const parametros = Object.fromEntries([...url.entries()].filter(([k]) => !["vista", "pagina"].includes(k)));
  const valoresFiltros = Object.fromEntries(CLAVES.map((k) => [k, url.get(k) ?? ""])) as Record<(typeof CLAVES)[number], string>;
  const activos = CLAVES.filter((k) => valoresFiltros[k]).length;
  const clave = url.toString();
  const consulta = useConsulta((signal) => vista === "renglones" ? Promise.resolve(null) : apiGet<Respuesta>("/bitacora", { ...parametros, pagina, tamano: 25 }, signal), clave);
  const cambiar = (campo: string, valor: string) => { const siguiente = new URLSearchParams(url); valor ? siguiente.set(campo, valor) : siguiente.delete(campo); siguiente.delete("pagina"); setUrl(siguiente, { replace: true }); };
  useEffect(() => { setTexto(url.get("q") ?? ""); }, [url.get("q")]);
  useEffect(() => { if (texto === (url.get("q") ?? "")) return; const timer = setTimeout(() => cambiar("q", texto), 300); return () => clearTimeout(timer); }, [texto]);
  const irAVista = (v: string) => navegar(`/bitacora?${new URLSearchParams({ ...parametros, vista: v })}`);
  const navegacion = <Tabs value={vista === "renglones" ? "renglones" : "vales"} onValueChange={(v) => irAVista(String(v))}><TabsList aria-label="Cómo ver la bitácora" className="h-auto! w-full sm:w-fit"><TabsTrigger value="vales" className="min-h-11 flex-1 px-4 text-base sm:flex-none">Por vale</TabsTrigger><TabsTrigger value="renglones" className="min-h-11 flex-1 px-4 text-base sm:flex-none">Detalle por renglón</TabsTrigger></TabsList></Tabs>;
  if (vista === "renglones") return <>{navegacion}<PorRenglon /></>;
  const enlaceVale = (v: ValeFila) => `/vales/${v.id}${texto ? `?q=${encodeURIComponent(texto)}` : ""}`;
  const fila = (v: ValeFila) => <tr className="border-b transition-colors last:border-0 hover:bg-muted/40 focus-visible:bg-muted/40 focus-visible:outline-none" key={v.id} tabIndex={puede("vales.ver") ? 0 : undefined} onClick={(e) => {if(puede("vales.ver") && !(e.target as HTMLElement).closest("a,button")) navegar(enlaceVale(v));}} onKeyDown={(e) => {if(e.key === "Enter" && e.target === e.currentTarget && puede("vales.ver")) navegar(enlaceVale(v));}}>
    <td className="px-4 py-3 align-top whitespace-nowrap">{formatearFechaHora(v.creado_en.endsWith("Z") ? v.creado_en : `${v.creado_en}Z`)}</td>
    <td className="px-4 py-3 align-top">{puede("vales.ver") ? <Link className="font-medium text-marino hover:underline" to={enlaceVale(v)}>{v.folio}</Link> : <span className="font-medium">{v.folio}</span>}{v.lote_id ? <p className="text-xs text-muted-foreground">Desde Excel</p> : null}{v.archivo_repetido ? <p className="text-xs text-muted-foreground">Archivo repetido</p> : null}</td>
    <td className="px-4 py-3 align-top"><Insignia estado="info">{v.tipo_texto}</Insignia><p className="mt-1 flex items-center gap-1 text-xs text-muted-foreground"><ArrowRightLeftIcon aria-hidden="true" className="size-3.5 shrink-0" />{v.tipo === "NO_ADEUDO" ? "Sin movimiento" : v.direccion_texto ?? "Sin dirección"}</p></td>
    <td className="px-4 py-3 align-top">{v.trabajador ? puede("trabajadores.ver") ? <Link className="hover:underline" to={`/trabajadores/${v.trabajador.id}`}>{v.trabajador.nombre}</Link> : v.trabajador.nombre : v.tiene_varios_titulares ? `Varios trabajadores (${v.titulares})` : v.destino?.nombre ?? (v.tipo === "ENTRADA" ? "Proveedor" : <span className="text-muted-foreground">Sin destino</span>)}</td>
    <td className="px-4 py-3 align-top">{v.proyecto?.nombre ?? (v.tipo === "ENTREGA" ? "Sin proyecto" : <span className="text-muted-foreground">Sin proyecto</span>)}</td>
    <td className="px-4 py-3 align-top text-right tabular-nums">{v.renglones}{v.coincidencias !== null ? <p className="text-xs text-muted-foreground">{v.coincidencias} coinciden</p> : null}</td>
    <td className="px-4 py-3 align-top text-right tabular-nums">{v.unidades}</td>
    <td className="px-4 py-3 align-top">{v.responsable.nombre}<p className="text-xs text-muted-foreground">{v.almacen.nombre}</p></td>
    <td className="px-4 py-3 align-top"><Insignia estado="neutra">{v.estado_texto}</Insignia>{v.cancelacion?.folio ? <p className="mt-1 text-xs">{puede("vales.ver") && v.cancelacion.id ? <Link className="text-marino hover:underline" to={`/vales/${v.cancelacion.id}`}>{v.cancelacion.folio}</Link> : v.cancelacion.folio}</p> : null}</td>
  </tr>;
  return <Pantalla titulo="Bitácora" descripcion="Operaciones del almacén, agrupadas por vale e importación." ancho="completo">
    {navegacion}
    <div className="mt-4 flex flex-wrap items-center gap-2">
      <CampoBusqueda etiqueta="Pieza o serie" placeholder="Pieza o serie" value={texto} alCambiar={setTexto} claseContenedor="min-w-56 basis-64" />
      <HojaFiltros valores={valoresFiltros} activos={activos} alAplicar={(b) => { const n = new URLSearchParams(url); CLAVES.forEach((k) => b[k] ? n.set(k, b[k]) : n.delete(k)); n.delete("pagina"); setUrl(n, { replace: true }); }} alLimpiar={() => { const n = new URLSearchParams(url); CLAVES.forEach((k) => n.delete(k)); n.delete("pagina"); setUrl(n, { replace: true }); }}>{(b, c) => <>
        <div className="grid gap-3 sm:grid-cols-2">{(["desde", "hasta"] as const).map((campo) => <Campo key={campo} etiqueta={campo === "desde" ? "Desde" : "Hasta"} type="date" value={b[campo]} onChange={(e) => c({ [campo]: e.target.value })} />)}</div>
        <FiltroLista etiqueta="Tipo" vacio="Todos los tipos" valor={b.tipo} opciones={["ENTRADA","ENTREGA","DEVOLUCION","TRASPASO","RECEPCION","CANCELACION","NO_ADEUDO","AJUSTE"].map((valor) => ({valor, texto: valor.replaceAll("_", " ").toLowerCase()}))} alCambiar={(v) => c({ tipo: v })} />
        <FiltroLista etiqueta="Responsable" vacio="Todos" valor={b.usuario_id} opciones={usuarios.opciones} alCambiar={(v) => c({ usuario_id: v })} />
        {puede("trabajadores.ver") ? <SelectorBusqueda tipo="trabajador" valor={b.trabajador_id} alCambiar={(v) => c({ trabajador_id: v ?? "" })} /> : null}
        {puede("catalogo.ver") ? <SelectorBusqueda tipo="articulo" valor={b.articulo_id} alCambiar={(v) => c({ articulo_id: v ?? "" })} /> : null}
        {puede("proyectos.ver") ? <FiltroLista etiqueta="Proyecto" vacio="Todos" valor={b.proyecto_id} opciones={(proyectos.datos?.elementos ?? []).map((p) => ({valor:p.id,texto:p.nombre}))} alCambiar={(v) => c({ proyecto_id: v })} /> : null}
        {(sesion.almacenes?.length ?? 0) > 1 || puede("almacenes.todos") ? <FiltroLista etiqueta="Almacén" vacio="Todos mis almacenes" valor={b.almacen_id} opciones={puede("almacenes.todos") ? almacenes.opciones : (sesion.almacenes ?? []).map((a) => ({valor:a.id,texto:a.nombre}))} alCambiar={(v) => c({ almacen_id: v })} /> : null}
        <label className="flex min-h-11 items-center gap-2"><input type="checkbox" className="size-5" checked={b.solo_mios === "true"} onChange={(e) => c({ solo_mios: e.target.checked ? "true" : "" })} /> Solo los míos</label>
      </>}</HojaFiltros>
      <Boton variante="contorno" className="shrink-0" onClick={() => { setErrorCsv(false); void descargarCsv("/bitacora", parametros, "bitacora.csv").catch(() => setErrorCsv(true)); }}><DownloadIcon aria-hidden="true" />Descargar CSV</Boton>
      {activos > 0 || url.get("q") ? <Boton variante="texto" className="shrink-0" onClick={() => setUrl(vista === "renglones" ? { vista } : {})}><XIcon aria-hidden="true" />Quitar filtros</Boton> : null}
    </div>
    {errorCsv ? <p role="alert">No pudimos descargar el archivo. Vuelve a intentar.</p> : null}
    {consulta.error ? <EstadoError error={consulta.error} alReintentar={consulta.recargar} /> : consulta.cargando && !consulta.datos ? <Cargando /> : consulta.datos ? <>
      <div className="mt-4 overflow-x-auto rounded-xl border bg-card"><table className="w-full min-w-[64rem] text-left text-sm"><thead className="bg-muted/60 text-xs uppercase tracking-wide text-muted-foreground"><tr>{["Fecha y hora", "Folio", "Tipo y dirección", "Trabajador o destino", "Proyecto", "Renglones", "Unidades", "Responsable", "Estado"].map((h) => <th className={`px-4 py-3 font-semibold ${h === "Renglones" || h === "Unidades" ? "text-right" : ""}`} key={h}>{h}</th>)}</tr></thead><tbody>{consulta.datos.elementos.map((v) => v.clase === "VALE" ? fila(v) : <Fragment key={v.lote_id}><tr className="border-b bg-muted/30"><td colSpan={9} className="px-4 py-3"><div className="flex flex-wrap items-center gap-3"><Boton variante="texto" onClick={() => setExpandidos((prev) => { const n = new Set(prev); n.has(v.lote_id!) ? n.delete(v.lote_id!) : n.add(v.lote_id!); return n; })}>{expandidos.has(v.lote_id!) ? "Ocultar" : "Ver"} los {v.vales?.length} vales</Boton><span>Importación · {v.renglones} renglones · {v.unidades} unidades · {v.estado_texto}</span>{puede("vales.ver") && v.vales?.[0] ? <BotonPdfVale id={v.vales[0].id} lote /> : null}</div></td></tr>{expandidos.has(v.lote_id!) ? v.vales?.map(fila) : null}</Fragment>)}</tbody></table></div>
      {!consulta.datos.total ? <p className="py-5">{consulta.datos.mensaje}</p> : null}<div className="mt-3 flex items-center gap-3"><Boton variante="contorno" disabled={pagina <= 1} onClick={() => { const n = new URLSearchParams(url); n.set("pagina", String(pagina - 1)); setUrl(n); }}>Anterior</Boton><span>Página {pagina} · {consulta.datos.total} operaciones</span><Boton variante="contorno" disabled={pagina * 25 >= consulta.datos.total} onClick={() => { const n = new URLSearchParams(url); n.set("pagina", String(pagina + 1)); setUrl(n); }}>Siguiente</Boton></div>
    </> : null}
  </Pantalla>;
}
