import { HomeIcon, LogOutIcon } from "lucide-react";
import { useState } from "react";
import { Link, useLocation } from "react-router";

import { Avatar } from "~/componentes/ui/avatar";
import { Boton } from "~/componentes/ui/boton";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
} from "~/components/ui/sidebar";
import { InterruptorTutorial } from "~/componentes/tutorial/interruptor-tutorial";
import { ConfirmarSalida } from "./confirmar-salida";
import { InstalarApp } from "./instalar-app";
import { EncabezadoGrupo, PanelGrupo } from "./grupo-menu";
import { agruparMenu, idActivo, idGrupoActivo, menuPermitido, type ElementoMenu } from "~/sesion/menu";
import { useGruposAbiertos } from "~/sesion/menu-estado";
import { useContadores } from "~/sesion/contadores";
import { useSesionActiva } from "~/sesion/sesion";

/** Estado de la opción: activa (la sección donde estás) con contorno azul, y un hover más suave. */
const CLASE_OPCION =
  "h-auto min-h-10 rounded-xl py-2 text-sm transition-colors hover:bg-accent/60 data-active:bg-accent data-active:font-semibold data-active:text-marino data-active:ring-1 data-active:ring-primary data-active:hover:bg-accent";

function Elemento({ elemento, activo, contador }: { elemento: ElementoMenu; activo: boolean; contador?: number }) {
  return (
    <SidebarMenuItem>
      <SidebarMenuButton
        isActive={activo}
        className={`${CLASE_OPCION} [&>span:last-child]:whitespace-normal`}
        render={<Link to={elemento.ruta} aria-current={activo ? "page" : undefined} />}
      >
        <elemento.icono aria-hidden="true" className={activo ? "size-4.5 text-primary" : "size-4.5"} />
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
  const permitidos = menuPermitido(puedeAlguno);
  const grupos = agruparMenu(permitidos);
  const { pathname } = useLocation();
  const activoId = idActivo(permitidos, pathname);
  const { abierto, alternar } = useGruposAbiertos(idGrupoActivo(grupos, activoId));

  return (
    <SidebarProvider>
      <Sidebar collapsible="none" className="sticky top-0 h-dvh border-r">
        <SidebarHeader className="flex-row items-center gap-3 p-4">
          <img src="/logo-imhotep.png" alt="" width={44} height={41} className="h-auto w-11" />
          <div className="min-w-0">
            <p className="text-base font-semibold text-marino">IMHOTEP</p>
            <p className="text-xs text-muted-foreground">{sesion.almacen?.nombre ?? "Todos los almacenes"}</p>
          </div>
        </SidebarHeader>
        <SidebarContent className="px-2">
          <SidebarGroup>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    isActive={pathname === "/"}
                    className={CLASE_OPCION}
                    render={<Link to="/" aria-current={pathname === "/" ? "page" : undefined} />}
                  >
                    <HomeIcon aria-hidden="true" className="size-4.5" />
                    <span>Inicio</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
          {grupos.map(({ id, titulo, elementos }) => (
            <SidebarGroup key={id}>
              <EncabezadoGrupo
                id={id}
                titulo={titulo}
                abierto={abierto(id)}
                activo={elementos.some((e) => e.id === activoId)}
                alAlternar={() => alternar(id)}
              />
              <PanelGrupo id={id} abierto={abierto(id)}>
                <SidebarGroupContent>
                  <SidebarMenu>
                    {elementos.map((e) => (
                      <Elemento
                        key={e.id}
                        elemento={e}
                        activo={e.id === activoId}
                        contador={e.contador ? contadores[e.contador] : undefined}
                      />
                    ))}
                  </SidebarMenu>
                </SidebarGroupContent>
              </PanelGrupo>
            </SidebarGroup>
          ))}
        </SidebarContent>
        <SidebarFooter className="gap-3 border-t p-4">
          <div className="flex items-center gap-3">
            <Avatar nombre={sesion.usuario.nombre} tamano="sm" />
            <div className="min-w-0">
              <p className="text-sm leading-tight font-semibold">{sesion.usuario.nombre}</p>
              <p className="text-xs text-muted-foreground">{sesion.rol.nombre}</p>
            </div>
          </div>
          <InstalarApp />
          <InterruptorTutorial />
          <Boton variante="contorno" onClick={() => setConfirmandoSalida(true)}>
            <LogOutIcon aria-hidden="true" />
            Salir
          </Boton>
        </SidebarFooter>
      </Sidebar>
      <SidebarInset>
        <main className="mx-auto w-full max-w-6xl flex-1 p-6 xl:p-8">{children}</main>
      </SidebarInset>
      <ConfirmarSalida abierta={confirmandoSalida} alCambiar={setConfirmandoSalida} />
    </SidebarProvider>
  );
}
