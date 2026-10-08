import { cn } from "cn";
import { HomeIcon } from "lucide-react";
import { useEffect, useRef } from "react";
import { Link, useLocation } from "react-router";

import { InterruptorTutorial } from "~/componentes/tutorial/interruptor-tutorial";
import { Hoja } from "~/componentes/ui/hoja";
import { armarMenu, idActivo, idEntradaActiva, menuPermitido, type EntradaMenu } from "~/sesion/menu";
import { useContadores } from "~/sesion/contadores";
import { useGruposAbiertos } from "~/sesion/menu-estado";
import { useSesion } from "~/sesion/sesion";
import { EncabezadoGrupo, PanelGrupo } from "./grupo-menu";
import { InstalarApp } from "./instalar-app";

/** Misma apariencia para toda opción; la activa lleva contorno azul, fondo suave y texto en azul marino. */
const BASE = "flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm font-medium transition-colors hover:bg-accent/60";
const ACTIVA = "bg-accent font-semibold text-marino ring-1 ring-primary hover:bg-accent";

/** Menú completo en una hoja (celular y tableta): todas las secciones que permiten los permisos. */
export function MenuHoja({ abierta, alCambiar }: { abierta: boolean; alCambiar: (abierta: boolean) => void }) {
  const { puedeAlguno } = useSesion();
  const { pathname } = useLocation();
  const permitidos = menuPermitido(puedeAlguno);
  const entradas = armarMenu(permitidos);
  const contadores = useContadores();
  const elActivo = idActivo(permitidos, pathname);
  const entradaActiva = idEntradaActiva(entradas, elActivo);
  // En Inicio se marca «inicio»; si no, la opción de un grupo (por su pantalla) o la entrada simple (por su sección).
  const activoId = pathname === "/" ? "inicio" : elActivo;
  const activa = useRef<HTMLAnchorElement | null>(null);
  const { abierto, alternar } = useGruposAbiertos(entradaActiva);
  const suma = (e: EntradaMenu) => e.contadores.reduce((total, c) => total + (contadores[c] ?? 0), 0) || undefined;

  // Al abrir, la opción activa queda a la vista aunque la lista sea larga.
  useEffect(() => {
    if (!abierta) return;
    const id = window.setTimeout(() => activa.current?.scrollIntoView({ block: "center" }), 60);
    return () => window.clearTimeout(id);
  }, [abierta]);

  const ref = (esActiva: boolean) => (nodo: HTMLAnchorElement | null) => {
    if (esActiva) activa.current = nodo;
  };

  return (
    <Hoja abierta={abierta} alCambiar={alCambiar} titulo="Menú">
      <nav aria-label="Secciones" className="flex flex-col gap-2">
        <Link
          ref={ref(activoId === "inicio")}
          to="/"
          onClick={() => alCambiar(false)}
          aria-current={activoId === "inicio" ? "page" : undefined}
          className={cn(BASE, activoId === "inicio" && ACTIVA)}
        >
          <HomeIcon aria-hidden="true" className="size-4.5 text-primary" />
          Inicio
        </Link>
        {entradas.map((entrada) => {
          if (!entrada.grupo) {
            const esActiva = entrada.id === entradaActiva && pathname !== "/";
            const cuenta = suma(entrada);
            return (
              <Link
                key={entrada.id}
                ref={ref(esActiva)}
                to={entrada.ruta}
                onClick={() => alCambiar(false)}
                aria-current={esActiva ? "page" : undefined}
                className={cn(BASE, "justify-between", esActiva && ACTIVA)}
              >
                <span className="flex items-center gap-3">
                  <entrada.icono aria-hidden="true" className="size-4.5 text-primary" />
                  {entrada.titulo}
                </span>
                {cuenta ? <span className="rounded-full bg-primary px-2 text-xs font-semibold text-primary-foreground">{cuenta}</span> : null}
              </Link>
            );
          }
          return (
            <div key={entrada.id} className="flex flex-col gap-1">
              <EncabezadoGrupo
                id={entrada.id}
                titulo={entrada.titulo}
                abierto={abierto(entrada.id)}
                activo={entrada.id === entradaActiva}
                alAlternar={() => alternar(entrada.id)}
              />
              <PanelGrupo id={entrada.id} abierto={abierto(entrada.id)}>
                <div className="flex flex-col gap-1">
                  {entrada.elementos.map((e) => {
                    const esActiva = e.id === activoId;
                    return (
                      <Link
                        key={e.id}
                        ref={ref(esActiva)}
                        to={e.ruta}
                        onClick={() => alCambiar(false)}
                        aria-current={esActiva ? "page" : undefined}
                        className={cn(BASE, esActiva && ACTIVA)}
                      >
                        <e.icono aria-hidden="true" className="size-4.5 text-primary" />
                        {e.titulo}
                      </Link>
                    );
                  })}
                </div>
              </PanelGrupo>
            </div>
          );
        })}
      </nav>
      <InstalarApp className="mt-5" />
      <InterruptorTutorial className="mt-3" alIniciar={() => alCambiar(false)} />
    </Hoja>
  );
}
