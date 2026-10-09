import { beforeEach, describe, expect, it, vi } from "vitest";

const plataforma = vi.hoisted(() => ({ nativa: false }));
vi.mock("~/movil/plataforma", () => ({
  esAppNativa: () => plataforma.nativa,
  origenApi: () => plataforma.nativa ? "https://imhotep.example" : "",
  versionApp: async () => plataforma.nativa ? "0.1.0" : null,
}));
vi.mock("./practica", () => ({ practicaActiva: () => false, recordarSesionPractica: vi.fn() }));
vi.mock("./red", () => ({ marcarConexion: vi.fn() }));

beforeEach(() => { vi.resetModules(); vi.restoreAllMocks(); plataforma.nativa = false; });
const json = (datos: unknown, status = 200) => new Response(JSON.stringify(datos), { status });

describe("OF-01 cliente compartido", () => {
  it("conserva rutas relativas y cookies en la web", async () => {
    const pedir = vi.fn().mockResolvedValue(json({ ok: true }));
    vi.stubGlobal("fetch", pedir);
    const { apiGet } = await import("./cliente");
    await apiGet("/sesion");
    expect(pedir).toHaveBeenCalledWith("/api/sesion", expect.objectContaining({ credentials: "include" }));
    expect(pedir.mock.calls[0][1].headers).not.toHaveProperty("X-App-Version");
  });
  it("OF-02 manda la versión del APK y el origen en Android", async () => {
    plataforma.nativa = true;
    const pedir = vi.fn().mockResolvedValue(json({ ok: true }));
    vi.stubGlobal("fetch", pedir);
    const { apiGet, construirUrl } = await import("./cliente");
    expect(construirUrl("/api/vales", { q: "Juan Pérez" })).toBe("https://imhotep.example/api/vales?q=Juan+P%C3%A9rez");
    await apiGet("/sesion");
    expect(pedir).toHaveBeenCalledWith("https://imhotep.example/api/sesion", expect.objectContaining({ headers: expect.objectContaining({ "X-App-Version": "0.1.0" }) }));
  });
  it("AC-16 dos 401 concurrentes comparten una renovación", async () => {
    plataforma.nativa = true;
    let renovada = false;
    const pedir = vi.fn(async (ruta: string) => {
      if (ruta.endsWith("/sesion/refresh")) {
        await new Promise((resolve) => setTimeout(resolve, 5));
        renovada = true;
        return json({ permisos: [] });
      }
      return renovada ? json({ ok: true }) : json({ codigo: "TOKEN_VENCIDO", mensaje: "Venció" }, 401);
    });
    vi.stubGlobal("fetch", pedir);
    const { apiGet } = await import("./cliente");
    await Promise.all([apiGet("/primera"), apiGet("/segunda")]);
    expect(pedir.mock.calls.filter(([ruta]) => ruta.endsWith("/sesion/refresh"))).toHaveLength(1);
  });
  it("no serializa FormData ni impone Content-Type al fetch nativo", async () => {
    plataforma.nativa = true;
    const pedir = vi.fn().mockResolvedValue(json({ ok: true }));
    vi.stubGlobal("fetch", pedir);
    const { apiPost } = await import("./cliente");
    const datos = new FormData(); datos.set("foto", new Blob(["foto"]), "foto.png");
    await apiPost("/foto", datos);
    expect(pedir.mock.calls[0][1].body).toBe(datos);
    expect(pedir.mock.calls[0][1].headers).not.toHaveProperty("Content-Type");
  });
  it("OF-02 publica el aviso de actualización sin renovar la sesión", async () => {
    const ventana = new EventTarget();
    const avisar = vi.fn(); ventana.addEventListener("imhotep:actualizar-app", avisar);
    vi.stubGlobal("window", ventana);
    const pedir = vi.fn().mockResolvedValue(json({ codigo: "APP_DESACTUALIZADA", mensaje: "Actualiza" }, 426));
    vi.stubGlobal("fetch", pedir);
    const { apiGet } = await import("./cliente");
    await expect(apiGet("/sesion")).rejects.toMatchObject({ status: 426 });
    expect(avisar).toHaveBeenCalledOnce(); expect(pedir).toHaveBeenCalledOnce();
    vi.unstubAllGlobals();
  });
});
