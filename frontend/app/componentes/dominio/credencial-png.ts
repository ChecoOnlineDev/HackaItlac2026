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
    ["400", "600", "700"].map((peso) => document.fonts.load(`${peso} 24px Poppins`, "Ñáéíóú").catch(() => [])),
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
  ctx.scale(PX_POR_MM, PX_POR_MM); // de aquí en adelante, todo en milímetros
  ctx.textBaseline = "alphabetic";

  // Tarjeta blanca con esquinas redondeadas; todo lo demás se recorta a ella.
  ctx.save();
  rectRedondeado(ctx, 0, 0, ANCHO_MM, ALTO_MM, 3);
  ctx.clip();
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, ANCHO_MM, ALTO_MM);

  // Banda superior azul marino con el logo en un círculo blanco.
  ctx.fillStyle = MARINO;
  ctx.fillRect(0, 0, ANCHO_MM, 13.5);
  ctx.fillStyle = "#ffffff";
  ctx.beginPath();
  ctx.arc(9.2, 6.75, 5.1, 0, Math.PI * 2);
  ctx.fill();
  ctx.drawImage(logo, 4.7, 2.3, 9, 8.47);
  ctx.fillStyle = "#ffffff";
  ctx.font = `700 4.6px ${FAMILIA}`;
  ctx.fillText("IMHOTEP", 16.2, 7.1);
  ctx.fillStyle = "#c7d2fe";
  ctx.font = `400 2.1px ${FAMILIA}`;
  ctx.fillText("Mantenimiento Industrial", 16.2, 10.4);
  // Franja delgada azul claro bajo la banda.
  ctx.fillStyle = AZUL;
  ctx.fillRect(0, 13.5, ANCHO_MM, 0.7);

  // Nombre completo (2 o 3 renglones; el tamaño baja si es largo, nunca se corta).
  const anchoTexto = 46.5;
  const { tamano, interlinea, lineas: maxLineas } = ajustarNombre(datos.nombre);
  ctx.fillStyle = TEXTO;
  ctx.font = `700 ${tamano}px ${FAMILIA}`;
  const lineas = partirEnLineas(ctx, datos.nombre, anchoTexto, maxLineas);
  let y = 14.2 + 2.9 + tamano * 0.95;
  for (const linea of lineas) {
    ctx.fillText(linea, 5, y);
    y += interlinea;
  }

  // Puesto y número de empleado, en posiciones fijas para que no se muevan según el nombre.
  ctx.fillStyle = AZUL;
  ctx.font = `600 3.1px ${FAMILIA}`;
  ctx.fillText(ajustarLinea(ctx, datos.puesto?.trim() || "Sin puesto registrado", anchoTexto), 5, 35.2);
  ctx.fillStyle = GRIS;
  ctx.font = `400 2.2px ${FAMILIA}`;
  ctx.fillText("Número de empleado", 5, 40.6);
  ctx.fillStyle = TEXTO;
  ctx.font = `700 3.9px ${FAMILIA}`;
  ctx.fillText(ajustarLinea(ctx, datos.numero_empleado, anchoTexto), 5, 45);

  // QR a la derecha, con su marco y el código en texto legible.
  ctx.strokeStyle = "#d1d5db";
  ctx.lineWidth = 0.25;
  rectRedondeado(ctx, 54.6, 18.4, 27.2, 27.2, 1.4);
  ctx.fillStyle = "#ffffff";
  ctx.fill();
  ctx.stroke();
  ctx.drawImage(qr, 55.2, 19, 26, 26);
  ctx.fillStyle = TEXTO;
  ctx.textAlign = "center";
  ctx.font = `700 2.9px ${FAMILIA}`;
  ctx.fillText(ajustarLinea(ctx, datos.codigo, 27), 68.2, 49);
  ctx.textAlign = "left";

  ctx.restore();

  // Contorno fino de la tarjeta.
  ctx.strokeStyle = "#cbd5e1";
  ctx.lineWidth = 0.2;
  rectRedondeado(ctx, 0.1, 0.1, ANCHO_MM - 0.2, ALTO_MM - 0.2, 3);
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
  lienzo.width = ancho * PX_POR_MM;
  lienzo.height = alto * PX_POR_MM;
  const ctx = lienzo.getContext("2d");
  if (!ctx) throw new Error("No se pudo preparar la imagen.");
  ctx.scale(PX_POR_MM, PX_POR_MM);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, ancho, alto);
  ctx.drawImage(qr, 3, 4, 28, 28);
  ctx.fillStyle = TEXTO;
  ctx.font = `700 3.2px ${FAMILIA}`;
  const lineas = partirEnLineas(ctx, datos.texto, 24, 4);
  let y = 10;
  for (const linea of lineas) {
    ctx.fillText(linea, 33, y);
    y += 4;
  }
  ctx.font = `600 3px ${FAMILIA}`;
  ctx.fillText(ajustarLinea(ctx, datos.codigo, 24), 33, 31);
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
