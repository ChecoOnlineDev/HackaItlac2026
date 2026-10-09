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
import { Cargando } from "~/componentes/ui/cargando";
import { EstadoError } from "~/componentes/ui/estado-error";
import { useSesionActiva } from "~/sesion/sesion";
import PorRenglon from "./rep-movimientos";

export const handle: ManejadorRuta = { permisosAlguno: ["bitacora.ver", "reportes.movimientos"] };
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
  const clave = url.toString();
  const consulta = useConsulta((signal) => vista === "renglones" ? Promise.resolve(null) : apiGet<Respuesta>("/bitacora", { ...parametros, pagina, tamano: 25 }, signal), clave);
  const cambiar = (campo: string, valor: string) => { const siguiente = new URLSearchParams(url); valor ? siguiente.set(campo, valor) : siguiente.delete(campo); siguiente.delete("pagina"); setUrl(siguiente, { replace: true }); };
  useEffect(() => { setTexto(url.get("q") ?? ""); }, [url.get("q")]);
  useEffect(() => { if (texto === (url.get("q") ?? "")) return; const timer = setTimeout(() => cambiar("q", texto), 300); return () => clearTimeout(timer); }, [texto]);
  const navegacion = <nav className="flex gap-3"><Link to={`/bitacora?${new URLSearchParams({ ...parametros, vista: "vales" })}`} className="underline">Por vale</Link><Link to={`/bitacora?${new URLSearchParams({ ...parametros, vista: "renglones" })}`} className="underline">Detalle por renglón</Link></nav>;
  if (vista === "renglones") return <>{navegacion}<PorRenglon /></>;
  const fila = (v: ValeFila) => <tr className="border-b" key={v.id} tabIndex={puede("vales.ver") ? 0 : undefined} onClick={(e) => {if(puede("vales.ver") && !(e.target as HTMLElement).closest("a,button")) navegar(`/vales/${v.id}${texto ? `?q=${encodeURIComponent(texto)}` : ""}`);}} onKeyDown={(e) => {if(e.key === "Enter" && e.target === e.currentTarget && puede("vales.ver")) navegar(`/vales/${v.id}${texto ? `?q=${encodeURIComponent(texto)}` : ""}`);}}><td className="p-3">{formatearFechaHora(v.creado_en.endsWith("Z") ? v.creado_en : `${v.creado_en}Z`)}</td><td className="p-3">{puede("vales.ver") ? <Link className="underline" to={`/vales/${v.id}${texto ? `?q=${encodeURIComponent(texto)}` : ""}`}>{v.folio}</Link> : v.folio}{v.lote_id ? <p className="text-xs">Desde Excel</p> : null}{v.archivo_repetido ? <p className="text-xs">Archivo repetido</p> : null}</td><td>{v.tipo_texto}<p className="text-xs">{v.tipo === "NO_ADEUDO" ? "Sin movimiento" : v.direccion_texto ?? "—"}</p></td><td>{v.trabajador ? puede("trabajadores.ver") ? <Link className="underline" to={`/trabajadores/${v.trabajador.id}`}>{v.trabajador.nombre}</Link> : v.trabajador.nombre : v.tiene_varios_titulares ? `Varios trabajadores (${v.titulares})` : v.destino?.nombre ?? (v.tipo === "ENTRADA" ? "Proveedor" : "—")}</td><td>{v.proyecto?.nombre ?? (v.tipo === "ENTREGA" ? "Sin proyecto" : "—")}</td><td>{v.renglones}{v.coincidencias !== null ? <p className="text-xs">{v.coincidencias} coinciden</p> : null}</td><td>{v.unidades}</td><td>{v.responsable.nombre}<p className="text-xs">{v.almacen.nombre}</p></td><td>{v.estado_texto}{v.cancelacion?.folio ? <p className="text-xs">{puede("vales.ver") && v.cancelacion.id ? <Link className="underline" to={`/vales/${v.cancelacion.id}`}>{v.cancelacion.folio}</Link> : v.cancelacion.folio}</p> : null}</td></tr>;
  return <Pantalla titulo="Bitácora" descripcion="Operaciones del almacén, agrupadas por vale e importación." ancho="completo">
    {navegacion}<div className="mt-4 flex flex-wrap items-end gap-3"><Campo etiqueta="Pieza o serie" value={texto} onChange={(e) => setTexto(e.target.value)} />
      <details className="rounded-xl border p-3"><summary>Filtros</summary><div className="grid gap-3 pt-3 sm:grid-cols-2">{[["desde", "Desde"], ["hasta", "Hasta"]].map(([campo, etiqueta]) => <Campo key={campo} etiqueta={etiqueta} type="date" value={url.get(campo) ?? ""} onChange={(e) => cambiar(campo, e.target.value)} />)}
      <FiltroLista etiqueta="Tipo" vacio="Todos los tipos" valor={url.get("tipo") ?? ""} opciones={["ENTRADA","ENTREGA","DEVOLUCION","TRASPASO","RECEPCION","CANCELACION","NO_ADEUDO","AJUSTE"].map((valor) => ({valor, texto: valor.replaceAll("_", " ").toLowerCase()}))} alCambiar={(v) => cambiar("tipo",v)} />
      <FiltroLista etiqueta="Responsable" vacio="Todos" valor={url.get("usuario_id") ?? ""} opciones={usuarios.opciones} alCambiar={(v) => cambiar("usuario_id",v)} />
      {puede("trabajadores.ver") ? <SelectorBusqueda tipo="trabajador" valor={url.get("trabajador_id") ?? ""} alCambiar={(v) => cambiar("trabajador_id",v ?? "")} /> : null}
      {puede("catalogo.ver") ? <SelectorBusqueda tipo="articulo" valor={url.get("articulo_id") ?? ""} alCambiar={(v) => cambiar("articulo_id",v ?? "")} /> : null}
      {puede("proyectos.ver") ? <FiltroLista etiqueta="Proyecto" vacio="Todos" valor={url.get("proyecto_id") ?? ""} opciones={(proyectos.datos?.elementos ?? []).map((p) => ({valor:p.id,texto:p.nombre}))} alCambiar={(v) => cambiar("proyecto_id",v)} /> : null}
      {(sesion.almacenes?.length ?? 0) > 1 || puede("almacenes.todos") ? <FiltroLista etiqueta="Almacén" vacio="Todos mis almacenes" valor={url.get("almacen_id") ?? ""} opciones={puede("almacenes.todos") ? almacenes.opciones : (sesion.almacenes ?? []).map((a) => ({valor:a.id,texto:a.nombre}))} alCambiar={(v) => cambiar("almacen_id",v)} /> : null}
      <label><input type="checkbox" checked={url.get("solo_mios") === "true"} onChange={(e) => cambiar("solo_mios", e.target.checked ? "true" : "")} /> Solo los míos</label></div></details>
      <Boton variante="contorno" onClick={() => { setErrorCsv(false); void descargarCsv("/bitacora", parametros, "bitacora.csv").catch(() => setErrorCsv(true)); }}>Descargar CSV</Boton><Boton variante="texto" onClick={() => setUrl({})}>Quitar filtros</Boton></div>
    {errorCsv ? <p role="alert">No pudimos descargar el archivo. Vuelve a intentar.</p> : null}
    {consulta.error ? <EstadoError error={consulta.error} alReintentar={consulta.recargar} /> : consulta.cargando && !consulta.datos ? <Cargando /> : consulta.datos ? <>
      <div className="mt-4 overflow-auto rounded-xl border"><table className="w-full text-left text-sm"><thead><tr>{["Fecha y hora", "Folio", "Tipo y dirección", "Trabajador o destino", "Proyecto", "Renglones", "Unidades", "Responsable", "Estado"].map((h) => <th className="p-3" key={h}>{h}</th>)}</tr></thead><tbody>{consulta.datos.elementos.map((v) => v.clase === "VALE" ? fila(v) : <Fragment key={v.lote_id}><tr className="border-b bg-muted/30"><td colSpan={9} className="p-3"><div className="flex flex-wrap items-center gap-3"><Boton variante="texto" onClick={() => setExpandidos((prev) => { const n = new Set(prev); n.has(v.lote_id!) ? n.delete(v.lote_id!) : n.add(v.lote_id!); return n; })}>{expandidos.has(v.lote_id!) ? "Ocultar" : "Ver"} los {v.vales?.length} vales</Boton><span>Importación · {v.renglones} renglones · {v.unidades} unidades · {v.estado_texto}</span>{puede("vales.ver") && v.vales?.[0] ? <BotonPdfVale id={v.vales[0].id} lote /> : null}</div></td></tr>{expandidos.has(v.lote_id!) ? v.vales?.map(fila) : null}</Fragment>)}</tbody></table></div>
      {!consulta.datos.total ? <p className="py-5">{consulta.datos.mensaje}</p> : null}<div className="mt-3 flex items-center gap-3"><Boton variante="contorno" disabled={pagina <= 1} onClick={() => { const n = new URLSearchParams(url); n.set("pagina", String(pagina - 1)); setUrl(n); }}>Anterior</Boton><span>Página {pagina} · {consulta.datos.total} operaciones</span><Boton variante="contorno" disabled={pagina * 25 >= consulta.datos.total} onClick={() => { const n = new URLSearchParams(url); n.set("pagina", String(pagina + 1)); setUrl(n); }}>Siguiente</Boton></div>
    </> : null}
  </Pantalla>;
}
