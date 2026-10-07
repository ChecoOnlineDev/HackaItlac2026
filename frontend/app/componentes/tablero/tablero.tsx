import { Loader2Icon } from "lucide-react";
import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { apiGet } from "~/api/cliente";
import { pedirConsumoTablero, pedirResumenTablero } from "~/api/tablero";
import type { Pagina } from "~/api/tipos";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import type { OpcionLista } from "~/componentes/ui/lista-desplegable";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { useSesionActiva } from "~/sesion/sesion";
import { FiltrosConsumoBarra, type FiltrosConsumo } from "./filtros-consumo";
import { esPeriodoPorOmision, periodoPorOmision } from "./periodos";
import { TarjetasIndicadores } from "./tarjetas-indicadores";

// recharts pesa: la gráfica se carga solo cuando el Inicio muestra el tablero (ADR-009).
const GraficaConsumo = lazy(() => import("./grafica-consumo"));

const NOMBRE_CATEGORIA_POR_OMISION = "consumibles de trabajo";
const normalizar = (t: string) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").trim().toLowerCase();

/**
 * Tablero del Inicio (FEAT-008 4.2): tarjetas de indicadores y, debajo, la gráfica de lo más usado con sus filtros.
 * Lo que se ve lo decide el servidor (`alcance` del resumen): quien no tiene `tablero.ver` no debe montarlo.
 */
export function Tablero() {
  const { puedeAlguno } = useSesionActiva();
  const [almacen, setAlmacen] = useState("");
  const resumen = useConsulta((signal) => pedirResumenTablero(almacen, signal), `resumen|${almacen}`);
  const alcance = resumen.datos?.alcance ?? null;
  const puedeElegir = alcance?.puede_elegir ?? false;

  return (
    <section aria-labelledby="titulo-tablero" className="flex flex-col gap-4">
      <h2 id="titulo-tablero" className="text-xl font-semibold text-marino">
        Tablero
        {alcance ? <span className="ml-2 text-base font-normal text-muted-foreground">· {alcance.nombre}</span> : null}
      </h2>

      {resumen.error && !resumen.datos ? (
        <EstadoError error={resumen.error} alReintentar={resumen.recargar} />
      ) : !resumen.datos ? (
        <Esqueleto tipo="tarjeta" cantidad={4} />
      ) : !alcance?.es_todos && !alcance?.almacen_id ? (
        <EstadoVacio titulo="No tienes un almacén asignado" descripcion="Pídele a tu supervisor que te asigne uno para ver el tablero." />
      ) : (
        <>
          {resumen.error ? <EstadoError error={resumen.error} alReintentar={resumen.recargar} /> : null}
          <div aria-busy={resumen.cargando} className={resumen.cargando ? "opacity-70 transition-opacity" : "transition-opacity"}>
            <TarjetasIndicadores resumen={resumen.datos} puedeVerSeguimiento={puedeAlguno(["reportes.existencias"])} />
          </div>
          <ConsumoMasUsado puedeElegir={puedeElegir} almacen={almacen} alCambiarAlmacen={setAlmacen} />
        </>
      )}
    </section>
  );
}

interface PropiedadesConsumo {
  puedeElegir: boolean;
  almacen: string;
  alCambiarAlmacen: (id: string) => void;
}

function ConsumoMasUsado({ puedeElegir, almacen, alCambiarAlmacen }: PropiedadesConsumo) {
  const [periodo, setPeriodo] = useState(periodoPorOmision);
  // null = todavía no se sabe cuál es la categoría de consumibles (se espera a que llegue la lista).
  const [categoria, setCategoria] = useState<string | null>(null);
  const [separar, setSeparar] = useState(false);

  const categorias = useConsulta((signal) => apiGet<Pagina<{ id: string; nombre: string }>>("/categorias", { tamano: 200 }, signal), "tablero-categorias");
  const almacenes = useConsulta((signal) => (puedeElegir ? apiGet<{ id: string; clave: string; nombre: string }[]>("/almacenes", undefined, signal) : Promise.resolve([])), `tablero-almacenes|${puedeElegir}`);

  const opcionesCategoria = useMemo<OpcionLista[]>(() => (categorias.datos?.elementos ?? []).map((c) => ({ valor: c.id, texto: c.nombre })), [categorias.datos]);
  const opcionesAlmacen = useMemo<OpcionLista[]>(
    () => (almacenes.datos ?? []).map((a) => ({ valor: a.id, texto: a.nombre })),
    [almacenes.datos],
  );
  const idConsumibles = useMemo(() => opcionesCategoria.find((o) => normalizar(o.texto) === NOMBRE_CATEGORIA_POR_OMISION)?.valor ?? "", [opcionesCategoria]);

  // Al llegar la lista (o fallar), se fija la categoría por omisión una sola vez.
  const fijada = useRef(false);
  useEffect(() => {
    if (fijada.current || categoria !== null) return;
    if (categorias.cargando && !categorias.datos && !categorias.error) return;
    fijada.current = true;
    setCategoria(idConsumibles);
  }, [categoria, categorias.cargando, categorias.datos, categorias.error, idConsumibles]);

  const categoriaActual = categoria ?? idConsumibles;
  const errorFechas = periodo.desde && periodo.hasta && periodo.desde > periodo.hasta ? "«Desde» no puede ser después de «Hasta»." : null;
  const sinFechas = !periodo.desde || !periodo.hasta;
  const listo = categoria !== null && !errorFechas && !sinFechas;
  const separando = separar && puedeElegir && !almacen;

  const consumo = useConsulta(
    (signal) =>
      listo
        ? pedirConsumoTablero(
            { desde: periodo.desde, hasta: periodo.hasta, almacen_id: puedeElegir ? almacen : undefined, categoria_id: categoriaActual, separar_por_almacen: separando },
            signal,
          )
        : new Promise<never>(() => undefined),
    `consumo|${listo}|${periodo.desde}|${periodo.hasta}|${almacen}|${categoriaActual}|${separando}`,
  );

  const hayCambios = Boolean(almacen) || !esPeriodoPorOmision(periodo) || categoriaActual !== idConsumibles || separar;
  const limpiar = useCallback(() => {
    alCambiarAlmacen("");
    setPeriodo(periodoPorOmision());
    setCategoria(idConsumibles);
    setSeparar(false);
  }, [alCambiarAlmacen, idConsumibles]);

  const cambiar = (c: Partial<FiltrosConsumo>) => {
    if (c.almacen !== undefined) alCambiarAlmacen(c.almacen);
    if (c.periodo) setPeriodo(c.periodo);
    if (c.categoria !== undefined) setCategoria(c.categoria);
    if (c.separar !== undefined) setSeparar(c.separar);
  };

  const datos = consumo.datos;
  const actualizando = listo && consumo.cargando && Boolean(datos);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg text-marino">Lo más usado</CardTitle>
        <p className="text-sm text-muted-foreground">Artículos entregados en el periodo, sin contar los vales cancelados.</p>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <FiltrosConsumoBarra
          valor={{ almacen, periodo, categoria: categoriaActual, separar }}
          alCambiar={cambiar}
          alLimpiar={limpiar}
          hayCambios={hayCambios}
          almacenes={puedeElegir && !almacenes.error ? opcionesAlmacen : null}
          categorias={opcionesCategoria}
          puedeSeparar={puedeElegir && !almacen}
          errorFechas={errorFechas}
        />

        {puedeElegir && almacen && datos?.almacen ? (
          <p className="text-sm font-medium text-marino">Viendo: {datos.almacen.nombre}</p>
        ) : null}

        <div aria-live="polite" className="min-h-6 text-sm text-muted-foreground">
          {actualizando ? (
            <span className="inline-flex items-center gap-2">
              <Loader2Icon aria-hidden="true" className="size-4 animate-spin" />
              Actualizando…
            </span>
          ) : null}
        </div>

        {consumo.error ? (
          <EstadoError error={consumo.error} alReintentar={consumo.recargar} />
        ) : !datos ? (
          errorFechas ? (
            <EstadoVacio titulo="Revisa las fechas" descripcion="Elige un periodo en el que «Desde» no sea después de «Hasta»." />
          ) : (
            <Esqueleto tipo="lista" cantidad={4} />
          )
        ) : datos.sin_registros ? (
          <div className={actualizando ? "opacity-60" : undefined}>
            <EstadoVacio titulo="No hubo consumo en estas fechas" descripcion="Prueba con otro periodo o con otra categoría." />
          </div>
        ) : (
          <div className={actualizando ? "opacity-60 transition-opacity" : "transition-opacity"} aria-busy={actualizando}>
            <Suspense fallback={<Esqueleto tipo="lista" cantidad={4} />}>
              <GraficaConsumo datos={datos} />
            </Suspense>
            <p className="mt-2 text-sm text-muted-foreground">
              Total del periodo: <strong className="text-foreground tabular-nums">{datos.total_general.toLocaleString("es-MX")}</strong>. Toca el nombre de un artículo para abrirlo.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
