import { ArrowLeftIcon, CopyIcon, PencilIcon } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";

import { api, apiDelete, apiGet, apiPatch } from "~/api/cliente";
import { mensajeDeError } from "~/api/errores";
import { HojaRol, type ModoHojaRol } from "~/componentes/acceso/hoja-rol";
import { MatrizPermisos } from "~/componentes/acceso/matriz-permisos";
import {
  PERMISO_ADMINISTRAR,
  PERMISO_TODOS_LOS_ALMACENES,
  textoPermisos,
  textoUsuarios,
  type PermisoInfo,
  type RolAcceso,
} from "~/componentes/acceso/tipos";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { AccionPrincipal, Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { Confirmacion } from "~/componentes/ui/confirmacion";
import { EstadoError } from "~/componentes/ui/estado-error";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { Insignia } from "~/componentes/ui/insignia";
import { useSesionActiva } from "~/sesion/sesion";

export const handle: ManejadorRuta = { permiso: "acceso.administrar" };

function plural(n: number, uno: string, varios: string): string {
  return `${n} ${n === 1 ? uno : varios}`;
}

/** "Se agregan 2 permisos y se quitan 1". */
function resumenDeCambios(agregan: number, quitan: number): string {
  const partes: string[] = [];
  if (agregan > 0) partes.push(`${agregan === 1 ? "se agrega" : "se agregan"} ${plural(agregan, "permiso", "permisos")}`);
  if (quitan > 0) partes.push(`${quitan === 1 ? "se quita" : "se quitan"} ${plural(quitan, "permiso", "permisos")}`);
  const texto = partes.join(" y ");
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

export default function RolDetalle() {
  const { id = "" } = useParams();
  const navegar = useNavigate();
  const { sesion, recargar: recargarSesion } = useSesionActiva();

  const catalogo = useConsulta((signal) => apiGet<PermisoInfo[]>("/permisos", undefined, signal), "permisos");
  const consulta = useConsulta((signal) => apiGet<RolAcceso>(`/roles/${id}`, undefined, signal), `rol-${id}`);
  const [rol, setRol] = useState<RolAcceso | null>(null);
  const [activos, setActivos] = useState<Set<string>>(new Set());
  const [modo, setModo] = useState<ModoHojaRol | null>(null);
  const [confirmando, setConfirmando] = useState<"guardar" | "eliminar" | "estado" | null>(null);
  const [ocupado, setOcupado] = useState(false);

  useEffect(() => {
    if (consulta.datos) {
      setRol(consulta.datos);
      setActivos(new Set(consulta.datos.permisos));
    }
  }, [consulta.datos]);

  const guardados = useMemo(() => new Set(rol?.permisos ?? []), [rol]);
  const porClave = useMemo(() => new Map((catalogo.datos ?? []).map((p) => [p.clave, p])), [catalogo.datos]);

  const agregados = [...activos].filter((c) => !guardados.has(c));
  const quitados = [...guardados].filter((c) => !activos.has(c));
  const hayCambios = agregados.length + quitados.length > 0;
  const esMiRol = rol?.id === sesion.rol.id;

  function descripcionDe(clave: string): string {
    return porClave.get(clave)?.descripcion ?? clave;
  }

  /** Por qué un permiso no se puede mover ahora; el servidor valida lo mismo al guardar. */
  function razonBloqueo(clave: string): string | null {
    if (!rol) return null;
    if (clave === PERMISO_ADMINISTRAR && rol.protegido) return "El rol Administrador siempre lleva este permiso.";
    if (clave === PERMISO_ADMINISTRAR && esMiRol && activos.has(clave)) {
      return "No puedes quitártelo a ti mismo: perderías el acceso a esta pantalla.";
    }
    if (activos.has(clave)) {
      const dependientes = [...activos].filter((c) => porClave.get(c)?.requiere.includes(clave));
      if (dependientes.length > 0) {
        return `Lo necesita «${descripcionDe(dependientes[0])}»${dependientes.length > 1 ? ` y ${dependientes.length - 1} más` : ""}. Quítalo primero.`;
      }
    }
    return null;
  }

  function cambiar(clave: string, activo: boolean) {
    setActivos((actual) => {
      const nuevo = new Set(actual);
      if (activo) {
        nuevo.add(clave);
        // Un permiso de acción incluye el de ver su módulo: se activan juntos.
        porClave.get(clave)?.requiere.forEach((c) => nuevo.add(c));
      } else {
        nuevo.delete(clave);
      }
      return nuevo;
    });
  }

  async function guardarPermisos() {
    if (!rol) return;
    setOcupado(true);
    try {
      const actualizado = await api<RolAcceso>(`/roles/${rol.id}/permisos`, { metodo: "PUT", cuerpo: { permisos: [...activos] } });
      setRol(actualizado);
      setActivos(new Set(actualizado.permisos));
      aviso({ titulo: "Los cambios ya aplican", descripcion: "Cada persona los nota en su siguiente acción.", tipo: "exito" });
      if (esMiRol) void recargarSesion();
    } catch (causa) {
      aviso({ titulo: "No se guardaron los cambios", descripcion: mensajeDeError(causa), tipo: "error", duracionMs: 9000 });
    } finally {
      setOcupado(false);
      setConfirmando(null);
    }
  }

  async function cambiarEstado() {
    if (!rol) return;
    setOcupado(true);
    try {
      const actualizado = await apiPatch<RolAcceso>(`/roles/${rol.id}`, { activo: !rol.activo });
      setRol(actualizado);
      aviso({ titulo: actualizado.activo ? "El rol quedó activo" : "El rol quedó inactivo", tipo: "exito" });
    } catch (causa) {
      aviso({ titulo: "No se pudo hacer el cambio", descripcion: mensajeDeError(causa), tipo: "error", duracionMs: 9000 });
    } finally {
      setOcupado(false);
      setConfirmando(null);
    }
  }

  async function eliminar() {
    if (!rol) return;
    setOcupado(true);
    try {
      await apiDelete(`/roles/${rol.id}`);
      aviso({ titulo: `Se eliminó el rol ${rol.nombre}`, tipo: "exito" });
      void navegar("/roles");
    } catch (causa) {
      aviso({ titulo: "No se pudo eliminar", descripcion: mensajeDeError(causa), tipo: "error", duracionMs: 9000 });
      setOcupado(false);
      setConfirmando(null);
    }
  }

  if ((consulta.error && !rol) || (catalogo.error && !catalogo.datos)) {
    return (
      <Pantalla titulo="Rol">
        <EstadoError
          error={consulta.error ?? catalogo.error}
          alReintentar={() => {
            consulta.recargar();
            catalogo.recargar();
          }}
        />
      </Pantalla>
    );
  }
  if (!rol || !catalogo.datos) {
    return (
      <Pantalla titulo="Rol">
        <Esqueleto tipo="tarjeta" cantidad={4} />
      </Pantalla>
    );
  }

  // Razones por las que no se puede inactivar o eliminar; cada una se explica junto al botón.
  const razonInactivar = rol.protegido
    ? "El rol Administrador no se puede inactivar."
    : rol.total_usuarios > 0
      ? `Tiene ${textoUsuarios(rol.total_usuarios).toLowerCase()}. Cámbiales el rol en Usuarios y vuelve a intentarlo.`
      : null;
  const razonEliminar = rol.protegido
    ? "El rol Administrador no se puede eliminar."
    : rol.inicial
      ? "Los cinco roles iniciales no se eliminan; si ya no lo usas, inactívalo."
      : rol.total_usuarios > 0
        ? `Tiene ${textoUsuarios(rol.total_usuarios).toLowerCase()}. Cámbiales el rol en Usuarios y vuelve a intentarlo.`
        : null;

  const efectosAlmacen: string[] = [];
  if (rol.total_usuarios > 0) {
    if (agregados.includes(PERMISO_TODOS_LOS_ALMACENES)) {
      efectosAlmacen.push(`Sus ${textoUsuarios(rol.total_usuarios).toLowerCase()} dejarán de tener un almacén asignado: operan todos.`);
    }
    if (quitados.includes(PERMISO_TODOS_LOS_ALMACENES)) {
      efectosAlmacen.push(
        `Sus ${textoUsuarios(rol.total_usuarios).toLowerCase()} quedarán sin almacén hasta que alguien se lo asigne en Personal.`,
      );
    }
  }
  const reservados = agregados.filter((c) => porClave.get(c)?.es_de_informacion);

  return (
    <Pantalla
      titulo={rol.nombre}
      descripcion={rol.descripcion ?? "Elige qué puede hacer y qué información puede ver este rol."}
      acciones={
        <>
          <Boton variante="contorno" onClick={() => setModo({ tipo: "duplicar", rol })}>
            <CopyIcon aria-hidden="true" />
            Duplicar
          </Boton>
          <Boton variante="contorno" onClick={() => setModo({ tipo: "editar", rol })}>
            <PencilIcon aria-hidden="true" />
            Editar
          </Boton>
        </>
      }
    >
      <div className={hayCambios ? "flex flex-col gap-5 pb-40 lg:pb-0" : "flex flex-col gap-5"}>
        <Boton variante="texto" className="self-start -ml-2" nativeButton={false} render={<Link to="/roles" />}>
          <ArrowLeftIcon aria-hidden="true" />
          Todos los roles
        </Boton>

        <div className="flex flex-wrap items-center gap-2">
          {rol.protegido ? <Insignia estado="info">Protegido</Insignia> : null}
          {rol.inicial && !rol.protegido ? <Insignia estado="neutra">Rol inicial</Insignia> : null}
          {!rol.activo ? <Insignia estado="neutra">Inactivo</Insignia> : null}
          <span className="text-sm text-muted-foreground">
            {textoUsuarios(rol.total_usuarios)} · {textoPermisos(rol.permisos.length)}
          </span>
        </div>

        {rol.permisos.length === 0 && !hayCambios ? (
          <p className="rounded-2xl border bg-accent p-3 text-sm text-marino">
            Este rol no tiene permisos: quien lo tenga entra al sistema pero no ve ningún módulo. Activa abajo lo que necesita.
          </p>
        ) : null}

        <MatrizPermisos
          catalogo={catalogo.datos}
          activos={activos}
          guardados={guardados}
          alCambiar={cambiar}
          razonBloqueo={razonBloqueo}
          deshabilitada={ocupado}
        />

        <section aria-labelledby="zona-rol" className="flex flex-col gap-3 rounded-2xl border bg-card p-4 shadow-xs">
          <h2 id="zona-rol" className="text-base font-semibold text-marino">
            Estado del rol
          </h2>
          <div className="flex flex-col gap-1.5">
            <Boton
              variante="contorno"
              className="self-start"
              disabled={razonInactivar !== null && rol.activo}
              onClick={() => setConfirmando("estado")}
            >
              {rol.activo ? "Inactivar rol" : "Reactivar rol"}
            </Boton>
            {rol.activo && razonInactivar ? <p className="text-sm text-muted-foreground">{razonInactivar}</p> : null}
            {!rol.activo ? <p className="text-sm text-muted-foreground">Un rol inactivo no se puede asignar a usuarios nuevos.</p> : null}
          </div>
          <div className="flex flex-col gap-1.5">
            <Boton variante="peligro" className="self-start" disabled={razonEliminar !== null} onClick={() => setConfirmando("eliminar")}>
              Eliminar rol
            </Boton>
            {razonEliminar ? <p className="text-sm text-muted-foreground">{razonEliminar}</p> : null}
          </div>
        </section>
      </div>

      {hayCambios ? (
        <AccionPrincipal>
          <div className="flex flex-col gap-1 rounded-2xl border bg-accent p-3 text-sm text-marino" role="status">
            <p className="font-semibold">{resumenDeCambios(agregados.length, quitados.length)}</p>
            {agregados.length > 0 ? <p>Se agrega: {agregados.map(descripcionDe).join("; ")}.</p> : null}
            {quitados.length > 0 ? <p>Se quita: {quitados.map(descripcionDe).join("; ")}.</p> : null}
            {efectosAlmacen.map((t) => (
              <p key={t}>{t}</p>
            ))}
            {reservados.length > 0 ? <p>Incluye información reservada: revisa que este rol deba verla.</p> : null}
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Boton variante="contorno" disabled={ocupado} onClick={() => setActivos(new Set(guardados))}>
              Descartar
            </Boton>
            <Boton variante="normal" disabled={ocupado} onClick={() => setConfirmando("guardar")}>
              Guardar cambios
            </Boton>
          </div>
        </AccionPrincipal>
      ) : null}

      <Confirmacion
        abierta={confirmando === "guardar"}
        alCambiar={(a) => !ocupado && !a && setConfirmando(null)}
        mensaje={`¿Guardar los cambios de ${rol.nombre}?`}
        detalle={`${resumenDeCambios(agregados.length, quitados.length)}. ${rol.total_usuarios === 0 ? "Todavía nadie tiene este rol." : `Aplican en la siguiente acción de ${textoUsuarios(rol.total_usuarios).toLowerCase()}.`}`}
        etiquetaConfirmar="Sí, guardar"
        etiquetaCancelar="Volver"
        cargando={ocupado}
        alConfirmar={guardarPermisos}
      />
      <Confirmacion
        abierta={confirmando === "estado"}
        alCambiar={(a) => !ocupado && !a && setConfirmando(null)}
        mensaje={rol.activo ? `¿Inactivar el rol ${rol.nombre}?` : `¿Reactivar el rol ${rol.nombre}?`}
        detalle={rol.activo ? "No se podrá asignar a usuarios hasta que lo reactives." : "Se podrá asignar otra vez a usuarios."}
        etiquetaConfirmar={rol.activo ? "Sí, inactivar" : "Sí, reactivar"}
        etiquetaCancelar="Volver"
        peligro={rol.activo}
        cargando={ocupado}
        alConfirmar={cambiarEstado}
      />
      <Confirmacion
        abierta={confirmando === "eliminar"}
        alCambiar={(a) => !ocupado && !a && setConfirmando(null)}
        mensaje={`¿Eliminar el rol ${rol.nombre}?`}
        detalle="Esto no se puede deshacer. Si lo necesitas después, tendrás que crearlo de nuevo."
        etiquetaConfirmar="Sí, eliminar"
        etiquetaCancelar="Volver"
        peligro
        cargando={ocupado}
        alConfirmar={eliminar}
      />
      <HojaRol
        modo={modo}
        alCerrar={() => setModo(null)}
        alGuardar={(guardado, usado) => {
          setModo(null);
          if (usado.tipo === "editar") {
            setRol(guardado);
          } else {
            void navegar(`/roles/${guardado.id}`);
          }
        }}
      />
    </Pantalla>
  );
}
