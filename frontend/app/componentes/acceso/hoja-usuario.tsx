import { useEffect, useState, type FormEvent } from "react";

import { apiPatch, apiPost } from "~/api/cliente";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { Hoja } from "~/componentes/ui/hoja";
import { ListaDesplegable } from "~/componentes/ui/lista-desplegable";
import { Label } from "~/components/ui/label";
import { ControlAutonomia } from "~/componentes/supervision/control-autonomia";
import { erroresDeAcceso } from "./errores";
import {
  PERMISO_AUTORIZA,
  PERMISO_TODOS_LOS_ALMACENES,
  operaUnAlmacen,
  type AlmacenAcceso,
  type RolAcceso,
  type UsuarioAcceso,
} from "./tipos";

interface Propiedades {
  abierta: boolean;
  alCambiar: (abierta: boolean) => void;
  /** Usuario a editar; sin él se crea uno nuevo. */
  usuario: UsuarioAcceso | null;
  roles: RolAcceso[];
  almacenes: AlmacenAcceso[];
  alGuardar: (usuario: UsuarioAcceso, esNuevo: boolean) => void;
}

interface Errores {
  nombre?: string;
  usuario?: string;
  rol_id?: string;
  almacen_id?: string;
  contrasena?: string;
  pin?: string;
}

/** Alta de un usuario o cambio de su nombre, rol y almacén. Las reglas las decide el servidor. */
export function HojaUsuario({ abierta, alCambiar, usuario, roles, almacenes, alGuardar }: Propiedades) {
  const [nombre, setNombre] = useState("");
  const [nombreUsuario, setNombreUsuario] = useState("");
  const [rolId, setRolId] = useState("");
  const [almacenId, setAlmacenId] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [pin, setPin] = useState("");
  const [errores, setErrores] = useState<Errores>({});
  const [general, setGeneral] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    if (!abierta) return;
    setNombre(usuario?.nombre ?? "");
    setNombreUsuario(usuario?.usuario ?? "");
    setRolId(usuario?.rol.id ?? "");
    setAlmacenId(usuario?.almacen?.id ?? "");
    setContrasena("");
    setPin("");
    setErrores({});
    setGeneral(null);
  }, [abierta, usuario]);

  const rol = roles.find((r) => r.id === rolId) ?? null;
  const operaTodos = rol?.permisos.includes(PERMISO_TODOS_LOS_ALMACENES) ?? false;
  // Lleva almacén quien trabaja en uno: RH, que solo administra personas, no (RG-07).
  const llevaAlmacen = rol ? operaUnAlmacen(rol.permisos) : false;
  const autoriza = rol?.permisos.includes(PERMISO_AUTORIZA) ?? false;
  // Un rol inactivo no se puede asignar, pero el usuario que ya lo tiene debe verlo en la lista.
  const opcionesRol = roles
    .filter((r) => r.activo || r.id === usuario?.rol.id)
    .map((r) => ({ valor: r.id, texto: r.activo ? r.nombre : `${r.nombre} (inactivo)` }));

  function quitar(campo: keyof Errores) {
    setErrores((e) => ({ ...e, [campo]: undefined }));
    setGeneral(null);
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    const nuevos: Errores = {};
    if (nombre.trim() === "") nuevos.nombre = "Escribe el nombre de la persona.";
    if (!usuario && nombreUsuario.trim().length < 3) nuevos.usuario = "El usuario lleva al menos 3 caracteres.";
    if (!usuario && !/^[A-Za-z0-9._-]*$/.test(nombreUsuario)) nuevos.usuario = "Usa solo letras, números, punto, guion y guion bajo.";
    if (rolId === "") nuevos.rol_id = "Elige el rol.";
    if (rol && llevaAlmacen && almacenId === "") nuevos.almacen_id = "Elige el almacén en el que va a trabajar.";
    if (!usuario && contrasena.length < 8) nuevos.contrasena = "La contraseña lleva al menos 8 caracteres.";
    if (pin !== "" && !/^\d{4,8}$/.test(pin)) nuevos.pin = "El PIN lleva de 4 a 8 números.";
    if (Object.values(nuevos).some(Boolean)) {
      setErrores(nuevos);
      return;
    }

    setGuardando(true);
    setErrores({});
    setGeneral(null);
    try {
      let guardado: UsuarioAcceso;
      if (usuario) {
        const cambios: Record<string, unknown> = {};
        if (nombre.trim() !== usuario.nombre) cambios.nombre = nombre.trim();
        if (rolId !== usuario.rol.id) cambios.rol_id = rolId;
        const almacenNuevo = llevaAlmacen ? almacenId : null;
        if (almacenNuevo !== (usuario.almacen?.id ?? null)) cambios.almacen_id = almacenNuevo;
        if (Object.keys(cambios).length === 0) {
          alCambiar(false);
          return;
        }
        guardado = await apiPatch<UsuarioAcceso>(`/usuarios/${usuario.id}`, cambios);
      } else {
        guardado = await apiPost<UsuarioAcceso>("/usuarios", {
          nombre: nombre.trim(),
          usuario: nombreUsuario.trim(),
          contrasena,
          rol_id: rolId,
          almacen_id: llevaAlmacen ? almacenId : null,
          pin: autoriza && pin !== "" ? pin : null,
        });
      }
      aviso({ titulo: usuario ? "Los cambios quedaron guardados" : `${guardado.nombre} ya puede entrar`, tipo: "exito" });
      alCambiar(false);
      alGuardar(guardado, usuario === null);
    } catch (causa) {
      const { campos, general: texto } = erroresDeAcceso(causa);
      const lista = campos as Errores;
      // Un 409 (usuario repetido, último administrador) se explica junto al campo que corresponde.
      if (!usuario && texto && /usuario ya existe/i.test(texto)) {
        setErrores({ usuario: texto });
      } else if (Object.keys(lista).length > 0) {
        setErrores(lista);
      } else {
        setGeneral(texto);
      }
    } finally {
      setGuardando(false);
    }
  }

  return (
    <Hoja
      abierta={abierta}
      alCambiar={(a) => !guardando && alCambiar(a)}
      titulo={usuario ? "Editar usuario" : "Nuevo usuario"}
      descripcion={
        usuario
          ? "El cambio de rol o de almacén aplica en cuanto la persona vuelva a usar el sistema."
          : "Quien entra con esta cuenta solo puede hacer lo que su rol permite."
      }
      pie={
        <>
          {general ? (
            <p role="alert" className="text-sm font-medium text-destructive">
              {general}
            </p>
          ) : null}
          <Boton variante="principal" type="submit" form="formulario-usuario" cargando={guardando}>
            {usuario ? "Guardar cambios" : "Crear usuario"}
          </Boton>
        </>
      }
    >
      <form id="formulario-usuario" onSubmit={enviar} noValidate className="flex flex-col gap-4">
        {usuario && usuario.despacho_autonomo !== undefined && roles.find((r) => r.id === usuario.rol.id)?.permisos.includes("entregas.crear") ? <ControlAutonomia
          key={usuario.id} ruta={`/usuarios/${usuario.id}/autonomia`} campo="despacho_autonomo" valor={usuario.despacho_autonomo}
          etiqueta="Despacha equipo de protección sin aprobación" bloqueado={guardando}
          alGuardar={(valor) => alGuardar({ ...usuario, despacho_autonomo: valor }, false)}
        /> : null}
        <Campo
          etiqueta="Nombre completo"
          value={nombre}
          maxLength={150}
          autoComplete="off"
          onChange={(e) => {
            setNombre(e.target.value);
            quitar("nombre");
          }}
          error={errores.nombre}
        />
        <Campo
          etiqueta="Usuario para entrar"
          value={nombreUsuario}
          maxLength={60}
          autoComplete="off"
          autoCapitalize="none"
          disabled={usuario !== null}
          ayuda={usuario ? "El usuario no se puede cambiar." : "Sin espacios. Por ejemplo: jperez."}
          onChange={(e) => {
            setNombreUsuario(e.target.value);
            quitar("usuario");
          }}
          error={errores.usuario}
        />
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="usuario-rol" className="text-sm font-medium text-foreground">
            Rol
          </Label>
          <ListaDesplegable
            id="usuario-rol"
            valor={rolId}
            alCambiar={(v) => {
              setRolId(v);
              quitar("rol_id");
              quitar("almacen_id");
            }}
            marcador="Elige el rol"
            opciones={opcionesRol}
            invalido={Boolean(errores.rol_id)}
            descritoPor={errores.rol_id ? "usuario-rol-error" : undefined}
          />
          {errores.rol_id ? (
            <p id="usuario-rol-error" role="alert" className="text-sm font-medium text-destructive">
              {errores.rol_id}
            </p>
          ) : null}
        </div>
        {rol && llevaAlmacen ? (
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="usuario-almacen" className="text-sm font-medium text-foreground">
              Almacén donde trabaja
            </Label>
            <ListaDesplegable
              id="usuario-almacen"
              valor={almacenId}
              alCambiar={(v) => {
                setAlmacenId(v);
                quitar("almacen_id");
              }}
              marcador="Elige el almacén"
              opciones={almacenes.map((a) => ({ valor: a.id, texto: a.nombre }))}
              invalido={Boolean(errores.almacen_id)}
              descritoPor={errores.almacen_id ? "usuario-almacen-error" : undefined}
            />
            {errores.almacen_id ? (
              <p id="usuario-almacen-error" role="alert" className="text-sm font-medium text-destructive">
                {errores.almacen_id}
              </p>
            ) : null}
          </div>
        ) : null}
        {rol && !llevaAlmacen ? (
          <p className="rounded-2xl border bg-accent p-3 text-sm text-marino">
            {operaTodos
              ? "Este rol opera todos los almacenes, así que no lleva un almacén asignado."
              : "Este rol no trabaja en un almacén, así que no lleva uno asignado."}
          </p>
        ) : null}
        {!usuario ? (
          <>
            <Campo
              etiqueta="Contraseña inicial"
              type="password"
              value={contrasena}
              autoComplete="new-password"
              ayuda="Al menos 8 caracteres. Díselo a la persona; después puedes restablecerla."
              onChange={(e) => {
                setContrasena(e.target.value);
                quitar("contrasena");
              }}
              error={errores.contrasena}
            />
            {autoriza ? (
              <Campo
                etiqueta="PIN para autorizar (opcional)"
                type="password"
                inputMode="numeric"
                value={pin}
                maxLength={8}
                autoComplete="off"
                ayuda="De 4 a 8 números y distinto de la contraseña. Sin PIN no podrá autorizar entregas."
                onChange={(e) => {
                  setPin(e.target.value.replace(/\D/g, ""));
                  quitar("pin");
                }}
                error={errores.pin}
              />
            ) : null}
          </>
        ) : autoriza && !usuario.tiene_pin ? (
          <p className="rounded-2xl border bg-muted p-3 text-sm">
            Este rol autoriza entregas y la persona aún no tiene PIN. Asígnaselo con «Restablecer contraseña».
          </p>
        ) : null}
      </form>
    </Hoja>
  );
}
