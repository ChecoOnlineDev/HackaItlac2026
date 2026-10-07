import { cn } from "cn";
import { TriangleAlertIcon, XIcon } from "lucide-react";
import { useState, type ReactNode } from "react";

import type { FilaTraspasoApi, NivelFilaTraspaso, VistaPreviaTraspasoApi } from "~/api/traspasos-lista";
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { Paginador } from "~/componentes/catalogo/campos";
import { POR_PAGINA } from "~/componentes/importacion/tabla-vista-previa";
import { Insignia } from "~/componentes/ui/insignia";

export type FiltroTraspaso = "TODAS" | NivelFilaTraspaso;

const TEXTO_ESTADO: Record<NivelFilaTraspaso, string> = { VERDE: "Correcto", AMARILLO: "Aviso", ROJO: "Error" };
const ESTADO_INSIGNIA = { VERDE: "verde", AMARILLO: "amarillo", ROJO: "rojo" } as const;

function InsigniaFila({ nivel }: { nivel: NivelFilaTraspaso }) {
  return <Insignia estado={ESTADO_INSIGNIA[nivel]}>{TEXTO_ESTADO[nivel]}</Insignia>;
}

function Contador({ etiqueta, valor, activo, alTocar, error }: { etiqueta: string; valor: number; activo: boolean; alTocar: () => void; error?: boolean }) {
  return (
    <button
      type="button"
      aria-pressed={activo}
      onClick={alTocar}
      className={cn(
        "flex min-h-14 flex-col items-start rounded-2xl border p-3 text-left outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50",
        activo && "border-primary bg-accent",
        error && valor > 0 && "border-destructive bg-destructive/5",
      )}
    >
      <span className="text-2xl leading-none font-semibold tabular-nums">{valor}</span>
      <span className="text-sm">{etiqueta}</span>
    </button>
  );
}

function Motivos({ f }: { f: FilaTraspasoApi }) {
  if (f.motivos.length === 0 && !(f.unida_de && f.unida_de.length > 0)) return null;
  const esError = f.nivel === "ROJO";
  return (
    <>
      {f.unida_de && f.unida_de.length > 0 ? <span className="text-sm font-medium">Unido: filas {[f.fila, ...f.unida_de].join(", ")}</span> : null}
      {f.motivos.map((m, i) =>
        esError ? (
          <span key={i} className="flex items-start gap-1.5 text-sm text-destructive">
            <XIcon aria-hidden="true" strokeWidth={3} className="mt-0.5 size-4 shrink-0" />
            <span>
              <span className="sr-only">Error: </span>
              {m.mensaje}
            </span>
          </span>
        ) : (
          <span key={i} className="flex items-start gap-1.5 rounded-lg border border-semaforo-amarillo bg-semaforo-amarillo/10 px-2 py-1 text-sm">
            <TriangleAlertIcon aria-hidden="true" strokeWidth={3} className="mt-0.5 size-4 shrink-0 text-semaforo-amarillo" />
            <span>
              <span className="sr-only">Aviso: </span>
              {m.mensaje}
            </span>
          </span>
        ),
      )}
    </>
  );
}

function Articulo({ f }: { f: FilaTraspasoApi }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-base font-semibold break-words">{f.articulo ?? <span className="text-muted-foreground">No se reconoce</span>}</span>
      <Motivos f={f} />
    </div>
  );
}

const Vacio = () => <span className="text-muted-foreground">—</span>;

function Dato({ etiqueta, children }: { etiqueta: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-muted-foreground">{etiqueta}</dt>
      <dd className="break-words">{children}</dd>
    </div>
  );
}

interface PropiedadesTablaVista {
  vista: VistaPreviaTraspasoApi;
  /** Las filas con error ya se decidió dejarlas fuera: no se muestran. */
  dejarFuera: boolean;
}

/**
 * Vista previa de un traspaso por lista: una fila por renglón del archivo, con su estado. Solo muestra lo que
 * evalúa el servidor. Se pagina de 12 en 12; en celular se presenta como tarjetas.
 */
export function TablaVistaTraspaso({ vista, dejarFuera }: PropiedadesTablaVista) {
  const [pagina, setPagina] = useState(1);
  const [filtro, setFiltro] = useState<FiltroTraspaso>("TODAS");
  const visibles = dejarFuera ? vista.filas.filter((f) => f.nivel !== "ROJO") : vista.filas;
  const filas = filtro === "TODAS" ? visibles : visibles.filter((f) => f.nivel === filtro);
  const ultima = Math.max(1, Math.ceil(filas.length / POR_PAGINA));
  const actual = Math.min(pagina, ultima);
  const porVer = filas.slice((actual - 1) * POR_PAGINA, actual * POR_PAGINA);
  const hayPieza = visibles.some((f) => f.pieza !== null);
  const { resumen } = vista;

  const filtrar = (f: NivelFilaTraspaso) => {
    setPagina(1);
    setFiltro(filtro === f ? "TODAS" : f);
  };

  return (
    <section aria-labelledby="tabla-traspaso-titulo" className="flex flex-col gap-3">
      <h2 id="tabla-traspaso-titulo" className="text-lg font-semibold">
        Fila por fila
      </h2>
      <div className="grid grid-cols-3 gap-3">
        <Contador etiqueta="Correctas" valor={resumen.ok} activo={filtro === "VERDE"} alTocar={() => filtrar("VERDE")} />
        <Contador etiqueta="Con aviso" valor={resumen.avisos} activo={filtro === "AMARILLO"} alTocar={() => filtrar("AMARILLO")} />
        <Contador etiqueta="Con error" valor={resumen.errores} activo={filtro === "ROJO"} alTocar={() => filtrar("ROJO")} error />
      </div>
      <p className="text-sm text-muted-foreground">Toca un número para ver solo esas filas; tócalo otra vez para ver todas.</p>

      {filas.length === 0 ? <p className="rounded-2xl border p-4 text-base text-muted-foreground">No hay filas con ese estado.</p> : null}

      {filas.length > 0 ? (
        <>
          <div className="hidden [contain:inline-size] md:block">
            <div className="overflow-x-auto rounded-2xl border">
              <Table>
                <TableCaption className="sr-only">Cada fila del archivo con su estado, su cantidad y lo que hay disponible en el origen</TableCaption>
                <TableHeader>
                  <TableRow>
                    <TableHead scope="col">Fila</TableHead>
                    <TableHead scope="col">Estado</TableHead>
                    <TableHead scope="col">Código</TableHead>
                    <TableHead scope="col">Artículo</TableHead>
                    {hayPieza ? <TableHead scope="col">Pieza / serie</TableHead> : null}
                    <TableHead scope="col" className="text-right">
                      Cantidad
                    </TableHead>
                    <TableHead scope="col" className="text-right">
                      Disponible en el origen
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {porVer.map((f) => (
                    <TableRow key={f.fila} className={cn(f.nivel === "ROJO" && "bg-destructive/5")}>
                      <TableCell className="align-top text-muted-foreground tabular-nums">{f.fila}</TableCell>
                      <TableCell className="align-top">
                        <InsigniaFila nivel={f.nivel} />
                      </TableCell>
                      <TableCell className="px-3 py-2 align-top text-sm whitespace-nowrap">{f.codigo || <Vacio />}</TableCell>
                      <TableCell className="min-w-56 px-3 py-2 align-top">
                        <Articulo f={f} />
                      </TableCell>
                      {hayPieza ? (
                        <TableCell className="px-3 py-2 align-top text-sm whitespace-nowrap">
                          {f.pieza ? (
                            <>
                              {f.pieza.codigo}
                              {f.pieza.numero_serie ? <span className="block text-muted-foreground">Serie {f.pieza.numero_serie}</span> : null}
                            </>
                          ) : (
                            <Vacio />
                          )}
                        </TableCell>
                      ) : null}
                      <TableCell className="px-3 py-2 text-right align-top tabular-nums">{f.cantidad}</TableCell>
                      <TableCell className="px-3 py-2 text-right align-top tabular-nums">{f.disponible_en_origen}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>

          <ul className="flex flex-col gap-3 md:hidden">
            {porVer.map((f) => (
              <li key={f.fila} className={cn("flex flex-col gap-2 rounded-2xl border p-3", f.nivel === "ROJO" && "border-destructive bg-destructive/5")}>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold text-muted-foreground">Fila {f.fila}</span>
                  <InsigniaFila nivel={f.nivel} />
                </div>
                <Articulo f={f} />
                <dl className="grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
                  <Dato etiqueta="Código">{f.codigo || <Vacio />}</Dato>
                  <Dato etiqueta="Cantidad">
                    <span className="tabular-nums">{f.cantidad}</span>
                  </Dato>
                  {f.pieza ? (
                    <Dato etiqueta="Pieza / serie">
                      {f.pieza.codigo}
                      {f.pieza.numero_serie ? ` · ${f.pieza.numero_serie}` : ""}
                    </Dato>
                  ) : null}
                  <Dato etiqueta="Disponible en el origen">
                    <span className="tabular-nums">{f.disponible_en_origen}</span>
                  </Dato>
                </dl>
              </li>
            ))}
          </ul>

          <Paginador pagina={actual} tamano={POR_PAGINA} total={filas.length} alCambiar={setPagina} />
        </>
      ) : null}
    </section>
  );
}
