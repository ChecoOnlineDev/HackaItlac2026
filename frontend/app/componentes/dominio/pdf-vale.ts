import { createElement } from "react";
import { QRCodeSVG } from "qrcode.react";
import { apiGet, imagenApi } from "~/api/cliente";
import type { RenglonValeApi, ValeDetalleApi } from "~/componentes/entrega/tipos";
import { esAppNativa } from "~/movil/plataforma";
import { prepararFuentePdf } from "./pdf-fuentes";
import { urlDeVale } from "./codigo-qr";
import { LEYENDA_RESPONSABILIDAD, NOMBRE_TIPO_VALE } from "./vale-imprimible";

interface Pagina<T> { elementos: T[]; total: number }
export interface CabeceraPdf extends ValeDetalleApi {
  proyecto?: { nombre: string } | null;
  resumen?: { categorias: { categoria: { nombre: string }; renglones: number; unidades: number; valor?: string | null }[]; valor_total?: string | null };
  lote?: { id: string; parte:number; partes:number; renglones:number; unidades:number; vales: { id: string; folio: string; estado: string }[] } | null;
}
export function filasPdf(renglones: RenglonValeApi[]): (string | number)[][] {
  // BT-07/F-12: proyección explícita, nunca serializar el DTO o sus montos.
  return renglones.map((r) => [r.renglon, r.codigo_articulo,
    [r.articulo, r.marca].filter(Boolean).join(" · "),
    [r.codigo_pieza, r.numero_serie].filter(Boolean).join(" · ") || "—", r.cantidad,
    r.condicion === "DANADO" ? "Dañado" : r.condicion === "DESGASTE" ? "Desgaste por uso" : r.condicion === "BUENO" ? "Bueno" : "—"]);
}
const fecha = (valor: string) => new Intl.DateTimeFormat("es-MX", { timeZone: "America/Mexico_City", dateStyle: "medium", timeStyle: "short" }).format(new Date(/[zZ]|[+-]\d\d:\d\d$/.test(valor) ? valor : `${valor}Z`));
async function imagen(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => { const r = new FileReader(); r.onload = () => resolve(String(r.result)); r.onerror = reject; r.readAsDataURL(blob); });
}
export async function svgDelVale(token: string): Promise<string> {
  const { renderToStaticMarkup } = await import("react-dom/server");
  const valor = urlDeVale(token);
  return renderToStaticMarkup(createElement(QRCodeSVG, { value: valor, size: 240, level: "M" })).replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ');
}
async function qr(token: string): Promise<string> {
  const svg = await svgDelVale(token);
  const url = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
  try {
    const img = new Image(); img.src = url; await img.decode();
    const canvas = document.createElement("canvas"); canvas.width = canvas.height = 240;
    const contexto = canvas.getContext("2d"); if (!contexto) throw new Error("No pudimos preparar el QR.");
    contexto.drawImage(img, 0, 0); return canvas.toDataURL("image/png");
  } finally { URL.revokeObjectURL(url); }
}
export async function descargarPdfVale(id: string, usuario: string, signal: AbortSignal,
  progreso: (texto: string) => void, lote = false): Promise<void> {
  const [{ jsPDF }, { default: tabla }] = await Promise.all([import("jspdf"), import("jspdf-autotable")]);
  const cabecera = await apiGet<CabeceraPdf>(`/vales/${id}`, { renglones: false }, signal);
  const vales = lote && cabecera.lote ? cabecera.lote.vales : [{ id, folio: cabecera.folio, estado: cabecera.estado }];
  const doc = new jsPDF({ format: "letter", unit: "mm" }); await prepararFuentePdf(doc);
  const logo = await fetch("/logo-imhotep.png", { signal }).then((r) => { if (!r.ok) throw new Error("Falta el logotipo del documento."); return r.blob(); }).then(imagen);
  const generaciones = fecha(new Date().toISOString());
  const encabezados = new Map<string,CabeceraPdf>([[id,cabecera]]);
  const codigosQr = new Map<string,string>();
  if (lote && vales.length > 1) {
    const categorias = new Map<string,{renglones:number;unidades:number}>();
    for(const v of vales) {
      signal.throwIfAborted(); progreso(`Preparando resumen del lote · ${encabezados.size} de ${vales.length} vales`);
      const encabezado = encabezados.get(v.id) ?? await apiGet<CabeceraPdf>(`/vales/${v.id}`,{renglones:false},signal);
      encabezados.set(v.id,encabezado); codigosQr.set(v.id,await qr(encabezado.token));
      for(const c of encabezado.resumen?.categorias ?? []) {const anterior=categorias.get(c.categoria.nombre) ?? {renglones:0,unidades:0}; anterior.renglones+=c.renglones; anterior.unidades+=c.unidades; categorias.set(c.categoria.nombre,anterior);}
    }
    doc.setFontSize(16); doc.text("Resumen del lote", 15, 22);
    doc.setFontSize(10); doc.text(`${cabecera.almacen.nombre} · ${cabecera.responsable.nombre}`, 15, 31);
    doc.text(`Importación del ${fecha(cabecera.creado_en)}`,15,37);
    tabla(doc, { startY: 43, head: [["Folio", "Estado", "Renglones", "Unidades", "QR"]], body: vales.map((v) => [v.folio, v.estado, (encabezados.get(v.id)?.resumen?.categorias ?? []).reduce((n,c)=>n+c.renglones,0), (encabezados.get(v.id)?.resumen?.categorias ?? []).reduce((n,c)=>n+c.unidades,0), ""]), styles: { font: "Poppins", fontStyle: "normal", minCellHeight:18 }, headStyles: { fontStyle: "normal" }, columnStyles:{4:{cellWidth:20}}, didDrawCell:(celda)=>{if(celda.section==="body" && celda.column.index===4){const v=vales[celda.row.index];doc.addImage(codigosQr.get(v.id)!,"PNG",celda.cell.x+2,celda.cell.y+2,14,14);}} });
    const y = (doc as unknown as {lastAutoTable:{finalY:number}}).lastAutoTable.finalY+7;
    tabla(doc,{startY:y,head:[["Categoría","Renglones","Unidades"]],body:[...categorias].map(([nombre,c])=>[nombre,c.renglones,c.unidades]),styles:{font:"Poppins",fontStyle:"normal",fontSize:9},headStyles:{fontStyle:"normal"}});
  }
  const foliosPorPagina = new Map<number, string>();
  for (let indice = 0; indice < vales.length; indice++) {
    signal.throwIfAborted();
    if (indice > 0 || (lote && vales.length > 1)) doc.addPage();
    const vale = encabezados.get(vales[indice].id) ?? await apiGet<CabeceraPdf>(`/vales/${vales[indice].id}`, { renglones: false }, signal);
    const paginaInicial = doc.getCurrentPageInfo().pageNumber;
    doc.setFontSize(13); doc.text(`${vale.folio} · ${NOMBRE_TIPO_VALE[vale.tipo]}`, 15, 24);
    doc.setFontSize(9);
    const lineas = [`${vale.estado} · ${fecha(vale.creado_en)}`, `Almacén: ${vale.almacen.nombre}`, `Responsable: ${vale.responsable.nombre}`,
      ...(vale.trabajador ? [`Trabajador: ${vale.trabajador.numero_empleado} · ${vale.trabajador.nombre}`, `Puesto: ${vale.trabajador.puesto ?? "—"} · Área: ${vale.trabajador.area_obra ?? "—"}`] : []),
      ...(vale.proyecto ? [`Proyecto: ${vale.proyecto.nombre}`] : []),
      ...(vale.destino_almacen ? [`Almacén destino: ${vale.destino_almacen.nombre}`] : []),
      ...(vale.observacion ? [`Observación: ${vale.observacion}`] : []),
      ...(vale.valido ? [`Validó: ${vale.valido.autorizo.nombre} · ${vale.valido.medio}`] : []),
      ...(vale.cancelacion ? [`Cancelación: ${vale.cancelacion.folio}`] : [])];
    const textoCabecera = doc.splitTextToSize(lineas.join("\n"), 175) as string[];
    let y = 32;
    for (const linea of textoCabecera) {
      if (y > 245) { doc.addPage(); y = 30; }
      doc.text(linea, 15, y); y += 4;
    }
    y += 2;
    tabla(doc, { startY: y, head: [["Categoría", "Renglones", "Unidades"]], body: (vale.resumen?.categorias ?? []).map((r) => [r.categoria.nombre, r.renglones, r.unidades]), styles: { font: "Poppins", fontStyle: "normal", fontSize: 8 }, headStyles: { fontStyle: "normal" } });
    y = ((doc as unknown as { lastAutoTable?: { finalY: number } }).lastAutoTable?.finalY ?? y) + 5;
    let pagina = 1; let leidos = 0; let total = 1;
    while (leidos < total) {
      signal.throwIfAborted(); progreso(`Vale ${indice + 1} de ${vales.length} · ${leidos} renglones preparados`);
      const datos = await apiGet<Pagina<RenglonValeApi>>(`/vales/${vale.id}/renglones`, { pagina, tamano: 500 }, signal);
      total = datos.total; if (total > leidos && !datos.elementos.length) throw new Error("La lista de renglones está incompleta.");
      tabla(doc, { startY: y, margin: { top: 23, bottom: 18 }, head: [["#", "Código", "Artículo y marca", "Pieza / serie", "Cantidad", "Condición"]], body: filasPdf(datos.elementos), styles: { font: "Poppins", fontStyle: "normal", fontSize: 7 }, headStyles: { fontStyle: "normal" }, didDrawPage: () => { foliosPorPagina.set(doc.getCurrentPageInfo().pageNumber, vale.folio); } });
      y = ((doc as unknown as { lastAutoTable: { finalY: number } }).lastAutoTable.finalY) + 6;
      leidos += datos.elementos.length; pagina++; await new Promise((resolve) => setTimeout(resolve, 0));
    }
    if (y > 220) { doc.addPage(); y = 30; }
    if (vale.tipo === "ENTREGA") { const leyenda = doc.splitTextToSize(LEYENDA_RESPONSABILIDAD, 160) as string[]; doc.text(leyenda, 15, y); y += leyenda.length * 4 + 3; }
    if (vale.tipo === "NO_ADEUDO") { doc.text(`Sin adeudos al ${fecha(vale.creado_en)}`, 15, y); y += 8; }
    doc.addImage(await qr(vale.token), "PNG", 175, y, 25, 25);
    if (vale.tiene_firma) {
      const firma = await imagenApi(`/vales/${vale.id}/firma`, signal).then(imagen);
      const propiedades = doc.getImageProperties(firma);
      if (vale.firma_modo === "PAPEL") {
        doc.text("Firma en papel · Copia firmada en la página siguiente", 15, y + 8);
        doc.addPage(); doc.setFontSize(11); doc.text(`Copia firmada · ${vale.folio}`, 15, 25);
        const escala = Math.min(175 / propiedades.width, 225 / propiedades.height);
        doc.addImage(firma, propiedades.fileType, 15, 32, propiedades.width * escala, propiedades.height * escala);
      } else {
        const escala = Math.min(70 / propiedades.width, 25 / propiedades.height);
        doc.addImage(firma, propiedades.fileType, 15, y, propiedades.width * escala, propiedades.height * escala);
      }
    } else doc.text(doc.splitTextToSize(`Firmado con la sesión de ${vale.responsable.nombre} el ${fecha(vale.creado_en)}`, 150), 15, y + 8);
    for(let p=paginaInicial;p<=doc.getCurrentPageInfo().pageNumber;p++) foliosPorPagina.set(p,vale.folio);
  }
  for (let p = 1; p <= doc.getNumberOfPages(); p++) {
    doc.setPage(p); doc.addImage(logo, "PNG", 15, 5, 17, 12);
    doc.setFontSize(8); doc.text(foliosPorPagina.get(p) ?? "Lote", 36, 12);
    doc.text(`Página ${p} de ${doc.getNumberOfPages()} · Generado ${generaciones} por ${usuario}`, 15, 270);
    const folio = foliosPorPagina.get(p);
    if (vales.some((v) => v.folio === folio && v.estado === "CANCELADO")) { doc.setTextColor(190, 190, 190); doc.setFontSize(40); doc.text("CANCELADO", 35, 150, { angle: 35 }); doc.setTextColor(0); }
  }
  signal.throwIfAborted();
  const nombre = lote && vales.length > 1 ? `lote-${vales[0].folio}-${vales.at(-1)!.folio.split("-").at(-1)}.pdf` : `${cabecera.folio}.pdf`;
  if (esAppNativa()) { const { compartirArchivo } = await import("~/movil/archivos"); await compartirArchivo(doc.output("blob"), nombre); }
  else doc.save(nombre);
}
