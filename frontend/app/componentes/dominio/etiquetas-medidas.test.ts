import { describe, expect, it } from "vitest";
import { CARTA, FORMATOS_ETIQUETA, hojasEtiquetas, posicionEtiqueta } from "./etiquetas-medidas";
import { qrMuyPequeno } from "./pdf-etiquetas";
import { coincideBusqueda } from "~/componentes/ui/busqueda-diferida";
import { formatearFecha, formatearFechaHora, hoyMexico } from "./formato";

describe("UX-03 palabras", () => {
  it("encuentra en cualquier orden ignorando acentos y mayúsculas", () => {
    expect(coincideBusqueda("Juan Pérez López", "PEREZ juan")).toBe(true);
    expect(coincideBusqueda("Juan Pérez López", "PEREZ mario")).toBe(false);
  });
});

describe("UX-05/07 etiquetas", () => {
  it("mantiene todos los formatos dentro de carta, con QR de al menos 20 mm", () => {
    for (const formato of [9, 18, 30] as const) {
      const m = FORMATOS_ETIQUETA[formato];
      const final = posicionEtiqueta(formato - 1, formato);
      expect(final.x + m.ancho).toBeLessThanOrEqual(CARTA.ancho);
      expect(final.y + m.alto).toBeLessThanOrEqual(CARTA.alto);
      expect(m.qr).toBeGreaterThanOrEqual(20);
    }
  });
  it("cuenta páginas incluyendo las posiciones vacías al principio", () => {
    expect(hojasEtiquetas(37, 18, 1)).toBe(3);
    expect(hojasEtiquetas(500, 18, 1)).toBe(28);
    expect(hojasEtiquetas(30, 30, 7)).toBe(2);
  });
  it("reutiliza tramos del SVG de códigos con Ñ, acentos, espacios y diagonal", () => {
    expect(qrMuyPequeno("ARNÉS/ALT-Ñ 01", 9)).toBe(false);
    expect(qrMuyPequeno("ñ".repeat(64), 30)).toBe(true);
  });
});

describe("UX-12 fechas México", () => {
  it("no cambia fechas simples y convierte instantes UTC", () => {
    expect(formatearFecha("2026-10-09")).toBe("09/10/2026");
    expect(formatearFechaHora("2026-10-09T02:30:00Z")).toBe("08/10/2026 20:30");
    expect(hoyMexico(new Date("2026-10-09T02:30:00Z"))).toBe("2026-10-08");
  });
});
