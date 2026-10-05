import { ChevronRightIcon, PackageIcon, SearchXIcon, WrenchIcon } from "lucide-react";
import { Link } from "react-router";

import { Avatar } from "~/componentes/ui/avatar";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Insignia } from "~/componentes/ui/insignia";
import { Seccion } from "./bloques";
import type { Busqueda } from "./tipos";

function Fila({ a, principal, secundario, derecha, icono }: { a: string; principal: string; secundario?: string; derecha?: React.ReactNode; icono: React.ReactNode }) {
  return (
    <li>
      <Link to={a} className="flex min-h-14 items-center gap-3 px-3 py-2 hover:bg-muted focus-visible:bg-muted focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring">
        {icono}
        <span className="flex min-w-0 flex-1 flex-col">
          <span className="truncate text-base font-semibold">{principal}</span>
          {secundario ? <span className="truncate text-sm text-muted-foreground">{secundario}</span> : null}
        </span>
        {derecha}
        <ChevronRightIcon aria-hidden="true" className="size-5 shrink-0 text-muted-foreground" />
      </Link>
    </li>
  );
}

function Icono({ children }: { children: React.ReactNode }) {
  return <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-accent text-marino">{children}</span>;
}

function Total({ mostrados, total }: { mostrados: number; total: number }) {
  if (total <= mostrados) return null;
  return <p className="text-sm text-muted-foreground">Se muestran {mostrados} de {total}. Escribe más del código o del nombre para afinar.</p>;
}

/** Coincidencias de una búsqueda por texto, agrupadas. Cada grupo respeta los permisos de quien busca. */
export function ResultadosBusqueda({ busqueda, texto }: { busqueda: Busqueda; texto: string }) {
  if (busqueda.sin_resultados) {
    return (
      <EstadoVacio
        icono={SearchXIcon}
        titulo="No se encontró nada con ese código o texto"
        descripcion={`Revisa cómo escribiste "${texto}" o prueba con otra parte del nombre.`}
      />
    );
  }
  const { articulos, piezas, trabajadores } = busqueda;
  return (
    <div className="flex flex-col gap-6">
      {trabajadores.elementos.length > 0 ? (
        <Seccion titulo={`Trabajadores (${trabajadores.total})`}>
          <ul className="flex flex-col divide-y rounded-xl border">
            {trabajadores.elementos.map((t) => (
              <Fila
                key={t.id}
                a={`/trabajadores/${t.id}`}
                icono={<Avatar nombre={t.nombre} tamano="md" />}
                principal={t.nombre}
                secundario={`Número ${t.numero_empleado}`}
                derecha={t.estado !== "ACTIVO" ? <Insignia estado="neutra">{t.estado_texto}</Insignia> : null}
              />
            ))}
          </ul>
          <Total mostrados={trabajadores.elementos.length} total={trabajadores.total} />
        </Seccion>
      ) : null}
      {articulos.elementos.length > 0 ? (
        <Seccion titulo={`Artículos (${articulos.total})`}>
          <ul className="flex flex-col divide-y rounded-xl border">
            {articulos.elementos.map((a) => (
              <Fila
                key={a.id}
                a={`/articulos/${a.id}`}
                icono={<Icono><PackageIcon aria-hidden="true" className="size-5" /></Icono>}
                principal={a.nombre}
                secundario={[a.codigo, a.marca, a.categoria].filter(Boolean).join(" · ")}
                derecha={!a.activo ? <Insignia estado="neutra">Inactivo</Insignia> : null}
              />
            ))}
          </ul>
          <Total mostrados={articulos.elementos.length} total={articulos.total} />
        </Seccion>
      ) : null}
      {piezas.elementos.length > 0 ? (
        <Seccion titulo={`Piezas (${piezas.total})`}>
          <ul className="flex flex-col divide-y rounded-xl border">
            {piezas.elementos.map((p) => (
              <Fila
                key={p.id}
                a={`/piezas/${p.id}`}
                icono={<Icono><WrenchIcon aria-hidden="true" className="size-5" /></Icono>}
                principal={`${p.articulo} · ${p.codigo}`}
                secundario={[p.numero_serie ? `Serie ${p.numero_serie}` : null, p.ubicacion ? `La tiene: ${p.ubicacion}` : null].filter(Boolean).join(" · ")}
                derecha={p.estado !== "APTO" ? <Insignia estado="rojo">{p.estado_texto}</Insignia> : null}
              />
            ))}
          </ul>
          <Total mostrados={piezas.elementos.length} total={piezas.total} />
        </Seccion>
      ) : null}
    </div>
  );
}

