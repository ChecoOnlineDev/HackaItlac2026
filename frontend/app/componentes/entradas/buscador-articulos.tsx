import { PlusIcon } from "lucide-react";
import { useState } from "react";

import { apiGet } from "~/api/cliente";
import { useConsulta, useRetraso } from "~/componentes/catalogo/usar-consulta";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { EstadoError } from "~/componentes/ui/estado-error";
import { Insignia } from "~/componentes/ui/insignia";

interface Busqueda {
  articulos: {
    elementos: { id: string; codigo: string; nombre: string; marca: string | null; categoria: string; control: string; activo: boolean }[];
  };
}

interface Propiedades {
  deshabilitado?: boolean;
  alElegir: (articuloId: string) => void;
  /** Si quien captura puede dar de alta artículos (`catalogo.administrar`), ofrece «Crear este artículo» (EK-07). */
  alCrear?: (nombre: string) => void;
}

/** Búsqueda de un artículo por nombre o código, para cuando no hay etiqueta que escanear. */
export function BuscadorArticulos({ deshabilitado, alElegir, alCrear }: Propiedades) {
  const [texto, setTexto] = useState("");
  const q = useRetraso(texto.trim());
  const buscable = q.length >= 2;
  const consulta = useConsulta(
    (signal) => (buscable ? apiGet<Busqueda>("/busqueda", { q, tamano: 8 }, signal) : Promise.resolve(null)),
    buscable ? q : "",
  );
  const resultados = consulta.datos?.articulos.elementos ?? [];

  return (
    <div className="flex flex-col gap-3">
      <Campo
        etiqueta="Buscar un artículo por nombre"
        type="search"
        value={texto}
        disabled={deshabilitado}
        autoComplete="off"
        placeholder="Por ejemplo: arnés, guantes, lente"
        onChange={(e) => setTexto(e.target.value)}
      />
      {buscable && consulta.error ? <EstadoError error={consulta.error} alReintentar={consulta.recargar} /> : null}
      {buscable && !consulta.error && !consulta.cargando && resultados.length === 0 ? (
        <div className="flex flex-col items-start gap-2 rounded-2xl border p-3" role="status">
          <p className="text-muted-foreground">No se encontró ningún artículo con “{q}”.</p>
          {alCrear ? (
            <Boton variante="normal" disabled={deshabilitado} onClick={() => alCrear(texto.trim())}>
              <PlusIcon aria-hidden="true" />
              Crear este artículo
            </Boton>
          ) : (
            <p className="text-sm">Este artículo no existe en el catálogo; pide que lo den de alta.</p>
          )}
        </div>
      ) : null}
      {resultados.length > 0 && buscable ? (
        <ul aria-label="Artículos encontrados" className="flex flex-col gap-2">
          {resultados.map((a) => (
            <li key={a.id}>
              <button
                type="button"
                disabled={deshabilitado}
                onClick={() => {
                  alElegir(a.id);
                  setTexto("");
                }}
                className="flex min-h-12 w-full flex-col items-start gap-0.5 rounded-2xl border p-3 text-left hover:bg-muted disabled:opacity-50"
              >
                <span className="flex flex-wrap items-center gap-2 text-base leading-tight font-semibold">
                  {a.nombre}
                  <Insignia estado="neutra">{a.control === "PIEZA" ? "Por pieza" : "Por cantidad"}</Insignia>
                  {!a.activo ? <Insignia estado="neutra">Inactivo</Insignia> : null}
                </span>
                <span className="text-sm text-muted-foreground">{[a.codigo, a.marca, a.categoria].filter(Boolean).join(" · ")}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
