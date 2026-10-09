import { spawnSync } from "node:child_process";
import { loadEnv } from "vite";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";

const require = createRequire(import.meta.url);
const router = resolve(dirname(require.resolve("@react-router/dev/package.json")), "bin.cjs");
const capacitor = resolve(dirname(require.resolve("@capacitor/cli/package.json")), "bin/capacitor");

const entorno = { ...loadEnv("android", process.cwd(), "VITE_"), ...process.env };
const origen = entorno.VITE_API_ORIGEN;
let url;
try { url = new URL(origen); } catch { /* El mensaje siguiente explica cómo corregirlo. */ }
if (!url || url.protocol !== "https:" || url.username || url.password || url.pathname !== "/" || url.search || url.hash) {
  console.error("Configura VITE_API_ORIGEN con el origen HTTPS del servidor en .env.android.local.");
  process.exit(1);
}

// Comandos fijos; la configuración viaja por el entorno, nunca como texto de shell.
for (const args of [[router, "build", "--mode", "android"], [capacitor, "sync", "android"]]) {
  const resultado = spawnSync(process.execPath, args, {
    stdio: "inherit", env: entorno,
  });
  if (resultado.error) throw resultado.error;
  if (resultado.status !== 0) process.exit(resultado.status ?? 1);
}
