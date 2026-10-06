import { useEffect, useState, type FormEvent } from "react";

import { apiPost } from "~/api/cliente";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { Confirmacion } from "~/componentes/ui/confirmacion";
import { Hoja } from "~/componentes/ui/hoja";
import { erroresDeAcceso } from "./errores";
import { PERMISO_AUTORIZA, type RolAcceso, type UsuarioAcceso } from "./tipos";

interface Propiedades {
  usuario: UsuarioAcceso | null;
  roles: RolAcceso[];
  alCerrar: () => void;
  alGuardar: (usuario: UsuarioAcceso) => void;
}

interface Errores {
  contrasena?: string;
  repetir?: string;
  pin?: string;
}

/** Restablece la contraseña (y el PIN, si el rol autoriza) con una confirmación antes de guardar. */
export function HojaContrasena({ usuario, roles, alCerrar, alGuardar }: Propiedades) {
  const [contrasena, setContrasena] = useState("");
  const [repetir, setRepetir] = useState("");
  const [pin, setPin] = useState("");
  const [errores, setErrores] = useState<Errores>({});
  const [general, setGeneral] = useState<string | null>(null);
  const [confirmando, setConfirmando] = useState(false);
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    setContrasena("");
    setRepetir("");
    setPin("");
    setErrores({});
    setGeneral(null);
    setConfirmando(false);
    setGuardando(false);
  }, [usuario]);

  const autoriza = roles.find((r) => r.id === usuario?.rol.id)?.permisos.includes(PERMISO_AUTORIZA) ?? false;

  function revisar(evento: FormEvent) {
    evento.preventDefault();
    const nuevos: Errores = {};
    if (contrasena.length < 8) nuevos.contrasena = "La contraseña lleva al menos 8 caracteres.";
    else if (repetir !== contrasena) nuevos.repetir = "Las dos contraseñas no coinciden.";
    if (pin !== "" && !/^\d{4,8}$/.test(pin)) nuevos.pin = "El PIN lleva de 4 a 8 números.";
    if (Object.values(nuevos).some(Boolean)) {
      setErrores(nuevos);
      return;
    }
    setErrores({});
    setConfirmando(true);
  }

  async function guardar() {
    if (!usuario) return;
    setGuardando(true);
    try {
      const actualizado = await apiPost<UsuarioAcceso>(`/usuarios/${usuario.id}/contrasena`, {
        contrasena,
        pin: autoriza && pin !== "" ? pin : null,
      });
      aviso({ titulo: `Se restableció la contraseña de ${usuario.nombre}`, tipo: "exito" });
      setConfirmando(false);
      alGuardar(actualizado);
    } catch (causa) {
      const { campos, general: texto } = erroresDeAcceso(causa);
      setConfirmando(false);
      setErrores(campos as Errores);
      setGeneral(texto);
      setGuardando(false);
    }
  }

  return (
    <>
      <Hoja
        abierta={usuario !== null}
        alCambiar={(a) => !a && !guardando && alCerrar()}
        titulo="Restablecer contraseña"
        descripcion={usuario ? `${usuario.nombre} · ${usuario.usuario}` : undefined}
        pie={
          <>
            {general ? (
              <p role="alert" className="text-sm font-medium text-destructive">
                {general}
              </p>
            ) : null}
            <Boton variante="principal" type="submit" form="formulario-contrasena">
              Restablecer
            </Boton>
          </>
        }
      >
        <form id="formulario-contrasena" onSubmit={revisar} noValidate className="flex flex-col gap-4">
          <p className="rounded-2xl border bg-accent p-3 text-sm text-marino">
            Al restablecerla se cierran las sesiones abiertas de la persona y se quitan sus bloqueos por intentos fallidos.
          </p>
          <Campo
            etiqueta="Contraseña nueva"
            type="password"
            value={contrasena}
            autoComplete="new-password"
            ayuda="Al menos 8 caracteres."
            onChange={(e) => {
              setContrasena(e.target.value);
              setErrores((x) => ({ ...x, contrasena: undefined }));
            }}
            error={errores.contrasena}
          />
          <Campo
            etiqueta="Repite la contraseña"
            type="password"
            value={repetir}
            autoComplete="new-password"
            onChange={(e) => {
              setRepetir(e.target.value);
              setErrores((x) => ({ ...x, repetir: undefined }));
            }}
            error={errores.repetir}
          />
          {autoriza ? (
            <Campo
              etiqueta="PIN nuevo (opcional)"
              type="password"
              inputMode="numeric"
              value={pin}
              maxLength={8}
              autoComplete="off"
              ayuda={`De 4 a 8 números y distinto de la contraseña. ${usuario?.tiene_pin ? "Si lo dejas vacío, conserva el que tiene." : "Sin PIN no puede autorizar entregas."}`}
              onChange={(e) => {
                setPin(e.target.value.replace(/\D/g, ""));
                setErrores((x) => ({ ...x, pin: undefined }));
              }}
              error={errores.pin}
            />
          ) : null}
        </form>
      </Hoja>
      <Confirmacion
        abierta={confirmando}
        alCambiar={(a) => !guardando && setConfirmando(a)}
        mensaje={`¿Restablecer la contraseña de ${usuario?.nombre ?? ""}?`}
        detalle="La contraseña anterior deja de servir y se cierran sus sesiones abiertas."
        etiquetaConfirmar="Sí, restablecer"
        etiquetaCancelar="Volver"
        cargando={guardando}
        alConfirmar={guardar}
      />
    </>
  );
}
