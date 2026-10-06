import { QRCodeSVG } from "qrcode.react";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { ALTO_MM, ANCHO_MM, ajustarNombre, type DatosCredencial } from "./credencial-medidas";

/**
 * Dibuja la credencial en un lienzo y la entrega como PNG, sin dependencias nuevas. Usa las mismas
 * medidas que la tarjeta de pantalla (`credencial.tsx`): 85.6 × 54 mm. Se dibuja a 24 píxeles por
 * milímetro (≈ 600 ppp), suficiente para imprimirla en un servicio de tarjetas.
 *
 * El QR contiene exactamente el código del trabajador. No lleva CURP ni NSS: los datos de entrada
 * no los traen (RG-13).
 */

const PX_POR_MM = 24;

/** Milímetros a píxeles del lienzo. */
const mm = (valor: number) => valor * PX_POR_MM;
const MARINO = "#1b1f8a";
const AZUL = "#0054a6";
const TEXTO = "#111827";
const GRIS = "#4b5563";
const FAMILIA = '"Poppins", system-ui, "Segoe UI", Arial, sans-serif';

const cacheImagenes = new Map<string, Promise<HTMLImageElement>>();

function cargarImagen(src: string): Promise<HTMLImageElement> {
  const guardada = cacheImagenes.get(src);
  if (guardada) return guardada;
  const promesa = new Promise<HTMLImageElement>((resolver, rechazar) => {
    const img = new Image();
    img.onload = () => resolver(img);
    img.onerror = () => {
      cacheImagenes.delete(src);
      rechazar(new Error("No se pudo cargar una imagen de la credencial."));
    };
    img.src = src;
  });
  cacheImagenes.set(src, promesa);
  return promesa;
}

/** El QR como imagen: el mismo SVG de la pantalla, con margen blanco, nivel de corrección M. */
function imagenQr(valor: string): Promise<HTMLImageElement> {
  const marcado = renderToStaticMarkup(
    createElement(QRCodeSVG, { value: valor, size: 512, level: "M", bgColor: "#ffffff", fgColor: "#000000", marginSize: 2 }),
  ).replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ');
  return cargarImagen(`data:image/svg+xml;charset=utf-8,${encodeURIComponent(marcado)}`);
}

async function esperarFuentes() {
  if (typeof document === "undefined" || !document.fonts) return;
  await Promise.all(
    ["400", "600", "700"].map((peso) => document.fonts.load(`${peso} 24px Poppins`, "Ñáéíóú ČŐŁŞ").catch(() => [])),
  );
}

function rectRedondeado(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

/** Recorta con puntos suspensivos para que el texto quepa en `ancho`. */
function ajustarLinea(ctx: CanvasRenderingContext2D, texto: string, ancho: number): string {
  if (ctx.measureText(texto).width <= ancho) return texto;
  let corto = texto;
  while (corto.length > 1 && ctx.measureText(`${corto}…`).width > ancho) corto = corto.slice(0, -1);
  return `${corto.trimEnd()}…`;
}

/** Parte el texto en un máximo de `maxLineas` renglones del ancho dado; el último lleva "…" si sobra. */
function partirEnLineas(ctx: CanvasRenderingContext2D, texto: string, ancho: number, maxLineas: number): string[] {
  const palabras = texto.split(/\s+/).filter(Boolean);
  const lineas: string[] = [];
  let actual = "";
  for (let i = 0; i < palabras.length; i++) {
    const prueba = actual ? `${actual} ${palabras[i]}` : palabras[i];
    if (ctx.measureText(prueba).width <= ancho || !actual) {
      actual = prueba;
      continue;
    }
    if (lineas.length === maxLineas - 1) {
      actual = [actual, ...palabras.slice(i)].join(" ");
      break;
    }
    lineas.push(actual);
    actual = palabras[i];
  }
  if (actual) lineas.push(ajustarLinea(ctx, actual, ancho));
  return lineas;
}

function aBlob(lienzo: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolver, rechazar) =>
    lienzo.toBlob((b) => (b ? resolver(b) : rechazar(new Error("No se pudo generar la imagen."))), "image/png"),
  );
}

/** Credencial completa (85.6 × 54 mm) como imagen PNG de alta resolución. */
export async function credencialComoPng(datos: DatosCredencial): Promise<Blob> {
  await esperarFuentes();
  const [logo, qr] = await Promise.all([cargarImagen("/logo-imhotep.png"), imagenQr(datos.codigo)]);

  const lienzo = document.createElement("canvas");
  lienzo.width = Math.round(ANCHO_MM * PX_POR_MM);
  lienzo.height = Math.round(ALTO_MM * PX_POR_MM);
  const ctx = lienzo.getContext("2d");
  if (!ctx) throw new Error("No se pudo preparar la imagen.");
  ctx.textBaseline = "alphabetic";

  // Todo se dibuja en píxeles reales: las medidas de abajo van en milímetros y `mm` las convierte.
  // Tarjeta blanca con esquinas redondeadas; todo lo demás se recorta a ella.
  ctx.save();
  rectRedondeado(ctx, 0, 0, mm(ANCHO_MM), mm(ALTO_MM), mm(3));
  ctx.clip();
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, mm(ANCHO_MM), mm(ALTO_MM));

  // Banda superior azul marino con el logo en un círculo blanco.
  ctx.fillStyle = MARINO;
  ctx.fillRect(0, 0, mm(ANCHO_MM), mm(13.5));
  ctx.fillStyle = "#ffffff";
  ctx.beginPath();
  ctx.arc(mm(9.2), mm(6.75), mm(5.1), 0, Math.PI * 2);
  ctx.fill();
  ctx.drawImage(logo, mm(4.7), mm(2.3), mm(9), mm(8.47));
  ctx.fillStyle = "#ffffff";
  ctx.font = `700 ${mm(4.6)}px ${FAMILIA}`;
  ctx.fillText("IMHOTEP", mm(16.2), mm(7.1));
  ctx.fillStyle = "#c7d2fe";
  ctx.font = `400 ${mm(2.1)}px ${FAMILIA}`;
  ctx.fillText("Mantenimiento Industrial", mm(16.2), mm(10.4));
  // Franja delgada azul claro bajo la banda.
  ctx.fillStyle = AZUL;
  ctx.fillRect(0, mm(13.5), mm(ANCHO_MM), mm(0.7));

  // Nombre completo (2 o 3 renglones; el tamaño baja si es largo; si aun así no cabe, termina en "…"
  // igual que la tarjeta de pantalla).
  const anchoTexto = mm(46.5);
  const { tamano, interlinea, lineas: maxLineas } = ajustarNombre(datos.nombre);
  ctx.fillStyle = TEXTO;
  ctx.font = `700 ${mm(tamano)}px ${FAMILIA}`;
  const lineas = partirEnLineas(ctx, datos.nombre, anchoTexto, maxLineas);
  let y = mm(14.2 + 2.9 + tamano * 0.95);
  for (const linea of lineas) {
    ctx.fillText(linea, mm(5), y);
    y += mm(interlinea);
  }

  // Puesto y número de empleado, en posiciones fijas para que no se muevan según el nombre.
  ctx.fillStyle = AZUL;
  ctx.font = `600 ${mm(3.1)}px ${FAMILIA}`;
  ctx.fillText(ajustarLinea(ctx, datos.puesto?.trim() || "Sin puesto registrado", anchoTexto), mm(5), mm(35.2));
  ctx.fillStyle = GRIS;
  ctx.font = `400 ${mm(2.2)}px ${FAMILIA}`;
  ctx.fillText("Número de empleado", mm(5), mm(40.6));
  ctx.fillStyle = TEXTO;
  ctx.font = `700 ${mm(3.9)}px ${FAMILIA}`;
  ctx.fillText(ajustarLinea(ctx, datos.numero_empleado, anchoTexto), mm(5), mm(45));

  // QR a la derecha, con su marco y el código en texto legible.
  ctx.strokeStyle = "#d1d5db";
  ctx.lineWidth = mm(0.25);
  rectRedondeado(ctx, mm(54.6), mm(18.4), mm(27.2), mm(27.2), mm(1.4));
  ctx.fillStyle = "#ffffff";
  ctx.fill();
  ctx.stroke();
  ctx.drawImage(qr, mm(55.2), mm(19), mm(26), mm(26));
  ctx.fillStyle = TEXTO;
  ctx.textAlign = "center";
  ctx.font = `700 ${mm(2.9)}px ${FAMILIA}`;
  ctx.fillText(ajustarLinea(ctx, datos.codigo, mm(27)), mm(68.2), mm(49));
  ctx.textAlign = "left";

  ctx.restore();

  // Contorno fino de la tarjeta.
  ctx.strokeStyle = "#cbd5e1";
  ctx.lineWidth = mm(0.2);
  rectRedondeado(ctx, mm(0.1), mm(0.1), mm(ANCHO_MM - 0.2), mm(ALTO_MM - 0.2), mm(3));
  ctx.stroke();

  return aBlob(lienzo);
}

/** Etiqueta de solo el código QR (60 × 36 mm): el QR, el nombre y el código en texto legible. */
export async function etiquetaQrComoPng(datos: { codigo: string; texto: string }): Promise<Blob> {
  await esperarFuentes();
  const qr = await imagenQr(datos.codigo);
  const ancho = 60;
  const alto = 36;
  const lienzo = document.createElement("canvas");
  lienzo.width = mm(ancho);
  lienzo.height = mm(alto);
  const ctx = lienzo.getContext("2d");
  if (!ctx) throw new Error("No se pudo preparar la imagen.");
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, lienzo.width, lienzo.height);
  ctx.drawImage(qr, mm(3), mm(4), mm(28), mm(28));
  ctx.fillStyle = TEXTO;
  ctx.font = `700 ${mm(3.2)}px ${FAMILIA}`;
  // Hasta 3 renglones, igual que la etiqueta de pantalla; si no cabe, termina en "…".
  const lineas = partirEnLineas(ctx, datos.texto, mm(24), 3);
  let y = mm(10);
  for (const linea of lineas) {
    ctx.fillText(linea, mm(33), y);
    y += mm(4);
  }
  ctx.font = `600 ${mm(3)}px ${FAMILIA}`;
  ctx.fillText(ajustarLinea(ctx, datos.codigo, mm(24)), mm(33), mm(31));
  return aBlob(lienzo);
}

/** Baja el archivo en el navegador. */
export function descargarBlob(blob: Blob, nombreArchivo: string) {
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombreArchivo;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Nombre de archivo sin acentos ni símbolos, por ejemplo `credencial-TRB-1001.png`. */
export function nombreDeArchivo(prefijo: string, codigo: string): string {
  const limpio = codigo.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^A-Za-z0-9_-]+/g, "-");
  return `${prefijo}-${limpio}.png`;
}
