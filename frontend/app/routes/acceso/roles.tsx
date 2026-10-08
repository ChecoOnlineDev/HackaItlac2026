import { CopyIcon, PlusIcon, PowerIcon, ShieldIcon } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router";

import { apiGet, apiPatch } from "~/api/cliente";
import { mensajeDeError } from "~/api/errores";
import { HojaRol, type ModoHojaRol } from "~/componentes/acceso/hoja-rol";
import { textoPermisos, textoUsuarios, type RolAcceso } from "~/componentes/acceso/tipos";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { Confirmacion } from "~/componentes/ui/confirmacion";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { Insignia } from "~/componentes/ui/insignia";
import { ListaDesplegable } from "~/componentes/ui/lista-desplegable";

export const handle: ManejadorRuta = { permiso: "acceso.roles" };

const OPCIONES_ESTADO = [
  { valor: "activos", texto: "Activos" },
  { valor: "inactivos", texto: "Inactivos" },
  { valor: "todos", texto: "Todos" },
];

/** Por qué un rol no se puede inactivar ahora; el servidor valida lo mismo (AC-11). */
function razonInactivar(r: RolAcceso): string | null {
  if (r.protegido) return "El rol Administrador no se puede inactivar.";
  if (r.total_usuarios > 0) return `Tiene ${textoUsuarios(r.total_usuarios).toLowerCase()}. Cámbiales el rol en Usuarios para inactivarlo.`;
  return null;
}

export default function Roles() {
  const navegar = useNavigate();
  const lista = useConsulta((signal) => apiGet<RolAcceso[]>("/roles", undefined, signal), "roles");
  const [modo, setModo] = useState<ModoHojaRol | null>(null);
  // Por defecto solo los activos: los inactivos estorban al armar usuarios y se consultan a propósito.
  const [estado, setEstado] = useState("activos");
  const [cambiando, setCambiando] = useState<RolAcceso | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const todos = lista.datos ?? [];
  const roles = todos.filter((r) => (estado === "activos" ? r.activo : estado === "inactivos" ? !r.activo : true));

  async function cambiarEstado() {
    if (!cambiando) return;
    setOcupado(true);
    try {
      const actualizado = await apiPatch<RolAcceso>(`/roles/${cambiando.id}`, { activo: !cambiando.activo });
      aviso({ titulo: actualizado.activo ? `“${actualizado.nombre}” se reactivó.` : `“${actualizado.nombre}” quedó inactivo.`, tipo: "exito" });
      setCambiando(null);
      lista.recargar();
    } catch (causa) {
      aviso({ titulo: "No se pudo hacer el cambio", descripcion: mensajeDeError(causa), tipo: "error", duracionMs: 9000 });
      setCambiando(null);
    } finally {
      setOcupado(false);
    }
  }

  let contenido;
  if (lista.error && !lista.datos) {
    contenido = <EstadoError error={lista.error} alReintentar={lista.recargar} />;
  } else if (lista.cargando && !lista.datos) {
    contenido = <Esqueleto tipo="tarjeta" cantidad={4} />;
  } else if (todos.length === 0) {
    contenido = (
      <EstadoVacio
        icono={ShieldIcon}
        titulo="Todavía no hay roles"
        descripcion="Crea el primero con «Nuevo rol»."
      />
    );
  } else if (roles.length === 0) {
    contenido = (
      <EstadoVacio
        icono={ShieldIcon}
        titulo={estado === "inactivos" ? "No hay roles inactivos" : "No hay roles activos"}
        descripcion="Cambia el filtro de estado para ver los demás."
        accion={
          <Boton variante="contorno" onClick={() => setEstado("todos")}>
            Ver todos
          </Boton>
        }
      />
    );
  } else {
    contenido = (
      <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {roles.map((r) => (
          <li key={r.id} className="flex flex-col gap-3 rounded-2xl border bg-card p-4 shadow-xs">
            <div className="flex flex-col gap-1.5">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <h2 className="text-base font-semibold text-marino">{r.nombre}</h2>
                <div className="flex flex-wrap gap-1.5">
                  {r.protegido ? <Insignia estado="info">Protegido</Insignia> : null}
                  {r.inicial && !r.protegido ? <Insignia estado="neutra">Rol inicial</Insignia> : null}
                  {!r.activo ? <Insignia estado="neutra">Inactivo</Insignia> : null}
                </div>
              </div>
              <p className="text-sm text-muted-foreground">{r.descripcion ?? "Sin descripción."}</p>
              <p className="text-sm">
                {textoUsuarios(r.total_usuarios)} · {textoPermisos(r.total_permisos)}
              </p>
            </div>
            <div className="mt-auto flex flex-wrap gap-2">
              <Boton variante="normal" nativeButton={false} render={<Link to={`/roles/${r.id}`} />} aria-label={`Ver los permisos de ${r.nombre}`}>
                Ver permisos
              </Boton>
              <Boton variante="contorno" onClick={() => setModo({ tipo: "duplicar", rol: r })} aria-label={`Duplicar el rol ${r.nombre}`}>
                <CopyIcon aria-hidden="true" />
                Duplicar
              </Boton>
              <Boton
                variante="contorno"
                disabled={r.activo && razonInactivar(r) !== null}
                onClick={() => setCambiando(r)}
                aria-label={`${r.activo ? "Inactivar" : "Reactivar"} el rol ${r.nombre}`}
              >
                <PowerIcon aria-hidden="true" />
                {r.activo ? "Inactivar" : "Reactivar"}
              </Boton>
            </div>
            {r.activo && razonInactivar(r) ? <p className="text-sm text-muted-foreground">{razonInactivar(r)}</p> : null}
          </li>
        ))}
      </ul>
    );
  }

  return (
    <Pantalla
      titulo="Roles y permisos"
      descripcion="Cada persona tiene un rol y el rol decide qué puede hacer y qué información ve."
      acciones={
        <Boton variante="normal" onClick={() => setModo({ tipo: "nuevo" })}>
          <PlusIcon aria-hidden="true" />
          Nuevo rol
        </Boton>
      }
    >
      <div className="flex max-w-56 flex-col gap-1.5">
        <label htmlFor="estado-roles" className="text-sm font-medium">
          Estado
        </label>
        <ListaDesplegable id="estado-roles" valor={estado} alCambiar={setEstado} opciones={OPCIONES_ESTADO} />
      </div>
      {contenido}
      <Confirmacion
        abierta={cambiando !== null}
        alCambiar={(a) => !ocupado && !a && setCambiando(null)}
        mensaje={cambiando?.activo ? `¿Inactivar el rol ${cambiando.nombre}?` : `¿Reactivar el rol ${cambiando?.nombre ?? ""}?`}
        detalle={cambiando?.activo ? "No se podrá asignar a usuarios hasta que lo reactives." : "Se podrá asignar otra vez a usuarios."}
        etiquetaConfirmar={cambiando?.activo ? "Sí, inactivar" : "Sí, reactivar"}
        etiquetaCancelar="Volver"
        peligro={cambiando?.activo ?? false}
        cargando={ocupado}
        alConfirmar={() => void cambiarEstado()}
      />
      <HojaRol
        modo={modo}
        alCerrar={() => setModo(null)}
        alGuardar={(guardado) => {
          setModo(null);
          lista.recargar();
          void navegar(`/roles/${guardado.id}`);
        }}
      />
    </Pantalla>
  );
}
