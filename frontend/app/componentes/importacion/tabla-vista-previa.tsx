import { cn } from "cn";
import { ArrowRightIcon, LinkIcon, PlusIcon, SigmaIcon, TriangleAlertIcon, XIcon } from "lucide-react";
import { useState, type ReactNode } from "react";

import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
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
  cantidad: string;
  almacen: string;
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
    cantidad: String(f.cantidad),
    almacen: f.almacen.nombre,
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
    cantidad: f.datos.cantidad ?? "",
    almacen: f.datos.almacen ?? "",
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

const POR_PAGINA = 50;

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
  const [visibles, setVisibles] = useState(POR_PAGINA);
  const todas = filasDeVista(vista, modo, categoriaPorFila);
  const cuenta = (e: EstadoFila) => todas.filter((f) => f.estado === e).length;
  const filas = filtro === "TODAS" ? todas : todas.filter((f) => f.estado === filtro);
  const porVer = filas.slice(0, visibles);
  const sugeridasSinAceptar = todas.filter((f) => f.sugerida && !categoriaPorFila[String(f.fila)]);

  const filtrar = (f: FiltroFilas) => {
    setVisibles(POR_PAGINA);
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
          {/* Computadora y tableta: tabla. */}
          <div className="hidden [contain:inline-size] md:block">
            <Table>
              <TableCaption className="sr-only">Cada fila del archivo con su estado, cantidad y saldo antes y después</TableCaption>
              <TableHeader>
                <TableRow>
                  {["Fila", "Estado", "Artículo", "Cantidad", "Saldo (antes → después)", ...(modo === "ALTA" ? ["Categoría"] : [])].map((t) => (
                    <TableHead key={t} scope="col">
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
                    <TableCell className="min-w-56 px-3 py-2 align-top">
                      <DatosArticulo f={f} />
                    </TableCell>
                    <TableCell className="px-3 py-2 align-top tabular-nums">
                      {f.cantidad}
                      {f.almacen ? <span className="block text-sm text-muted-foreground">{f.almacen}</span> : null}
                    </TableCell>
                    <TableCell className="px-3 py-2 align-top tabular-nums whitespace-nowrap">
                      <Saldo f={f} />
                    </TableCell>
                    {modo === "ALTA" ? (
                      <TableCell className="min-w-64 px-3 py-2 align-top">
                        <CategoriaFila f={f} elegida={categoriaPorFila[String(f.fila)] ?? ""} opciones={opcionesCategoria} listas={categoriasListas} alElegir={alElegirCategoria} />
                      </TableCell>
                    ) : null}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Celular: la misma lista como tarjetas. */}
          <ul className="flex flex-col gap-3 md:hidden">
            {porVer.map((f) => (
              <li key={f.fila} className={cn("flex flex-col gap-2 rounded-2xl border p-3", f.estado === "ERROR" && "border-destructive bg-destructive/5")}>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold text-muted-foreground">Fila {f.fila}</span>
                  <InsigniaEstado estado={f.estado} />
                </div>
                <DatosArticulo f={f} />
                <p className="text-base tabular-nums">
                  <span className="text-sm text-muted-foreground">Cantidad: </span>
                  {f.cantidad}
                  {f.almacen ? <span className="text-sm text-muted-foreground"> · {f.almacen}</span> : null}
                </p>
                {f.saldoAntes !== null ? (
                  <p className="text-base tabular-nums">
                    <span className="text-sm text-muted-foreground">Saldo: </span>
                    <Saldo f={f} />
                  </p>
                ) : null}
                {modo === "ALTA" ? <CategoriaFila f={f} elegida={categoriaPorFila[String(f.fila)] ?? ""} opciones={opcionesCategoria} listas={categoriasListas} alElegir={alElegirCategoria} /> : null}
              </li>
            ))}
          </ul>

          {filas.length > visibles ? (
            <Boton variante="contorno" className="self-start" onClick={() => setVisibles((n) => n + POR_PAGINA)}>
              Ver más filas ({Math.min(POR_PAGINA, filas.length - visibles)} de {filas.length - visibles} que faltan)
            </Boton>
          ) : null}
        </>
      ) : null}
    </section>
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
      {f.codigo ? (
        <span className="text-sm text-muted-foreground">
          {f.codigo}
          {f.codigoGenerado ? " (código provisional: se asigna al confirmar)" : ""}
        </span>
      ) : null}
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
