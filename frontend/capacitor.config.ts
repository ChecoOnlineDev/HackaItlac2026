import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "mx.imhotep.almacen",
  appName: "IMHOTEP",
  webDir: "build/client",
  loggingBehavior: "none",
  server: { androidScheme: "https" },
  plugins: {
    CapacitorHttp: { enabled: true },
    // La sesión conserva HttpOnly; nunca se copia a document.cookie.
    CapacitorCookies: { enabled: false },
  },
};

export default config;
