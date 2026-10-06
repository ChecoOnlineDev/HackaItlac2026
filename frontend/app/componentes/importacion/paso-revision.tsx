import { cn } from "cn";
import { CircleAlertIcon, DownloadIcon, InfoIcon, TriangleAlertIcon, WifiOffIcon, XIcon } from "lucide-react";
import { useState } from "react";

import { Checkbox } from "~/components/ui/checkbox";
import { apiGet } from "~/api/cliente";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import type { Categoria } from "~/componentes/catalogo/tipos";
import { AccionPrincipal } from "~/componentes/pantalla";
import { Boton } from "~/componentes/ui/boton";
import { Cargando } from "~/componentes/ui/cargando";
import { EstadoError } from "~/componentes/ui/estado-error";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import type { Pagina } from "~/api/tipos";
import { CampoSelect } from "./campo-select";
import { filasDeVista, TablaVistaPrevia, type FiltroFilas } from "./tabla-vista-previa";
import type { CategoriaDesconocida, FilaError, ModoImportacion, OpcionesImportacion, VistaPreviaApi } from "./tipos";

interface AlmacenLista {
  id: string;
  clave: string;
  nombre: string;
  estado: string;
}

export interface ErrorConfirmacion {
  tipo: "conexion" | "otro";
  mensaje: string;
}

interface PropiedadesPasoRevision {
  modo: ModoImportacion;
  vista: VistaPreviaApi | null;
  /**
   * Las categorías que no existían en el archivo. Una vez que se elige una, el servidor ya no las lista como
   * desconocidas; la pantalla las recuerda para que la elección siga a la vista y se pueda cambiar.
   */
  desconocidas: CategoriaDesconocida[];
  /** Se está esperando una vista previa nueva. */
  cargando: boolean;
  error: unknown;
  alReintentar: () => void;
  opciones: OpcionesImportacion;
  alCambiarOpciones: (opciones: OpcionesImportacion) => void;
  confirmando: boolean;
  errorConfirmacion: ErrorConfirmacion | null;
  /** El servidor avisó que los datos cambiaron: se vuelve a revisar. */
  avisoCambio: string | null;
  /** Fecha (UTC) de la importación anterior con este mismo archivo, si el servidor la avisó al confirmar (I-12). */
  fechaRepetido: string | null;
  repetidoAceptado: boolean;
  alAceptarRepetido: (aceptado: boolean) => void;
  alConfirmar: () => void;
  alDescargarErrores: (filas: FilaError[]) => void;
}

function fechaLegible(utc: string): string {
  const d = new Date(utc);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString("es-MX", { timeZone: "America/Mexico_City", dateStyle: "long", timeStyle: "short" });
}

function Dato({ etiqueta, valor, tono }: { etiqueta: string; valor: number; tono?: "error" }) {
  return (
    <div className={cn("flex flex-col gap-0.5 rounded-2xl border p-3", tono === "error" && valor > 0 && "border-2 border-semaforo-rojo bg-semaforo-rojo/5")}>
      <dt className="flex items-center gap-1.5 text-sm text-muted-foreground">
        {tono === "error" && valor > 0 ? <XIcon aria-hidden="true" strokeWidth={3} className="size-4 text-semaforo-rojo" /> : null}
        {etiqueta}
      </dt>
      <dd className="text-xl font-semibold tabular-nums">{valor.toLocaleString("es-MX")}</dd>
    </div>
  );
}

/**
 * Paso 3: la vista previa que calcula el servidor, sin guardar nada. Resumen, avisos, categorías que no
 * existen, almacén para las filas que no lo traen, filas con error en rojo con su motivo y número de fila,
 * artículos nuevos y filas válidas. "Confirmar importación" es la acción principal.
 */
export function PasoRevision({
  modo,
  vista,
  desconocidas,
  cargando,
  error,
  alReintentar,
  opciones,
  alCambiarOpciones,
  confirmando,
  errorConfirmacion,
  avisoCambio,
  fechaRepetido,
  repetidoAceptado,
  alAceptarRepetido,
  alConfirmar,
  alDescargarErrores,
}: PropiedadesPasoRevision) {
  const [filtro, setFiltro] = useState<FiltroFilas>("TODAS");
  const categorias = useConsulta((signal) => apiGet<Pagina<Categoria>>("/categorias", { tamano: 200 }, signal), "importar-categorias");
  const almacenes = useConsulta((signal) => apiGet<AlmacenLista[]>("/almacenes", undefined, signal), "importar-almacenes");

  const hayDesconocidas = modo === "ALTA" && desconocidas.length > 0;
  const opcionesCategoria = (categorias.datos?.elementos ?? []).map((c) => ({ valor: c.id, texto: c.nombre }));
  const opcionesAlmacen = (almacenes.datos ?? []).filter((a) => a.estado === "ACTIVO").map((a) => ({ valor: a.clave, texto: `${a.nombre} (${a.clave})` }));

  const resumen = vista?.resumen;
  const reintento = errorConfirmacion?.tipo === "conexion";
  // Filas de artículo nuevo que siguen sin categoría: no entran hasta elegir una (I-14).
  const sinCategoria = vista
    ? filasDeVista(vista, modo, opciones.categoriaPorFila).filter((f) => f.estado !== "ERROR" && f.pideCategoria && f.categoria === null && !opciones.categoriaPorFila[String(f.fila)]).length
    : 0;
  const entran = resumen ? Math.max(0, resumen.validas - sinCategoria) : 0;
  const afuera = resumen ? resumen.con_error + sinCategoria : 0;
  const hayRepetido = Boolean(vista?.archivo_repetido?.fecha) || fechaRepetido !== null;
  const fechaAnterior = fechaLegible(vista?.archivo_repetido?.fecha ?? fechaRepetido ?? "");
  const razon = !vista
    ? error
      ? "No pudimos revisar la tabla."
      : "Revisando la tabla…"
    : cargando
      ? "Revisando la tabla…"
      : entran === 0
        ? "No hay filas que puedan entrar. Corrige los errores, elige las categorías o cambia las columnas."
        : hayRepetido && !repetidoAceptado
          ? "Este archivo ya se importó. Marca la casilla si quieres importarlo de nuevo."
          : null;
  const nota =
    razon ?? (afuera > 0 ? `Entran ${entran}; ${afuera} ${afuera === 1 ? "fila se queda fuera" : "filas se quedan fuera"}.` : `Entran ${entran} ${entran === 1 ? "fila" : "filas"}.`);

  return (
    <div className="flex flex-col gap-6">
      {avisoCambio ? (
        <p role="alert" className="flex items-start gap-2 rounded-2xl border border-semaforo-rojo bg-semaforo-rojo/10 p-3 text-sm font-semibold">
          <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-semaforo-rojo" />
          {avisoCambio}
        </p>
      ) : null}

      {error && !vista ? <EstadoError error={error} alReintentar={alReintentar} /> : null}
      {!vista && !error ? <Esqueleto tipo="tarjeta" cantidad={2} /> : null}

      {error && vista ? (
        <section role="alert" className="flex flex-col gap-2 rounded-2xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-4">
          <p className="flex items-start gap-2 text-base font-semibold">
            <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
            No pudimos actualizar la revisión. Lo que ves puede no estar al día.
          </p>
          <Boton variante="secundario" className="self-start" onClick={alReintentar}>
            Reintentar
          </Boton>
        </section>
      ) : null}

      {vista ? (
        <div className={cn("flex flex-col gap-6", cargando && "opacity-70")} aria-busy={cargando}>
          <section aria-labelledby="resumen-titulo" className="flex flex-col gap-3">
            <h2 id="resumen-titulo" className="flex items-center gap-3 text-lg font-semibold">
              Resumen
              {cargando ? <Cargando variante="en-linea" texto="Actualizando…" className="p-0" /> : null}
            </h2>
            <dl className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <Dato etiqueta="Filas leídas" valor={vista.resumen.total} />
              {modo === "ALTA" ? <Dato etiqueta="Artículos nuevos" valor={vista.resumen.articulos_nuevos} /> : null}
              <Dato etiqueta="Existentes (suman)" valor={vista.resumen.existentes ?? 0} />
              <Dato etiqueta="Unidos" valor={vista.resumen.unidos ?? 0} />
              <Dato etiqueta="Con error" valor={vista.resumen.con_error} tono="error" />
              <Dato etiqueta="Excluidas" valor={vista.resumen.excluidas ?? vista.filas_excluidas?.length ?? 0} />
              <Dato etiqueta="Piezas" valor={vista.resumen.piezas} />
              <Dato etiqueta="Unidades" valor={vista.resumen.unidades} />
            </dl>
            <p className="text-sm text-muted-foreground">
              {vista.resumen.vacias > 0 ? `${vista.resumen.vacias} ${vista.resumen.vacias === 1 ? "fila vacía se ignora" : "filas vacías se ignoran"}. ` : ""}
              Los vales de entrada serán {vista.resumen.almacenes}: uno por almacén.
            </p>
          </section>

          {vista.avisos.length > 0 ? (
            <ul aria-label="Avisos" className="flex flex-col gap-2">
              {vista.avisos.map((a, i) => (
                <li key={i} className="flex items-start gap-2 rounded-2xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-3 text-sm">
                  <TriangleAlertIcon aria-hidden="true" strokeWidth={3} className="mt-1 size-4 shrink-0 text-semaforo-amarillo" />
                  <span>
                    <span className="sr-only">Aviso: </span>
                    {a}
                  </span>
                </li>
              ))}
            </ul>
          ) : null}

          {hayRepetido ? (
            <section aria-labelledby="repetido-titulo" className="flex flex-col gap-3 rounded-2xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-4">
              <h2 id="repetido-titulo" className="flex items-center gap-2 text-lg font-semibold">
                <TriangleAlertIcon aria-hidden="true" strokeWidth={3} className="size-5 text-semaforo-amarillo" />
                Este archivo ya se importó
              </h2>
              <p className="text-base">
                {fechaAnterior ? `Ya se importó el ${fechaAnterior}. ` : ""}Si lo importas otra vez, las cantidades se sumarán de nuevo y el inventario quedará con el doble.
              </p>
              <label className="flex min-h-12 cursor-pointer items-center gap-3 text-base font-medium">
                <Checkbox checked={repetidoAceptado} onCheckedChange={(marcado) => alAceptarRepetido(marcado)} className="size-6 rounded-md [&_svg]:size-4" />
                Entiendo, importar de nuevo
              </label>
            </section>
          ) : null}

          {hayDesconocidas ? (
            <section aria-labelledby="cat-titulo" className="flex flex-col gap-3 rounded-2xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-4">
              <h2 id="cat-titulo" className="flex items-center gap-2 text-lg font-semibold">
                <TriangleAlertIcon aria-hidden="true" strokeWidth={3} className="size-5 text-semaforo-amarillo" />
                Categorías que no existen
              </h2>
              <p className="text-base">
                Estos artículos son nuevos y su categoría no existe en el catálogo o no viene en la tabla. Elige una para todos, o relaciona cada nombre con una categoría existente.
              </p>
              {categorias.error ? (
                <EstadoError error={categorias.error} alReintentar={categorias.recargar} />
              ) : (
                <>
                  <CampoSelect
                    etiqueta="Categoría para todos los que no existan"
                    valor={opciones.categoriaPorDefectoId ?? ""}
                    alCambiar={(v) => alCambiarOpciones({ ...opciones, categoriaPorDefectoId: v || null })}
                    opciones={opcionesCategoria}
                    vacio="Ninguna: dejar esas filas con error"
                    deshabilitado={!categorias.datos}
                  />
                  <ul className="flex flex-col gap-3">
                    {desconocidas.map((c) => (
                      <li key={c.nombre}>
                        <CampoSelect
                          etiqueta={
                            <>
                              “{c.nombre}” <span className="font-normal text-muted-foreground">(fila{c.filas.length === 1 ? "" : "s"} {c.filas.join(", ")})</span>
                            </>
                          }
                          valor={opciones.mapaCategorias[c.nombre] ?? ""}
                          alCambiar={(v) => {
                            const mapa = { ...opciones.mapaCategorias };
                            if (v) mapa[c.nombre] = v;
                            else delete mapa[c.nombre];
                            alCambiarOpciones({ ...opciones, mapaCategorias: mapa });
                          }}
                          opciones={opcionesCategoria}
                          vacio="Usar la de todos"
                          deshabilitado={!categorias.datos}
                        />
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </section>
          ) : null}

          <section aria-labelledby="alm-titulo" className="flex flex-col gap-3">
            <h2 id="alm-titulo" className="text-lg font-semibold">
              Almacén
            </h2>
            {almacenes.error ? (
              <EstadoError error={almacenes.error} alReintentar={almacenes.recargar} />
            ) : (
              <CampoSelect
                etiqueta="Almacén para las filas que no traen almacén"
                ayuda="Si no eliges uno, esas filas quedan con error."
                valor={opciones.almacenPorDefecto ?? ""}
                alCambiar={(v) => alCambiarOpciones({ ...opciones, almacenPorDefecto: v || null })}
                opciones={opcionesAlmacen}
                vacio="Ninguno"
                deshabilitado={!almacenes.datos}
                className="max-w-md"
              />
            )}
          </section>

          {(vista.filas_excluidas ?? []).length > 0 ? (
            <details className="rounded-2xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-3">
              <summary className="flex min-h-12 cursor-pointer items-center gap-2 text-base font-semibold">
                <InfoIcon aria-hidden="true" className="size-5 shrink-0" />
                {vista.filas_excluidas.length} {vista.filas_excluidas.length === 1 ? "fila excluida" : "filas excluidas"} (no son artículos)
              </summary>
              <ul className="mt-2 flex flex-col divide-y">
                {vista.filas_excluidas.map((f) => (
                  <li key={f.fila} className="py-2 text-base">
                    <span className="font-semibold">Fila {f.fila}:</span> {f.nombre}
                    <span className="block text-sm text-muted-foreground">{f.motivo} No se importa y no cuenta como error.</span>
                  </li>
                ))}
              </ul>
            </details>
          ) : null}

          <TablaVistaPrevia
            vista={vista}
            modo={modo}
            filtro={filtro}
            alFiltrar={setFiltro}
            categoriaPorFila={opciones.categoriaPorFila}
            opcionesCategoria={opcionesCategoria}
            alElegirCategoria={(fila, id) => {
              const mapa = { ...opciones.categoriaPorFila };
              if (id) mapa[String(fila)] = id;
              else delete mapa[String(fila)];
              alCambiarOpciones({ ...opciones, categoriaPorFila: mapa });
            }}
            alAceptarSugeridas={(sugeridas) => alCambiarOpciones({ ...opciones, categoriaPorFila: { ...opciones.categoriaPorFila, ...sugeridas } })}
            categoriasListas={Boolean(categorias.datos)}
          />

          {vista.filas_error.length > 0 ? (
            <section aria-labelledby="err-titulo" className="flex flex-col gap-2 rounded-2xl border border-destructive bg-destructive/5 p-4">
              <h2 id="err-titulo" className="flex items-center gap-2 text-lg font-semibold">
                <XIcon aria-hidden="true" strokeWidth={3} className="size-5 text-destructive" />
                {vista.filas_error.length} {vista.filas_error.length === 1 ? "fila con error" : "filas con error"}
              </h2>
              <p className="text-base">Estas filas no se importarán. Descárgalas, corrígelas en Excel y vuelve a importarlas después.</p>
              <Boton variante="contorno" className="self-start" onClick={() => alDescargarErrores(vista.filas_error)}>
                <DownloadIcon aria-hidden="true" />
                Descargar filas con error
              </Boton>
            </section>
          ) : null}
        </div>
      ) : null}

      {errorConfirmacion ? (
        <section role="alert" className="flex flex-col gap-1 rounded-2xl border border-semaforo-rojo bg-semaforo-rojo/10 p-4">
          <p className="flex items-start gap-2 text-base font-semibold">
            {errorConfirmacion.tipo === "conexion" ? <WifiOffIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" /> : <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />}
            {errorConfirmacion.mensaje}
          </p>
          {errorConfirmacion.tipo === "conexion" ? <p className="text-base">Toca “Reintentar” cuando vuelva la conexión: se comprueba y no se importará dos veces.</p> : null}
        </section>
      ) : null}

      <AccionPrincipal nota={nota}>
        <Boton variante="principal" cargando={confirmando} disabled={razon !== null && !reintento} onClick={alConfirmar}>
          {reintento ? "Reintentar" : "Confirmar importación"}
        </Boton>
      </AccionPrincipal>
    </div>
  );
}
