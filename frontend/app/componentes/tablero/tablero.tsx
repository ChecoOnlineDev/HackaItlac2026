import { AnimatePresence, MotionConfig, motion } from "motion/react";
import { useEffect, useId, useMemo, useState, type ReactNode } from "react";

import { apiGet } from "~/api/cliente";
import { pedirResumenTablero, pedirValorTablero } from "~/api/tablero";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { ListaDesplegable, type OpcionLista } from "~/componentes/ui/lista-desplegable";
import { Tabs, TabsList, TabsTrigger } from "~/components/ui/tabs";
import { useSesionActiva } from "~/sesion/sesion";
import { ConsumoMasUsado } from "./pestana-consumo";
import { PestanaValor } from "./pestana-valor";
import { TarjetasPiezas, TarjetasResumen } from "./tarjetas-indicadores";
import "./tablero-admin.css";

type Pestana = "resumen" | "valor" | "piezas" | "consumo";
const CLAVE_GUARDADA = "tablero-pestana";

function leerGuardada(): string | null {
  try {
    return localStorage.getItem(CLAVE_GUARDADA);
  } catch {
    return null;
  }
}

function guardar(valor: string) {
  try {
    localStorage.setItem(CLAVE_GUARDADA, valor);
  } catch {
    // Sin almacenamiento: la pestaña simplemente no se recuerda.
  }
}

const sinEsperar = () => new Promise<never>(() => undefined);

/**
 * Tablero del Inicio (FEAT-008 4.2) en pestañas. Cada pestaña pide sus datos solo la primera vez que se abre;
 * lo que se ve lo decide el servidor. Quien no tiene `tablero.ver` no debe montarlo.
 */
export function Tablero() {
  const { puede } = useSesionActiva();
  const puedeElegir = puede("almacenes.todos");
  const conValor = puede("reportes.valor_inventario");
  const puedeVerSeguimiento = puede("reportes.existencias");
  const [almacen, setAlmacen] = useState("");
  const idBase = useId();

  const pestanas = useMemo(() => {
    const lista: { valor: Pestana; texto: string }[] = [{ valor: "resumen", texto: puedeElegir ? "Resumen" : "Mi almacén" }];
    if (puedeElegir) {
      if (conValor) lista.push({ valor: "valor", texto: "Valor" });
      lista.push({ valor: "piezas", texto: "Piezas" });
    }
    lista.push({ valor: "consumo", texto: "Consumo" });
    return lista;
  }, [puedeElegir, conValor]);

  const [activa, setActiva] = useState<Pestana>(() => {
    const g = leerGuardada();
    return (pestanas.find((p) => p.valor === g)?.valor ?? "resumen") as Pestana;
  });
  const [visitadas, setVisitadas] = useState<Set<Pestana>>(() => new Set([activa]));
  useEffect(() => {
    setVisitadas((v) => (v.has(activa) ? v : new Set(v).add(activa)));
  }, [activa]);

  const cambiar = (v: string) => {
    setActiva(v as Pestana);
    guardar(v);
  };

  const almacenes = useConsulta(
    (signal) => (puedeElegir ? apiGet<{ id: string; clave: string; nombre: string }[]>("/almacenes", undefined, signal) : Promise.resolve([])),
    `tablero-almacenes|${puedeElegir}`,
  );
  const opcionesAlmacen = useMemo<OpcionLista[]>(() => (almacenes.datos ?? []).map((a) => ({ valor: a.id, texto: a.nombre })), [almacenes.datos]);

  // Los datos de «Resumen» y «Piezas» salen de la misma petición; se pide al abrir la primera de las dos.
  const quiereResumen = visitadas.has("resumen") || visitadas.has("piezas");
  const resumen = useConsulta((signal) => (quiereResumen ? pedirResumenTablero(almacen, signal) : sinEsperar()), `resumen|${quiereResumen}|${almacen}`);
  // Quien no ve todos los almacenes tiene el valor dentro de «Mi almacén».
  const quiereValor = conValor && (visitadas.has("valor") || (!puedeElegir && visitadas.has("resumen")));
  const valor = useConsulta((signal) => (quiereValor ? pedirValorTablero(almacen, signal) : sinEsperar()), `valor|${quiereValor}|${almacen}`);

  const alcance = resumen.datos?.alcance ?? null;
  const sinAlmacen = alcance !== null && !alcance.es_todos && !alcance.almacen_id;

  const bloque = (c: typeof resumen, pintar: (d: NonNullable<typeof resumen.datos>) => ReactNode) =>
    c.error && !c.datos ? (
      <EstadoError error={c.error} alReintentar={c.recargar} />
    ) : !c.datos ? (
      <Esqueleto tipo="tarjeta" cantidad={4} />
    ) : (
      <div aria-busy={c.cargando} className={c.cargando ? "opacity-70 transition-opacity" : "transition-opacity"}>
        {pintar(c.datos)}
      </div>
    );

  let contenido: ReactNode;
  if ((activa === "resumen" || activa === "piezas") && sinAlmacen) {
    contenido = <EstadoVacio titulo="No tienes un almacén asignado" descripcion="Pídele a tu supervisor que te asigne uno para ver el tablero." />;
  } else if (activa === "resumen") {
    contenido = (
      <div className="flex flex-col gap-5">
        {bloque(resumen, (d) => <TarjetasResumen resumen={d} />)}
        {conValor && !puedeElegir ? (
          valor.error && !valor.datos ? (
            <EstadoError error={valor.error} alReintentar={valor.recargar} />
          ) : !valor.datos ? (
            <Esqueleto tipo="tarjeta" cantidad={4} />
          ) : (
            <PestanaValor valor={valor.datos} />
          )
        ) : null}
      </div>
    );
  } else if (activa === "piezas") {
    contenido = bloque(resumen, (d) => <TarjetasPiezas resumen={d} puedeVerSeguimiento={puedeVerSeguimiento} />);
  } else if (activa === "valor") {
    contenido =
      valor.error && !valor.datos ? (
        <EstadoError error={valor.error} alReintentar={valor.recargar} />
      ) : !valor.datos ? (
        <Esqueleto tipo="tarjeta" cantidad={4} />
      ) : (
        <div aria-busy={valor.cargando} className={valor.cargando ? "opacity-70 transition-opacity" : "transition-opacity"}>
          <PestanaValor valor={valor.datos} administrativo={puedeElegir} />
        </div>
      );
  } else {
    contenido = <ConsumoMasUsado puedeElegir={puedeElegir} almacen={almacen} />;
  }

  return (
    <MotionConfig reducedMotion="user">
      <section aria-labelledby="titulo-tablero" className={`flex flex-col gap-4 ${puedeElegir ? "tablero-admin" : ""}`}>
        <h2 id="titulo-tablero" className="text-xl font-semibold text-marino">
          Tablero
          {alcance ? <span className="ml-2 text-base font-normal text-muted-foreground">· {alcance.nombre}</span> : null}
        </h2>

        {puedeElegir && !almacenes.error ? (
          <div className="flex max-w-sm flex-col gap-1.5">
            <label htmlFor={`${idBase}-almacen`} className="text-sm font-medium">
              Almacén
            </label>
            <ListaDesplegable id={`${idBase}-almacen`} valor={almacen} alCambiar={setAlmacen} opciones={opcionesAlmacen} vacio="Todos los almacenes" />
          </div>
        ) : null}

        <Tabs value={activa} onValueChange={cambiar} className="w-full gap-4">
          <TabsList
            aria-label="Secciones del tablero"
            className="no-scrollbar h-auto! w-full gap-1 overflow-x-auto rounded-2xl border border-border bg-muted/40 p-1 sm:w-fit"
          >
            {pestanas.map((p) => {
              const esActiva = p.valor === activa;
              return (
                <TabsTrigger
                  key={p.valor}
                  value={p.valor}
                  id={`${idBase}-tab-${p.valor}`}
                  className="relative z-0 h-11 shrink-0 flex-1 cursor-pointer rounded-xl border-none bg-transparent px-4 text-sm font-medium shadow-none after:hidden data-active:bg-transparent data-active:shadow-none sm:flex-none"
                >
                  {esActiva ? (
                    <motion.span
                      layoutId={`${idBase}-indicador`}
                      className="absolute inset-0 -z-10 rounded-xl bg-background shadow-xs ring-1 ring-border"
                      transition={{ duration: 0.15, ease: "easeOut" }}
                    />
                  ) : null}
                  {p.texto}
                </TabsTrigger>
              );
            })}
          </TabsList>

          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={activa}
              role="tabpanel"
              aria-labelledby={`${idBase}-tab-${activa}`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.12 }}
            >
              {contenido}
            </motion.div>
          </AnimatePresence>
        </Tabs>
      </section>
    </MotionConfig>
  );
}
