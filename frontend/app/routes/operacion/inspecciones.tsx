import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { ClipboardCheckIcon, MapPinIcon } from "lucide-react";
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
const CLASE_SELECCION = "whitespace-nowrap data-[size=default]:h-11 *:data-[slot=select-value]:line-clamp-1";
const CLASE_PESTANA = "min-h-11 flex-1 gap-2 px-3 text-sm font-semibold data-active:bg-primary data-active:text-primary-foreground data-active:shadow-sm dark:data-active:bg-primary dark:data-active:text-primary-foreground";
const INSIGNIA = "inline-flex w-fit items-center gap-1.5 rounded-full border px-2.5 py-1 text-sm font-semibold";
const CLASE_VIGENCIA: Record<EstadoPendiente, string> = {
  VENCIDA: "border-destructive/30 bg-destructive/10 text-destructive",
  POR_VENCER: "border-semaforo-amarillo/50 bg-semaforo-amarillo/15 text-foreground",
  SIN_INSPECCION: "border-primary/25 bg-primary/10 text-primary",
};

function Conteo({ activo, valor }: { activo: boolean; valor: number | undefined }) {
  if (valor === undefined) return null;
  return (
    <span className={`inline-flex min-w-6 items-center justify-center rounded-full px-1.5 text-xs font-bold tabular-nums leading-5 ${activo ? "bg-primary-foreground/20 text-primary-foreground" : "bg-background text-foreground ring-1 ring-border"}`}>
      {valor}
    </span>
  );
}

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
  const textoUbicacion = (p: PendienteInspeccion) =>
    `${p.ubicacion.tipo === "TRABAJADOR" ? `Con ${p.ubicacion.trabajador?.nombre ?? "un trabajador"}${p.ubicacion.desde ? ` desde ${formatearFecha(p.ubicacion.desde)}` : ""}` : p.ubicacion.tipo === "TRANSITO" ? `En tránsito hacia ${p.ubicacion.destino?.nombre ?? "otro almacén"}` : `En ${p.ubicacion.almacen?.nombre ?? "el almacén"}`}${p.ubicacion.folio ? ` · Vale ${p.ubicacion.folio}` : ""}`;
  return (
    <Pantalla
      titulo="Inspecciones"
      descripcion="Revisa lo vencido, lo que vence pronto y las piezas sin inspección."
      acciones={
        puede("piezas.inspeccionar") ? (
          <Boton variante="normal" nativeButton={false} render={<Link to="/inspeccionar" />}>
            <ClipboardCheckIcon aria-hidden="true" />
            Inspeccionar
          </Boton>
        ) : null
      }
    >
      <Tabs
        value={estado}
        onValueChange={(v) => {
          inicioElegido.current = true;
          setParametros({ estado: String(v) });
          setPagina(1);
        }}
      >
        <TabsList className="h-auto w-full flex-col gap-1 rounded-xl p-1 sm:flex-row">
          <TabsTrigger value="VENCIDA" className={CLASE_PESTANA}>
            Vencidas
            <Conteo activo={estado === "VENCIDA"} valor={c?.vencidas} />
          </TabsTrigger>
          <TabsTrigger value="POR_VENCER" className={CLASE_PESTANA}>
            Por vencer
            <Conteo activo={estado === "POR_VENCER"} valor={c?.por_vencer} />
          </TabsTrigger>
          <TabsTrigger value="SIN_INSPECCION" className={CLASE_PESTANA}>
            Sin inspección
            <Conteo activo={estado === "SIN_INSPECCION"} valor={c?.sin_inspeccion} />
          </TabsTrigger>
        </TabsList>
      </Tabs>
      <div className="grid grid-cols-1 items-end gap-3 rounded-2xl border bg-card p-3 shadow-xs sm:grid-cols-2 sm:p-4 lg:grid-cols-4">
        <div className="flex min-w-0 flex-col gap-1.5 sm:col-span-2 lg:col-span-1">
          <span aria-hidden="true" className="text-sm font-medium text-foreground">Buscar pieza</span>
          <CampoBusqueda etiqueta="Buscar pieza" value={texto} alCambiar={setTexto} placeholder="Código, serie o artículo" className="text-base" />
        </div>
        {(almacenes.datos?.length ?? 0) > 1 ? (
          <Seleccion
            etiqueta="Almacén"
            className={CLASE_SELECCION}
            value={almacen}
            alCambiar={(v) => { setAlmacen(v); setPagina(1); }}
            vacio="Todos tus almacenes"
            opciones={(almacenes.datos ?? []).map((a) => ({ valor: a.id, texto: a.nombre }))}
          />
        ) : null}
        <Seleccion
          etiqueta="Categoría"
          className={CLASE_SELECCION}
          value={categoria}
          alCambiar={(v) => { setCategoria(v); setPagina(1); }}
          vacio="Todas"
          opciones={(categorias.datos?.elementos ?? []).map((a) => ({ valor: a.id, texto: a.nombre }))}
        />
        <Seleccion
          etiqueta="Dónde está"
          className={CLASE_SELECCION}
          value={ubicacion}
          alCambiar={(v) => { setUbicacion(v); setPagina(1); }}
          vacio="Todas las ubicaciones"
          opciones={[{ valor: "ALMACEN", texto: "En el almacén" }, { valor: "TRABAJADOR", texto: "Con trabajadores" }]}
        />
      </div>
      {errorAccion ? <p role="alert" className="text-destructive">{errorAccion}</p> : null}
      {c?.no_aptas_con_trabajador ? <p role="status" className="rounded-xl border bg-muted/50 px-4 py-3 text-sm">{c.no_aptas_con_trabajador} piezas no aptas están con trabajadores. Pide que las devuelvan.</p> : null}
      {lista.error ? <EstadoError error={lista.error} alReintentar={lista.recargar} /> : null}
      {lista.cargando && !lista.datos ? <Esqueleto tipo="lista" cantidad={4} /> : null}
      {lista.datos?.elementos.length === 0 ? <EstadoVacio icono={ClipboardCheckIcon} titulo="No hay piezas en esta lista" descripcion="Prueba otra pestaña o cambia los filtros." /> : null}
      <ul className="grid gap-4 md:grid-cols-2" aria-busy={lista.cargando}>
        {lista.datos?.elementos.map((p) => (
          <li key={p.pieza.id} className="flex flex-col gap-4 rounded-2xl border bg-card p-4 shadow-xs transition-shadow hover:shadow-md sm:p-5">
            <div className="flex flex-col gap-1">
              <h2 className="text-base font-semibold leading-snug text-foreground">{p.articulo.nombre}</h2>
              <p className="text-sm text-muted-foreground">{p.pieza.codigo} · {p.pieza.numero_serie || "Serie pendiente"}</p>
            </div>
            <p className={`${INSIGNIA} ${CLASE_VIGENCIA[estado]}`}>{textoVigencia(p.dias_restantes)}</p>
            <p className="flex items-start gap-2 text-sm text-foreground">
              <MapPinIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
              <span>{textoUbicacion(p)}</span>
            </p>
            <div className="mt-auto flex flex-col gap-2 border-t pt-4 sm:flex-row sm:flex-wrap">
              <Boton variante="contorno" className="w-full sm:w-auto" nativeButton={false} render={<Link to={`/piezas/${p.pieza.id}`} />}>Ver ficha</Boton>
              {p.accion === "INSPECCIONAR" && puede("piezas.inspeccionar") ? (
                <Boton variante="normal" className="w-full sm:w-auto" disabled={cambiando} onClick={() => void inspeccionar(p)}>
                  {!puede("almacenes.todos") && p.ubicacion.almacen?.id !== sesion.almacen?.id ? `Cambiar a ${p.ubicacion.almacen?.nombre ?? "su almacén"} e inspeccionar` : "Inspeccionar"}
                </Boton>
              ) : p.accion === "PEDIR_DEVOLUCION" ? (
                <Boton variante="contorno" className="w-full sm:w-auto" onClick={() => setDevolver(p)}>Pedir que la devuelva</Boton>
              ) : p.ubicacion.tipo === "TRANSITO" ? (
                <p className="text-sm text-muted-foreground">Inspecciónala cuando la reciban.</p>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
    {lista.datos ? <Paginador pagina={pagina} tamano={20} total={lista.datos.total} alCambiar={setPagina} ocupado={lista.cargando} /> : null}
    {c && (c.no_aptas || c.en_mantenimiento) ? <p className="text-sm text-muted-foreground">Fuera de estas listas: {c.no_aptas} no aptas y {c.en_mantenimiento} en mantenimiento o calibración. <Link to="/seguimiento" className="underline">Ver seguimiento</Link></p> : null}
    <Hoja abierta={Boolean(devolver)} alCambiar={(a) => !a && setDevolver(null)} titulo="Pedir devolución" descripcion="Este recordatorio no envía mensajes ni modifica el resguardo.">
      {devolver ? <div className="flex flex-col gap-3"><p className="font-semibold">{devolver.ubicacion.trabajador?.nombre} · {devolver.ubicacion.trabajador?.numero_empleado}</p><p>{devolver.ubicacion.trabajador?.puesto}</p><p>{devolver.articulo.nombre} · {devolver.pieza.codigo}</p>{devolver.ubicacion.desde ? <p>Desde {formatearFecha(devolver.ubicacion.desde)}{devolver.ubicacion.folio ? ` · Vale ${devolver.ubicacion.folio}` : ""}</p> : null}<p>Pídele que la devuelva para inspeccionarla.</p>{puede("devoluciones.crear") ? <Boton variante="normal" nativeButton={false} render={<Link to="/devolver" />}>Ir a Devolver</Boton> : null}</div> : null}
    </Hoja>
    </Pantalla>
  );
}
