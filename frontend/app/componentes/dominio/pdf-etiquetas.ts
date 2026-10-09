import { QRCodeSVG } from "qrcode.react";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import type { jsPDF } from "jspdf";

import type { EtiquetaElemento } from "./tipos";
import { CARTA, FORMATOS_ETIQUETA, hojasEtiquetas, posicionEtiqueta, type FormatoEtiqueta } from "./etiquetas-medidas";
import { prepararFuentePdf } from "./pdf-fuentes";
import { credencialComoPng, descargarBlob } from "./credencial-png";

/** qrcode.react produce tramos horizontales: se reutiliza su matriz sin añadir otra biblioteca. */
function matrizQr(codigo: string) {
  const svg = renderToStaticMarkup(createElement(QRCodeSVG, { value: codigo, size: 600, level: "M", marginSize: 4 }));
  const lado = Number(/viewBox="0 0 (\d+) \d+"/.exec(svg)?.[1]);
  const trazos = [...svg.matchAll(/M(\d+)[ ,](\d+)\s*h(\d+)v1H\d+z/g)].map((r) => ({ x: Number(r[1]), y: Number(r[2]), ancho: Number(r[3]) }));
  if (!lado || !trazos.length) throw new Error("No pudimos preparar el código QR.");
  return { lado, trazos };
}

export function qrMuyPequeno(codigo: string, formato: FormatoEtiqueta): boolean {
  return FORMATOS_ETIQUETA[formato].qr / matrizQr(codigo).lado < 0.5;
}

function dibujarQr(doc: jsPDF, codigo: string, x: number, y: number, ancho: number) {
  const matriz = matrizQr(codigo);
  const unidad = ancho / matriz.lado;
  doc.setFillColor(255, 255, 255);
  doc.rect(x, y, ancho, ancho, "F");
  doc.setFillColor(0, 0, 0);
  for (const tramo of matriz.trazos) doc.rect(x + tramo.x * unidad, y + tramo.y * unidad, tramo.ancho * unidad, unidad, "F");
}

function textoLimitado(doc: jsPDF, texto: string, x: number, y: number, ancho: number, pt: number, maximo: number) {
  doc.setFontSize(pt);
  const lineas = doc.splitTextToSize(texto, ancho) as string[];
  const visibles = lineas.slice(0, maximo);
  if (lineas.length > maximo) {
    let ultima = visibles[maximo - 1] ?? "";
    while (ultima.length && doc.getTextWidth(`${ultima}…`) > ancho) ultima = ultima.slice(0, -1);
    visibles[maximo - 1] = `${ultima}…`;
  }
  doc.text(visibles, x, y, { lineHeightFactor: 1.15 });
  return visibles.length * pt * 0.3528 * 1.15;
}

function nombreArchivo(tipo: string, formato: string) {
  const partes = new Intl.DateTimeFormat("sv-SE", { timeZone: "America/Mexico_City", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(new Date()).replace(" ", "-").replace(":", "");
  return `${tipo}-${formato}-${partes}.pdf`;
}

export async function descargarEtiquetasPdf(elementos: EtiquetaElemento[], opciones: { tipo: string; formato: FormatoEtiqueta; completas?: boolean; inicio: number; signal: AbortSignal; progreso: (hoja: number, total: number) => void }) {
  if (!elementos.length || elementos.length > 1000) throw new Error("Elige entre 1 y 1000 etiquetas.");
  const { jsPDF } = await import("jspdf");
  const doc = new jsPDF({ unit: "mm", format: [CARTA.ancho, CARTA.alto], compress: true });
  await prepararFuentePdf(doc);
  const porHoja = opciones.completas ? 8 : opciones.formato;
  const total = hojasEtiquetas(elementos.length, porHoja, opciones.inicio);
  for (let hoja = 0; hoja < total; hoja++) {
    if (opciones.signal.aborted) throw new DOMException("Cancelado", "AbortError");
    if (hoja) doc.addPage();
    opciones.progreso(hoja + 1, total);
    for (let celda = 0; celda < porHoja; celda++) {
      const indice = hoja * porHoja + celda - opciones.inicio + 1;
      if (indice < 0 || indice >= elementos.length) continue;
      const e = elementos[indice];
      if (opciones.completas) {
        if (!e.nombre || !e.numero_empleado) throw new Error("La credencial no tiene todos sus datos.");
        const png = await credencialComoPng({ codigo: e.codigo, nombre: e.nombre, numero_empleado: e.numero_empleado, puesto: e.puesto });
        doc.addImage(new Uint8Array(await png.arrayBuffer()), "PNG", 18 + (celda % 2) * 94.3, 23.7 + Math.floor(celda / 2) * 59, 85.6, 54);
        continue;
      }
      const m = FORMATOS_ETIQUETA[opciones.formato];
      const { x, y } = posicionEtiqueta(celda, opciones.formato);
      if (opciones.formato !== 30) { doc.setDrawColor(160); doc.setLineWidth(0.15); doc.setLineDashPattern([1, 1], 0); doc.rect(x, y, m.ancho, m.alto); doc.setLineDashPattern([], 0); }
      const vertical = opciones.formato === 9;
      dibujarQr(doc, e.codigo, vertical ? x + (m.ancho - m.qr) / 2 : x + 2, y + 2, m.qr);
      doc.setTextColor(0, 0, 0);
      const tx = vertical ? x + 3 : x + m.qr + 4;
      const ty = vertical ? y + m.qr + 8 : y + 5;
      const ancho = vertical ? m.ancho - 6 : m.ancho - m.qr - 6;
      const sufijoSerie = e.numero_serie ? ` · serie ${e.numero_serie}` : "";
      const nombre = sufijoSerie && e.texto.endsWith(sufijoSerie) ? e.texto.slice(0, -sufijoSerie.length) : e.texto;
      const altoNombre = textoLimitado(doc, nombre, tx, ty, ancho, m.nombrePt, m.lineas);
      let pt = m.codigoPt;
      doc.setFontSize(pt);
      while (pt > 7 && doc.getTextWidth(e.codigo) > ancho) doc.setFontSize(--pt);
      const codigo = doc.splitTextToSize(e.codigo, ancho) as string[];
      doc.text(codigo, tx, ty + altoNombre + 2, { lineHeightFactor: 1.1 });
      if (e.numero_serie) textoLimitado(doc, `Serie ${e.numero_serie}`, tx, ty + altoNombre + 3 + codigo.length * pt * 0.3528 * 1.1, ancho, opciones.formato === 9 ? 10 : 8, 1);
    }
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
  }
  if (opciones.signal.aborted) throw new DOMException("Cancelado", "AbortError");
  await descargarBlob(doc.output("blob"), nombreArchivo(opciones.completas ? "credenciales" : `etiquetas-${opciones.tipo}`, opciones.completas ? "8" : String(opciones.formato)));
}
