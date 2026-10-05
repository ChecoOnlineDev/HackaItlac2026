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
    <ul className="flex flex-col gap-0.5">
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
        <div className="hidden overflow-hidden rounded-xl border lg:block">
          <Table className="w-full text-left">
            <TableHeader className="bg-muted text-sm">
              <TableRow>
                <TableHead scope="col" className="p-3 font-semibold">Categoría</TableHead>
                <TableHead scope="col" className="p-3 font-semibold">Tipo</TableHead>
                <TableHead scope="col" className="p-3 font-semibold">Control y entrega</TableHead>
                <TableHead scope="col" className="p-3 font-semibold">Reglas de la plantilla</TableHead>
                <TableHead scope="col" className="p-3 font-semibold"><span className="sr-only">Acciones</span></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {categorias.map((c) => (
                <TableRow key={c.id} className="border-t align-top">
                  <TableHead scope="row" className="p-3 font-semibold">
                    <Link to={`/catalogo/articulos?categoria=${c.id}`} className="underline-offset-4 hover:underline">
                      {c.nombre}
                    </Link>
                  </TableHead>
                  <TableCell className="p-3"><Insignia estado="neutra">{TEXTO_TIPO[c.tipo]}</Insignia></TableCell>
                  <TableCell className="p-3">
                    {TEXTO_CONTROL[c.control]}
                    <br />
                    <span className="text-muted-foreground">{textoRetorno(c.retornable)}</span>
                  </TableCell>
                  <TableCell className="p-3"><Resumen categoria={c} /></TableCell>
                  <TableCell className="p-3 text-right">
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
        <ul className="flex flex-col gap-3 lg:hidden">
          {categorias.map((c) => (
            <li key={c.id} className="flex flex-col gap-3 rounded-xl border p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <Link to={`/catalogo/articulos?categoria=${c.id}`} className="text-xl font-bold text-marino">
                  {c.nombre}
                </Link>
                <Insignia estado="neutra">{TEXTO_TIPO[c.tipo]}</Insignia>
              </div>
              <p>
                {TEXTO_CONTROL[c.control]} · {textoRetorno(c.retornable)}
              </p>
              <Resumen categoria={c} />
              {puedeEditar ? (
                <Boton variante="contorno" onClick={() => abrir(c)} aria-label={`Editar ${c.nombre}`}>
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
      descripcion="Tipos de artículo y sus reglas de entrega. Cada artículo nuevo copia las reglas de su categoría."
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
