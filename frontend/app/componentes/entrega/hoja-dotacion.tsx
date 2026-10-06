import { cn } from "cn";
import { useEffect, useMemo, useState } from "react";

import { Checkbox } from "~/components/ui/checkbox";
import { Boton } from "~/componentes/ui/boton";
import { Hoja } from "~/componentes/ui/hoja";
import type { DotacionApi, RenglonDotacionApi } from "./tipos";

/** Lo que se agrega a la entrega: el código del artículo y lo que le falta. */
export interface DotacionElegida {
  codigo: string;
  cantidad: number;
}

interface PropiedadesHojaDotacion {
  abierta: boolean;
  alCambiar: (abierta: boolean) => void;
  dotacion: DotacionApi;
  /**
   * `consulta`: solo muestra lo que falta (paso del trabajador). `seleccion`: casillas para elegir qué
   * agregar a la entrega (paso de artículos). La dotación es una sugerencia: nada se agrega solo.
   */
  modo: "consulta" | "seleccion";
  /** Códigos de artículo (en mayúsculas) que ya están en la entrega en curso. */
  yaEnLista?: ReadonlySet<string>;
  alAgregar?: (elegidos: DotacionElegida[]) => void;
}

function textoFalta(r: RenglonDotacionApi): string {
  return r.falta > 0 ? `Falta ${r.falta} de ${r.recomendada}` : "Completo";
}

/**
 * Hoja con la dotación de un trabajador (FEAT-003, D-02): cada artículo con lo que le falta. En modo
 * `seleccion` el almacenista marca lo que quiere agregar (por omisión nada) y los artículos se agregan como
 * renglones normales: el servidor los evalúa y el semáforo manda. Un artículo que se entrega por pieza se
 * escanea: no tiene casilla.
 */
export function HojaDotacion({ abierta, alCambiar, dotacion, modo, yaEnLista, alAgregar }: PropiedadesHojaDotacion) {
  const [marcados, setMarcados] = useState<ReadonlySet<string>>(new Set());

  useEffect(() => {
    if (abierta) setMarcados(new Set());
  }, [abierta]);

  const seleccionando = modo === "seleccion";
  const estaEnLista = (r: RenglonDotacionApi) => yaEnLista?.has(r.articulo.codigo.trim().toLocaleUpperCase("es-MX")) ?? false;
  const sePuedeMarcar = (r: RenglonDotacionApi) => seleccionando && r.falta > 0 && r.articulo.control === "CANTIDAD" && !estaEnLista(r);
  const marcables = useMemo(
    () => dotacion.renglones.filter(sePuedeMarcar),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [dotacion, yaEnLista, seleccionando],
  );
  const faltan = dotacion.renglones.filter((r) => r.falta > 0).length;

  const alternar = (id: string, valor: boolean) =>
    setMarcados((previos) => {
      const copia = new Set(previos);
      if (valor) copia.add(id);
      else copia.delete(id);
      return copia;
    });

  const agregar = () => {
    const elegidos = marcables.filter((r) => marcados.has(r.articulo.id)).map((r) => ({ codigo: r.articulo.codigo, cantidad: r.falta }));
    if (elegidos.length === 0) return;
    alAgregar?.(elegidos);
    alCambiar(false);
  };

  return (
    <Hoja
      abierta={abierta}
      alCambiar={alCambiar}
      titulo="Dotación sugerida"
      descripcion={dotacion.puesto ? `Puesto: ${dotacion.puesto.nombre}` : undefined}
      pie={
        seleccionando ? (
          <Boton variante="principal" disabled={marcados.size === 0} onClick={agregar}>
            {marcados.size === 0 ? "Agregar a la entrega" : `Agregar a la entrega (${marcados.size})`}
          </Boton>
        ) : (
          <Boton variante="contorno" onClick={() => alCambiar(false)}>
            Cerrar
          </Boton>
        )
      }
    >
      <div className="flex flex-col gap-4">
        <p className="text-sm text-muted-foreground">
          {faltan === 0 ? "Tiene completa su dotación." : `Le faltan ${faltan} de ${dotacion.renglones.length} artículos.`}{" "}
          {seleccionando ? "Es solo una sugerencia: marca lo que quieras entregar ahora." : "Es solo una sugerencia."}
        </p>

        {seleccionando && marcables.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            <Boton variante="secundario" onClick={() => setMarcados(new Set(marcables.map((r) => r.articulo.id)))}>
              Marcar lo que falta
            </Boton>
            <Boton variante="texto" disabled={marcados.size === 0} onClick={() => setMarcados(new Set())}>
              Quitar marcas
            </Boton>
          </div>
        ) : null}

        <ul className="flex flex-col gap-2">
          {dotacion.renglones.map((r) => {
            const completo = r.falta === 0;
            const enLista = seleccionando && !completo && estaEnLista(r);
            const porPieza = seleccionando && !completo && !enLista && r.articulo.control === "PIEZA";
            const marcable = sePuedeMarcar(r);
            const cuerpo = (
              <>
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="text-base leading-tight font-semibold wrap-break-word">{r.articulo.nombre}</span>
                  <span className="text-sm text-muted-foreground">{r.articulo.codigo}</span>
                </span>
                <span className="flex shrink-0 flex-col items-end text-right text-sm">
                  <span className={cn("font-semibold", !completo && "text-foreground")}>{textoFalta(r)}</span>
                  {enLista ? <span className="text-xs text-muted-foreground">Ya está en la lista</span> : null}
                  {porPieza ? <span className="text-xs text-muted-foreground">Escanea la pieza</span> : null}
                </span>
              </>
            );
            const base = "flex min-h-14 items-center gap-3 rounded-2xl border bg-card px-3 py-2";
            return (
              <li key={r.articulo.id}>
                {marcable ? (
                  <label className={cn(base, "cursor-pointer hover:bg-muted", marcados.has(r.articulo.id) && "border-primary bg-accent")}>
                    <Checkbox
                      checked={marcados.has(r.articulo.id)}
                      onCheckedChange={(valor) => alternar(r.articulo.id, valor === true)}
                      aria-label={`Agregar ${r.articulo.nombre}`}
                    />
                    {cuerpo}
                  </label>
                ) : (
                  <div className={cn(base, (completo || enLista) && "opacity-60")}>
                    {seleccionando ? <span aria-hidden="true" className="size-5 shrink-0" /> : null}
                    {cuerpo}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      </div>
    </Hoja>
  );
}
