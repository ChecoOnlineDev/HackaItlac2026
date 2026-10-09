import { readFileSync } from "node:fs";
import { afterEach, describe, expect, it, vi } from "vitest";

const recibido = vi.hoisted(() => ({ blob: null as Blob | null }));
vi.mock("./credencial-png", () => ({ descargarBlob: vi.fn(async (blob: Blob) => { recibido.blob = blob; }), credencialComoPng: vi.fn() }));
import { descargarEtiquetasPdf } from "./pdf-etiquetas";

afterEach(() => vi.unstubAllGlobals());
describe("UX-05/07 PDF de etiquetas", () => {
  it("genera 1, 37 y 500 etiquetas en cada formato; las 500 pesan menos de 5 MB", async () => {
    const fuente = readFileSync(new URL("../../../public/fuentes/Poppins-Regular.ttf", import.meta.url));
    vi.stubGlobal("fetch", vi.fn(async () => new Response(fuente)));
    for (const formato of [9, 18, 30] as const) {
      for (const cantidad of [1, 37, 500]) {
        recibido.blob = null;
        const progreso = vi.fn();
        await descargarEtiquetasPdf(Array.from({ length: cantidad }, (_, i) => ({ codigo: `UX-Ñ/ALT ${i}`, texto: "Arnés de seguridad · talla M" })), { tipo: "piezas", formato, inicio: 1, signal: new AbortController().signal, progreso });
        const blob = recibido.blob as Blob | null;
        expect(blob).not.toBeNull();
        expect(blob!.size).toBeLessThan(5_000_000);
        const contenido = new TextDecoder().decode(await blob!.arrayBuffer());
        expect(contenido).toContain(`/Count ${Math.ceil(cantidad / formato)}`);
        expect(progreso).toHaveBeenLastCalledWith(Math.ceil(cantidad / formato), Math.ceil(cantidad / formato));
      }
    }
  }, 20000);
  it("cancelar impide descargar un PDF parcial", async () => {
    const fuente = readFileSync(new URL("../../../public/fuentes/Poppins-Regular.ttf", import.meta.url));
    vi.stubGlobal("fetch", vi.fn(async () => new Response(fuente)));
    const control = new AbortController();
    control.abort();
    recibido.blob = null;
    await expect(descargarEtiquetasPdf([{ codigo: "UX19", texto: "Equipo" }], { tipo: "piezas", formato: 18, inicio: 1, signal: control.signal, progreso: vi.fn() })).rejects.toMatchObject({ name: "AbortError" });
    expect(recibido.blob).toBeNull();
  });
});
