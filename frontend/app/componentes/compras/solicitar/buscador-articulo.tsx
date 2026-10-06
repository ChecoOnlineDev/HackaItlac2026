import { useState } from "react";

import { apiGet } from "~/api/cliente";
import { useConsulta, useRetraso } from "~/componentes/catalogo/usar-consulta";
import { CampoBusqueda } from "~/componentes/ui/campo-busqueda";
import { EstadoError } from "~/componentes/ui/estado-error";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import type { ArticuloElegido } from "./tipos";

interface ResultadoBusqueda {
  articulos: {
    elementos: { id: string; codigo: string; nombre: string; marca: string | null; categoria: string; activo: boolean }[];
  };
}

const MINIMO = 2;

interface Propiedades {
  deshabilitado?: boolean;
  alElegir: (articulo: ArticuloElegido) => void;
}

/** Busca un artículo del catálogo por nombre o código (espera 300 ms tras dejar de escribir). Solo ofrece los activos. */
export function BuscadorArticuloCompra({ deshabilitado, alElegir }: Propiedades) {
  const [texto, setTexto] = useState("");
  const q = useRetraso(texto.trim());
  const buscable = q.length >= MINIMO;
  const consulta = useConsulta(
    (signal) => (buscable ? apiGet<ResultadoBusqueda>("/busqueda", { q, tamano: 8 }, signal) : Promise.resolve(null)),
    buscable ? q : "",
  );
  const resultados = (consulta.datos?.articulos.elementos ?? []).filter((a) => a.activo);
  const esperando = texto.trim() !== q || (buscable && consulta.cargando && !consulta.datos);

  return (
    <div className="flex flex-col gap-3">
      <CampoBusqueda
        etiqueta="Buscar un artículo del catálogo por nombre o código"
        placeholder="Por ejemplo: llave, arnés, guantes"
        value={texto}
        alCambiar={setTexto}
        disabled={deshabilitado}
        className="h-12 rounded-xl text-base"
      />
      {texto.trim().length === 1 ? <p className="text-sm text-muted-foreground">Escribe al menos dos letras para buscar.</p> : null}
      {buscable && consulta.error ? <EstadoError error={consulta.error} alReintentar={consulta.recargar} className="p-4" /> : null}
      {buscable && esperando && !consulta.error ? <Esqueleto tipo="renglon" /> : null}
      {buscable && !esperando && !consulta.error && resultados.length === 0 ? (
        <p role="status" className="text-sm text-muted-foreground">
          No hay ningún artículo del catálogo con “{q}”. Si es un equipo nuevo, toca “No está en el catálogo”.
        </p>
      ) : null}
      {buscable && !esperando && resultados.length > 0 ? (
        <ul aria-label="Artículos encontrados" className="flex flex-col gap-2">
          {resultados.map((a) => (
            <li key={a.id}>
              <button
                type="button"
                disabled={deshabilitado}
                onClick={() => {
                  alElegir({ id: a.id, codigo: a.codigo, nombre: a.nombre, marca: a.marca });
                  setTexto("");
                }}
                className="flex min-h-12 w-full flex-col items-start gap-0.5 rounded-2xl border bg-card p-3 text-left hover:bg-muted disabled:opacity-50"
              >
                <span className="text-base leading-tight font-semibold">{a.nombre}</span>
                <span className="text-sm text-muted-foreground">{[a.codigo, a.marca, a.categoria].filter(Boolean).join(" · ")}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
