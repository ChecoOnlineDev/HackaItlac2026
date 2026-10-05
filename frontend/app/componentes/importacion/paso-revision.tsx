import { cn } from "cn";
import { CircleAlertIcon, DownloadIcon, TriangleAlertIcon, WifiOffIcon, XIcon } from "lucide-react";
import { useState } from "react";

import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
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
import { ETIQUETA_CAMPO } from "./tabla";
import type { CampoImportacion, CategoriaDesconocida, FilaError, OpcionesImportacion, VistaPreviaApi } from "./tipos";

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
  alConfirmar: () => void;
  alDescargarErrores: (filas: FilaError[]) => void;
}

const LIMITE_INICIAL = 50;

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

/** Resume una fila con error para reconocerla: lo que traía en código, nombre y cantidad. */
function resumenDeDatos(datos: Record<string, string>): string {
  return (["codigo", "nombre", "cantidad", "almacen", "categoria"] as CampoImportacion[])
    .filter((c) => datos[c])
    .map((c) => `${ETIQUETA_CAMPO[c]}: ${datos[c]}`)
    .join(" · ");
}

/**
 * Paso 3: la vista previa que calcula el servidor, sin guardar nada. Resumen, avisos, categorías que no
 * existen, almacén para las filas que no lo traen, filas con error en rojo con su motivo y número de fila,
 * artículos nuevos y filas válidas. "Confirmar importación" es la acción principal.
 */
export function PasoRevision({
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
  alConfirmar,
  alDescargarErrores,
}: PropiedadesPasoRevision) {
  const [verTodasErrores, setVerTodasErrores] = useState(false);
  const [verTodasValidas, setVerTodasValidas] = useState(false);
  const categorias = useConsulta((signal) => apiGet<Pagina<Categoria>>("/categorias", { tamano: 200 }, signal), "importar-categorias");
  const almacenes = useConsulta((signal) => apiGet<AlmacenLista[]>("/almacenes", undefined, signal), "importar-almacenes");

  const hayDesconocidas = desconocidas.length > 0;
  const opcionesCategoria = (categorias.datos?.elementos ?? []).map((c) => ({ valor: c.id, texto: c.nombre }));
  const opcionesAlmacen = (almacenes.datos ?? []).filter((a) => a.estado === "ACTIVO").map((a) => ({ valor: a.clave, texto: `${a.nombre} (${a.clave})` }));

  const resumen = vista?.resumen;
  const reintento = errorConfirmacion?.tipo === "conexion";
  const razon = !vista
    ? error
      ? "No pudimos revisar la tabla."
      : "Revisando la tabla…"
    : cargando
      ? "Revisando la tabla…"
      : resumen && resumen.validas === 0
        ? "No hay filas válidas para importar. Corrige los errores o cambia las columnas."
        : null;
  const nota =
    razon ??
    (resumen && resumen.con_error > 0
      ? `${resumen.con_error} ${resumen.con_error === 1 ? "fila con error no se importará" : "filas con error no se importarán"}.`
      : null);

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
              <Dato etiqueta="Listas para importar" valor={vista.resumen.validas} />
              <Dato etiqueta="Con error" valor={vista.resumen.con_error} tono="error" />
              <Dato etiqueta="Artículos nuevos" valor={vista.resumen.articulos_nuevos} />
              <Dato etiqueta="Piezas" valor={vista.resumen.piezas} />
              <Dato etiqueta="Unidades" valor={vista.resumen.unidades} />
              <Dato etiqueta="Almacenes" valor={vista.resumen.almacenes} />
              <Dato etiqueta="Filas vacías (se ignoran)" valor={vista.resumen.vacias} />
            </dl>
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

          {vista.filas_error.length > 0 ? (
            <section aria-labelledby="err-titulo" className="flex flex-col gap-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 id="err-titulo" className="flex items-center gap-2 text-lg font-semibold">
                  <XIcon aria-hidden="true" strokeWidth={3} className="size-5 text-semaforo-rojo" />
                  Filas con error ({vista.filas_error.length})
                </h2>
                <Boton variante="contorno" onClick={() => alDescargarErrores(vista.filas_error)}>
                  <DownloadIcon aria-hidden="true" />
                  Descargar filas con error
                </Boton>
              </div>
              <p className="text-sm text-muted-foreground">Estas filas no se importarán. Corrígelas en Excel y vuelve a importarlas después.</p>
              <ul className="flex flex-col gap-3">
                {(verTodasErrores ? vista.filas_error : vista.filas_error.slice(0, LIMITE_INICIAL)).map((f) => (
                  <li key={f.fila} className="flex flex-col gap-1.5 rounded-2xl border border-semaforo-rojo bg-semaforo-rojo/5 p-3">
                    <p className="text-base font-semibold">Fila {f.fila}</p>
                    <p className="text-sm text-muted-foreground">{resumenDeDatos(f.datos) || "Fila sin datos reconocibles"}</p>
                    <ul className="flex flex-col gap-1">
                      {f.motivos.map((m, i) => (
                        <li key={i} className="flex items-start gap-2 text-base">
                          <XIcon aria-hidden="true" strokeWidth={3} className="mt-1 size-4 shrink-0 text-semaforo-rojo" />
                          <span>
                            <span className="sr-only">Error: </span>
                            {m.mensaje} <span className="text-xs font-medium whitespace-nowrap text-muted-foreground">({m.regla})</span>
                          </span>
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ul>
              {!verTodasErrores && vista.filas_error.length > LIMITE_INICIAL ? (
                <Boton variante="contorno" className="self-start" onClick={() => setVerTodasErrores(true)}>
                  Ver las {vista.filas_error.length} filas con error
                </Boton>
              ) : null}
            </section>
          ) : null}

          {vista.articulos_nuevos.length > 0 ? (
            <details className="rounded-2xl border p-3">
              <summary className="flex min-h-12 cursor-pointer items-center text-base font-semibold">Artículos nuevos que se crearán ({vista.articulos_nuevos.length})</summary>
              <ul className="mt-2 flex flex-col divide-y">
                {vista.articulos_nuevos.map((a) => (
                  <li key={a.codigo} className="flex flex-col py-2 text-base">
                    <span className="font-semibold">
                      {a.nombre} <span className="font-normal text-muted-foreground">· {a.codigo}</span>
                    </span>
                    <span className="text-muted-foreground">
                      {[a.marca, a.categoria.nombre, a.control === "PIEZA" ? "Por pieza" : "Por cantidad", `${a.filas} ${a.filas === 1 ? "fila" : "filas"}`, a.costo ? `Costo ${a.costo}` : null]
                        .filter(Boolean)
                        .join(" · ")}
                    </span>
                  </li>
                ))}
              </ul>
            </details>
          ) : null}

          {vista.filas_validas.length > 0 ? (
            <details className="rounded-2xl border p-3">
              <summary className="flex min-h-12 cursor-pointer items-center text-base font-semibold">Filas listas para importar ({vista.filas_validas.length})</summary>
              <div className="mt-2 overflow-x-auto [contain:inline-size]">
                <Table>
                  <TableCaption className="sr-only">Filas que se importarán</TableCaption>
                  <TableHeader>
                    <TableRow>
                      {["Fila", "Código", "Nombre", "Cantidad", "Almacén", "Pieza / serie"].map((t) => (
                        <TableHead key={t} scope="col">
                          {t}
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(verTodasValidas ? vista.filas_validas : vista.filas_validas.slice(0, LIMITE_INICIAL)).map((f) => (
                      <TableRow key={f.fila}>
                        <TableCell className="text-muted-foreground">{f.fila}</TableCell>
                        <TableCell className="px-3 py-2 whitespace-nowrap">{f.codigo}</TableCell>
                        <TableCell className="px-3 py-2">
                          {f.nombre}
                          {f.articulo_nuevo ? <span className="ml-2 text-sm font-semibold text-marino">(nuevo)</span> : null}
                          {f.avisos.map((a, i) => (
                            <span key={i} className="block text-sm text-muted-foreground">
                              Aviso: {a}
                            </span>
                          ))}
                        </TableCell>
                        <TableCell className="px-3 py-2 tabular-nums">{f.cantidad}</TableCell>
                        <TableCell className="px-3 py-2 whitespace-nowrap">{f.almacen.nombre}</TableCell>
                        <TableCell className="px-3 py-2 whitespace-nowrap">{[f.codigo_pieza, f.numero_serie].filter(Boolean).join(" · ") || "—"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              {!verTodasValidas && vista.filas_validas.length > LIMITE_INICIAL ? (
                <Boton variante="contorno" className="mt-3" onClick={() => setVerTodasValidas(true)}>
                  Ver las {vista.filas_validas.length} filas
                </Boton>
              ) : null}
            </details>
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
