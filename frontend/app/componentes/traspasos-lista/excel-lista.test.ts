import { describe, expect, it } from "vitest";
import type { VistaPreviaTraspasoApi } from "~/api/traspasos-lista";
import { crearExcelLista } from "./excel-lista";

function vista(cantidad = 3): VistaPreviaTraspasoApi {
  return { origen: { id: "o", clave: "OR", nombre: "Origen & compañía" }, destino: { id: "d", clave: "DE", nombre: "Destino" }, ruta: { habitual: true, nivel: "VERDE", pide_observacion: false, mensaje: "" }, archivo_repetido: null, resumen: { total: cantidad, ok: cantidad - 1, avisos: 0, errores: 1, unidades: cantidad * 2, piezas: 1, excedido: false }, avisos: [], filas: Array.from({ length: cantidad }, (_, i) => ({ fila: i + 2, codigo: i === 0 ? "=HYPERLINK(\"x\")" : `000${i}`, articulo: `Artículo <${i}>`, pieza: i === 1 ? { id: "p", codigo: "PZ-001", numero_serie: "SERIE-Ñ/01" } : null, cantidad: 2, disponible_en_origen: 9, nivel: i === 2 ? "ROJO" : "VERDE", motivos: i === 2 ? [{ regla: "X-02", codigo: "FALTA", mensaje: "No alcanza" }] : [], unida_de: i === 0 ? [7, 9] : undefined })) };
}

async function leerZip(blob: Blob) {
  const bytes = new Uint8Array(await blob.arrayBuffer()), view = new DataView(bytes.buffer);
  const archivos: Record<string, string> = {};
  let offset = 0;
  while (view.getUint32(offset, true) === 0x04034b50) {
    expect(view.getUint16(offset + 8, true)).toBe(0);
    const tamano = view.getUint32(offset + 18, true), nombreLargo = view.getUint16(offset + 26, true), extra = view.getUint16(offset + 28, true);
    const nombre = new TextDecoder().decode(bytes.slice(offset + 30, offset + 30 + nombreLargo));
    const inicio = offset + 30 + nombreLargo + extra;
    archivos[nombre] = new TextDecoder().decode(bytes.slice(inicio, inicio + tamano));
    offset = inicio + tamano;
  }
  expect(view.getUint32(offset, true)).toBe(0x02014b50);
  expect(view.getUint32(bytes.length - 22, true)).toBe(0x06054b50);
  return archivos;
}

describe("TR-10 Excel de la lista cargada", () => {
  it("incluye los códigos exactos como texto seguro, serie y avisos sin tratarlo como enviado", async () => {
    const original = vista();
    const archivos = await leerZip(crearExcelLista(original));
    expect(Object.keys(archivos)).toHaveLength(6);
    const hoja = archivos["xl/worksheets/sheet1.xml"];
    expect(hoja).toContain("VISTA PREVIA");
    expect(hoja).toContain("todavía no se ha enviado");
    expect(hoja).toContain("Origen &amp; compañía");
    expect(hoja).toContain('t="inlineStr"><is><t xml:space="preserve">=HYPERLINK(&quot;x&quot;)');
    expect(hoja).not.toContain("<f>");
    expect(hoja).toContain("PZ-001"); expect(hoja).toContain("SERIE-Ñ/01");
    expect(hoja).toContain("Unido: filas 2, 7, 9"); expect(hoja).toContain("No alcanza");
    expect(original.filas).toHaveLength(3);
  });
  it("descarga todos los renglones y deja fuera sólo las filas indicadas tras confirmar", async () => {
    const archivos = await leerZip(crearExcelLista(vista(500), { folio: "OR-TRS-0123", filasExcluidas: [4] }));
    const hoja = archivos["xl/worksheets/sheet1.xml"];
    expect(hoja).toContain("OR-TRS-0123"); expect(hoja).toContain("Traspaso confirmado");
    expect(hoja).not.toContain("No alcanza");
    expect(hoja.match(/<row /g)).toHaveLength(505);
    expect(hoja).toContain("000499");
    expect(hoja).toContain("499 renglones · 998 unidades · 1 filas dejadas fuera");
  });
  it("prepara Carta horizontal, ancho de una página y encabezado repetido para recepción", async () => {
    const archivos = await leerZip(crearExcelLista(vista()));
    const hoja = archivos["xl/worksheets/sheet1.xml"];
    expect(hoja).toContain('paperSize="1" orientation="landscape" fitToWidth="1" fitToHeight="0"');
    expect(archivos["xl/workbook.xml"]).toContain("'Lista de recepción'!$6:$6");
    expect(hoja).toContain("Recibido"); expect(hoja).toContain("Verificado");
    expect(hoja).toContain('r="E7" s="2"><v>2</v>');
    expect(archivos["xl/styles.xml"]).toContain('wrapText="1"');
  });
});
