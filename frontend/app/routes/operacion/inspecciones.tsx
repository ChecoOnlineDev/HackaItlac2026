import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { ClipboardCheckIcon } from "lucide-react";
import { consultarPendientes, textoVigencia, type EstadoPendiente, type PendienteInspeccion } from "~/api/inspecciones";
import { apiGet } from "~/api/cliente";
import { mensajeDeError } from "~/api/errores";
import type { Pagina } from "~/api/tipos";
import { Tabs, TabsList, TabsTrigger } from "~/components/ui/tabs";
import { useConsulta, useRetraso } from "~/componentes/catalogo/usar-consulta";
import { Paginador, Seleccion } from "~/componentes/catalogo/campos";
import { formatearFecha } from "~/componentes/dominio/fechas";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { Boton } from "~/componentes/ui/boton";
import { CampoBusqueda } from "~/componentes/ui/campo-busqueda";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { Hoja } from "~/componentes/ui/hoja";
import { useSesionActiva } from "~/sesion/sesion";

export const handle: ManejadorRuta = { dispositivo: "celular", permiso: "inspecciones.ver" };
const ESTADOS: EstadoPendiente[] = ["VENCIDA", "POR_VENCER", "SIN_INSPECCION"];

export default function Inspecciones() {
  const { sesion, puede, cambiarAlmacen } = useSesionActiva();
  const navegar = useNavigate();
  const [parametros, setParametros] = useSearchParams();
  const pedido = parametros.get("estado") as EstadoPendiente;
  const estado = ESTADOS.includes(pedido) ? pedido : "VENCIDA";
  const inicioElegido = useRef(ESTADOS.includes(pedido));
  const [texto, setTexto] = useState(""); const q = useRetraso(texto);
  const [almacen, setAlmacen] = useState(""); const [categoria, setCategoria] = useState(""); const [ubicacion, setUbicacion] = useState("");
  const [pagina, setPagina] = useState(1); const [devolver, setDevolver] = useState<PendienteInspeccion | null>(null);
  const [cambiando, setCambiando] = useState(false); const [errorAccion, setErrorAccion] = useState<string | null>(null);
  const lista = useConsulta((signal) => consultarPendientes({ estado, almacen_id: almacen, categoria_id: categoria, ubicacion, q, pagina, tamano: 20 }, signal), JSON.stringify([estado, almacen, categoria, ubicacion, q, pagina]));
  const almacenes = useConsulta((signal) => apiGet<{ id: string; nombre: string }[]>("/almacenes", undefined, signal), "almacenes-inspecciones");
  const categorias = useConsulta((signal) => apiGet<Pagina<{ id: string; nombre: string }>>("/categorias", { tamano: 200 }, signal), "categorias-inspecciones");
  useEffect(() => { setPagina(1); }, [q]);
  useEffect(() => {
    if (inicioElegido.current || !lista.datos) return;
    inicioElegido.current = true;
    const c = lista.datos.conteos;
    setParametros({ estado: c.vencidas ? "VENCIDA" : c.por_vencer ? "POR_VENCER" : c.sin_inspeccion ? "SIN_INSPECCION" : "VENCIDA" }, { replace: true });
  }, [lista.datos, setParametros]);
  async function inspeccionar(p: PendienteInspeccion) {
    if (cambiando) return; setCambiando(true); setErrorAccion(null);
    try {
      if (!puede("almacenes.todos") && p.ubicacion.almacen && p.ubicacion.almacen.id !== sesion.almacen?.id) await cambiarAlmacen(p.ubicacion.almacen.id);
      void navegar(`/inspeccionar?pieza=${p.pieza.id}`);
    } catch (causa) { setErrorAccion(mensajeDeError(causa)); } finally { setCambiando(false); }
  }
  const c = lista.datos?.conteos;
  return <Pantalla titulo="Inspecciones" descripcion="Revisa lo vencido, lo que vence pronto y las piezas sin inspección." acciones={puede("piezas.inspeccionar") ? <Boton variante="normal" nativeButton={false} render={<Link to="/inspeccionar" />}><ClipboardCheckIcon aria-hidden="true" />Inspeccionar</Boton> : null}>
    <Tabs value={estado} onValueChange={(v) => { inicioElegido.current = true; setParametros({ estado: String(v) }); setPagina(1); }}><TabsList className="w-full"><TabsTrigger value="VENCIDA">Vencidas {c ? `(${c.vencidas})` : ""}</TabsTrigger><TabsTrigger value="POR_VENCER">Por vencer {c ? `(${c.por_vencer})` : ""}</TabsTrigger><TabsTrigger value="SIN_INSPECCION">Sin inspección {c ? `(${c.sin_inspeccion})` : ""}</TabsTrigger></TabsList></Tabs>
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><CampoBusqueda etiqueta="Buscar pieza" value={texto} alCambiar={setTexto} placeholder="Código, serie o artículo" />
      {(almacenes.datos?.length ?? 0) > 1 ? <Seleccion etiqueta="Almacén" value={almacen} alCambiar={(v) => { setAlmacen(v); setPagina(1); }} vacio="Todos tus almacenes" opciones={(almacenes.datos ?? []).map((a) => ({ valor: a.id, texto: a.nombre }))} /> : null}
      <Seleccion etiqueta="Categoría" value={categoria} alCambiar={(v) => { setCategoria(v); setPagina(1); }} vacio="Todas" opciones={(categorias.datos?.elementos ?? []).map((a) => ({ valor: a.id, texto: a.nombre }))} />
      <Seleccion etiqueta="Dónde está" value={ubicacion} alCambiar={(v) => { setUbicacion(v); setPagina(1); }} vacio="Todas las ubicaciones" opciones={[{ valor: "ALMACEN", texto: "En el almacén" }, { valor: "TRABAJADOR", texto: "Con trabajadores" }]} />
    </div>
    {errorAccion ? <p role="alert" className="text-destructive">{errorAccion}</p> : null}
    {c?.no_aptas_con_trabajador ? <p role="status">{c.no_aptas_con_trabajador} piezas no aptas están con trabajadores. Pide que las devuelvan.</p> : null}
    {lista.error ? <EstadoError error={lista.error} alReintentar={lista.recargar} /> : null}
    {lista.cargando && !lista.datos ? <Esqueleto tipo="lista" cantidad={4} /> : null}
    {lista.datos?.elementos.length === 0 ? <EstadoVacio icono={ClipboardCheckIcon} titulo="No hay piezas en esta lista" descripcion="Prueba otra pestaña o cambia los filtros." /> : null}
    <ul className="grid gap-3 md:grid-cols-2" aria-busy={lista.cargando}>{lista.datos?.elementos.map((p) => <li key={p.pieza.id} className="flex flex-col gap-3 rounded-2xl border bg-card p-4"><div><h2 className="text-base font-semibold">{p.articulo.nombre}</h2><p className="text-sm text-muted-foreground">{p.pieza.codigo} · {p.pieza.numero_serie || "Serie pendiente"}</p></div><p className="font-semibold">{textoVigencia(p.dias_restantes)}</p><p className="text-sm">{p.ubicacion.tipo === "TRABAJADOR" ? `Con ${p.ubicacion.trabajador?.nombre ?? "un trabajador"}${p.ubicacion.desde ? ` desde ${formatearFecha(p.ubicacion.desde)}` : ""}` : p.ubicacion.tipo === "TRANSITO" ? `En tránsito hacia ${p.ubicacion.destino?.nombre ?? "otro almacén"}` : `En ${p.ubicacion.almacen?.nombre ?? "el almacén"}`}{p.ubicacion.folio ? ` · Vale ${p.ubicacion.folio}` : ""}</p>
      <div className="flex flex-wrap gap-2"><Boton variante="contorno" nativeButton={false} render={<Link to={`/piezas/${p.pieza.id}`} />}>Ver ficha</Boton>{p.accion === "INSPECCIONAR" && puede("piezas.inspeccionar") ? <Boton variante="normal" disabled={cambiando} onClick={() => void inspeccionar(p)}>{!puede("almacenes.todos") && p.ubicacion.almacen?.id !== sesion.almacen?.id ? `Cambiar a ${p.ubicacion.almacen?.nombre ?? "su almacén"} e inspeccionar` : "Inspeccionar"}</Boton> : p.accion === "PEDIR_DEVOLUCION" ? <Boton variante="contorno" onClick={() => setDevolver(p)}>Pedir que la devuelva</Boton> : p.ubicacion.tipo === "TRANSITO" ? <p className="text-sm text-muted-foreground">Inspecciónala cuando la reciban.</p> : null}</div>
    </li>)}</ul>
    {lista.datos ? <Paginador pagina={pagina} tamano={20} total={lista.datos.total} alCambiar={setPagina} ocupado={lista.cargando} /> : null}
    {c && (c.no_aptas || c.en_mantenimiento) ? <p className="text-sm text-muted-foreground">Fuera de estas listas: {c.no_aptas} no aptas y {c.en_mantenimiento} en mantenimiento o calibración. <Link to="/seguimiento" className="underline">Ver seguimiento</Link></p> : null}
    <Hoja abierta={Boolean(devolver)} alCambiar={(a) => !a && setDevolver(null)} titulo="Pedir devolución" descripcion="Este recordatorio no envía mensajes ni modifica el resguardo.">
      {devolver ? <div className="flex flex-col gap-3"><p className="font-semibold">{devolver.ubicacion.trabajador?.nombre} · {devolver.ubicacion.trabajador?.numero_empleado}</p><p>{devolver.ubicacion.trabajador?.puesto}</p><p>{devolver.articulo.nombre} · {devolver.pieza.codigo}</p>{devolver.ubicacion.desde ? <p>Desde {formatearFecha(devolver.ubicacion.desde)}{devolver.ubicacion.folio ? ` · Vale ${devolver.ubicacion.folio}` : ""}</p> : null}<p>Pídele que la devuelva para inspeccionarla.</p>{puede("devoluciones.crear") ? <Boton variante="normal" nativeButton={false} render={<Link to="/devolver" />}>Ir a Devolver</Boton> : null}</div> : null}
    </Hoja>
  </Pantalla>;
}
