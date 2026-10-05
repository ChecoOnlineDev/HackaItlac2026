import { InfoIcon } from "lucide-react";

import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { AccionPrincipal } from "~/componentes/pantalla";
import { Boton } from "~/componentes/ui/boton";
import { CampoSelect } from "./campo-select";
import { AYUDA_CAMPO, ETIQUETA_CAMPO, nombreDeColumna } from "./tabla";
import { CAMPOS, type CampoImportacion, type Columnas, type Tabla } from "./tipos";

interface PropiedadesPasoColumnas {
  tabla: Tabla;
  columnas: Columnas;
  alCambiar: (columnas: Columnas) => void;
  /** Solo con `catalogo.costos` se ofrece relacionar el costo. */
  puedeCostos: boolean;
  alContinuar: () => void;
}

/**
 * Paso 2: decir qué trae cada columna. Ya viene propuesto por los encabezados; se puede cambiar. Debajo, las
 * primeras filas para comprobar que cada columna es lo que se cree.
 */
export function PasoColumnas({ tabla, columnas, alCambiar, puedeCostos, alContinuar }: PropiedadesPasoColumnas) {
  const ancho = Math.max(tabla.encabezados?.length ?? 0, ...tabla.filas.map((f) => f.length));
  const opciones = Array.from({ length: ancho }, (_, i) => ({
    valor: String(i),
    texto: `${nombreDeColumna(tabla.encabezados, i)}${tabla.filas[0]?.[i] ? ` — ej.: ${tabla.filas[0][i].slice(0, 24)}` : ""}`,
  }));
  const campos = CAMPOS.filter((c) => c !== "costo" || puedeCostos);
  const fijar = (campo: CampoImportacion, valor: string) => {
    const indice = valor === "" ? null : Number(valor);
    const siguiente = { ...columnas, [campo]: indice };
    // Una columna es un solo dato: si ya era de otro, ese otro se queda sin columna.
    if (indice !== null) for (const otro of CAMPOS) if (otro !== campo && siguiente[otro] === indice) siguiente[otro] = null;
    alCambiar(siguiente);
  };
  const sinCodigo = columnas.codigo === null;
  const dueno = (indice: number) => CAMPOS.find((c) => columnas[c] === indice && (c !== "costo" || puedeCostos));
  const muestra = tabla.filas.slice(0, 5);

  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-3" aria-labelledby="columnas-titulo">
        <h2 id="columnas-titulo" className="text-lg font-semibold">
          ¿Qué trae cada columna?
        </h2>
        <p className="flex items-start gap-2 text-sm text-muted-foreground">
          <InfoIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-marino" />
          {tabla.encabezados
            ? "Propusimos las columnas según sus encabezados. Revísalas y corrige las que no sean."
            : "La tabla no trae encabezados: elige qué columna es cada dato."}
        </p>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-[repeat(2,minmax(0,1fr))]">
          {campos.map((campo) => (
            <CampoSelect
              key={campo}
              etiqueta={
                <>
                  {ETIQUETA_CAMPO[campo]}
                  {campo === "codigo" ? <span className="font-semibold text-destructive"> (obligatorio)</span> : null}
                </>
              }
              ayuda={AYUDA_CAMPO[campo]}
              valor={columnas[campo] === null ? "" : String(columnas[campo])}
              alCambiar={(v) => fijar(campo, v)}
              opciones={opciones}
              vacio={campo === "codigo" ? "Elige una columna" : "No viene en la tabla"}
            />
          ))}
        </div>
      </section>

      <section className="flex flex-col gap-2" aria-labelledby="muestra-titulo">
        <h2 id="muestra-titulo" className="text-lg font-semibold">
          Primeras filas
        </h2>
        <div className="overflow-x-auto [contain:inline-size] rounded-2xl border">
          <Table>
            <TableCaption className="sr-only">Primeras filas de la tabla, con el dato que trae cada columna</TableCaption>
            <TableHeader>
              <TableRow>
                <TableHead scope="col">
                  Fila
                </TableHead>
                {Array.from({ length: ancho }, (_, i) => {
                  const campo = dueno(i);
                  return (
                    <TableHead key={i} scope="col" className="align-top">
                      {nombreDeColumna(tabla.encabezados, i)}
                      <span className="block text-sm font-medium text-marino">{campo ? `→ ${ETIQUETA_CAMPO[campo]}` : "No se usa"}</span>
                    </TableHead>
                  );
                })}
              </TableRow>
            </TableHeader>
            <TableBody>
              {muestra.map((f, i) => (
                <TableRow key={i}>
                  <TableCell className="text-muted-foreground">{tabla.primeraFila + i}</TableCell>
                  {Array.from({ length: ancho }, (_, j) => (
                    <TableCell key={j} className="max-w-56 truncate">
                      {f[j] ?? ""}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <p className="text-sm text-muted-foreground">
          {tabla.filas.length.toLocaleString("es-MX")} {tabla.filas.length === 1 ? "fila de datos" : "filas de datos"}
          {tabla.archivo ? ` en ${tabla.archivo}` : ""}.
        </p>
      </section>

      <AccionPrincipal nota={sinCodigo ? "Elige qué columna trae el código del artículo." : null}>
        <Boton variante="principal" disabled={sinCodigo} onClick={alContinuar}>
          Revisar la importación
        </Boton>
      </AccionPrincipal>
    </div>
  );
}
