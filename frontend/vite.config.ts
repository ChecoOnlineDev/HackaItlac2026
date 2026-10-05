import { reactRouter } from "@react-router/dev/vite";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

// En desarrollo, /api se reenvía al backend para que la cookie de sesión y la API
// sean del mismo origen (no se usa CORS). En producción lo entrega el mismo servidor.
const destinoApi = process.env.API_DESTINO ?? "http://127.0.0.1:21011";

export default defineConfig({
  plugins: [tailwindcss(), reactRouter()],
  resolve: {
    tsconfigPaths: true,
  },
  // Sin esto, Vite descubre las dependencias al abrir cada pantalla por primera vez y recarga
  // la página completa: en desarrollo, cada módulo nuevo se sentía lento y tosco.
  optimizeDeps: {
    entries: ["app/root.tsx", "app/routes/**/*.tsx"],
  },
  server: {
    port: 21010,
    strictPort: true,
    proxy: {
      "/api": { target: destinoApi },
    },
  },
});
