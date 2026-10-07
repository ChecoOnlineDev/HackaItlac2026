import { cn } from "cn";
import { ArrowRightIcon, LinkIcon, PlusIcon, SigmaIcon, TriangleAlertIcon, XIcon } from "lucide-react";
import { useState, type ReactNode } from "react";

import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { Skeleton } from "~/components/ui/skeleton";
import { Paginador } from "~/componentes/catalogo/campos";
import { Boton } from "~/componentes/ui/boton";
import { ListaDesplegable, type OpcionLista } from "~/componentes/ui/lista-desplegable";
import type { CategoriaRef, EstadoFila, Motivo, ModoImportacion, VistaPreviaApi } from "./tipos";

/** Una fila de la vista previa, sea buena o con error, lista para mostrarse. */
export interface FilaVista {
  fila: number;
  estado: EstadoFila;
  codigo: string;
  codigoGenerado: boolean;
  nombre: string;
  marca: string;
  cantidad: string;
  almacen: string;
  costo: string;
  codigoPieza: string;
  serie: string;
  saldoAntes: number | null;
  saldoDespues: number | null;
  unidaDe: number[];
  /** Avisos que no bloquean (nombre distinto, pieza sin inspección…). */
  avisos: string[];
  categoria: CategoriaRef | null;
  sugerida: CategoriaRef | null;
  motivoSugerencia: string | null;
  motivos: Motivo[];
  /** Es un artículo nuevo al que hay que elegirle categoría (la que viene del archivo no se edita). */
  pideCategoria: boolean;
}

export type FiltroFilas = "TODAS" | "NUEVO" | "EXISTENTE" | "UNIDO" | "ERROR";

/** Junta las filas buenas y las que tienen error en una sola lista, en el orden del archivo. */
export function filasDeVista(vista: VistaPreviaApi, modo: ModoImportacion, elegidas: Record<string, string> = {}): FilaVista[] {
  const buenas: FilaVista[] = vista.filas_validas.map((f) => ({
    fila: f.fila,
    estado: f.estado ?? (f.articulo_nuevo ? "NUEVO" : "EXISTENTE"),
    codigo: f.codigo,
    codigoGenerado: f.codigo_generado === true,
    nombre: f.nombre,
    marca: f.marca ?? "",
    cantidad: String(f.cantidad),
    almacen: f.almacen.nombre,
    costo: f.costo ?? "",
    codigoPieza: f.codigo_pieza ?? "",
    serie: f.numero_serie ?? "",
    saldoAntes: f.saldo_antes ?? null,
    saldoDespues: f.saldo_despues ?? null,
    unidaDe: f.unida_de ?? [],
    avisos: f.avisos.filter((a) => !a.startsWith("Unido")),
    categoria: f.categoria,
    sugerida: f.categoria_sugerida ?? null,
    motivoSugerencia: f.motivo_sugerencia ?? null,
    motivos: [],
    pideCategoria: modo === "ALTA" && f.articulo_nuevo && (f.categoria === null || f.categoria_sugerida != null || String(f.fila) in elegidas),
  }));
  const malas: FilaVista[] = vista.filas_error.map((f) => ({
    fila: f.fila,
    estado: "ERROR",
    codigo: f.datos.codigo ?? "",
    codigoGenerado: false,
    nombre: f.datos.nombre || f.datos.codigo || "Sin nombre",
    marca: f.datos.marca ?? "",
    cantidad: f.datos.cantidad ?? "",
    almacen: f.datos.almacen ?? "",
    costo: f.datos.costo ?? "",
    codigoPieza: f.datos.codigo_pieza ?? "",
    serie: f.datos.serie ?? "",
    saldoAntes: null,
    saldoDespues: null,
    unidaDe: [],
    avisos: [],
    categoria: null,
    sugerida: null,
    motivoSugerencia: null,
    motivos: f.motivos,
    pideCategoria: modo === "ALTA" && f.motivos.some((m) => m.codigo === "CATEGORIA_DESCONOCIDA"),
  }));
  return [...buenas, ...malas].sort((a, b) => a.fila - b.fila);
}

const ESTADOS: Record<EstadoFila, { texto: string; icono: typeof PlusIcon; clases: string }> = {
  NUEVO: { texto: "Nuevo", icono: PlusIcon, clases: "border-primary/40 bg-accent text-marino" },
  EXISTENTE: { texto: "Existente (suma)", icono: SigmaIcon, clases: "border-border bg-muted" },
  UNIDO: { texto: "Unido", icono: LinkIcon, clases: "border-border bg-muted" },
  ERROR: { texto: "Error", icono: XIcon, clases: "border-destructive bg-destructive/10 text-destructive" },
};

/** El estado de la fila: icono y texto, nunca solo color. */
function InsigniaEstado({ estado }: { estado: EstadoFila }) {
  const e = ESTADOS[estado];
  const Icono = e.icono;
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap", e.clases)}>
      <Icono aria-hidden="true" className="size-3.5 shrink-0" strokeWidth={3} />
      {e.texto}
    </span>
  );
}

interface PropiedadesTabla {
  vista: VistaPreviaApi;
  modo: ModoImportacion;
  filtro: FiltroFilas;
  alFiltrar: (filtro: FiltroFilas) => void;
  /** Lo que la persona eligió o aceptó: `{número de fila: categoria_id}`. */
  categoriaPorFila: Record<string, string>;
  opcionesCategoria: OpcionLista[];
  alElegirCategoria: (fila: number, categoriaId: string) => void;
  /** Acepta todas las sugerencias a la vez (la persona las está viendo en la tabla). */
  alAceptarSugeridas: (sugeridas: Record<string, string>) => void;
  categoriasListas: boolean;
}

/** Filas por página de la vista previa. */
export const POR_PAGINA = 12;

function Contador({ etiqueta, valor, activo, alTocar, error }: { etiqueta: string; valor: number; activo: boolean; alTocar: () => void; error?: boolean }) {
  return (
    <button
      type="button"
      aria-pressed={activo}
      onClick={alTocar}
      className={cn(
        "flex min-h-14 flex-col items-start gap-0.5 rounded-2xl border p-3 text-left transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
        activo ? "border-2 border-primary bg-accent" : "hover:bg-accent/50",
        error && valor > 0 && !activo && "border-2 border-destructive bg-destructive/5",
      )}
    >
      <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
        {error && valor > 0 ? <XIcon aria-hidden="true" strokeWidth={3} className="size-4 text-destructive" /> : null}
        {etiqueta}
      </span>
      <span className="text-xl font-semibold tabular-nums">{valor.toLocaleString("es-MX")}</span>
    </button>
  );
}

/**
 * La vista previa de la importación como tabla: una fila por renglón del archivo con su estado, la cantidad,
 * el saldo antes y después en ese almacén y, en el alta, la categoría sugerida editable. Todo lo calcula el
 * servidor; aquí solo se muestra y se recogen las categorías que la persona elige.
 */
export function TablaVistaPrevia({ vista, modo, filtro, alFiltrar, categoriaPorFila, opcionesCategoria, alElegirCategoria, alAceptarSugeridas, categoriasListas }: PropiedadesTabla) {
  const [pagina, setPagina] = useState(1);
  const todas = filasDeVista(vista, modo, categoriaPorFila);
  const cuenta = (e: EstadoFila) => todas.filter((f) => f.estado === e).length;
  const filas = filtro === "TODAS" ? todas : todas.filter((f) => f.estado === filtro);
  const ultima = Math.max(1, Math.ceil(filas.length / POR_PAGINA));
  const actual = Math.min(pagina, ultima);
  const porVer = filas.slice((actual - 1) * POR_PAGINA, actual * POR_PAGINA);
  const sugeridasSinAceptar = todas.filter((f) => f.sugerida && !categoriaPorFila[String(f.fila)]);
  // Las columnas opcionales solo salen si alguna fila trae ese dato (el costo, por ejemplo, depende del permiso).
  const hay = {
    marca: todas.some((f) => f.marca !== ""),
    costo: todas.some((f) => f.costo !== ""),
    pieza: todas.some((f) => f.codigoPieza !== "" || f.serie !== ""),
    saldo: todas.some((f) => f.saldoAntes !== null),
  };
  const encabezados = [
    "Fila",
    "Estado",
    "Código",
    "Artículo",
    ...(hay.marca ? ["Marca"] : []),
    ...(modo === "ALTA" ? ["Categoría"] : []),
    "Cantidad",
    "Almacén",
    ...(hay.costo ? ["Costo"] : []),
    ...(hay.pieza ? ["Código de pieza", "Serie"] : []),
    ...(hay.saldo ? ["Saldo (antes → después)"] : []),
  ];

  const filtrar = (f: FiltroFilas) => {
    setPagina(1);
    alFiltrar(filtro === f ? "TODAS" : f);
  };

  return (
    <section aria-labelledby="tabla-titulo" className="flex flex-col gap-3">
      <h2 id="tabla-titulo" className="text-lg font-semibold">
        Fila por fila
      </h2>
      <div className={cn("grid gap-3", modo === "ALTA" ? "grid-cols-2 md:grid-cols-4" : "grid-cols-3")}>
        {modo === "ALTA" ? <Contador etiqueta="Nuevos" valor={cuenta("NUEVO")} activo={filtro === "NUEVO"} alTocar={() => filtrar("NUEVO")} /> : null}
        <Contador etiqueta="Existentes (suman)" valor={cuenta("EXISTENTE")} activo={filtro === "EXISTENTE"} alTocar={() => filtrar("EXISTENTE")} />
        <Contador etiqueta="Unidos" valor={cuenta("UNIDO")} activo={filtro === "UNIDO"} alTocar={() => filtrar("UNIDO")} />
        <Contador etiqueta="Con error" valor={cuenta("ERROR")} activo={filtro === "ERROR"} alTocar={() => filtrar("ERROR")} error />
      </div>
      <p className="text-sm text-muted-foreground">Toca un número para ver solo esas filas; tócalo otra vez para ver todas.</p>

      {sugeridasSinAceptar.length > 0 ? (
        <div className="flex flex-col gap-2 rounded-2xl border border-semaforo-amarillo bg-semaforo-amarillo/10 p-3">
          <p className="flex items-start gap-2 text-base">
            <TriangleAlertIcon aria-hidden="true" strokeWidth={3} className="mt-1 size-4 shrink-0 text-semaforo-amarillo" />
            <span>
              Sugerimos una categoría para {sugeridasSinAceptar.length} {sugeridasSinAceptar.length === 1 ? "artículo nuevo" : "artículos nuevos"}, según lo que dice su descripción. Es solo una
              sugerencia: no se usa hasta que la aceptes o elijas otra en cada fila.
            </span>
          </p>
          <Boton
            variante="secundario"
            className="self-start"
            onClick={() => alAceptarSugeridas(Object.fromEntries(sugeridasSinAceptar.map((f) => [String(f.fila), f.sugerida!.id])))}
          >
            Aceptar todas las sugeridas ({sugeridasSinAceptar.length})
          </Boton>
        </div>
      ) : null}

      {filas.length === 0 ? <p className="rounded-2xl border p-4 text-base text-muted-foreground">No hay filas con ese estado.</p> : null}

      {filas.length > 0 ? (
        <>
          {/* Computadora y tableta: tabla con todos los campos; si no caben, se desliza hacia los lados. */}
          <div className="hidden [contain:inline-size] md:block">
            <div className="overflow-x-auto rounded-2xl border">
              <Table>
                <TableCaption className="sr-only">Cada fila del archivo con todos sus datos, su estado y el saldo antes y después</TableCaption>
                <TableHeader>
                  <TableRow>
                    {encabezados.map((t) => (
                      <TableHead key={t} scope="col" className="whitespace-nowrap">
                        {t}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {porVer.map((f) => (
                    <TableRow key={f.fila} className={cn(f.estado === "ERROR" && "bg-destructive/5")}>
                      <TableCell className="align-top text-muted-foreground tabular-nums">{f.fila}</TableCell>
                      <TableCell className="align-top">
                        <InsigniaEstado estado={f.estado} />
                      </TableCell>
                      <TableCell className="px-3 py-2 align-top text-sm whitespace-nowrap">
                        {f.codigo ? (
                          <>
                            {f.codigo}
                            {f.codigoGenerado ? <span className="block text-xs text-muted-foreground">Provisional: se asigna al confirmar</span> : null}
                          </>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell className="min-w-56 px-3 py-2 align-top">
                        <DatosArticulo f={f} />
                      </TableCell>
                      {hay.marca ? <TableCell className="px-3 py-2 align-top">{f.marca || <span className="text-muted-foreground">—</span>}</TableCell> : null}
                      {modo === "ALTA" ? (
                        <TableCell className="min-w-64 px-3 py-2 align-top">
                          <CategoriaFila f={f} elegida={categoriaPorFila[String(f.fila)] ?? ""} opciones={opcionesCategoria} listas={categoriasListas} alElegir={alElegirCategoria} />
                        </TableCell>
                      ) : null}
                      <TableCell className="px-3 py-2 align-top tabular-nums">{f.cantidad || <span className="text-muted-foreground">—</span>}</TableCell>
                      <TableCell className="px-3 py-2 align-top whitespace-nowrap">{f.almacen || <span className="text-muted-foreground">—</span>}</TableCell>
                      {hay.costo ? <TableCell className="px-3 py-2 align-top tabular-nums">{f.costo ? `$${f.costo}` : <span className="text-muted-foreground">—</span>}</TableCell> : null}
                      {hay.pieza ? (
                        <>
                          <TableCell className="px-3 py-2 align-top text-sm whitespace-nowrap">{f.codigoPieza || <span className="text-muted-foreground">—</span>}</TableCell>
                          <TableCell className="px-3 py-2 align-top text-sm whitespace-nowrap">{f.serie || <span className="text-muted-foreground">—</span>}</TableCell>
                        </>
                      ) : null}
                      {hay.saldo ? (
                        <TableCell className="px-3 py-2 align-top tabular-nums whitespace-nowrap">
                          <Saldo f={f} />
                        </TableCell>
                      ) : null}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>

          {/* Celular: la misma lista como tarjetas, con todos los datos. */}
          <ul className="flex flex-col gap-3 md:hidden">
            {porVer.map((f) => (
              <li key={f.fila} className={cn("flex flex-col gap-2 rounded-2xl border p-3", f.estado === "ERROR" && "border-destructive bg-destructive/5")}>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold text-muted-foreground">Fila {f.fila}</span>
                  <InsigniaEstado estado={f.estado} />
                </div>
                <DatosArticulo f={f} />
                <dl className="grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
                  <Campo etiqueta="Código" valor={f.codigo} nota={f.codigoGenerado ? "Provisional" : undefined} />
                  {hay.marca ? <Campo etiqueta="Marca" valor={f.marca} /> : null}
                  <Campo etiqueta="Cantidad" valor={f.cantidad} />
                  <Campo etiqueta="Almacén" valor={f.almacen} />
                  {hay.costo ? <Campo etiqueta="Costo" valor={f.costo ? `$${f.costo}` : ""} /> : null}
                  {hay.pieza ? <Campo etiqueta="Código de pieza" valor={f.codigoPieza} /> : null}
                  {hay.pieza ? <Campo etiqueta="Serie" valor={f.serie} /> : null}
                  {f.saldoAntes !== null ? (
                    <div>
                      <dt className="text-muted-foreground">Saldo</dt>
                      <dd className="tabular-nums">
                        <Saldo f={f} />
                      </dd>
                    </div>
                  ) : null}
                </dl>
                {modo === "ALTA" ? <CategoriaFila f={f} elegida={categoriaPorFila[String(f.fila)] ?? ""} opciones={opcionesCategoria} listas={categoriasListas} alElegir={alElegirCategoria} /> : null}
              </li>
            ))}
          </ul>

          <Paginador pagina={actual} tamano={POR_PAGINA} total={filas.length} alCambiar={setPagina} />
        </>
      ) : null}
    </section>
  );
}

function Campo({ etiqueta, valor, nota }: { etiqueta: string; valor: string; nota?: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-muted-foreground">{etiqueta}</dt>
      <dd className="break-words">
        {valor || <span className="text-muted-foreground">—</span>}
        {nota ? <span className="block text-xs text-muted-foreground">{nota}</span> : null}
      </dd>
    </div>
  );
}

/** Marcador de lugar de la tabla mientras se revisa el archivo: la misma forma que tendrá, con 12 filas. */
export function EsqueletoTablaVista({ columnas = 8 }: { columnas?: number }) {
  return (
    <div role="status" aria-label="Revisando la tabla" aria-busy="true" className="flex flex-col gap-3">
      <span className="sr-only">Revisando la tabla</span>
      <div className="hidden overflow-hidden rounded-2xl border bg-card md:block">
        <div className="flex gap-4 border-b bg-muted/60 p-3">
          {Array.from({ length: columnas }, (_, i) => (
            <Skeleton key={i} className="h-4 flex-1" />
          ))}
        </div>
        {Array.from({ length: POR_PAGINA }, (_, i) => (
          <div key={i} className="flex gap-4 border-b p-3 last:border-b-0">
            {Array.from({ length: columnas }, (_, c) => (
              <Skeleton key={c} className={cn("h-5 flex-1", c === 3 && "h-9 flex-[2]")} />
            ))}
          </div>
        ))}
      </div>
      <div className="flex flex-col gap-3 md:hidden">
        {Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="space-y-3 rounded-2xl border bg-card p-4">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-5 w-4/5" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3" />
          </div>
        ))}
      </div>
    </div>
  );
}

function Saldo({ f }: { f: FilaVista }): ReactNode {
  if (f.saldoAntes === null || f.saldoDespues === null) return <span className="text-muted-foreground">—</span>;
  return (
    <span className="inline-flex items-center gap-1.5">
      <span>
        <span className="sr-only">Antes: </span>
        {f.saldoAntes.toLocaleString("es-MX")}
      </span>
      <ArrowRightIcon aria-hidden="true" className="size-4 text-muted-foreground" />
      <span className="font-semibold">
        <span className="sr-only">Después: </span>
        {f.saldoDespues.toLocaleString("es-MX")}
      </span>
    </span>
  );
}

function DatosArticulo({ f }: { f: FilaVista }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-base font-semibold break-words">{f.nombre}</span>
      {f.unidaDe.length > 0 ? <span className="text-sm font-medium">Unido: filas {[f.fila, ...f.unidaDe].join(", ")}</span> : null}
      {f.avisos.map((a, i) => (
        <span key={i} className="flex items-start gap-1.5 rounded-lg border border-semaforo-amarillo bg-semaforo-amarillo/10 px-2 py-1 text-sm">
          <TriangleAlertIcon aria-hidden="true" strokeWidth={3} className="mt-0.5 size-4 shrink-0 text-semaforo-amarillo" />
          <span>
            <span className="sr-only">Aviso: </span>
            {a}
          </span>
        </span>
      ))}
      {f.motivos.map((m, i) => (
        <span key={i} className="flex items-start gap-1.5 text-sm text-destructive">
          <XIcon aria-hidden="true" strokeWidth={3} className="mt-0.5 size-4 shrink-0" />
          <span>
            <span className="sr-only">Error: </span>
            {m.mensaje}
          </span>
        </span>
      ))}
    </div>
  );
}

function CategoriaFila({
  f,
  elegida,
  opciones,
  listas,
  alElegir,
}: {
  f: FilaVista;
  elegida: string;
  opciones: OpcionLista[];
  listas: boolean;
  alElegir: (fila: number, categoriaId: string) => void;
}) {
  // La categoría que viene del archivo no se edita; solo se muestra.
  if (!f.pideCategoria) return f.categoria ? <span className="text-base">{f.categoria.nombre}</span> : <span className="text-muted-foreground">—</span>;
  const porRevisar = elegida === "" && f.sugerida === null;
  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      <ListaDesplegable
        valor={elegida}
        alCambiar={(v) => alElegir(f.fila, v)}
        opciones={opciones}
        vacio={porRevisar ? "Por revisar: elige una categoría" : "Elegir categoría"}
        deshabilitado={!listas}
        descritoPor={undefined}
      />
      {elegida === "" && f.sugerida ? (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span>
            Sugerida: <span className="font-semibold">{f.sugerida.nombre}</span>
            {f.motivoSugerencia ? <span className="block text-muted-foreground">{f.motivoSugerencia}</span> : null}
          </span>
          <Boton variante="secundario" onClick={() => alElegir(f.fila, f.sugerida!.id)} aria-label={`Usar la sugerida ${f.sugerida.nombre} en la fila ${f.fila}`}>
            Usar
          </Boton>
        </div>
      ) : null}
      {elegida === "" ? (
        <span className="text-sm font-medium">{f.estado === "ERROR" || f.sugerida === null ? "Elige una categoría: sin ella esta fila no entra." : "Sin categoría esta fila no entra."}</span>
      ) : f.sugerida && elegida !== f.sugerida.id ? (
        <span className="text-sm text-muted-foreground">Cambiaste la sugerida ({f.sugerida.nombre}).</span>
      ) : null}
    </div>
  );
}
