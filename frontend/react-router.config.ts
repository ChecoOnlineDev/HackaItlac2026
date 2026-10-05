import type { Config } from "@react-router/dev/config";

export default {
  // Aplicación de una sola página: la entrega el servidor de la API como archivos estáticos.
  ssr: false,
} satisfies Config;
