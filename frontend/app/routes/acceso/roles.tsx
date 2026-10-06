import { CopyIcon, PlusIcon, ShieldIcon } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router";

import { apiGet } from "~/api/cliente";
import { HojaRol, type ModoHojaRol } from "~/componentes/acceso/hoja-rol";
import { textoPermisos, textoUsuarios, type RolAcceso } from "~/componentes/acceso/tipos";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { Boton } from "~/componentes/ui/boton";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { Insignia } from "~/componentes/ui/insignia";

export const handle: ManejadorRuta = { permiso: "acceso.administrar" };

export default function Roles() {
  const navegar = useNavigate();
  const lista = useConsulta((signal) => apiGet<RolAcceso[]>("/roles", undefined, signal), "roles");
  const [modo, setModo] = useState<ModoHojaRol | null>(null);
  const roles = lista.datos ?? [];

  let contenido;
  if (lista.error && !lista.datos) {
    contenido = <EstadoError error={lista.error} alReintentar={lista.recargar} />;
  } else if (lista.cargando && !lista.datos) {
    contenido = <Esqueleto tipo="tarjeta" cantidad={4} />;
  } else if (roles.length === 0) {
    contenido = (
      <EstadoVacio
        icono={ShieldIcon}
        titulo="Todavía no hay roles"
        descripcion="Crea el primero con «Nuevo rol»."
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
            </div>
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
      {contenido}
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
