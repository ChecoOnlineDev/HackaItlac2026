import { cn } from "cn";
import { RefreshCwIcon, ShoppingCartIcon, XIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { apiGet } from "~/api/cliente";
import type { Pagina } from "~/api/tipos";
import { Paginador } from "~/componentes/catalogo/campos";
import { useConsulta, useRetraso } from "~/componentes/catalogo/usar-consulta";
import { useAlmacenesDeLaCola } from "~/componentes/compras/atender/almacenes";
import { FlujoAccion } from "~/componentes/compras/atender/flujo-accion";
import { TablaSolicitudes, TarjetasSolicitudes } from "~/componentes/compras/atender/lista";
import { ResumenCompras, useResumenCola } from "~/componentes/compras/atender/resumen";
import {
  TAMANO_COLA,
  TEXTO_ESTADO,
  TEXTO_URGENCIA,
  type AccionSolicitud,
  type SolicitudCompra,
} from "~/componentes/compras/atender/tipos";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { chipPeriodo, FiltroLista, FiltroPeriodo, textoDeOpcion } from "~/componentes/reportes/filtros-comunes";
import { useFiltrosUrl } from "~/componentes/reportes/usar-filtros";
import { Boton } from "~/componentes/ui/boton";
import { CampoBusqueda } from "~/componentes/ui/campo-busqueda";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { HojaFiltros } from "~/componentes/ui/hoja-filtros";

export const handle: ManejadorRuta = { permiso: "compras.atender" };

const CLAVES = ["q", "estado", "urgencia", "almacen", "desde", "hasta"] as const;

const OPCIONES_ESTADO = Object.entries(TEXTO_ESTADO).map(([valor, texto]) => ({ valor, texto }));
const OPCIONES_URGENCIA = Object.entries(TEXTO_URGENCIA).map(([valor, texto]) => ({ valor, texto }));

export default function ColaDeCompras() {
  const { valores, pagina, cambiar, cambiarPagina, quitarTodos } = useFiltrosUrl(CLAVES);
  const almacenes = useAlmacenesDeLaCola();

  // El texto se guarda aparte para escribir sin trabas; pasa a la dirección al dejar de escribir.
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
    q: valores.q,
    estado: valores.estado,
    urgencia: valores.urgencia,
    almacen_id: valores.almacen,
    desde: valores.desde,
    hasta: valores.hasta,
  };
  const consulta = useConsulta(
    (signal) => apiGet<Pagina<SolicitudCompra>>("/solicitudes-compra", { ...parametros, pagina, tamano: TAMANO_COLA }, signal),
    JSON.stringify([parametros, pagina]),
  );
  const { datos, cargando, error, recargar } = consulta;
  const elementos = datos?.elementos ?? [];
  const total = datos?.total ?? 0;

  const [version, setVersion] = useState(0);
  const { resumen } = useResumenCola(version);
  const actualizar = () => {
    recargar();
    setVersion((v) => v + 1);
  };

  // Al volver a esta pestaña, la cola se pone al día.
  useEffect(() => {
    const alVolver = () => {
      if (document.visibilityState === "visible") actualizar();
    };
    document.addEventListener("visibilitychange", alVolver);
    return () => document.removeEventListener("visibilitychange", alVolver);
    // `actualizar` solo usa setters y `recargar`, que son estables.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const [enAccion, setEnAccion] = useState<{ solicitud: SolicitudCompra; accion: AccionSolicitud } | null>(null);

  const chips: { clave: string; texto: string }[] = [];
  if (valores.estado) chips.push({ clave: "estado", texto: `Estado: ${textoDeOpcion(OPCIONES_ESTADO, valores.estado) ?? valores.estado}` });
  if (valores.urgencia) chips.push({ clave: "urgencia", texto: `Urgencia: ${textoDeOpcion(OPCIONES_URGENCIA, valores.urgencia) ?? valores.urgencia}` });
  if (valores.almacen) chips.push({ clave: "almacen", texto: `Almacén: ${textoDeOpcion(almacenes, valores.almacen) ?? "elegido"}` });
  const periodo = chipPeriodo(valores.desde, valores.hasta);
  if (periodo) chips.push(periodo);
  const hayFiltros = chips.length > 0 || valores.q !== "";

  function quitarChip(clave: string) {
    if (clave === "periodo") cambiar({ desde: null, hasta: null });
    else cambiar({ [clave]: null } as Record<(typeof CLAVES)[number], null>);
  }

  function limpiar() {
    setTexto("");
    qEnUrl.current = "";
    quitarTodos();
  }

  let contenido;
  if (error && !datos) {
    contenido = <EstadoError error={error} alReintentar={actualizar} />;
  } else if (cargando && !datos) {
    contenido = (
      <>
        <div className="hidden md:block">
          <Esqueleto tipo="tabla" cantidad={6} />
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
        titulo={hayFiltros ? "No hay solicitudes con ese filtro" : "No hay solicitudes de compra"}
        descripcion={hayFiltros ? "Prueba con otra palabra o quita algún filtro." : "Cuando un almacén pida una compra urgente, aparecerá aquí."}
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
        {error ? <EstadoError error={error} alReintentar={actualizar} /> : null}
        <TablaSolicitudes solicitudes={elementos} alAccion={(solicitud, accion) => setEnAccion({ solicitud, accion })} />
        <TarjetasSolicitudes solicitudes={elementos} alAccion={(solicitud, accion) => setEnAccion({ solicitud, accion })} />
        <Paginador pagina={pagina} tamano={TAMANO_COLA} total={total} alCambiar={cambiarPagina} ocupado={cargando} />
      </div>
    );
  }

  return (
    <Pantalla
      titulo="Solicitudes de compra"
      descripcion="Lo que piden los almacenes. Las urgentes y las más antiguas van primero."
      acciones={
        <Boton variante="contorno" onClick={actualizar} disabled={cargando}>
          <RefreshCwIcon aria-hidden="true" />
          Actualizar
        </Boton>
      }
    >
      <div className="flex flex-col gap-4">
        <ResumenCompras
          resumen={resumen}
          activo={valores.estado}
          alElegir={(estado) => cambiar({ estado: valores.estado === estado ? null : estado })}
        />

        <div className="flex flex-wrap items-center gap-2">
          <CampoBusqueda
            etiqueta="Buscar por folio, artículo, descripción o motivo"
            placeholder="Buscar folio, artículo o motivo"
            value={texto}
            alCambiar={setTexto}
            claseContenedor="min-w-64"
            className="h-12 rounded-xl text-base"
          />
          <HojaFiltros
            valores={{ estado: valores.estado, urgencia: valores.urgencia, almacen: valores.almacen, desde: valores.desde, hasta: valores.hasta }}
            activos={[valores.estado, valores.urgencia, valores.almacen, valores.desde || valores.hasta].filter(Boolean).length}
            alAplicar={(v) => cambiar({ estado: v.estado, urgencia: v.urgencia, almacen: v.almacen, desde: v.desde, hasta: v.hasta })}
            alLimpiar={() => cambiar({ estado: null, urgencia: null, almacen: null, desde: null, hasta: null })}
          >
            {(borrador, cambiarBorrador) => (
              <>
                <FiltroLista
                  etiqueta="Estado"
                  vacio="Todos los estados"
                  valor={borrador.estado}
                  opciones={OPCIONES_ESTADO}
                  alCambiar={(v) => cambiarBorrador({ estado: v })}
                />
                <FiltroLista
                  etiqueta="Urgencia"
                  vacio="Todas"
                  valor={borrador.urgencia}
                  opciones={OPCIONES_URGENCIA}
                  alCambiar={(v) => cambiarBorrador({ urgencia: v })}
                />
                {almacenes.length > 0 ? (
                  <FiltroLista
                    etiqueta="Almacén"
                    vacio="Todos los almacenes"
                    valor={borrador.almacen}
                    opciones={almacenes}
                    alCambiar={(v) => cambiarBorrador({ almacen: v })}
                  />
                ) : null}
                <FiltroPeriodo
                  desde={borrador.desde}
                  hasta={borrador.hasta}
                  alCambiar={(r) => cambiarBorrador({ desde: r.desde ?? "", hasta: r.hasta ?? "" })}
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
                  onClick={() => quitarChip(f.clave)}
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

        <p className="text-sm font-semibold" aria-live="polite">
          {datos && !error ? `${total} ${total === 1 ? "solicitud" : "solicitudes"}` : " "}
        </p>

        {contenido}
      </div>

      <FlujoAccion
        solicitud={enAccion?.solicitud ?? null}
        accion={enAccion?.accion ?? null}
        alCerrar={() => setEnAccion(null)}
        alTerminar={actualizar}
        alDesactualizar={actualizar}
      />
    </Pantalla>
  );
}
