import { FolderTree, PencilIcon, PlusIcon } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { apiGet } from "~/api/cliente";
import type { Pagina } from "~/api/tipos";
import { HojaCategoria } from "~/componentes/catalogo/hoja-categoria";
import {
  resumenReglas,
  TEXTO_CONTROL,
  TEXTO_TIPO,
  textoRetorno,
  type Categoria,
} from "~/componentes/catalogo/tipos";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { Boton } from "~/componentes/ui/boton";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { Insignia } from "~/componentes/ui/insignia";
import { useSesion } from "~/sesion/sesion";

export const handle: ManejadorRuta = { permiso: "catalogo.ver" };

function Resumen({ categoria }: { categoria: Categoria }) {
  const partes = resumenReglas(categoria);
  if (partes.length === 0) return <span className="text-muted-foreground">Sin reglas extra</span>;
  return (
    <ul className="flex flex-col gap-0.5 text-sm">
      {partes.map((p) => (
        <li key={p}>{p}</li>
      ))}
    </ul>
  );
}

export default function Categorias() {
  const { puede } = useSesion();
  const puedeEditar = puede("catalogo.administrar");
  const consulta = useConsulta((signal) => apiGet<Pagina<Categoria>>("/categorias", { tamano: 200 }, signal), "categorias");
  const [hoja, setHoja] = useState<{ abierta: boolean; categoria: Categoria | null }>({ abierta: false, categoria: null });

  const abrir = (categoria: Categoria | null) => setHoja({ abierta: true, categoria });
  const categorias = consulta.datos?.elementos ?? [];

  const botonNueva = puedeEditar ? (
    <Boton variante="normal" onClick={() => abrir(null)}>
      <PlusIcon aria-hidden="true" />
      Nueva categoría
    </Boton>
  ) : null;

  let contenido;
  if (consulta.error && !consulta.datos) {
    contenido = <EstadoError error={consulta.error} alReintentar={consulta.recargar} />;
  } else if (consulta.cargando && !consulta.datos) {
    contenido = <Esqueleto tipo="tabla" cantidad={5} />;
  } else if (categorias.length === 0) {
    contenido = (
      <EstadoVacio
        icono={FolderTree}
        titulo="Todavía no hay categorías"
        descripcion={puedeEditar ? "Crea la primera para empezar a dar de alta artículos." : "Compras o el supervisor las dan de alta."}
        accion={botonNueva}
      />
    );
  } else {
    contenido = (
      <>
        {/* Computadora: tabla */}
        <div className="hidden lg:block">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead scope="col">Categoría</TableHead>
                <TableHead scope="col">Tipo</TableHead>
                <TableHead scope="col">Control y entrega</TableHead>
                <TableHead scope="col">Reglas de la plantilla</TableHead>
                <TableHead scope="col"><span className="sr-only">Acciones</span></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {categorias.map((c) => (
                <TableRow key={c.id} className="align-top">
                  <TableHead scope="row">
                    <Link to={`/catalogo/articulos?categoria=${c.id}`} className="underline-offset-4 hover:underline">
                      {c.nombre}
                    </Link>
                  </TableHead>
                  <TableCell><Insignia estado="neutra">{TEXTO_TIPO[c.tipo]}</Insignia></TableCell>
                  <TableCell>
                    {TEXTO_CONTROL[c.control]}
                    <br />
                    <span className="text-muted-foreground">{textoRetorno(c.retornable)}</span>
                  </TableCell>
                  <TableCell><Resumen categoria={c} /></TableCell>
                  <TableCell className="text-right">
                    {puedeEditar ? (
                      <Boton variante="contorno" onClick={() => abrir(c)} aria-label={`Editar ${c.nombre}`}>
                        <PencilIcon aria-hidden="true" />
                        Editar
                      </Boton>
                    ) : null}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {/* Celular y tableta: tarjetas */}
        <ul className="grid gap-3 sm:grid-cols-2 lg:hidden">
          {categorias.map((c) => (
            <li key={c.id} className="flex flex-col gap-2 rounded-2xl border bg-card p-4 shadow-xs">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <Link to={`/catalogo/articulos?categoria=${c.id}`} className="inline-flex min-h-10 items-center text-base font-semibold text-marino">
                  {c.nombre}
                </Link>
                <Insignia estado="neutra">{TEXTO_TIPO[c.tipo]}</Insignia>
              </div>
              <p className="text-sm text-muted-foreground">
                {TEXTO_CONTROL[c.control]} · {textoRetorno(c.retornable)}
              </p>
              <Resumen categoria={c} />
              {puedeEditar ? (
                <Boton variante="contorno" className="mt-1 self-start" onClick={() => abrir(c)} aria-label={`Editar ${c.nombre}`}>
                  <PencilIcon aria-hidden="true" />
                  Editar
                </Boton>
              ) : null}
            </li>
          ))}
        </ul>
      </>
    );
  }

  return (
    <Pantalla
      titulo="Categorías"
      descripcion="Cada artículo nuevo copia las reglas de su categoría."
      acciones={categorias.length > 0 ? botonNueva : null}
    >
      {contenido}
      <HojaCategoria
        abierta={hoja.abierta}
        alCambiar={(abierta) => setHoja((h) => ({ ...h, abierta }))}
        categoria={hoja.categoria}
        alGuardar={consulta.recargar}
      />
    </Pantalla>
  );
}
