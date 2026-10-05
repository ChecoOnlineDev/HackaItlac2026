import { cn } from "cn";
import { LogOutIcon, MenuIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router";

import { ConfirmarSalida } from "~/componentes/navegacion/confirmar-salida";
import { MenuHoja } from "~/componentes/navegacion/menu-hoja";
import { Pantalla } from "~/componentes/pantalla";
import { Boton } from "~/componentes/ui/boton";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { useEsEscritorio } from "~/hooks/use-escritorio";
import { useContadores } from "~/sesion/contadores";
import { elementosDeInicio, menuPermitido, type ElementoMenu } from "~/sesion/menu";
import { useSesionActiva } from "~/sesion/sesion";

function BotonInicio({ elemento, contador, ultimoImpar, esFlujo }: { elemento: ElementoMenu; contador?: number; ultimoImpar: boolean; esFlujo: boolean }) {
  return (
    <Link
      to={elemento.ruta}
      // En el inicio del almacenista se precargan en segundo plano las pantallas de su flujo.
      prefetch={esFlujo ? "render" : "intent"}
      className={cn(
        "relative flex min-h-28 flex-col items-center justify-center gap-2.5 rounded-2xl p-4 text-center text-base font-semibold shadow-xs transition-colors select-none active:translate-y-px",
        esFlujo
          ? "bg-primary text-primary-foreground hover:bg-primary/90"
          : "border border-border bg-accent text-marino hover:bg-accent/70",
        ultimoImpar && "col-span-2 md:col-span-1",
      )}
    >
      <elemento.icono aria-hidden="true" className="size-8" strokeWidth={2} />
      <span>{elemento.titulo}</span>
      {contador ? (
        <span
          aria-label={`${contador} por atender`}
          className="absolute top-2 right-2 inline-flex min-w-8 items-center justify-center rounded-full bg-white px-2 py-0.5 text-sm font-bold text-marino tabular-nums ring-2 ring-marino/20"
        >
          {contador}
        </span>
      ) : null}
    </Link>
  );
}

/** Inicio según los permisos: botones grandes para operar, o las secciones de gestión del rol. */
export default function Inicio() {
  const { sesion, puede, puedeAlguno } = useSesionActiva();
  const [confirmandoSalida, setConfirmandoSalida] = useState(false);
  const contadores = useContadores();
  const esEscritorio = useEsEscritorio();
  const [menuAbierto, setMenuAbierto] = useState(false);

  const elementos = elementosDeInicio(menuPermitido(puedeAlguno));
  const nombreAlmacen = sesion.almacen?.nombre ?? (puede("almacenes.todos") ? "Todos los almacenes" : sesion.rol.nombre);

  useEffect(() => {
    document.title = "Inicio · IMHOTEP";
  }, []);

  // Los botones azules son las operaciones del almacén; quien no opera uno (Compras, RH) ve botones suaves.
  const operaAlmacen = elementos.some((e) => e.inicio === "flujo" && e.id !== "consultar");

  const cuadricula = (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
      {elementos.map((e, i) => (
        <BotonInicio
          key={e.id}
          elemento={e}
          esFlujo={operaAlmacen && e.inicio === "flujo"}
          contador={e.contador ? contadores[e.contador] : undefined}
          ultimoImpar={i === elementos.length - 1 && elementos.length % 2 === 1}
        />
      ))}
    </div>
  );

  if (esEscritorio) {
    return (
      <Pantalla titulo={`Hola, ${sesion.usuario.nombre}`} descripcion={`${nombreAlmacen}. ¿Qué quieres hacer?`}>
        {elementos.length ? cuadricula : <EstadoVacio titulo="Todavía no tienes pantallas asignadas" descripcion="Pídele a tu supervisor que revise los permisos de tu rol." />}
      </Pantalla>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-sm text-muted-foreground">Hola, {sesion.usuario.nombre}</p>
          <h1 className="text-balance">{nombreAlmacen}</h1>
        </div>
        <div className="flex shrink-0 gap-2">
          <Boton variante="contorno" onClick={() => setMenuAbierto(true)}>
            <MenuIcon aria-hidden="true" />
            Menú
          </Boton>
          <Boton variante="contorno" aria-label="Salir" onClick={() => setConfirmandoSalida(true)}>
            <LogOutIcon aria-hidden="true" />
          </Boton>
        </div>
      </header>
      {elementos.length ? cuadricula : <EstadoVacio titulo="Todavía no tienes pantallas asignadas" descripcion="Pídele a tu supervisor que revise los permisos de tu rol." />}
      <MenuHoja abierta={menuAbierto} alCambiar={setMenuAbierto} />
      <ConfirmarSalida abierta={confirmandoSalida} alCambiar={setConfirmandoSalida} />
    </div>
  );
}
