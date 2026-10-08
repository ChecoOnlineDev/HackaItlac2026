import { KeyRoundIcon, PencilIcon, PlusIcon, SearchIcon, UserCheckIcon, UserXIcon, UsersIcon } from "lucide-react";
import { useState } from "react";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { Label } from "~/components/ui/label";
import { apiGet, apiPatch } from "~/api/cliente";
import type { Pagina } from "~/api/tipos";
import { HojaContrasena } from "~/componentes/acceso/hoja-contrasena";
import { HojaUsuario } from "~/componentes/acceso/hoja-usuario";
import {
  PERMISO_TODOS_LOS_ALMACENES,
  TAMANO_PAGINA_USUARIOS,
  type AlmacenAcceso,
  type RolAcceso,
  type UsuarioAcceso,
} from "~/componentes/acceso/tipos";
import { Paginador } from "~/componentes/catalogo/campos";
import { useConsulta, useRetraso } from "~/componentes/catalogo/usar-consulta";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { CampoBusqueda } from "~/componentes/ui/campo-busqueda";
import { Confirmacion } from "~/componentes/ui/confirmacion";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { HojaFiltros } from "~/componentes/ui/hoja-filtros";
import { Insignia } from "~/componentes/ui/insignia";
import { ListaDesplegable } from "~/componentes/ui/lista-desplegable";
import { mensajeDeError } from "~/api/errores";
import { useSesionActiva } from "~/sesion/sesion";

export const handle: ManejadorRuta = { permiso: "acceso.usuarios" };

const SIN_ALMACEN = "sin";

interface Filtros extends Record<string, string> {
  rol: string;
  almacen: string;
  estado: string;
}

const SIN_FILTROS: Filtros = { rol: "", almacen: "", estado: "" };

function AlmacenDe({ usuario, opera }: { usuario: UsuarioAcceso; opera: boolean }) {
  if (usuario.almacen) return <span>{usuario.almacen.nombre}</span>;
  return <span className="text-muted-foreground">{opera ? "Sin almacén" : "Todos los almacenes"}</span>;
}

export default function Usuarios() {
  const { sesion } = useSesionActiva();
  const [texto, setTexto] = useState("");
  const q = useRetraso(texto.trim());
  const [filtros, setFiltros] = useState<Filtros>(SIN_FILTROS);
  const [pagina, setPagina] = useState(1);
  const [editando, setEditando] = useState<UsuarioAcceso | null>(null);
  const [creando, setCreando] = useState(false);
  const [restableciendo, setRestableciendo] = useState<UsuarioAcceso | null>(null);
  const [cambiandoEstado, setCambiandoEstado] = useState<UsuarioAcceso | null>(null);
  const [guardandoEstado, setGuardandoEstado] = useState(false);

  const roles = useConsulta((signal) => apiGet<RolAcceso[]>("/roles", undefined, signal), "usuarios-roles");
  const almacenes = useConsulta((signal) => apiGet<AlmacenAcceso[]>("/almacenes", undefined, signal), "usuarios-almacenes");
  const lista = useConsulta(
    (signal) =>
      apiGet<Pagina<UsuarioAcceso>>(
        "/usuarios",
        {
          q,
          rol_id: filtros.rol,
          almacen_id: filtros.almacen && filtros.almacen !== SIN_ALMACEN ? filtros.almacen : undefined,
          sin_almacen: filtros.almacen === SIN_ALMACEN ? true : undefined,
          activo: filtros.estado === "activos" ? true : filtros.estado === "inactivos" ? false : undefined,
          pagina,
          tamano: TAMANO_PAGINA_USUARIOS,
        },
        signal,
      ),
    `${q}|${filtros.rol}|${filtros.almacen}|${filtros.estado}|${pagina}`,
  );

  const todosLosRoles = roles.datos ?? [];
  const almacenesActivos = (almacenes.datos ?? []).filter((a) => a.estado === "ACTIVO");
  const usuarios = lista.datos?.elementos ?? [];
  /** Opera un almacén quien no tiene `almacenes.todos`: ese necesita almacén asignado. */
  const opera = (u: UsuarioAcceso) =>
    !(todosLosRoles.find((r) => r.id === u.rol.id)?.permisos.includes(PERMISO_TODOS_LOS_ALMACENES) ?? false);
  const activos = Object.values(filtros).filter((v) => v !== "").length;
  const hayFiltros = q !== "" || activos > 0;

  function quitarFiltros() {
    setTexto("");
    setFiltros(SIN_FILTROS);
    setPagina(1);
  }

  async function cambiarEstado() {
    if (!cambiandoEstado) return;
    const objetivo = cambiandoEstado;
    setGuardandoEstado(true);
    try {
      await apiPatch(`/usuarios/${objetivo.id}`, { activo: !objetivo.activo });
      aviso({
        titulo: objetivo.activo ? `${objetivo.nombre} quedó inactivo` : `${objetivo.nombre} ya puede entrar otra vez`,
        tipo: "exito",
      });
      lista.recargar();
    } catch (causa) {
      aviso({ titulo: "No se pudo hacer el cambio", descripcion: mensajeDeError(causa), tipo: "error", duracionMs: 8000 });
    } finally {
      setGuardandoEstado(false);
      setCambiandoEstado(null);
    }
  }

  /** `compacto`: solo iconos (tabla); si no, con texto (tarjetas del celular). */
  function acciones(u: UsuarioAcceso, compacto: boolean) {
    const soyYo = u.id === sesion.usuario.id;
    return (
      <div className={compacto ? "flex gap-2" : "flex flex-wrap gap-2"}>
        <Boton variante="contorno" className={compacto ? "size-10 px-0" : undefined} onClick={() => setEditando(u)} aria-label={`Editar a ${u.nombre}`} title="Editar">
          <PencilIcon aria-hidden="true" />
          {compacto ? null : "Editar"}
        </Boton>
        <Boton variante="contorno" className={compacto ? "size-10 px-0" : undefined} onClick={() => setRestableciendo(u)} aria-label={`Restablecer la contraseña de ${u.nombre}`} title="Restablecer contraseña">
          <KeyRoundIcon aria-hidden="true" />
          {compacto ? null : "Contraseña"}
        </Boton>
        {soyYo ? null : (
          <Boton
            variante="contorno"
            className={compacto ? "size-10 px-0" : undefined}
            onClick={() => setCambiandoEstado(u)}
            aria-label={`${u.activo ? "Inactivar" : "Reactivar"} a ${u.nombre}`}
            title={u.activo ? "Inactivar" : "Reactivar"}
          >
            {u.activo ? <UserXIcon aria-hidden="true" /> : <UserCheckIcon aria-hidden="true" />}
            {compacto ? null : u.activo ? "Inactivar" : "Reactivar"}
          </Boton>
        )}
      </div>
    );
  }

  let contenido;
  if (lista.error && !lista.datos) {
    contenido = <EstadoError error={lista.error} alReintentar={lista.recargar} />;
  } else if (lista.cargando && !lista.datos) {
    contenido = <Esqueleto tipo="tabla" cantidad={6} />;
  } else if (usuarios.length === 0) {
    contenido = (
      <EstadoVacio
        icono={hayFiltros ? SearchIcon : UsersIcon}
        titulo={hayFiltros ? "No hay usuarios con ese filtro" : "Todavía no hay usuarios"}
        descripcion={hayFiltros ? "Prueba con otra palabra o quita los filtros." : "Crea el primero con «Nuevo usuario»."}
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
                <TableHead scope="col">Persona</TableHead>
                <TableHead scope="col">Rol</TableHead>
                <TableHead scope="col">Almacén</TableHead>
                <TableHead scope="col">Estado</TableHead>
                <TableHead scope="col"><span className="sr-only">Acciones</span></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {usuarios.map((u) => (
                <TableRow key={u.id}>
                  <TableHead scope="row" className="whitespace-normal">
                    {u.nombre}
                    {u.id === sesion.usuario.id ? <span className="ml-2 text-xs font-normal text-muted-foreground">(tú)</span> : null}
                    <span className="block text-xs font-normal text-muted-foreground">{u.usuario}</span>
                  </TableHead>
                  <TableCell>{u.rol.nombre}</TableCell>
                  <TableCell className="whitespace-normal"><AlmacenDe usuario={u} opera={opera(u)} /></TableCell>
                  <TableCell>
                    <Insignia estado={u.activo ? "info" : "neutra"}>{u.activo ? "Activo" : "Inactivo"}</Insignia>
                  </TableCell>
                  <TableCell className="w-px whitespace-nowrap">{acciones(u, true)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {/* Celular: tarjetas */}
        <ul className="flex flex-col gap-3 md:hidden">
          {usuarios.map((u) => (
            <li key={u.id} className="flex flex-col gap-2 rounded-2xl border bg-card p-4 shadow-xs">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <span className="text-base font-semibold text-marino">
                  {u.nombre}
                  {u.id === sesion.usuario.id ? <span className="ml-2 text-xs font-normal text-muted-foreground">(tú)</span> : null}
                </span>
                <Insignia estado={u.activo ? "info" : "neutra"}>{u.activo ? "Activo" : "Inactivo"}</Insignia>
              </div>
              <p className="text-sm text-muted-foreground">
                {u.usuario} · {u.rol.nombre}
              </p>
              <p className="text-sm">
                Almacén: <AlmacenDe usuario={u} opera={opera(u)} />
              </p>
              {acciones(u, false)}
            </li>
          ))}
        </ul>
        <Paginador pagina={pagina} tamano={TAMANO_PAGINA_USUARIOS} total={lista.datos?.total ?? 0} alCambiar={setPagina} ocupado={lista.cargando} />
      </div>
    );
  }

  return (
    <Pantalla
      titulo="Usuarios"
      descripcion="Quién puede entrar al sistema, con qué rol y en qué almacén trabaja."
      acciones={
        <Boton variante="normal" onClick={() => setCreando(true)}>
          <PlusIcon aria-hidden="true" />
          Nuevo usuario
        </Boton>
      }
    >
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
          valores={filtros}
          activos={activos}
          alAplicar={(v) => {
            setFiltros(v);
            setPagina(1);
          }}
          alLimpiar={() => {
            setFiltros(SIN_FILTROS);
            setPagina(1);
          }}
        >
          {(b, cambiar) => (
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="filtro-rol" className="text-sm font-medium text-foreground">Rol</Label>
                <ListaDesplegable
                  id="filtro-rol"
                  valor={b.rol}
                  alCambiar={(v) => cambiar({ rol: v })}
                  vacio="Todos los roles"
                  opciones={todosLosRoles.map((r) => ({ valor: r.id, texto: r.nombre }))}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="filtro-almacen-usuario" className="text-sm font-medium text-foreground">Almacén</Label>
                <ListaDesplegable
                  id="filtro-almacen-usuario"
                  valor={b.almacen}
                  alCambiar={(v) => cambiar({ almacen: v })}
                  vacio="Todos los almacenes"
                  opciones={[{ valor: SIN_ALMACEN, texto: "Sin almacén asignado" }, ...almacenesActivos.map((a) => ({ valor: a.id, texto: a.nombre }))]}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="filtro-estado" className="text-sm font-medium text-foreground">Estado</Label>
                <ListaDesplegable
                  id="filtro-estado"
                  valor={b.estado}
                  alCambiar={(v) => cambiar({ estado: v })}
                  vacio="Activos e inactivos"
                  opciones={[
                    { valor: "activos", texto: "Solo activos" },
                    { valor: "inactivos", texto: "Solo inactivos" },
                  ]}
                />
              </div>
            </div>
          )}
        </HojaFiltros>
      </div>
      {contenido}

      <HojaUsuario
        abierta={creando || editando !== null}
        alCambiar={(a) => {
          if (!a) {
            setCreando(false);
            setEditando(null);
          }
        }}
        usuario={editando}
        roles={todosLosRoles}
        almacenes={almacenesActivos}
        alGuardar={() => {
          lista.recargar();
          roles.recargar();
        }}
      />
      <HojaContrasena
        usuario={restableciendo}
        roles={todosLosRoles}
        alCerrar={() => setRestableciendo(null)}
        alGuardar={() => {
          setRestableciendo(null);
          lista.recargar();
        }}
      />
      <Confirmacion
        abierta={cambiandoEstado !== null}
        alCambiar={(a) => !guardandoEstado && !a && setCambiandoEstado(null)}
        mensaje={
          cambiandoEstado?.activo
            ? `¿Inactivar a ${cambiandoEstado.nombre}?`
            : `¿Reactivar a ${cambiandoEstado?.nombre ?? ""}?`
        }
        detalle={
          cambiandoEstado?.activo
            ? "Ya no podrá entrar al sistema y se cierran sus sesiones abiertas. Sus movimientos anteriores se conservan."
            : "Podrá entrar de nuevo con su usuario y contraseña."
        }
        etiquetaConfirmar={cambiandoEstado?.activo ? "Sí, inactivar" : "Sí, reactivar"}
        etiquetaCancelar="Volver"
        peligro={cambiandoEstado?.activo}
        cargando={guardandoEstado}
        alConfirmar={cambiarEstado}
      />
    </Pantalla>
  );
}
