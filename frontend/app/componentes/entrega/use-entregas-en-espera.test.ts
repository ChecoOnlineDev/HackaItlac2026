import { beforeEach, describe, expect, it, vi } from "vitest";
vi.mock("~/api/practica", () => ({ practicaActiva: () => false }));
vi.mock("~/api/cliente", () => ({ apiGet: vi.fn() }));
vi.mock("~/componentes/ui/aviso", () => ({ aviso: vi.fn() }));
vi.mock("~/componentes/dominio/sonido", () => ({ reproducir: vi.fn() }));
import { guardarEntregasEnEspera, leerEntregasEnEspera } from "./use-entregas-en-espera";
import type { BorradorEntrega } from "./borrador";

let datos: Map<string, string>;
beforeEach(() => {
  datos = new Map();
  vi.stubGlobal("localStorage", { getItem: (k: string) => datos.get(k) ?? null, setItem: (k: string, v: string) => datos.set(k, v) });
  vi.stubGlobal("window", { dispatchEvent: vi.fn() });
});
const borrador = (usuarioId: string, idCliente = "uno") => ({ version: 1, usuarioId, idCliente, paso: "aprobacion", renglones: [{ codigo: "CASCO", cantidad: 1 }], autorizacion: { id: "autorizacion", estado: "PENDIENTE", codigos: ["CASCO"], vence_en: "2026-10-09T07:00:00Z" } } as BorradorEntrega);
describe("DE-15 cola local de entregas", () => {
  it("otro usuario no lee la captura ni los datos del trabajador", () => {
    guardarEntregasEnEspera([borrador("ana")]);
    expect(leerEntregasEnEspera("pedro")).toEqual([]);
    expect(leerEntregasEnEspera("ana")).toHaveLength(1);
  });
  it("una falla al guardar se informa para impedir que se pierda la captura activa", () => {
    vi.stubGlobal("localStorage", { setItem: () => { throw new Error("Cuota agotada"); } });
    expect(guardarEntregasEnEspera([borrador("ana")])).toBe(false);
  });
  it("datos dañados no hacen fallar el arranque", () => {
    datos.set("imhotep.borrador.entregas.en-espera.v1", "contenido dañado");
    expect(leerEntregasEnEspera("ana")).toEqual([]);
  });
  it("recupera como máximo diez capturas aunque el almacenamiento esté alterado", () => {
    const once = Array.from({ length: 11 }, (_, i) => borrador("ana", String(i)));
    expect(guardarEntregasEnEspera(once)).toBe(false);
    datos.set("imhotep.borrador.entregas.en-espera.v1", JSON.stringify(once));
    expect(leerEntregasEnEspera("ana")).toHaveLength(10);
  });
});
