import { cn } from "cn";
import { ChevronDownIcon, SearchIcon } from "lucide-react";
import { useId, useState } from "react";

import { apiGet } from "~/api/cliente";
import { useConsulta, useRetraso } from "~/componentes/catalogo/usar-consulta";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { EstadoError } from "~/componentes/ui/estado-error";
import { Hoja } from "~/componentes/ui/hoja";
import { Insignia } from "~/componentes/ui/insignia";
import { Label } from "~/components/ui/label";
import { recordarEtiqueta, useEtiqueta } from "./listas";

interface Busqueda {
  q: string;
  articulos: { elementos: { id: string; codigo: string; nombre: string; marca: string | null; categoria: string; activo: boolean }[] };
  trabajadores: { elementos: { id: string; numero_empleado: string; nombre: string; estado_texto: string }[] };
  sin_resultados: boolean;
  mensaje: string | null;
}

const TEXTOS = {
  trabajador: {
    etiqueta: "Trabajador",
    todos: "Todos los trabajadores",
    titulo: "Elegir trabajador",
    ayuda: "Escribe el nombre o el número de empleado.",
  },
  articulo: {
    etiqueta: "Artículo",
    todos: "Todos los artículos",
    titulo: "Elegir artículo",
    ayuda: "Escribe el nombre o el código del artículo.",
  },
} as const;

interface Propiedades {
  tipo: "trabajador" | "articulo";
  /** Id elegido, o vacío si no hay filtro. */
  valor: string;
  alCambiar: (id: string | null) => void;
}

/**
 * Filtro por trabajador o por artículo: un botón que abre una hoja con búsqueda. Usa la búsqueda
 * general del servidor, que respeta lo que cada persona puede ver.
 */
export function SelectorBusqueda({ tipo, valor, alCambiar }: Propiedades) {
  const textos = TEXTOS[tipo];
  const idEtiqueta = useId();
  const [abierta, setAbierta] = useState(false);
  const [texto, setTexto] = useState("");
  const q = useRetraso(texto.trim());
  const buscable = q.length >= 2;
  const etiquetaElegida = useEtiqueta(tipo, valor);

  const consulta = useConsulta(
    (signal) =>
      buscable ? apiGet<Busqueda>("/busqueda", { q, tamano: 20 }, signal) : Promise.resolve(null),
    `${tipo}|${buscable ? q : ""}|${abierta}`,
  );

  const resultados =
    tipo === "trabajador"
      ? (consulta.datos?.trabajadores.elementos ?? []).map((t) => ({
          id: t.id,
          titulo: t.nombre,
          detalle: t.numero_empleado,
          nota: t.estado_texto,
        }))
      : (consulta.datos?.articulos.elementos ?? []).map((a) => ({
          id: a.id,
          titulo: a.nombre,
          detalle: [a.codigo, a.marca, a.categoria].filter(Boolean).join(" · "),
          nota: a.activo ? null : "Inactivo",
        }));

  function elegir(id: string, titulo: string, detalle: string) {
    recordarEtiqueta(tipo, id, tipo === "trabajador" ? `${titulo} (${detalle})` : titulo);
    alCambiar(id);
    setAbierta(false);
    setTexto("");
  }

  return (
    <div className="flex flex-col gap-1.5">
      <Label id={idEtiqueta} className="text-sm font-medium text-foreground">
        {textos.etiqueta}
      </Label>
      <Boton
        variante="contorno"
        aria-labelledby={`${idEtiqueta} ${idEtiqueta}-valor`}
        aria-haspopup="dialog"
        title={valor ? (etiquetaElegida ?? textos.etiqueta) : textos.todos}
        className={cn("h-11 w-full justify-between rounded-xl px-3 text-base font-normal")}
        onClick={() => setAbierta(true)}
      >
        <span id={`${idEtiqueta}-valor`} className="truncate">{valor ? (etiquetaElegida ?? "Elegido") : textos.todos}</span>
        <ChevronDownIcon aria-hidden="true" className="size-4 shrink-0" />
      </Boton>

      <Hoja
        abierta={abierta}
        alCambiar={setAbierta}
        titulo={textos.titulo}
        descripcion={textos.ayuda}
        pie={
          valor ? (
            <Boton
              variante="contorno"
              onClick={() => {
                alCambiar(null);
                setAbierta(false);
              }}
            >
              {textos.todos}
            </Boton>
          ) : undefined
        }
      >
        <div className="flex flex-col gap-4">
          <Campo
            etiqueta="Buscar"
            value={texto}
            autoFocus
            autoComplete="off"
            placeholder="Al menos dos letras"
            onChange={(e) => setTexto(e.target.value)}
          />
          {!buscable && texto.trim().length < 2 ? (
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <SearchIcon aria-hidden="true" className="size-4" />
              Escribe al menos dos letras para buscar.
            </p>
          ) : !buscable ? (
            <p className="text-sm text-muted-foreground" role="status">
              Buscando…
            </p>
          ) : consulta.error ? (
            <EstadoError error={consulta.error} alReintentar={consulta.recargar} />
          ) : consulta.cargando && !consulta.datos ? (
            <p className="text-sm text-muted-foreground" role="status">
              Buscando…
            </p>
          ) : resultados.length === 0 ? (
            <p className="text-sm text-muted-foreground" role="status">
              No se encontró nada con esa búsqueda.
            </p>
          ) : (
            <ul className="flex flex-col gap-2" aria-label="Resultados">
              {resultados.map((r) => (
                <li key={r.id}>
                  <button
                    type="button"
                    onClick={() => elegir(r.id, r.titulo, r.detalle)}
                    className="flex min-h-12 w-full flex-col items-start gap-0.5 rounded-xl border bg-card p-3 text-left shadow-xs hover:bg-muted"
                  >
                    <span className="flex flex-wrap items-center gap-2 text-base leading-tight font-semibold">
                      {r.titulo}
                      {r.nota ? <Insignia estado="neutra">{r.nota}</Insignia> : null}
                    </span>
                    <span className="text-sm text-muted-foreground">{r.detalle}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </Hoja>
    </div>
  );
}
