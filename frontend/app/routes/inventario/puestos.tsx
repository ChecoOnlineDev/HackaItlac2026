import { cn } from "cn";
import { BriefcaseBusinessIcon, ListChecksIcon, PencilIcon, PlusIcon, PowerIcon, SearchIcon } from "lucide-react";
import { useState } from "react";

import { apiGet, apiPatch } from "~/api/cliente";
import { mensajeDeError } from "~/api/errores";
import type { Pagina } from "~/api/tipos";
import { Seleccion } from "~/componentes/catalogo/campos";
import { useConsulta, useRetraso } from "~/componentes/catalogo/usar-consulta";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { HojaDotacion } from "~/componentes/puestos/hoja-dotacion";
import { HojaPuesto } from "~/componentes/puestos/hoja-puesto";
import { normalizar, textoArticulos, type Puesto } from "~/componentes/puestos/tipos";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { CampoBusqueda } from "~/componentes/ui/campo-busqueda";
import { Confirmacion } from "~/componentes/ui/confirmacion";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { HojaFiltros } from "~/componentes/ui/hoja-filtros";
import { Insignia } from "~/componentes/ui/insignia";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { useSesion } from "~/sesion/sesion";

export const handle: ManejadorRuta = { dispositivo: "computadora", permiso: "catalogo.ver" };

const OPCIONES_ESTADO = [
  { valor: "activos", texto: "Activos" },
  { valor: "inactivos", texto: "Inactivos" },
  { valor: "todos", texto: "Todos" },
];

export default function Puestos() {
  const { puede } = useSesion();
  const puedeEditar = puede("catalogo.administrar");

  const [texto, setTexto] = useState("");
  const q = useRetraso(texto.trim());
  const [estado, setEstado] = useState("activos");

  const consulta = useConsulta(
    (signal) =>
      apiGet<Pagina<Puesto>>(
        "/puestos",
        { activo: estado === "activos" ? true : estado === "inactivos" ? false : undefined, tamano: 200 },
        signal,
      ),
    estado,
  );

  const [nombreHoja, setNombreHoja] = useState<{ abierta: boolean; puesto: Puesto | null }>({ abierta: false, puesto: null });
  const [dotacionHoja, setDotacionHoja] = useState<{ abierta: boolean; puesto: Puesto | null }>({ abierta: false, puesto: null });
  // El puesto de la confirmación se conserva mientras la ventana se cierra, para que el texto no parpadee.
  const [cambiando, setCambiando] = useState<Puesto | null>(null);
  const [confirma, setConfirma] = useState(false);
  const [ocupado, setOcupado] = useState(false);

  const todos = consulta.datos?.elementos ?? [];
  const buscado = normalizar(q);
  const puestos = buscado ? todos.filter((p) => normalizar(p.nombre).includes(buscado)) : todos;
  const hayFiltros = q !== "" || estado !== "activos";

  async function cambiarEstado() {
    if (!cambiando) return;
    setOcupado(true);
    try {
      await apiPatch(`/puestos/${cambiando.id}`, { activo: !cambiando.activo });
      aviso({ titulo: cambiando.activo ? `“${cambiando.nombre}” quedó inactivo.` : `“${cambiando.nombre}” se reactivó.`, tipo: "exito" });
      setConfirma(false);
      consulta.recargar();
    } catch (causa) {
      aviso({ titulo: mensajeDeError(causa), tipo: "error" });
    } finally {
      setOcupado(false);
    }
  }

  const botonNuevo = puedeEditar ? (
    <Boton variante="normal" onClick={() => setNombreHoja({ abierta: true, puesto: null })}>
      <PlusIcon aria-hidden="true" />
      Nuevo puesto
    </Boton>
  ) : null;

  const acciones = (p: Puesto, enTabla = false) => (
    <div className={cn("flex gap-2", enTabla ? "flex-nowrap" : "flex-wrap")}>
      <Boton variante="contorno" onClick={() => setDotacionHoja({ abierta: true, puesto: p })} aria-label={`Dotación de ${p.nombre}`}>
        <ListChecksIcon aria-hidden="true" />
        Dotación
      </Boton>
      {puedeEditar ? (
        <>
          <Boton variante="texto" onClick={() => setNombreHoja({ abierta: true, puesto: p })} aria-label={`Cambiar el nombre de ${p.nombre}`}>
            <PencilIcon aria-hidden="true" />
            Renombrar
          </Boton>
          <Boton variante="texto" onClick={() => {
              setCambiando(p);
              setConfirma(true);
            }} aria-label={`${p.activo ? "Inactivar" : "Reactivar"} ${p.nombre}`}>
            <PowerIcon aria-hidden="true" />
            {p.activo ? "Inactivar" : "Reactivar"}
          </Boton>
        </>
      ) : null}
    </div>
  );

  let contenido;
  if (consulta.error && !consulta.datos) {
    contenido = <EstadoError error={consulta.error} alReintentar={consulta.recargar} />;
  } else if (consulta.cargando && !consulta.datos) {
    contenido = <Esqueleto tipo="tabla" cantidad={5} />;
  } else if (puestos.length === 0) {
    contenido = hayFiltros ? (
      <EstadoVacio
        icono={SearchIcon}
        titulo="No hay puestos con esos filtros"
        descripcion="Prueba con otra palabra o quita los filtros."
        accion={
          <Boton
            variante="contorno"
            onClick={() => {
              setTexto("");
              setEstado("activos");
            }}
          >
            Quitar filtros
          </Boton>
        }
      />
    ) : (
      <EstadoVacio
        icono={BriefcaseBusinessIcon}
        titulo="Todavía no hay puestos"
        descripcion={puedeEditar ? "Crea el primero y arma su dotación para que el almacén sepa qué entregar." : "Compras o el supervisor los dan de alta."}
        accion={botonNuevo}
      />
    );
  } else {
    contenido = (
      <div className={cn("transition-opacity", consulta.cargando && "opacity-60")} aria-busy={consulta.cargando}>
        {/* Computadora y tableta ancha: tabla */}
        <div className="hidden md:block">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead scope="col">Puesto</TableHead>
                <TableHead scope="col">Dotación</TableHead>
                <TableHead scope="col">Estado</TableHead>
                <TableHead scope="col">
                  <span className="sr-only">Acciones</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {puestos.map((p) => (
                <TableRow key={p.id} className={cn(!p.activo && "bg-muted/40 text-muted-foreground")}>
                  <TableHead scope="row" className="whitespace-normal">
                    {p.nombre}
                  </TableHead>
                  <TableCell>{textoArticulos(p.total_articulos)}</TableCell>
                  <TableCell>
                    <Insignia estado="neutra">{p.activo ? "Activo" : "Inactivo"}</Insignia>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end">{acciones(p, true)}</div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {/* Celular: tarjetas */}
        <ul className="grid gap-3 sm:grid-cols-2 md:hidden">
          {puestos.map((p) => (
            <li key={p.id} className={cn("flex flex-col gap-2 rounded-2xl border bg-card p-4 shadow-xs", !p.activo && "bg-muted/40")}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <span className="text-base font-semibold text-marino">{p.nombre}</span>
                <Insignia estado="neutra">{p.activo ? "Activo" : "Inactivo"}</Insignia>
              </div>
              <p className="text-sm text-muted-foreground">{textoArticulos(p.total_articulos)}</p>
              {acciones(p)}
            </li>
          ))}
        </ul>
      </div>
    );
  }

  return (
    <Pantalla
      titulo="Puestos"
      descripcion="Cada puesto tiene una dotación recomendada. Al entregar algo fuera de ella, el sistema avisa sin bloquear."
      acciones={puestos.length > 0 || hayFiltros ? botonNuevo : null}
    >
      <div className="flex items-center gap-2">
        <CampoBusqueda etiqueta="Buscar puesto" placeholder="Buscar puesto" value={texto} alCambiar={setTexto} />
        <HojaFiltros
          valores={{ estado }}
          activos={estado !== "activos" ? 1 : 0}
          alAplicar={(v) => setEstado(v.estado)}
          alLimpiar={() => setEstado("activos")}
        >
          {(b, cambiar) => <Seleccion etiqueta="Estado" opciones={OPCIONES_ESTADO} value={b.estado} alCambiar={(v) => cambiar({ estado: v })} />}
        </HojaFiltros>
      </div>
      {contenido}

      <HojaPuesto
        abierta={nombreHoja.abierta}
        alCambiar={(abierta) => setNombreHoja((h) => ({ ...h, abierta }))}
        puesto={nombreHoja.puesto}
        alGuardar={(guardado, esNuevo) => {
          consulta.recargar();
          // Un puesto recién creado no tiene dotación: se pasa directo a armarla.
          if (esNuevo) setDotacionHoja({ abierta: true, puesto: guardado });
        }}
      />
      <HojaDotacion
        abierta={dotacionHoja.abierta}
        alCambiar={(abierta) => setDotacionHoja((h) => ({ ...h, abierta }))}
        puesto={dotacionHoja.puesto}
        puedeEditar={puedeEditar}
        alGuardar={consulta.recargar}
      />
      <Confirmacion
        abierta={confirma}
        alCambiar={(a) => !a && !ocupado && setConfirma(false)}
        mensaje={cambiando?.activo ? `¿Inactivar “${cambiando.nombre}”?` : `¿Reactivar “${cambiando?.nombre ?? ""}”?`}
        detalle={
          cambiando?.activo
            ? "Ya no se podrá dar este puesto a un trabajador nuevo. Su dotación se conserva y quienes lo tienen no cambian."
            : "Vuelve a poder darse a trabajadores nuevos."
        }
        etiquetaConfirmar={cambiando?.activo ? "Sí, inactivar" : "Sí, reactivar"}
        etiquetaCancelar="Cancelar"
        cargando={ocupado}
        alConfirmar={() => void cambiarEstado()}
      />
    </Pantalla>
  );
}
