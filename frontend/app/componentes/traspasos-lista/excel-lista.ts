import type { VistaPreviaTraspasoApi } from "~/api/traspasos-lista";

const XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>';
const NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main";
const escapar = (s: string) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&apos;" }[c]!));

/** ZIP almacenado (sin compresión): un XLSX pequeño no necesita otra dependencia. */
function zip(archivos: Record<string, string>): Uint8Array<ArrayBuffer> {
  const encoder = new TextEncoder();
  const locales: Uint8Array[] = [];
  const centrales: Uint8Array[] = [];
  let posicion = 0;
  for (const [nombre, texto] of Object.entries(archivos)) {
    const ruta = encoder.encode(nombre), datos = encoder.encode(texto);
    let crc = 0xffffffff;
    for (const byte of datos) {
      crc ^= byte;
      for (let i = 0; i < 8; i++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
    }
    crc = (crc ^ 0xffffffff) >>> 0;
    const local = new Uint8Array(30 + ruta.length + datos.length);
    const l = new DataView(local.buffer);
    l.setUint32(0, 0x04034b50, true); l.setUint16(4, 20, true); l.setUint16(6, 0x800, true);
    l.setUint32(14, crc, true); l.setUint32(18, datos.length, true); l.setUint32(22, datos.length, true); l.setUint16(26, ruta.length, true);
    local.set(ruta, 30); local.set(datos, 30 + ruta.length);
    const central = new Uint8Array(46 + ruta.length);
    const c = new DataView(central.buffer);
    c.setUint32(0, 0x02014b50, true); c.setUint16(4, 20, true); c.setUint16(6, 20, true); c.setUint16(8, 0x800, true);
    c.setUint32(16, crc, true); c.setUint32(20, datos.length, true); c.setUint32(24, datos.length, true); c.setUint16(28, ruta.length, true); c.setUint32(42, posicion, true);
    central.set(ruta, 46); locales.push(local); centrales.push(central); posicion += local.length;
  }
  const largoCentral = centrales.reduce((n, c) => n + c.length, 0);
  const fin = new Uint8Array(22), f = new DataView(fin.buffer);
  f.setUint32(0, 0x06054b50, true); f.setUint16(8, centrales.length, true); f.setUint16(10, centrales.length, true); f.setUint32(12, largoCentral, true); f.setUint32(16, posicion, true);
  const salida = new Uint8Array(posicion + largoCentral + fin.length);
  let offset = 0;
  for (const parte of [...locales, ...centrales, fin]) { salida.set(parte, offset); offset += parte.length; }
  return salida;
}

function celda(referencia: string, valor: string | number, estilo: number): string {
  // inlineStr conserva ceros iniciales y evita que un código se interprete como fórmula.
  return typeof valor === "number"
    ? `<c r="${referencia}" s="${estilo}"><v>${valor}</v></c>`
    : `<c r="${referencia}" s="${estilo}" t="inlineStr"><is><t xml:space="preserve">${escapar(valor)}</t></is></c>`;
}

/** TR-10: exporta toda la vista cargada, sin depender de la página o filtro visual de la tabla. */
export function crearExcelLista(vista: VistaPreviaTraspasoApi, opciones: { folio?: string; observacion?: string; filasExcluidas?: number[] } = {}): Blob {
  const excluidas = new Set(opciones.filasExcluidas ?? []);
  const filas = vista.filas.filter((f) => !excluidas.has(f.fila));
  const cabecera = ["Fila", "Código", "Artículo", "Serie", "Enviado", "Recibido", "Verificado", "Avisos / diferencias"];
  const datos: (string | number)[][] = [
    [`IMHOTEP · Lista de recepción${opciones.folio ? ` · ${opciones.folio}` : " · VISTA PREVIA"}`],
    [`Origen: ${vista.origen.clave} · ${vista.origen.nombre} → Destino: ${vista.destino.clave} · ${vista.destino.nombre}`],
    [opciones.folio ? "Traspaso confirmado. Anota lo recibido y las diferencias; la recepción se registra en la aplicación." : "Vista previa: este traspaso todavía no se ha enviado."],
    [`${filas.length} renglones · ${filas.reduce((n, f) => n + f.cantidad, 0)} unidades · ${excluidas.size} filas dejadas fuera. ${opciones.observacion ?? ""}`],
    [], cabecera,
    ...filas.map((f) => [f.fila, f.pieza?.codigo ?? f.codigo ?? "", f.articulo ?? "No se reconoce", f.pieza?.numero_serie ?? "", f.cantidad, "", "", [f.nivel === "ROJO" ? "ERROR: no se puede enviar" : "", ...(f.unida_de?.length ? [`Unido: filas ${[f.fila, ...f.unida_de].join(", ")}`] : []), ...f.motivos.map((m) => m.mensaje)].filter(Boolean).join(" · ")]),
  ];
  const anchos = [6, 19, 31, 18, 10, 10, 11, 38];
  const altura = (fila: (string | number)[], indice: number) => indice < 6 ? 30 : Math.min(409, Math.max(44, ...fila.map((v, j) => Math.ceil(String(v).length / Math.max(1, anchos[j] - 3)) * 15 + 8)));
  const hoja = `${XML}<worksheet xmlns="${NS}"><sheetPr><pageSetUpPr fitToPage="1"/></sheetPr><dimension ref="A1:H${datos.length}"/><sheetViews><sheetView workbookViewId="0"><pane ySplit="6" topLeftCell="A7" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols>${anchos.map((ancho, i) => `<col min="${i + 1}" max="${i + 1}" width="${ancho}" customWidth="1"/>`).join("")}</cols><sheetData>${datos.map((fila, i) => `<row r="${i + 1}" ht="${altura(fila, i)}" customHeight="1">${fila.map((valor, j) => celda(`${String.fromCharCode(65 + j)}${i + 1}`, valor, i < 4 ? 0 : i === 5 ? 1 : 2)).join("")}</row>`).join("")}</sheetData><mergeCells count="4">${[1, 2, 3, 4].map((r) => `<mergeCell ref="A${r}:H${r}"/>`).join("")}</mergeCells><printOptions horizontalCentered="1"/><pageMargins left="0.25" right="0.25" top="0.4" bottom="0.4" header="0.15" footer="0.15"/><pageSetup paperSize="1" orientation="landscape" fitToWidth="1" fitToHeight="0"/><headerFooter><oddFooter>&amp;C Página &amp;P de &amp;N</oddFooter></headerFooter></worksheet>`;
  const estilos = `${XML}<styleSheet xmlns="${NS}"><fonts count="2"><font><sz val="10"/><name val="Arial"/></font><font><b/><sz val="10"/><name val="Arial"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FFE6E6E6"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="2"><border/><border><left style="thin"/><right style="thin"/><top style="thin"/><bottom style="thin"/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" applyAlignment="1"><alignment wrapText="1" vertical="center"/></xf><xf numFmtId="0" fontId="1" fillId="2" borderId="1" applyAlignment="1"><alignment wrapText="1" vertical="center"/></xf><xf numFmtId="0" fontId="0" fillId="0" borderId="1" applyAlignment="1"><alignment wrapText="1" vertical="center"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>`;
  const contenido = zip({
    "[Content_Types].xml": `${XML}<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>`,
    "_rels/.rels": `${XML}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`,
    "xl/workbook.xml": `${XML}<workbook xmlns="${NS}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Lista de recepción" sheetId="1" r:id="rId1"/></sheets><definedNames><definedName name="_xlnm.Print_Titles" localSheetId="0">'Lista de recepción'!$6:$6</definedName><definedName name="_xlnm.Print_Area" localSheetId="0">'Lista de recepción'!$A$1:$H$${datos.length}</definedName></definedNames></workbook>`,
    "xl/_rels/workbook.xml.rels": `${XML}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`,
    "xl/styles.xml": estilos,
    "xl/worksheets/sheet1.xml": hoja,
  });
  return new Blob([contenido], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
}
