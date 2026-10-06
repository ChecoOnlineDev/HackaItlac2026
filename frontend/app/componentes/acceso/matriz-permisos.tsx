import { cn } from "cn";
import { LockIcon, ShieldAlertIcon } from "lucide-react";

import { Switch } from "~/components/ui/switch";
import { Insignia } from "~/componentes/ui/insignia";
import { AVISO_RESERVADO, agruparPermisos, type PermisoInfo } from "./tipos";

interface Propiedades {
  catalogo: readonly PermisoInfo[];
  /** Permisos que el rol tendría con los cambios de la pantalla. */
  activos: ReadonlySet<string>;
  /** Permisos que el rol tiene guardados: lo que cambió se marca. */
  guardados: ReadonlySet<string>;
  alCambiar: (clave: string, activo: boolean) => void;
  /** Si no se puede cambiar un permiso, la razón en español llano; `null` si sí se puede. */
  razonBloqueo: (clave: string) => string | null;
  /** Bloquea toda la matriz (por ejemplo, mientras se guarda). */
  deshabilitada?: boolean;
}

/**
 * La matriz de permisos de un rol, agrupada por módulo. Cada renglón es un interruptor con la
 * descripción del permiso en lenguaje de persona y su clave técnica en segundo plano. Los permisos
 * de información reservada llevan su advertencia; el servidor vuelve a validar todo al guardar.
 */
export function MatrizPermisos({ catalogo, activos, guardados, alCambiar, razonBloqueo, deshabilitada }: Propiedades) {
  const grupos = agruparPermisos(catalogo);
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {grupos.map((g) => {
        const encendidos = g.permisos.filter((p) => activos.has(p.clave)).length;
        return (
          <section key={g.id} aria-labelledby={`grupo-${g.id}`} className="flex flex-col rounded-2xl border bg-card shadow-xs">
            <header className="flex items-center justify-between gap-3 border-b px-4 py-3">
              <h2 id={`grupo-${g.id}`} className="text-base font-semibold text-marino">
                {g.titulo}
              </h2>
              <span className="text-xs text-muted-foreground tabular-nums">
                {encendidos} de {g.permisos.length}
              </span>
            </header>
            <ul className="divide-y">
              {g.permisos.map((p) => {
                const activo = activos.has(p.clave);
                const cambio = activo !== guardados.has(p.clave);
                const razon = razonBloqueo(p.clave);
                const idTexto = `permiso-${p.clave}`;
                const aviso = p.es_de_informacion ? (AVISO_RESERVADO[p.clave] ?? "Muestra información reservada.") : null;
                return (
                  <li key={p.clave} className={cn("flex flex-col gap-2 px-4 py-3", cambio && "bg-accent/60")}>
                    <div className="flex items-start gap-3">
                      <div className="flex min-h-10 min-w-10 items-center justify-center">
                        <Switch
                          checked={activo}
                          onCheckedChange={(valor) => alCambiar(p.clave, valor)}
                          disabled={deshabilitada || razon !== null}
                          aria-labelledby={idTexto}
                          aria-describedby={razon ? `${idTexto}-razon` : undefined}
                        />
                      </div>
                      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                          <span id={idTexto} className="text-sm font-medium text-foreground">
                            {p.descripcion}
                          </span>
                          {p.es_de_informacion ? (
                            <Insignia estado="info" className="text-[11px]">
                              Información reservada
                            </Insignia>
                          ) : null}
                          {!p.mvp ? <Insignia estado="neutra" className="text-[11px]">Aún no se usa</Insignia> : null}
                          {cambio ? (
                            <Insignia estado="info" className="text-[11px]">
                              {activo ? "Se agrega" : "Se quita"}
                            </Insignia>
                          ) : null}
                        </div>
                        <code className="break-all font-sans text-xs text-muted-foreground">{p.clave}</code>
                      </div>
                    </div>
                    {aviso && activo ? (
                      <p className="ml-[3.25rem] flex items-start gap-1.5 text-xs text-foreground">
                        <ShieldAlertIcon aria-hidden="true" className="mt-0.5 size-3.5 shrink-0 text-marino" />
                        {aviso}
                      </p>
                    ) : null}
                    {razon ? (
                      <p id={`${idTexto}-razon`} className="ml-[3.25rem] flex items-start gap-1.5 text-xs text-muted-foreground">
                        <LockIcon aria-hidden="true" className="mt-0.5 size-3.5 shrink-0" />
                        {razon}
                      </p>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
