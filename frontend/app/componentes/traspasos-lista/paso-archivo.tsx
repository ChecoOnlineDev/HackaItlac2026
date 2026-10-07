import { CircleAlertIcon, DownloadIcon, UploadIcon } from "lucide-react";
import { useId, useMemo, useRef, useState } from "react";

import { Checkbox } from "~/components/ui/checkbox";
import { Textarea } from "~/components/ui/textarea";
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { descargarPlantillaTraspaso, leerArchivoTraspaso, mensajeTraspasoLista, type ColumnasTraspaso } from "~/api/traspasos-lista";
import { armarTabla, leerTextoPegado, nombreDeColumna, pareceEncabezado } from "~/componentes/importacion/tabla";
import type { Tabla } from "~/componentes/importacion/tipos";
import { AccionPrincipal } from "~/componentes/pantalla";
import { Boton } from "~/componentes/ui/boton";
import { columnasDelServidor, MAX_BYTES_ARCHIVO, motivoDeTopeTabla, proponerColumnasTraspaso } from "./lectura";

interface PropiedadesPasoArchivo {
  destinoId: string;
  almacenId: string | null;
  textoInicial: string;
  alCambiarTexto: (texto: string) => void;
  alTener: (tabla: Tabla, columnas: ColumnasTraspaso) => void;
}

/**
 * Paso 2: bajar la plantilla, subir un `.xlsx` (lo lee el servidor) o pegar la tabla copiada de Excel (se lee
 * aquí). Hasta confirmar no se guarda nada.
 */
export function PasoArchivo({ destinoId, almacenId, textoInicial, alCambiarTexto, alTener }: PropiedadesPasoArchivo) {
  const idTexto = useId();
  const idArchivo = useId();
  const [texto, setTexto] = useState(textoInicial);
  const lectura = useMemo(() => (texto.trim() ? leerTextoPegado(texto) : null), [texto]);
  const [conEncabezadosElegido, setConEncabezadosElegido] = useState<boolean | null>(null);
  const [subiendo, setSubiendo] = useState(false);
  const [bajando, setBajando] = useState(false);
  const [errorArchivo, setErrorArchivo] = useState<string | null>(null);
  const entradaArchivo = useRef<HTMLInputElement>(null);

  const sugerido = lectura?.ok ? pareceEncabezado(lectura.filas[0] ?? []) : false;
  const conEncabezados = conEncabezadosElegido ?? sugerido;
  const filas = lectura?.ok ? lectura.filas : [];
  const columnas = filas[0]?.length ?? 0;
  const datos = filas.length - (conEncabezados ? 1 : 0);
  const sinDatos = lectura?.ok === true && datos <= 0;
  const tablaPegada = lectura?.ok && !sinDatos ? armarTabla(lectura.filas, conEncabezados) : null;
  const motivoTope = tablaPegada ? motivoDeTopeTabla(tablaPegada) : null;

  const nota = !texto.trim()
    ? "Pega la tabla o sube un archivo de Excel para continuar."
    : lectura && !lectura.ok
      ? lectura.mensaje
      : sinDatos
        ? "La tabla solo trae los encabezados: no hay filas que enviar."
        : motivoTope;

  const continuar = () => {
    if (!tablaPegada || motivoTope) return;
    alTener(tablaPegada, tablaPegada.encabezados ? proponerColumnasTraspaso(tablaPegada.encabezados) : columnasDelServidor(undefined));
  };

  const bajarPlantilla = async () => {
    setErrorArchivo(null);
    setBajando(true);
    try {
      await descargarPlantillaTraspaso();
    } catch (causa) {
      setErrorArchivo(mensajeTraspasoLista(causa, "No pudimos bajar la plantilla."));
    } finally {
      setBajando(false);
    }
  };

  const subir = async (archivo: File) => {
    setErrorArchivo(null);
    if (archivo.size > MAX_BYTES_ARCHIVO) {
      setErrorArchivo(`El archivo pesa más de ${MAX_BYTES_ARCHIVO / (1024 * 1024)} MB. Sube uno más pequeño.`);
      return;
    }
    setSubiendo(true);
    try {
      const r = await leerArchivoTraspaso(archivo, destinoId, almacenId);
      const tabla: Tabla = { origen: "archivo", archivo: archivo.name, encabezados: r.encabezados, filas: r.filas, primeraFila: r.primera_fila };
      const tope = motivoDeTopeTabla(tabla);
      if (tope) {
        setErrorArchivo(tope);
        return;
      }
      alTener(tabla, columnasDelServidor(r.columnas));
    } catch (causa) {
      setErrorArchivo(mensajeTraspasoLista(causa, "No pudimos leer el archivo."));
    } finally {
      setSubiendo(false);
      if (entradaArchivo.current) entradaArchivo.current.value = "";
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">¿Cómo armas la lista?</h2>
        <p className="text-sm text-muted-foreground">
          La lista lleva el código de cada artículo y su cantidad. Si es un artículo por pieza, una fila por pieza con su código o su serie. Un traspaso admite hasta 500 renglones.
        </p>
        <Boton variante="secundario" className="self-start" cargando={bajando} onClick={() => void bajarPlantilla()}>
          <DownloadIcon aria-hidden="true" className={bajando ? "hidden" : undefined} />
          Descargar la plantilla de Excel
        </Boton>
      </section>

      <section className="flex flex-col gap-3" aria-labelledby={`${idArchivo}-t`}>
        <h2 id={`${idArchivo}-t`} className="text-lg font-semibold">
          Sube un archivo de Excel
        </h2>
        <p className="text-sm text-muted-foreground">Un archivo .xlsx de hasta 5 MB. Se lee la primera hoja.</p>
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

      <div className="flex items-center gap-3 text-sm text-muted-foreground" aria-hidden="true">
        <span className="h-px flex-1 bg-border" />o<span className="h-px flex-1 bg-border" />
      </div>

      <section className="flex flex-col gap-3" aria-labelledby={`${idTexto}-t`}>
        <h2 id={`${idTexto}-t`} className="text-lg font-semibold">
          Pega la tabla copiada de Excel
        </h2>
        <label htmlFor={idTexto} className="sr-only">
          Tabla copiada de Excel
        </label>
        <Textarea
          id={idTexto}
          value={texto}
          rows={7}
          spellCheck={false}
          placeholder={"Código\tCantidad\tCódigo pieza\tSerie"}
          aria-invalid={lectura && !lectura.ok ? true : undefined}
          aria-describedby={`${idTexto}-estado`}
          onChange={(e) => {
            setTexto(e.target.value);
            alCambiarTexto(e.target.value);
            setConEncabezadosElegido(null);
          }}
          className="min-h-40 w-full rounded-xl border border-input bg-background p-3 text-base leading-snug"
        />
        <div id={`${idTexto}-estado`} aria-live="polite" className="flex flex-col gap-3">
          {lectura && !lectura.ok ? (
            <p role="alert" className="flex items-start gap-2 text-base font-semibold text-destructive">
              <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
              {lectura.mensaje}
            </p>
          ) : null}
          {motivoTope ? (
            <p role="alert" className="flex items-start gap-2 text-base font-semibold text-destructive">
              <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
              {motivoTope}
            </p>
          ) : null}
          {lectura?.ok ? (
            <>
              <p className="text-base font-medium">
                Se leyeron {filas.length.toLocaleString("es-MX")} {filas.length === 1 ? "fila" : "filas"} y {columnas} {columnas === 1 ? "columna" : "columnas"}.
              </p>
              <label className="flex min-h-12 cursor-pointer items-center gap-3 text-base font-medium">
                <Checkbox checked={conEncabezados} onCheckedChange={(m) => setConEncabezadosElegido(m)} className="size-6 rounded-md [&_svg]:size-4" />
                La primera fila trae los encabezados
              </label>
              <div className="[contain:inline-size]">
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

      <AccionPrincipal nota={nota}>
        <Boton variante="principal" disabled={nota !== null} onClick={continuar}>
          Continuar
        </Boton>
      </AccionPrincipal>
    </div>
  );
}
