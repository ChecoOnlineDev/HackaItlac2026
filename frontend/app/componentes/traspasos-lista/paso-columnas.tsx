import { InfoIcon } from "lucide-react";

import type { ColumnasTraspaso } from "~/api/traspasos-lista";
import { CampoSelect } from "~/componentes/importacion/campo-select";
import { nombreDeColumna } from "~/componentes/importacion/tabla";
import type { Tabla } from "~/componentes/importacion/tipos";
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { AccionPrincipal } from "~/componentes/pantalla";
import { Boton } from "~/componentes/ui/boton";
import { AYUDA_TRASPASO, CAMPOS_TRASPASO, ETIQUETA_TRASPASO, type CampoTraspaso } from "./lectura";

interface PropiedadesPasoColumnas {
  tabla: Tabla;
  columnas: ColumnasTraspaso;
  alCambiar: (columnas: ColumnasTraspaso) => void;
  alContinuar: () => void;
}

/** Paso 3: decir qué trae cada columna. Ya viene propuesto por los encabezados; se puede cambiar. */
export function PasoColumnasTraspaso({ tabla, columnas, alCambiar, alContinuar }: PropiedadesPasoColumnas) {
  const ancho = Math.max(tabla.encabezados?.length ?? 0, ...tabla.filas.map((f) => f.length));
  const opciones = Array.from({ length: ancho }, (_, i) => ({
    valor: String(i),
    texto: `${nombreDeColumna(tabla.encabezados, i)}${tabla.filas[0]?.[i] ? ` — ej.: ${tabla.filas[0][i].slice(0, 24)}` : ""}`,
  }));
  const fijar = (campo: CampoTraspaso, valor: string) => {
    const indice = valor === "" ? null : Number(valor);
    const siguiente = { ...columnas, [campo]: indice };
    // Una columna es un solo dato: si ya era de otro, ese otro se queda sin columna.
    if (indice !== null) for (const otro of CAMPOS_TRASPASO) if (otro !== campo && siguiente[otro] === indice) siguiente[otro] = null;
    alCambiar(siguiente);
  };
  const dueno = (indice: number) => CAMPOS_TRASPASO.find((c) => columnas[c] === indice);
  const muestra = tabla.filas.slice(0, 5);
  // Solo se pide lo mínimo para poder revisar; si falta algo más, el servidor lo dice fila por fila.
  const sinIdentificar = columnas.codigo === null && columnas.codigo_pieza === null;
  const nota = sinIdentificar ? "Elige la columna del código del artículo o la del código de la pieza." : null;

  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-3" aria-labelledby="columnas-traspaso-titulo">
        <h2 id="columnas-traspaso-titulo" className="text-lg font-semibold">
          ¿Qué trae cada columna?
        </h2>
        <p className="flex items-start gap-2 text-sm text-muted-foreground">
          <InfoIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-marino" />
          {tabla.encabezados
            ? "Propusimos las columnas según sus encabezados. Revísalas y corrige las que no sean. Lo demás que traiga el archivo se ignora."
            : "La tabla no trae encabezados: elige qué columna es cada dato."}
        </p>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-[repeat(2,minmax(0,1fr))]">
          {CAMPOS_TRASPASO.map((campo) => (
            <CampoSelect
              key={campo}
              etiqueta={ETIQUETA_TRASPASO[campo]}
              ayuda={AYUDA_TRASPASO[campo]}
              valor={columnas[campo] === null ? "" : String(columnas[campo])}
              alCambiar={(v) => fijar(campo, v)}
              opciones={opciones}
              vacio="No viene en la tabla"
            />
          ))}
        </div>
      </section>

      <section className="flex flex-col gap-2" aria-labelledby="muestra-traspaso-titulo">
        <h2 id="muestra-traspaso-titulo" className="text-lg font-semibold">
          Primeras filas
        </h2>
        <div className="[contain:inline-size]">
          <Table>
            <TableCaption className="sr-only">Primeras filas de la tabla, con el dato que trae cada columna</TableCaption>
            <TableHeader>
              <TableRow>
                <TableHead scope="col">Fila</TableHead>
                {Array.from({ length: ancho }, (_, i) => {
                  const campo = dueno(i);
                  return (
                    <TableHead key={i} scope="col" className="align-top">
                      {nombreDeColumna(tabla.encabezados, i)}
                      <span className="block text-sm font-medium text-marino">{campo ? `→ ${ETIQUETA_TRASPASO[campo]}` : "No se usa"}</span>
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

      <AccionPrincipal nota={nota}>
        <Boton variante="principal" disabled={sinIdentificar} onClick={alContinuar}>
          Revisar la lista
        </Boton>
      </AccionPrincipal>
    </div>
  );
}
