import { cn } from "cn";
import { LockIcon, ShieldAlertIcon } from "lucide-react";

import { Switch } from "~/components/ui/switch";
import { Boton } from "~/componentes/ui/boton";
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
  /** «Activar todos» o «Quitar todos» de un grupo: solo mueve los interruptores en pantalla, no guarda. */
  alMoverGrupo: (grupoId: string, claves: string[], activar: boolean) => void;
  /** «Activar todo» o «Quitar todo» de todo el rol. */
  alMoverTodo: (activar: boolean) => void;
  /** Lo que el último botón no pudo mover o movió de más, por grupo (`todo` para los botones de arriba). */
  avisos: Readonly<Record<string, readonly string[]>>;
}

function Avisos({ lineas, id }: { lineas: readonly string[] | undefined; id: string }) {
  if (!lineas || lineas.length === 0) return null;
  return (
    <div id={id} role="status" className="flex flex-col gap-0.5 rounded-xl bg-accent px-3 py-2 text-xs text-marino">
      {lineas.map((t) => (
        <p key={t}>{t}</p>
      ))}
    </div>
  );
}

/**
 * La matriz de permisos de un rol, agrupada por módulo. Cada renglón es un interruptor con la
 * descripción del permiso en lenguaje de persona y su clave técnica en segundo plano. Los permisos
 * de información reservada llevan su advertencia; el servidor vuelve a validar todo al guardar.
 */
export function MatrizPermisos({ catalogo, activos, guardados, alCambiar, razonBloqueo, deshabilitada, alMoverGrupo, alMoverTodo, avisos }: Propiedades) {
  const grupos = agruparPermisos(catalogo);
  const hayMovibles = catalogo.some((p) => razonBloqueo(p.clave) === null);
  return (
    <div className="flex flex-col gap-4">
      {hayMovibles ? (
        <div className="flex flex-col gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <Boton variante="contorno" disabled={deshabilitada} onClick={() => alMoverTodo(true)}>
              Activar todo
            </Boton>
            <Boton variante="contorno" disabled={deshabilitada} onClick={() => alMoverTodo(false)}>
              Quitar todo
            </Boton>
            <span className="text-xs text-muted-foreground">Solo mueve los interruptores: nada se guarda hasta que lo confirmes.</span>
          </div>
          <Avisos id="avisos-todo" lineas={avisos.todo} />
        </div>
      ) : null}
    <div className="grid gap-4 lg:grid-cols-2">
      {grupos.map((g) => {
        const encendidos = g.permisos.filter((p) => activos.has(p.clave)).length;
        const completo = encendidos === g.permisos.length;
        // Un grupo con todos los interruptores bloqueados no ofrece el botón.
        const sePuedeMover = g.permisos.some((p) => razonBloqueo(p.clave) === null);
        const claves = g.permisos.map((p) => p.clave);
        return (
          <section key={g.id} aria-labelledby={`grupo-${g.id}`} className="flex flex-col rounded-2xl border bg-card shadow-xs">
            <header className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2 border-b px-4 py-3">
              <div className="flex min-w-0 flex-col">
                <h2 id={`grupo-${g.id}`} className="text-base font-semibold text-marino">
                  {g.titulo}
                </h2>
                <span className="text-xs text-muted-foreground tabular-nums">
                  {encendidos} de {g.permisos.length} activos
                </span>
              </div>
              {sePuedeMover ? (
                <Boton
                  variante="contorno"
                  disabled={deshabilitada}
                  aria-label={`${completo ? "Quitar" : "Activar"} todos los permisos de ${g.titulo}`}
                  aria-describedby={avisos[g.id]?.length ? `avisos-${g.id}` : undefined}
                  onClick={() => alMoverGrupo(g.id, claves, !completo)}
                >
                  {completo ? "Quitar todos" : "Activar todos"}
                </Boton>
              ) : null}
            </header>
            {avisos[g.id]?.length ? (
              <div className="border-b px-4 py-2">
                <Avisos id={`avisos-${g.id}`} lineas={avisos[g.id]} />
              </div>
            ) : null}
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
    </div>
  );
}
