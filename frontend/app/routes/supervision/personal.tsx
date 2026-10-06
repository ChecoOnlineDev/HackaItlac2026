import { SearchIcon, UserCog } from "lucide-react";
import { useState } from "react";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { apiGet } from "~/api/cliente";
import type { Pagina } from "~/api/tipos";
import { Paginador } from "~/componentes/catalogo/campos";
import { useConsulta, useRetraso } from "~/componentes/catalogo/usar-consulta";
import { HojaCambiarAlmacen } from "~/componentes/personal/hoja-cambiar-almacen";
import { TAMANO_PAGINA_PERSONAL, TEXTO_SIN_ALMACEN, type AlmacenOpcion, type PersonaAlmacen } from "~/componentes/personal/tipos";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { Boton } from "~/componentes/ui/boton";
import { CampoBusqueda } from "~/componentes/ui/campo-busqueda";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { HojaFiltros } from "~/componentes/ui/hoja-filtros";
import { Insignia } from "~/componentes/ui/insignia";
import { ListaDesplegable } from "~/componentes/ui/lista-desplegable";
import { Label } from "~/components/ui/label";
import { useSesionActiva } from "~/sesion/sesion";

export const handle: ManejadorRuta = { permiso: "almacenes.asignar_personal" };

/** Valor del filtro para "solo quienes no tienen almacén". */
const SIN = "sin";

function AlmacenActual({ persona }: { persona: PersonaAlmacen }) {
  return persona.almacen ? (
    <Insignia estado="info">{persona.almacen.nombre}</Insignia>
  ) : (
    <Insignia estado="neutra">{TEXTO_SIN_ALMACEN}</Insignia>
  );
}

export default function PersonalPorAlmacen() {
  const { sesion, puede } = useSesionActiva();
  const [texto, setTexto] = useState("");
  const q = useRetraso(texto.trim());
  const [almacen, setAlmacen] = useState("");
  const [pagina, setPagina] = useState(1);
  const [editando, setEditando] = useState<PersonaAlmacen | null>(null);

  const almacenes = useConsulta((signal) => apiGet<AlmacenOpcion[]>("/almacenes", undefined, signal), "personal-almacenes");
  const lista = useConsulta(
    (signal) =>
      apiGet<Pagina<PersonaAlmacen>>(
        "/personal",
        {
          q,
          almacen_id: almacen && almacen !== SIN ? almacen : undefined,
          sin_almacen: almacen === SIN ? true : undefined,
          pagina,
          tamano: TAMANO_PAGINA_PERSONAL,
        },
        signal,
      ),
    `${q}|${almacen}|${pagina}`,
  );

  // Solo quien tiene `almacenes.todos` mueve personas entre almacenes; los demás supervisores solo
  // traen gente a su almacén o la dejan libre, así que su lista de destinos es su propio almacén.
  const veTodos = puede("almacenes.todos");
  const activos = (almacenes.datos ?? []).filter((a) => a.estado === "ACTIVO" && (veTodos || a.id === sesion.almacen?.id));
  const personas = lista.datos?.elementos ?? [];
  const hayFiltros = q !== "" || almacen !== "";

  let contenido;
  if (lista.error && !lista.datos) {
    contenido = <EstadoError error={lista.error} alReintentar={lista.recargar} />;
  } else if (lista.cargando && !lista.datos) {
    contenido = <Esqueleto tipo="tabla" cantidad={6} />;
  } else if (personas.length === 0) {
    contenido = (
      <EstadoVacio
        icono={hayFiltros ? SearchIcon : UserCog}
        titulo="No hay personal con ese filtro"
        descripcion={hayFiltros ? "Prueba con otra palabra o quita los filtros." : "Aquí aparecen quienes operan un almacén."}
        accion={
          hayFiltros ? (
            <Boton
              variante="contorno"
              onClick={() => {
                setTexto("");
                setAlmacen("");
                setPagina(1);
              }}
            >
              Quitar filtros
            </Boton>
          ) : null
        }
      />
    );
  } else {
    contenido = (
      <div className="flex flex-col gap-4">
        {/* Escritorio y tableta: tabla */}
        <div className="hidden md:block">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead scope="col">Nombre</TableHead>
                <TableHead scope="col">Usuario</TableHead>
                <TableHead scope="col">Rol</TableHead>
                <TableHead scope="col">Almacén</TableHead>
                <TableHead scope="col"><span className="sr-only">Acciones</span></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {personas.map((p) => (
                <TableRow key={p.id}>
                  <TableHead scope="row" className="whitespace-normal">{p.nombre}</TableHead>
                  <TableCell>{p.usuario}</TableCell>
                  <TableCell>{p.rol.nombre}</TableCell>
                  <TableCell><AlmacenActual persona={p} /></TableCell>
                  <TableCell className="text-right">
                    <Boton variante="contorno" onClick={() => setEditando(p)} aria-label={`Cambiar almacén de ${p.nombre}`}>
                      Cambiar almacén
                    </Boton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {/* Celular: tarjetas */}
        <ul className="flex flex-col gap-3 md:hidden">
          {personas.map((p) => (
            <li key={p.id} className="flex flex-col gap-2 rounded-2xl border bg-card p-4 shadow-xs">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <span className="text-base font-semibold text-marino">{p.nombre}</span>
                <AlmacenActual persona={p} />
              </div>
              <p className="text-sm text-muted-foreground">
                {p.usuario} · {p.rol.nombre}
              </p>
              <Boton variante="contorno" className="mt-1 self-start" onClick={() => setEditando(p)} aria-label={`Cambiar almacén de ${p.nombre}`}>
                Cambiar almacén
              </Boton>
            </li>
          ))}
        </ul>
        <Paginador pagina={pagina} tamano={TAMANO_PAGINA_PERSONAL} total={lista.datos?.total ?? 0} alCambiar={setPagina} ocupado={lista.cargando} />
      </div>
    );
  }

  return (
    <Pantalla titulo="Personal" descripcion={veTodos ? "Elige en qué almacén trabaja cada persona." : "Trae a tu almacén a quien no tiene uno, o déjalo libre."}>
      <div className="flex items-center gap-2">
        <CampoBusqueda
          etiqueta="Buscar por nombre o usuario"
          placeholder="Buscar persona"
          value={texto}
          alCambiar={(v) => {
            setTexto(v);
            setPagina(1);
          }}
        />
        <HojaFiltros
          valores={{ almacen }}
          activos={almacen ? 1 : 0}
          alAplicar={(v) => {
            setAlmacen(v.almacen);
            setPagina(1);
          }}
          alLimpiar={() => {
            setAlmacen("");
            setPagina(1);
          }}
        >
          {(b, cambiar) => (
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="filtro-almacen" className="text-sm font-medium text-foreground">
                Almacén
              </Label>
              <ListaDesplegable
                id="filtro-almacen"
                valor={b.almacen}
                alCambiar={(v) => cambiar({ almacen: v })}
                vacio="Todos los almacenes"
                opciones={[{ valor: SIN, texto: TEXTO_SIN_ALMACEN }, ...activos.map((a) => ({ valor: a.id, texto: a.nombre }))]}
              />
            </div>
          )}
        </HojaFiltros>
      </div>
      {contenido}
      <HojaCambiarAlmacen
        persona={editando}
        almacenes={activos}
        alCerrar={() => setEditando(null)}
        alGuardar={() => {
          setEditando(null);
          lista.recargar();
        }}
      />
    </Pantalla>
  );
}
