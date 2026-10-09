import { PencilIcon, PlusIcon, SearchIcon, WarehouseIcon } from "lucide-react";
import { useMemo, useState } from "react";
import { useSearchParams } from "react-router";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { Label } from "~/components/ui/label";
import { apiGet } from "~/api/cliente";
import { HojaAlmacen, type ModoHojaAlmacen } from "~/componentes/almacenes/hoja-almacen";
import { HojaDetalleAlmacen } from "~/componentes/almacenes/hoja-detalle";
import { TEXTO_TIPO, textoResumen, type FichaAlmacen } from "~/componentes/almacenes/tipos";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { Boton } from "~/componentes/ui/boton";
import { CampoBusqueda } from "~/componentes/ui/campo-busqueda";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { HojaFiltros } from "~/componentes/ui/hoja-filtros";
import { Insignia } from "~/componentes/ui/insignia";
import { ListaDesplegable } from "~/componentes/ui/lista-desplegable";

export const handle: ManejadorRuta = { dispositivo: "computadora", permiso: "almacenes.administrar" };

interface Filtros extends Record<string, string> {
  estado: string;
}
const SIN_FILTROS: Filtros = { estado: "" };

const normalizar = (t: string) => t.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();

export default function Almacenes() {
  const [parametros, setParametros] = useSearchParams();
  const sinProyecto = parametros.get("sin_proyecto") === "true";
  const [texto, setTexto] = useState("");
  const [filtros, setFiltros] = useState<Filtros>(SIN_FILTROS);
  const [modo, setModo] = useState<ModoHojaAlmacen | null>(null);
  const [verId, setVerId] = useState<string | null>(null);

  const lista = useConsulta((signal) => apiGet<FichaAlmacen[]>("/almacenes", { resumen: true }, signal), "almacenes-admin");
  const todos = useMemo(() => lista.datos ?? [], [lista.datos]);

  const visibles = useMemo(() => {
    const buscado = normalizar(texto.trim());
    return todos.filter((a) => {
      if (sinProyecto && (a.tipo !== "PROYECTO" || a.estado !== "ACTIVO" || a.proyectos_activos !== 0)) return false;
      if (filtros.estado === "activos" && a.estado !== "ACTIVO") return false;
      if (filtros.estado === "cerrados" && a.estado !== "CERRADO") return false;
      if (!buscado) return true;
      return normalizar(`${a.clave} ${a.nombre}`).includes(buscado);
    });
  }, [todos, texto, filtros.estado, sinProyecto]);

  const activos = Object.values(filtros).filter((v) => v !== "").length;
  const hayFiltros = texto.trim() !== "" || activos > 0 || sinProyecto;
  const abierto = todos.find((a) => a.id === verId) ?? null;

  function quitarFiltros() {
    setTexto("");
    setFiltros(SIN_FILTROS);
    parametros.delete("sin_proyecto"); setParametros(parametros);
  }

  const dependeDe = (a: FichaAlmacen) => (a.padre_clave ? `${todos.find((p) => p.id === a.padre_id)?.nombre ?? a.padre_clave} (${a.padre_clave})` : "No depende de otro");
  const resumenDe = (a: FichaAlmacen) => (a.resumen ? textoResumen(a.resumen) : "—");
  const estadoDe = (a: FichaAlmacen) => <Insignia estado={a.estado === "ACTIVO" ? "info" : "neutra"}>{a.estado === "ACTIVO" ? "Activo" : "Cerrado"}</Insignia>;

  let contenido;
  if (lista.error && !lista.datos) {
    contenido = <EstadoError error={lista.error} alReintentar={lista.recargar} />;
  } else if (lista.cargando && !lista.datos) {
    contenido = <Esqueleto tipo="tabla" cantidad={6} />;
  } else if (visibles.length === 0) {
    contenido = (
      <EstadoVacio
        icono={hayFiltros ? SearchIcon : WarehouseIcon}
        titulo={hayFiltros ? "No hay almacenes con ese filtro" : "Todavía no hay almacenes"}
        descripcion={hayFiltros ? "Prueba con otra palabra o quita los filtros." : "Crea el primero con «Nuevo almacén». Empieza por el central."}
        accion={
          hayFiltros ? (
            <Boton variante="contorno" onClick={quitarFiltros}>
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
                <TableHead scope="col">Clave</TableHead>
                <TableHead scope="col">Nombre</TableHead>
                <TableHead scope="col">Tipo</TableHead>
                <TableHead scope="col">Depende de</TableHead>
                <TableHead scope="col">Estado</TableHead>
                <TableHead scope="col">Resumen</TableHead>
                <TableHead scope="col">
                  <span className="sr-only">Acciones</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visibles.map((a) => (
                <TableRow key={a.id} className={a.estado === "CERRADO" ? "opacity-70" : undefined}>
                  <TableHead scope="row">{a.clave}</TableHead>
                  <TableCell className="whitespace-normal">{a.nombre}</TableCell>
                  <TableCell>{TEXTO_TIPO[a.tipo]}</TableCell>
                  <TableCell className="whitespace-normal">{dependeDe(a)}</TableCell>
                  <TableCell>{estadoDe(a)}</TableCell>
                  <TableCell className="max-w-64 whitespace-normal text-sm">{resumenDe(a)}</TableCell>
                  <TableCell className="w-px whitespace-nowrap">
                    <div className="flex gap-2">
                      <Boton variante="contorno" onClick={() => setVerId(a.id)} aria-label={`Ver la ficha de ${a.nombre}`}>
                        Ver ficha
                      </Boton>
                      {a.estado === "ACTIVO" ? (
                        <Boton variante="contorno" className="size-10 px-0" onClick={() => setModo({ tipo: "editar", almacen: a })} aria-label={`Editar ${a.nombre}`} title="Editar">
                          <PencilIcon aria-hidden="true" />
                        </Boton>
                      ) : null}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {/* Celular: tarjetas */}
        <ul className="flex flex-col gap-3 md:hidden">
          {visibles.map((a) => (
            <li key={a.id} className={`flex flex-col gap-2 rounded-2xl border bg-card p-4 shadow-xs ${a.estado === "CERRADO" ? "opacity-70" : ""}`}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <span className="text-base font-semibold text-marino">
                  {a.nombre} <span className="text-sm font-normal text-muted-foreground">({a.clave})</span>
                </span>
                {estadoDe(a)}
              </div>
              <p className="text-sm text-muted-foreground">
                {TEXTO_TIPO[a.tipo]} · Depende de: {dependeDe(a)}
              </p>
              <p className="text-sm">{resumenDe(a)}</p>
              <div className="flex flex-wrap gap-2">
                <Boton variante="contorno" onClick={() => setVerId(a.id)}>
                  Ver ficha
                </Boton>
                {a.estado === "ACTIVO" ? (
                  <Boton variante="contorno" onClick={() => setModo({ tipo: "editar", almacen: a })}>
                    <PencilIcon aria-hidden="true" />
                    Editar
                  </Boton>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  return (
    <Pantalla
      titulo="Almacenes"
      descripcion="Los almacenes de la red: de cuál depende cada uno y cómo está. Aquí se dan de alta, se editan y se inactivan."
      acciones={
        <Boton variante="normal" onClick={() => setModo({ tipo: "nuevo" })}>
          <PlusIcon aria-hidden="true" />
          Nuevo almacén
        </Boton>
      }
    >
      <div className="flex items-center gap-2">
        <CampoBusqueda etiqueta="Buscar por clave o nombre" placeholder="Buscar almacén" value={texto} alCambiar={setTexto} />
        <HojaFiltros valores={filtros} activos={activos} alAplicar={setFiltros} alLimpiar={() => setFiltros(SIN_FILTROS)}>
          {(b, cambiar) => (
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="filtro-estado-almacen" className="text-sm font-medium text-foreground">
                Estado
              </Label>
              <ListaDesplegable
                id="filtro-estado-almacen"
                valor={b.estado}
                alCambiar={(v) => cambiar({ estado: v })}
                vacio="Activos y cerrados"
                opciones={[
                  { valor: "activos", texto: "Solo activos" },
                  { valor: "cerrados", texto: "Solo cerrados" },
                ]}
              />
            </div>
          )}
        </HojaFiltros>
      </div>
      {contenido}

      <HojaDetalleAlmacen
        almacen={abierto}
        alCerrar={() => setVerId(null)}
        alEditar={(a) => {
          setVerId(null);
          setModo({ tipo: "editar", almacen: a });
        }}
        alCambiar={lista.recargar}
      />
      <HojaAlmacen
        modo={modo}
        almacenes={todos}
        alCerrar={() => setModo(null)}
        alGuardar={(ficha, usado) => {
          setModo(null);
          lista.recargar();
          if (usado.tipo === "nuevo") setVerId(ficha.id);
        }}
      />
    </Pantalla>
  );
}
