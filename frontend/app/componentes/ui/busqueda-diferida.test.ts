import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Arnés de hooks sin DOM: conserva las celdas entre renders y ejecuta los efectos con su limpieza.
const hooks = vi.hoisted(() => ({ celdas: [] as unknown[], cursor: 0, efectos: [] as (() => void)[] }));
vi.mock("react", () => ({
  useState: <T>(inicial: T) => {
    const i = hooks.cursor++;
    if (!(i in hooks.celdas)) hooks.celdas[i] = inicial;
    return [hooks.celdas[i], (valor: T | ((anterior: T) => T)) => { hooks.celdas[i] = typeof valor === "function" ? (valor as (anterior: T) => T)(hooks.celdas[i] as T) : valor; }];
  },
  useRef: <T>(valor: T) => {
    const i = hooks.cursor++;
    if (!(i in hooks.celdas)) hooks.celdas[i] = { current: valor };
    return hooks.celdas[i];
  },
  useCallback: <T>(fn: T) => fn,
  useEffect: (efecto: () => (() => void) | undefined, deps: unknown[]) => {
    const i = hooks.cursor++;
    const anterior = hooks.celdas[i] as unknown[] | undefined;
    if (!anterior || deps.some((v, n) => !Object.is(v, anterior[n]))) {
      hooks.efectos[i]?.();
      hooks.celdas[i] = deps;
      hooks.efectos[i] = efecto() ?? (() => {});
    }
  },
}));
import { useBusquedaDiferida } from "./busqueda-diferida";

beforeEach(() => { hooks.celdas = []; hooks.efectos = []; hooks.cursor = 0; vi.useFakeTimers(); });
afterEach(() => { hooks.efectos.forEach((limpiar) => limpiar?.()); vi.useRealTimers(); });

describe("UX-01/02 búsqueda diferida", () => {
  it("espera 300 ms desde la última tecla y no pide con un carácter", async () => {
    const pedir = vi.fn(async (texto: string) => [texto]);
    const render = (texto: string) => { hooks.cursor = 0; return useBusquedaDiferida(texto, pedir); };
    render("j");
    await vi.advanceTimersByTimeAsync(500);
    expect(pedir).not.toHaveBeenCalled();
    expect(render("j").estado).toBe("corto");
    render("ju");
    await vi.advanceTimersByTimeAsync(200);
    render("juan");
    await vi.advanceTimersByTimeAsync(299);
    expect(pedir).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1);
    expect(pedir).toHaveBeenCalledTimes(1);
    expect(render("juan").resultado).toEqual(["juan"]);
  });
  it("Enter consulta sin espera", async () => {
    const pedir = vi.fn(async () => ["Juan"]);
    const render = () => { hooks.cursor = 0; return useBusquedaDiferida("juan", pedir); };
    render().buscarYa();
    render();
    await vi.advanceTimersByTimeAsync(0);
    expect(pedir).toHaveBeenCalledTimes(1);
  });
  it("aborta la anterior y descarta su respuesta tardía aunque el adaptador ignore el aborto", async () => {
    let vieja: ((valor: string[]) => void) | undefined;
    let senalVieja: AbortSignal | undefined;
    const pedir = vi.fn((texto: string, signal: AbortSignal): Promise<string[]> => texto === "jua" ? new Promise((resolve) => { vieja = resolve; senalVieja = signal; }) : Promise.resolve(["Juan"]));
    const render = (texto: string) => { hooks.cursor = 0; return useBusquedaDiferida(texto, pedir); };
    render("jua");
    await vi.advanceTimersByTimeAsync(300);
    render("juan");
    expect(senalVieja!.aborted).toBe(true);
    await vi.advanceTimersByTimeAsync(300);
    vieja!(["Respuesta vieja"]);
    await Promise.resolve();
    expect(render("juan").resultado).toEqual(["Juan"]);
    expect(render("juan").textoDelResultado).toBe("juan");
  });
});
