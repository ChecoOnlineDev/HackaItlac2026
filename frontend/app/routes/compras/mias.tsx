import { cn } from "cn";
import { PlusIcon, ShoppingCartIcon, XIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";

import { apiGet, apiPost } from "~/api/cliente";
import { esErrorApi, mensajeDeError } from "~/api/errores";
import { Paginador } from "~/componentes/catalogo/campos";
import { useConsulta, useRetraso } from "~/componentes/catalogo/usar-consulta";
import { CancelarSolicitud } from "~/componentes/compras/solicitar/cancelar-solicitud";
import { TablaSolicitudes, TarjetasSolicitudes } from "~/componentes/compras/solicitar/lista";
import {
  OPCIONES_ESTADO,
  OPCIONES_URGENCIA,
  TAMANO_SOLICITUDES,
  type PaginaSolicitudes,
  type SolicitudCompra,
} from "~/componentes/compras/solicitar/tipos";
import { useAlmacenesParaPedir } from "~/componentes/compras/solicitar/usar-almacenes";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { FiltroLista, NotaAlcance, textoDeOpcion } from "~/componentes/reportes/filtros-comunes";
import { useFiltrosUrl } from "~/componentes/reportes/usar-filtros";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { CampoBusqueda } from "~/componentes/ui/campo-busqueda";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { HojaFiltros } from "~/componentes/ui/hoja-filtros";
import { useSesionActiva } from "~/sesion/sesion";

export const handle: ManejadorRuta = { permiso: "compras.solicitar" };

const CLAVES = ["q", "estado", "urgencia", "mias", "almacen"] as const;

const OPCIONES_QUIEN = [{ valor: "true", texto: "Solo las que yo pedí" }];

export default function ComprasUrgentes() {
  const { sesion, puede } = useSesionActiva();
  // Solo quien opera todos los almacenes (el Administrador) ve de todos y puede filtrar por almacén.
  const veTodos = puede("almacenes.todos");
  const almacenes = useAlmacenesParaPedir(veTodos);
  const { valores, pagina, cambiar, cambiarPagina, quitarTodos } = useFiltrosUrl(CLAVES);

  // El texto se guarda aparte para escribir sin trabas; se aplica a la dirección al dejar de escribir.
  const [texto, setTexto] = useState(valores.q);
  const q = useRetraso(texto.trim());
  const qEnUrl = useRef(valores.q);
  useEffect(() => {
    if (q !== qEnUrl.current) {
      qEnUrl.current = q;
      cambiar({ q });
    }
    // `cambiar` es estable; solo importa el texto ya retrasado.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  const parametros = {
    q,
    estado: valores.estado,
    urgencia: valores.urgencia,
    mias: valores.mias === "true" ? true : undefined,
    almacen_id: veTodos ? valores.almacen : undefined,
  };
  const consulta = useConsulta(
    (signal) => apiGet<PaginaSolicitudes>("/solicitudes-compra", { ...parametros, pagina, tamano: TAMANO_SOLICITUDES }, signal),
    JSON.stringify([parametros, pagina]),
  );
  const { datos, cargando, error } = consulta;
  const elementos = datos?.elementos ?? [];
  const total = datos?.total ?? 0;

  // ---------------------------------------------------------------- cancelar una pendiente
  const [porCancelar, setPorCancelar] = useState<SolicitudCompra | null>(null);
  const [cancelando, setCancelando] = useState(false);
  const [errorCancelar, setErrorCancelar] = useState<string | null>(null);

  async function cancelar(nota: string) {
    if (!porCancelar || cancelando) return;
    setCancelando(true);
    setErrorCancelar(null);
    try {
      await apiPost(`/solicitudes-compra/${porCancelar.id}/cancelacion`, nota ? { nota } : undefined);
      aviso({ titulo: `Se canceló la solicitud ${porCancelar.folio}`, tipo: "exito" });
      setPorCancelar(null);
      consulta.recargar();
    } catch (causa) {
      setErrorCancelar(mensajeDeError(causa));
      // Si Compras ya la tomó (o ya no existe), la lista se pone al día para mostrar cómo está.
      if (esErrorApi(causa) && (causa.status === 409 || causa.status === 404)) consulta.recargar();
    } finally {
      setCancelando(false);
    }
  }

  function limpiar() {
    setTexto("");
    qEnUrl.current = "";
    quitarTodos();
  }

  const chips: { clave: (typeof CLAVES)[number]; texto: string }[] = [];
  if (valores.estado) chips.push({ clave: "estado", texto: `Estado: ${textoDeOpcion(OPCIONES_ESTADO, valores.estado) ?? valores.estado}` });
  if (valores.urgencia) chips.push({ clave: "urgencia", texto: `Urgencia: ${textoDeOpcion(OPCIONES_URGENCIA, valores.urgencia) ?? valores.urgencia}` });
  if (veTodos && valores.almacen) chips.push({ clave: "almacen", texto: `Almacén: ${textoDeOpcion(almacenes.opciones, valores.almacen) ?? "elegido"}` });
  if (valores.mias === "true") chips.push({ clave: "mias", texto: "Solo las que yo pedí" });
  const hayFiltros = chips.length > 0 || q !== "";

  const titulo = veTodos ? "Solicitudes de compra" : "Compras urgentes de mi almacén";
  const botonPedir = (
    <Boton variante="normal" nativeButton={false} render={<Link to="/compras/nueva" />}>
      <PlusIcon aria-hidden="true" />
      Pedir compra urgente
    </Boton>
  );

  let contenido;
  if (error) {
    contenido = <EstadoError error={error} alReintentar={consulta.recargar} />;
  } else if (cargando && !datos) {
    contenido = (
      <>
        <div className="hidden md:block">
          <Esqueleto tipo="tabla" cantidad={5} />
        </div>
        <div className="md:hidden">
          <Esqueleto tipo="lista" cantidad={4} />
        </div>
      </>
    );
  } else if (total === 0 && !cargando) {
    contenido = (
      <EstadoVacio
        icono={ShoppingCartIcon}
        titulo={hayFiltros ? "No hay solicitudes con ese filtro" : "Todavía no hay solicitudes"}
        descripcion={
          hayFiltros
            ? "Prueba con otra palabra o quita algún filtro."
            : "Cuando falte una herramienta que el almacén no tiene, pide una compra urgente y aquí verás cómo avanza."
        }
        accion={
          hayFiltros ? (
            <Boton variante="contorno" onClick={limpiar}>
              Quitar filtros
            </Boton>
          ) : undefined
        }
      />
    );
  } else {
    contenido = (
      <div className={cn("flex flex-col gap-4 transition-opacity", cargando && "opacity-60")} aria-busy={cargando}>
        {/* `w-0 min-w-full`: la tabla ancha se desplaza dentro de su caja y no ensancha la página. */}
        <div className="w-0 min-w-full">
          <TablaSolicitudes solicitudes={elementos} conAlmacen={veTodos} alCancelar={(s) => { setErrorCancelar(null); setPorCancelar(s); }} />
        </div>
        <TarjetasSolicitudes solicitudes={elementos} conAlmacen={veTodos} alCancelar={(s) => { setErrorCancelar(null); setPorCancelar(s); }} />
        <Paginador pagina={pagina} tamano={TAMANO_SOLICITUDES} total={total} alCambiar={cambiarPagina} ocupado={cargando} />
      </div>
    );
  }

  return (
    <Pantalla
      titulo={titulo}
      descripcion={veTodos ? "Lo que se ha pedido a Compras en todos los almacenes y cómo va." : "Lo que tú y tus compañeros han pedido a Compras y cómo va."}
      acciones={botonPedir}
    >
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <CampoBusqueda
            etiqueta="Buscar solicitudes por folio, artículo o motivo"
            placeholder="Buscar por folio, artículo o motivo"
            value={texto}
            alCambiar={setTexto}
            claseContenedor="min-w-64"
            className="h-12 rounded-xl text-base"
          />
          <HojaFiltros
            valores={{ estado: valores.estado, urgencia: valores.urgencia, mias: valores.mias, almacen: valores.almacen }}
            activos={[valores.estado, valores.urgencia, valores.mias, veTodos ? valores.almacen : ""].filter(Boolean).length}
            alAplicar={(v) => cambiar({ estado: v.estado, urgencia: v.urgencia, mias: v.mias, almacen: veTodos ? v.almacen : null })}
            alLimpiar={() => cambiar({ estado: null, urgencia: null, mias: null, almacen: null })}
          >
            {(borrador, cambiarBorrador) => (
              <>
                {veTodos && almacenes.opciones.length > 0 ? (
                  <FiltroLista
                    etiqueta="Almacén"
                    vacio="Todos los almacenes"
                    valor={borrador.almacen}
                    opciones={almacenes.opciones}
                    alCambiar={(v) => cambiarBorrador({ almacen: v })}
                  />
                ) : null}
                <FiltroLista
                  etiqueta="Estado"
                  vacio="Todos los estados"
                  valor={borrador.estado}
                  opciones={OPCIONES_ESTADO}
                  alCambiar={(v) => cambiarBorrador({ estado: v })}
                />
                <FiltroLista
                  etiqueta="Urgencia"
                  vacio="Cualquier urgencia"
                  valor={borrador.urgencia}
                  opciones={OPCIONES_URGENCIA}
                  alCambiar={(v) => cambiarBorrador({ urgencia: v })}
                />
                <FiltroLista
                  etiqueta="Quién la pidió"
                  vacio={veTodos ? "Cualquiera" : "Cualquiera de mi almacén"}
                  valor={borrador.mias}
                  opciones={OPCIONES_QUIEN}
                  alCambiar={(v) => cambiarBorrador({ mias: v })}
                />
              </>
            )}
          </HojaFiltros>
        </div>

        {chips.length > 0 ? (
          <ul aria-label="Filtros activos" className="flex flex-wrap items-center gap-2">
            {chips.map((f) => (
              <li key={f.clave}>
                <button
                  type="button"
                  onClick={() => cambiar({ [f.clave]: null })}
                  aria-label={`Quitar filtro: ${f.texto}`}
                  className="inline-flex min-h-10 items-center gap-1.5 rounded-full border border-primary/30 bg-accent px-3 text-xs font-semibold text-marino hover:bg-accent/70"
                >
                  {f.texto}
                  <XIcon aria-hidden="true" className="size-3.5" />
                </button>
              </li>
            ))}
            <li>
              <Boton variante="texto" className="h-10 px-3 text-xs" onClick={limpiar}>
                Quitar todos
              </Boton>
            </li>
          </ul>
        ) : null}

        <div className="flex flex-col gap-1 text-xs text-muted-foreground">
          <NotaAlcance almacen={veTodos ? null : sesion.almacen} />
          <p>Toca una solicitud para ver su historial. Solo se puede cancelar mientras Compras no la haya tomado.</p>
        </div>

        <p className="text-sm font-semibold" aria-live="polite">
          {datos && !error ? `${total} ${total === 1 ? "solicitud" : "solicitudes"}` : " "}
        </p>

        {contenido}
      </div>

      <CancelarSolicitud
        solicitud={porCancelar}
        cargando={cancelando}
        error={errorCancelar}
        alCerrar={() => setPorCancelar(null)}
        alConfirmar={(nota) => void cancelar(nota)}
      />
    </Pantalla>
  );
}
