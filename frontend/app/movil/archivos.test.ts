import { beforeEach, expect, it, vi } from "vitest";
import { compartirArchivo, limpiarCompartidos } from "./archivos";

const fs = vi.hoisted(() => ({
  readdir: vi.fn(), rmdir: vi.fn(), writeFile: vi.fn(),
}));
const compartir = vi.hoisted(() => vi.fn());
vi.mock("@capacitor/filesystem", () => ({ Filesystem: fs, Directory: { Cache: "CACHE" } }));
vi.mock("@capacitor/share", () => ({ Share: { share: compartir } }));

beforeEach(() => {
  vi.clearAllMocks();
  fs.readdir.mockResolvedValue({ files: [] });
  fs.writeFile.mockResolvedValue({ uri: "file:///cache/exportacion.csv" });
  compartir.mockResolvedValue({ activityType: "" });
});

it("OF-01 compartir retiene el archivo cuando el selector vuelve antes que el receptor", async () => {
  vi.stubGlobal("FileReader", class {
    result = "data:text/csv;base64,Zm9saW8=";
    onload: (() => void) | null = null;
    readAsDataURL() { this.onload?.(); }
  });
  await compartirArchivo(new Blob(["folio"]), "../vales.csv");
  expect(compartir).toHaveBeenCalledWith({ title: ".._vales.csv", files: ["file:///cache/exportacion.csv"] });
  expect(fs.rmdir).not.toHaveBeenCalled();
  expect(fs.writeFile.mock.calls[0][0].path).toMatch(/^compartidos\/\d+-[0-9a-f-]{36}\/\.\._vales.csv$/);
  vi.unstubAllGlobals();
});

it("OF-01 limpia exportaciones antiguas dentro de la carpeta privada y conserva las recientes", async () => {
  const ahora = Date.now();
  const uuid = "12345678-1234-1234-1234-123456789abc";
  fs.readdir.mockResolvedValue({ files: [
    { name: `${ahora - 7_200_000}-${uuid}` },
    { name: `${ahora}-${uuid}` },
    { name: "../../otra-carpeta" },
  ] });
  await limpiarCompartidos();
  expect(fs.rmdir).toHaveBeenCalledExactlyOnceWith({
    path: `compartidos/${ahora - 7_200_000}-${uuid}`, directory: "CACHE", recursive: true,
  });
});
