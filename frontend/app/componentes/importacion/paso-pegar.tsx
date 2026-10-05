import { CircleAlertIcon, UploadIcon } from "lucide-react";
import { useId, useMemo, useRef, useState } from "react";

import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { Checkbox } from "~/components/ui/checkbox";
import { Textarea } from "~/components/ui/textarea";
import { api } from "~/api/cliente";
import { mensajeDeError } from "~/api/errores";
import { AccionPrincipal } from "~/componentes/pantalla";
import { Boton } from "~/componentes/ui/boton";
import { MAX_BYTES_ARCHIVO, armarTabla, leerTextoPegado, nombreDeColumna, pareceEncabezado } from "./tabla";
import type { ArchivoApi, Columnas, Tabla } from "./tipos";

interface PropiedadesPasoPegar {
  /** Lo que ya se había pegado (al volver de un paso posterior). */
  textoInicial: string;
  alCambiarTexto: (texto: string) => void;
  /** Se lee una tabla pegada y se pasa al siguiente paso. */
  alContinuarConTexto: (tabla: Tabla) => void;
  /** Se subió un `.xlsx` y el servidor devolvió sus filas y la propuesta de columnas. */
  alSubirArchivo: (tabla: Tabla, columnas: Columnas) => void;
}

/**
 * Paso 1: pegar la tabla copiada de Excel (texto con tabuladores, que se lee aquí mismo) o subir un
 * `.xlsx` (que lee el servidor). Hasta confirmar no se guarda nada.
 */
export function PasoPegar({ textoInicial, alCambiarTexto, alContinuarConTexto, alSubirArchivo }: PropiedadesPasoPegar) {
  const idTexto = useId();
  const idArchivo = useId();
  const [texto, setTexto] = useState(textoInicial);
  const lectura = useMemo(() => (texto.trim() ? leerTextoPegado(texto) : null), [texto]);
  const [conEncabezadosElegido, setConEncabezadosElegido] = useState<boolean | null>(null);
  const [subiendo, setSubiendo] = useState(false);
  const [errorArchivo, setErrorArchivo] = useState<string | null>(null);
  const entradaArchivo = useRef<HTMLInputElement>(null);

  const sugerido = lectura?.ok ? pareceEncabezado(lectura.filas[0] ?? []) : false;
  const conEncabezados = conEncabezadosElegido ?? sugerido;

  const filas = lectura?.ok ? lectura.filas : [];
  const columnas = filas[0]?.length ?? 0;
  const datos = filas.length - (conEncabezados ? 1 : 0);
  const sinDatos = lectura?.ok === true && datos <= 0;

  const continuar = () => {
    if (!lectura?.ok || sinDatos) return;
    alContinuarConTexto(armarTabla(lectura.filas, conEncabezados));
  };

  const nota = !texto.trim()
    ? "Pega la tabla o sube un archivo de Excel para continuar."
    : lectura && !lectura.ok
      ? lectura.mensaje
      : sinDatos
        ? "La tabla solo trae los encabezados: no hay filas que importar."
        : null;

  const subir = async (archivo: File) => {
    setErrorArchivo(null);
    if (archivo.size > MAX_BYTES_ARCHIVO) {
      setErrorArchivo(`El archivo pesa más de ${MAX_BYTES_ARCHIVO / (1024 * 1024)} MB. Sube uno más pequeño.`);
      return;
    }
    setSubiendo(true);
    try {
      const cuerpo = new FormData();
      cuerpo.append("archivo", archivo);
      const r = await api<ArchivoApi>("/importacion/archivo", { metodo: "POST", cuerpo });
      alSubirArchivo(
        { origen: "archivo", archivo: archivo.name, encabezados: r.encabezados, filas: r.filas, primeraFila: r.primera_fila },
        r.columnas,
      );
    } catch (causa) {
      setErrorArchivo(mensajeDeError(causa));
    } finally {
      setSubiendo(false);
      if (entradaArchivo.current) entradaArchivo.current.value = "";
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-3" aria-labelledby={`${idTexto}-t`}>
        <h2 id={`${idTexto}-t`} className="text-lg font-semibold">
          Pega la tabla copiada de Excel
        </h2>
        <p className="text-base text-muted-foreground">
          En Excel selecciona las celdas (con los encabezados, si los tiene), cópialas y pégalas aquí. Todavía no se guarda nada.
        </p>
        <label htmlFor={idTexto} className="sr-only">
          Tabla copiada de Excel
        </label>
        <Textarea
          id={idTexto}
          value={texto}
          rows={8}
          spellCheck={false}
          placeholder={"Código\tNombre\tMarca\tCategoría\tCantidad\tAlmacén"}
          aria-invalid={lectura && !lectura.ok ? true : undefined}
          aria-describedby={`${idTexto}-estado`}
          onChange={(e) => {
            setTexto(e.target.value);
            alCambiarTexto(e.target.value);
            setConEncabezadosElegido(null);
          }}
          className="min-h-48 w-full rounded-lg border border-input bg-background p-3 font-mono text-base leading-snug"
        />
        <div id={`${idTexto}-estado`} aria-live="polite" className="flex flex-col gap-3">
          {lectura && !lectura.ok ? (
            <p role="alert" className="flex items-start gap-2 text-base font-semibold text-destructive">
              <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
              {lectura.mensaje}
            </p>
          ) : null}
          {lectura?.ok ? (
            <>
              <p className="text-base font-medium">
                Se leyeron {filas.length.toLocaleString("es-MX")} {filas.length === 1 ? "fila" : "filas"} y {columnas} {columnas === 1 ? "columna" : "columnas"}.
              </p>
              <label className="flex min-h-12 cursor-pointer items-center gap-3 text-base font-medium">
                <Checkbox
                  checked={conEncabezados}
                  onCheckedChange={(marcado) => setConEncabezadosElegido(marcado)}
                  className="size-6 rounded-md [&_svg]:size-4"
                />
                La primera fila trae los encabezados
              </label>
              <div className="overflow-x-auto [contain:inline-size] rounded-xl border">
                <Table>
                  <TableCaption className="sr-only">Primeras filas de lo pegado</TableCaption>
                  <TableHeader>
                    <TableRow>
                      {Array.from({ length: columnas }, (_, i) => (
                        <TableHead key={i} scope="col">
                          {nombreDeColumna(conEncabezados ? filas[0] : null, i)}
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filas.slice(conEncabezados ? 1 : 0, (conEncabezados ? 1 : 0) + 3).map((f, i) => (
                      <TableRow key={i}>
                        {f.map((c, j) => (
                          <TableCell key={j} className="max-w-56 truncate">
                            {c}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </>
          ) : null}
        </div>
      </section>

      <div className="flex items-center gap-3 text-base text-muted-foreground" aria-hidden="true">
        <span className="h-px flex-1 bg-border" />
        o
        <span className="h-px flex-1 bg-border" />
      </div>

      <section className="flex flex-col gap-3" aria-labelledby={`${idArchivo}-t`}>
        <h2 id={`${idArchivo}-t`} className="text-lg font-semibold">
          Sube un archivo de Excel
        </h2>
        <p className="text-base text-muted-foreground">Un archivo .xlsx de hasta 5 MB. Se lee la primera hoja; la primera fila con datos son los encabezados.</p>
        <input
          ref={entradaArchivo}
          id={idArchivo}
          type="file"
          accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          className="sr-only"
          disabled={subiendo}
          onChange={(e) => {
            const archivo = e.target.files?.[0];
            if (archivo) void subir(archivo);
          }}
        />
        <Boton variante="secundario" className="self-start" cargando={subiendo} onClick={() => entradaArchivo.current?.click()}>
          <UploadIcon aria-hidden="true" className={subiendo ? "hidden" : undefined} />
          {subiendo ? "Leyendo el archivo…" : "Elegir archivo de Excel"}
        </Boton>
        {errorArchivo ? (
          <p role="alert" className="flex items-start gap-2 text-base font-semibold text-destructive">
            <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
            {errorArchivo}
          </p>
        ) : null}
      </section>

      <AccionPrincipal nota={nota}>
        <Boton variante="principal" disabled={nota !== null} onClick={continuar}>
          Continuar
        </Boton>
      </AccionPrincipal>
    </div>
  );
}
