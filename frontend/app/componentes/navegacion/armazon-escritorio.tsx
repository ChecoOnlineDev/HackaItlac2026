import { HomeIcon, LogOutIcon } from "lucide-react";
import { useState } from "react";
import { NavLink, useLocation } from "react-router";

import { Avatar } from "~/componentes/ui/avatar";
import { Boton } from "~/componentes/ui/boton";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
} from "~/components/ui/sidebar";
import { ConfirmarSalida } from "./confirmar-salida";
import { InstalarApp } from "./instalar-app";
import { agruparMenu, menuPermitido, type ElementoMenu } from "~/sesion/menu";
import { useContadores } from "~/sesion/contadores";
import { useSesionActiva } from "~/sesion/sesion";

function Elemento({ elemento, contador }: { elemento: ElementoMenu; contador?: number }) {
  const { pathname } = useLocation();
  const activo = elemento.prefijoActivo
    ? pathname.startsWith(elemento.prefijoActivo) && !(elemento.id === "trabajadores" && pathname === "/trabajadores/nuevo")
    : pathname === elemento.ruta;
  return (
    <SidebarMenuItem>
      <SidebarMenuButton size="lg" isActive={activo} className="text-base" render={<NavLink to={elemento.ruta} end />}>
        <elemento.icono aria-hidden="true" className="size-5" />
        <span>{elemento.titulo}</span>
      </SidebarMenuButton>
      {contador ? <SidebarMenuBadge className="bg-primary text-primary-foreground">{contador}</SidebarMenuBadge> : null}
    </SidebarMenuItem>
  );
}

/** Navegación de computadora: menú lateral con las secciones que permiten los permisos. */
export function ArmazonEscritorio({ children }: { children: React.ReactNode }) {
  const { sesion, puedeAlguno } = useSesionActiva();
  const [confirmandoSalida, setConfirmandoSalida] = useState(false);
  const contadores = useContadores();
  const grupos = agruparMenu(menuPermitido(puedeAlguno));

  return (
    <SidebarProvider>
      <Sidebar collapsible="none" className="sticky top-0 h-dvh border-r">
        <SidebarHeader className="flex-row items-center gap-3 p-4">
          <img src="/logo-imhotep.png" alt="" width={44} height={41} className="h-auto w-11" />
          <div className="min-w-0">
            <p className="text-base font-bold text-marino">IMHOTEP</p>
            <p className="truncate text-sm text-muted-foreground">{sesion.almacen?.nombre ?? "Todos los almacenes"}</p>
          </div>
        </SidebarHeader>
        <SidebarContent className="px-2">
          <SidebarGroup>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton size="lg" className="text-base" render={<NavLink to="/" end />}>
                    <HomeIcon aria-hidden="true" className="size-5" />
                    <span>Inicio</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
          {grupos.map(({ grupo, elementos }) => (
            <SidebarGroup key={grupo}>
              <SidebarGroupLabel className="text-xs font-semibold tracking-wide uppercase">{grupo}</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {elementos.map((e) => (
                    <Elemento
                      key={e.id}
                      elemento={e}
                      contador={e.contador ? contadores[e.contador] : undefined}
                    />
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          ))}
        </SidebarContent>
        <SidebarFooter className="gap-3 border-t p-4">
          <div className="flex items-center gap-3">
            <Avatar nombre={sesion.usuario.nombre} tamano="sm" />
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">{sesion.usuario.nombre}</p>
              <p className="truncate text-xs text-muted-foreground">{sesion.rol.nombre}</p>
            </div>
          </div>
          <InstalarApp />
          <Boton variante="contorno" onClick={() => setConfirmandoSalida(true)}>
            <LogOutIcon aria-hidden="true" />
            Salir
          </Boton>
        </SidebarFooter>
      </Sidebar>
      <SidebarInset>
        <main className="mx-auto w-full max-w-6xl flex-1 p-8">{children}</main>
      </SidebarInset>
      <ConfirmarSalida abierta={confirmandoSalida} alCambiar={setConfirmandoSalida} />
    </SidebarProvider>
  );
}
