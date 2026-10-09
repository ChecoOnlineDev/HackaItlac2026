// Lectura de la tabla pegada desde Excel (texto con tabuladores) y utilidades de las columnas. La lectura
// se hace en el navegador: al servidor llegan filas ya separadas. Aquí no se decide si una fila es válida:
// eso lo revisa el servidor en la vista previa.

import { CAMPOS, type CampoImportacion, type Columnas, type FilaError, type ModoImportacion, type Tabla } from "./tipos";
import { esAppNativa } from "~/movil/plataforma";
import { aviso } from "~/componentes/ui/aviso";

// Los mismos límites que el servidor (backend/app/modulos/importacion/schemas.py), para avisar antes.
export const MAX_FILAS = 5000;
export const MAX_COLUMNAS = 30;
export const MAX_CELDA = 500;
export const MAX_BYTES_ARCHIVO = 5 * 1024 * 1024;

export const ETIQUETA_CAMPO: Record<CampoImportacion, string> = {
  codigo: "Código del artículo",
  nombre: "Nombre",
  marca: "Marca",
  categoria: "Categoría",
  cantidad: "Cantidad",
  almacen: "Almacén",
  serie: "Número de serie",
  costo: "Costo",
  codigo_pieza: "Código de la pieza",
  unidad: "Unidad de medida",
};

/** Cada modo habla distinto de algunos datos. */
export function ayudaDeCampo(campo: CampoImportacion, modo: ModoImportacion): string {
  if (modo === "REPOSICION") {
    if (campo === "codigo") return "Obligatorio. Debe ser el código de un artículo que ya existe.";
    if (campo === "cantidad") return "Cuántas unidades llegaron. Solo números enteros.";
    if (campo === "serie") return "Solo para artículos por pieza.";
  }
  return AYUDA_CAMPO[campo];
}

/** Qué es cada dato, en una frase, para quien relaciona las columnas. */
export const AYUDA_CAMPO: Record<CampoImportacion, string> = {
  codigo: "Con él se reconoce el artículo. Si no lo traes, hace falta el nombre.",
  nombre: "Hace falta en los artículos nuevos.",
  marca: "Opcional.",
  categoria: "Hace falta en los artículos nuevos.",
  cantidad: "Cuántas unidades entran (los artículos por pieza entran de una en una).",
  almacen: "Ya no se usa: todo entra a Kepler.",
  serie: "Solo para artículos por pieza. Si no la traes, la pieza entra con la serie pendiente.",
  costo: "Solo se guarda en artículos nuevos.",
  codigo_pieza: "Opcional. Si no lo traes, se genera al confirmar.",
  unidad: "Opcional: kilos, metros, pieza… Si no la traes, se usa «pieza». No cambia la de un artículo que ya existe.",
};

/** Una columna vacía en todos sus datos: `null` para cada campo. */
export function columnasVacias(): Columnas {
  return Object.fromEntries(CAMPOS.map((c) => [c, null])) as Columnas;
}

/** "A", "B", … "Z", "AA": como las llama Excel. */
export function letraDeColumna(indice: number): string {
  let n = indice;
  let letras = "";
  do {
    letras = String.fromCharCode(65 + (n % 26)) + letras;
    n = Math.floor(n / 26) - 1;
  } while (n >= 0);
  return letras;
}

/** Cómo se llama una columna: su encabezado, o "Columna C" si no tiene. */
export function nombreDeColumna(encabezados: string[] | null, indice: number): string {
  const encabezado = encabezados?.[indice]?.trim();
  return encabezado ? encabezado : `Columna ${letraDeColumna(indice)}`;
}

// ---------------------------------------------------------------------------------------------
// Lectura del texto pegado

export type ResultadoLectura = { ok: true; filas: string[][] } | { ok: false; mensaje: string };

/** Separa un texto con tabuladores en filas y celdas. Respeta las celdas entre comillas que Excel agrega. */
export function leerTextoPegado(texto: string): ResultadoLectura {
  const entrada = texto.replace(/^﻿/, "");
  const filas: string[][] = [];
  let fila: string[] = [];
  let celda = "";
  let enComillas = false;
  let i = 0;
  const cerrarCelda = () => {
    fila.push(celda);
    celda = "";
  };
  const cerrarFila = () => {
    cerrarCelda();
    filas.push(fila);
    fila = [];
  };
  while (i < entrada.length) {
    const c = entrada[i];
    if (enComillas) {
      if (c === '"') {
        if (entrada[i + 1] === '"') {
          celda += '"';
          i += 2;
          continue;
        }
        enComillas = false;
      } else {
        celda += c;
      }
    } else if (c === '"' && celda === "") {
      enComillas = true;
    } else if (c === "\t") {
      cerrarCelda();
    } else if (c === "\n") {
      cerrarFila();
    } else if (c === "\r") {
      // Se ignora: el salto de línea de Windows trae \r\n.
    } else {
      celda += c;
    }
    i += 1;
  }
  if (celda !== "" || fila.length > 0) cerrarFila();

  const limpias = filas.map((f) => f.map((c) => c.replace(/\s+/g, " ").trim()));
  while (limpias.length > 0 && limpias[limpias.length - 1].every((c) => c === "")) limpias.pop();
  if (limpias.length === 0) return { ok: false, mensaje: "No hay nada que leer. Pega aquí las celdas que copiaste de Excel." };

  const ancho = Math.max(...limpias.map((f) => f.length));
  if (ancho > MAX_COLUMNAS) return { ok: false, mensaje: `La tabla tiene ${ancho} columnas y el máximo es ${MAX_COLUMNAS}. Copia solo las columnas que necesitas.` };
  if (limpias.length > MAX_FILAS + 1) return { ok: false, mensaje: `La tabla tiene ${limpias.length.toLocaleString("es-MX")} filas y el máximo es ${MAX_FILAS.toLocaleString("es-MX")}. Divídela en partes.` };
  if (limpias.some((f) => f.some((c) => c.length > MAX_CELDA))) return { ok: false, mensaje: `Una celda pasa de ${MAX_CELDA} caracteres. Revisa lo que copiaste.` };

  const rectangular = limpias.map((f) => (f.length < ancho ? [...f, ...Array<string>(ancho - f.length).fill("")] : f));
  if (ancho === 1 && (rectangular[0][0] ?? "").split(/[;,|]/).length >= 3) {
    return { ok: false, mensaje: "No vimos columnas separadas. Copia las celdas directamente desde Excel (no desde un archivo de texto)." };
  }
  return { ok: true, filas: rectangular };
}

// ---------------------------------------------------------------------------------------------
// Encabezados y columnas propuestas

const sinAcentos = (t: string) =>
  t
    .normalize("NFKD")
    .replace(/\p{M}/gu, "")
    .toLocaleLowerCase("es-MX")
    .replace(/\s+/g, " ")
    .trim();
const palabrasDe = (t: string) => new Set(sinAcentos(t).match(/[a-z0-9]+/g) ?? []);

// Las mismas palabras que usa el servidor para proponer las columnas de un `.xlsx`
// (backend/app/modulos/importacion/lectura.py): el dato más específico primero.
const PALABRAS: [CampoImportacion, string[]][] = [
  ["serie", ["serie", "serial"]],
  ["costo", ["costo", "precio", "importe"]],
  ["cantidad", ["cantidad", "cant", "existencia", "existencias", "stock", "unidades"]],
  ["almacen", ["almacen", "bodega"]],
  ["categoria", ["categoria", "familia", "rubro"]],
  ["marca", ["marca", "fabricante"]],
  ["unidad", ["unidad", "um", "medida"]],
  ["nombre", ["nombre", "descripcion", "producto", "material", "herramienta"]],
];
const CODIGO = ["codigo", "clave", "sku", "folio", "etiqueta", "qr"];

/** Relaciona cada dato con la columna cuyo encabezado se le parece. Solo es una propuesta: se puede cambiar. */
export function proponerColumnas(encabezados: string[]): Columnas {
  const columnas = columnasVacias();
  const usadas = new Set<number>();
  const palabras = encabezados.map(palabrasDe);
  const tomar = (campo: CampoImportacion, buscadas: string[], exigir: string[] = []) => {
    palabras.forEach((conjunto, i) => {
      if (usadas.has(i) || columnas[campo] !== null) return;
      const coincide = buscadas.some((p) => conjunto.has(p));
      const exigida = exigir.length === 0 || exigir.some((p) => conjunto.has(p));
      if (coincide && exigida) {
        columnas[campo] = i;
        usadas.add(i);
      }
    });
  };
  tomar("codigo_pieza", [...CODIGO, "id"], ["pieza", "piezas"]);
  for (const [campo, buscadas] of PALABRAS) tomar(campo, buscadas);
  tomar("codigo", CODIGO);
  return columnas;
}

/**
 * TR-12: ¿se reconocieron solas las columnas obligatorias? Hace falta saber qué artículo es (código o nombre; en
 * la reposición, el código) y cuántos entran (cantidad, o una fila por pieza). Solo entonces se salta
 * «Relacionar columnas» y la vista previa aparece sola.
 */
export function columnasObligatoriasReconocidas(modo: ModoImportacion, c: Columnas): boolean {
  const articulo = modo === "REPOSICION" ? c.codigo !== null : c.codigo !== null || c.nombre !== null;
  const cuantos = c.cantidad !== null || c.codigo_pieza !== null || c.serie !== null;
  return articulo && cuantos;
}

/** ¿La primera fila parece de encabezados? (si tiene palabras como "código", "cantidad", "almacén"…). */
export function pareceEncabezado(fila: string[]): boolean {
  const conocidas = new Set([...PALABRAS.flatMap(([, p]) => p), ...CODIGO]);
  return fila.some((celda) => [...palabrasDe(celda)].some((p) => conocidas.has(p)));
}

/** Arma la tabla a partir de lo pegado, con o sin encabezados en la primera fila. */
export function armarTabla(filas: string[][], conEncabezados: boolean): Tabla {
  if (conEncabezados && filas.length > 0) {
    return { origen: "pegado", encabezados: filas[0], filas: filas.slice(1), primeraFila: 2 };
  }
  return { origen: "pegado", encabezados: null, filas, primeraFila: 1 };
}

// ---------------------------------------------------------------------------------------------
// Filas con error en CSV

/**
 * Una celda del CSV. Los datos del archivo son ajenos: si empiezan con `=`, `+`, `-`, `@`, tabulador o
 * retorno de carro, Excel los tomaría por una fórmula; se les antepone un apóstrofo.
 */
export function celdaCsv(valor: string): string {
  const segura = /^[=+\-@\t\r]/.test(valor) ? `'${valor}` : valor;
  return /[",\n\r]/.test(segura) ? `"${segura.replace(/"/g, '""')}"` : segura;
}

/** Las filas que no entraron, como CSV (con acentos que Excel lee bien), para corregirlas y volver a importar. */
export function filasConErrorACsv(filas: FilaError[]): string {
  const claves: string[] = [];
  for (const campo of CAMPOS) if (filas.some((f) => campo in f.datos)) claves.push(campo);
  for (const f of filas) for (const k of Object.keys(f.datos)) if (!claves.includes(k)) claves.push(k);
  const etiqueta = (k: string) => ETIQUETA_CAMPO[k as CampoImportacion] ?? k;
  const encabezado = ["Fila", ...claves.map(etiqueta), "Motivo"];
  const lineas = filas.map((f) =>
    [String(f.fila), ...claves.map((k) => f.datos[k] ?? ""), f.motivos.map((m) => m.mensaje).join(" | ")].map(celdaCsv).join(","),
  );
  return `﻿${[encabezado.map(celdaCsv).join(","), ...lineas].join("\r\n")}\r\n`;
}

/** Baja un texto como archivo. */
export function descargarTexto(nombre: string, contenido: string, tipo = "text/csv;charset=utf-8"): void {
  const blob = new Blob([contenido], { type: tipo });
  if (esAppNativa()) {
    void import("~/movil/archivos").then(({ compartirArchivo }) => compartirArchivo(blob, nombre))
      .catch(() => aviso({ titulo: "No pudimos guardar el archivo. Inténtalo de nuevo.", tipo: "error" }));
    return;
  }
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombre;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
