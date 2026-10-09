import { describe, expect, it } from "vitest";
import { filasPdf, svgDelVale } from "./pdf-vale";
import type { RenglonValeApi } from "~/componentes/entrega/tipos";

describe("BT-07 BT-09 proyección de PDF", () => {
  it("produce SVG autónomo con namespace para decodificar el QR como imagen", async () => {
    const svg = await svgDelVale("token-prueba");
    expect(svg).toMatch(/^<svg xmlns="http:\/\/www.w3.org\/2000\/svg" /);
    expect(svg).toContain("<path");
  });
  it("conserva acentos y serie pero nunca valores reservados", () => {
    const fila = {renglon:1,codigo_articulo:"COD-1",articulo:"Máquina eléctrica",marca:"Señal",codigo_pieza:"PIEZA-1",numero_serie:"SERIE-1",cantidad:2,condicion:"DANADO",costo_unitario:"99999.99",importe:"199999.98",curp:"CURP-RESERVADA",nss:"NSS-RESERVADO"} as unknown as RenglonValeApi;
    const texto = JSON.stringify(filasPdf([fila]));
    expect(texto).toContain("Máquina eléctrica"); expect(texto).toContain("Señal"); expect(texto).toContain("SERIE-1");
    for(const reservado of ["99999.99","199999.98","CURP-RESERVADA","NSS-RESERVADO","costo_unitario"]) expect(texto).not.toContain(reservado);
  });
  it("proyecta 500 renglones completos sin modificar sus DTO", () => {
    const originales = Array.from({length:500}, (_,i) => ({renglon:i+1,codigo_articulo:`A${i}`,articulo:"Artículo",cantidad:1,condicion:null}) as RenglonValeApi);
    const resultado = filasPdf(originales);
    expect(resultado).toHaveLength(500); expect(resultado.at(-1)?.[0]).toBe(500); expect(originales.at(-1)?.renglon).toBe(500);
  });
});
