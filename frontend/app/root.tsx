import { useEffect } from "react";
import {
  isRouteErrorResponse,
  Links,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
} from "react-router";

import type { Route } from "./+types/root";
import "./app.css";

import { BandaSinConexion } from "~/componentes/ui/banda-sin-conexion";
import { Cargando } from "~/componentes/ui/cargando";
import { EstadoError } from "~/componentes/ui/estado-error";
import { Toaster } from "~/components/ui/toast";
import { registrarServiceWorker } from "~/pwa/registrar";
import { SesionProvider } from "~/sesion/sesion";
import { IntegracionNativa } from "~/movil/integracion";

export const links: Route.LinksFunction = () => [
  { rel: "icon", type: "image/png", href: "/logo-imhotep.png" },
  { rel: "apple-touch-icon", href: "/apple-touch-icon.png" },
  { rel: "manifest", href: "/manifest.webmanifest" },
];

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <head>
        <meta charSet="utf-8" />
        {/* interactive-widget: en celular, el teclado reduce la pantalla en lugar de tapar el botón. */}
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1, viewport-fit=cover, interactive-widget=resizes-content"
        />
        <meta name="theme-color" content="#0054A6" />
        <meta name="description" content="Control de herramientas y equipo de protección personal: entregas, devoluciones y consultas." />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-title" content="IMHOTEP" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <title>IMHOTEP · Control de herramientas y EPP</title>
        <Meta />
        <Links />
      </head>
      <body>
        {children}
        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  );
}

/** Lo que se ve mientras la aplicación carga por primera vez. */
export function HydrateFallback() {
  return <Cargando variante="pantalla" />;
}

export default function App() {
  useEffect(() => {
    registrarServiceWorker();
  }, []);
  return (
    <IntegracionNativa><SesionProvider>
      <Toaster>
        <BandaSinConexion />
        <Outlet />
      </Toaster>
    </SesionProvider></IntegracionNativa>
  );
}

export function ErrorBoundary({ error }: Route.ErrorBoundaryProps) {
  const noEncontrada = isRouteErrorResponse(error) && error.status === 404;
  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center gap-4 p-6">
      <EstadoError
        mensaje={noEncontrada ? "No encontramos esa pantalla." : "Algo salió mal en esta pantalla."}
        alReintentar={() => window.location.assign("/")}
      />
      {import.meta.env.DEV && error instanceof Error ? (
        <pre className="w-full overflow-x-auto rounded-lg bg-muted p-3 text-xs">
          <code>{error.stack}</code>
        </pre>
      ) : null}
    </main>
  );
}
