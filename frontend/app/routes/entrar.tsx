import { CircleAlertIcon, TimerIcon, UserRoundIcon } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router";

import { esErrorApi, formatearEspera, mensajeDeError } from "~/api/errores";
import { Boton } from "~/componentes/ui/boton";
import { Campo } from "~/componentes/ui/campo";
import { CampoClave } from "~/componentes/ui/campo-clave";
import { Cargando } from "~/componentes/ui/cargando";
import { rutaDeRegreso, useSesion } from "~/sesion/sesion";

export function meta() {
  return [{ title: "Entrar · IMHOTEP" }];
}

export default function Entrar() {
  const { estado, iniciarSesion } = useSesion();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const volver = rutaDeRegreso(params.get("volver"));

  const [usuario, setUsuario] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [espera, setEspera] = useState(0);
  const botonRef = useRef<HTMLButtonElement>(null);

  // Cuenta regresiva del bloqueo temporal.
  useEffect(() => {
    if (espera <= 0) return;
    const reloj = window.setInterval(() => {
      setEspera((s) => {
        if (s <= 1) {
          window.clearInterval(reloj);
          setError(null);
          return 0;
        }
        return s - 1;
      });
    }, 1000);
    return () => window.clearInterval(reloj);
  }, [espera > 0]); // eslint-disable-line react-hooks/exhaustive-deps

  if (estado === "cargando") return <Cargando variante="pantalla" />;
  if (estado === "autenticada" && !enviando) return <Navigate to={volver} replace />;

  const enviar = async (evento: FormEvent) => {
    evento.preventDefault();
    if (enviando || espera > 0) return;
    setEnviando(true);
    setError(null);
    try {
      await iniciarSesion(usuario.trim(), contrasena);
      navigate(volver, { replace: true });
    } catch (causa) {
      setEnviando(false);
      setContrasena("");
      if (esErrorApi(causa) && causa.segundosEspera !== null) setEspera(causa.segundosEspera);
      setError(mensajeDeError(causa));
    }
  };

  const enBloqueo = espera > 0;

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-sm flex-col justify-start gap-8 px-4 pt-10 pb-8 sm:pt-[10vh]">
      <div className="flex flex-col items-center gap-3 text-center">
        <img src="/logo-imhotep.png" alt="IMHOTEP" width={160} height={151} className="h-auto w-36" />
        <h1>Control de herramientas y equipo de protección</h1>
      </div>

      <form onSubmit={enviar} className="flex flex-col gap-5" noValidate>
        <Campo
          etiqueta="Usuario"
          icono={<UserRoundIcon />}
          name="usuario"
          autoComplete="username"
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          enterKeyHint="next"
          autoFocus
          required
          value={usuario}
          onChange={(e) => setUsuario(e.target.value)}
        />
        <CampoClave
          etiqueta="Contraseña"
          name="contrasena"
          autoComplete="current-password"
          enterKeyHint="go"
          required
          value={contrasena}
          onChange={(e) => setContrasena(e.target.value)}
          onFocus={() => window.setTimeout(() => botonRef.current?.scrollIntoView({ block: "nearest" }), 300)}
        />

        <div className="flex flex-col gap-3">
          <Boton
            ref={botonRef}
            type="submit"
            variante="principal"
            cargando={enviando}
            disabled={enBloqueo || !usuario.trim() || !contrasena}
          >
            {enviando ? "Entrando" : "Entrar"}
          </Boton>

          {error ? (
            <div
              role="alert"
              className="flex items-start gap-2 rounded-xl border border-destructive/40 bg-destructive/5 p-3 text-sm font-medium text-destructive"
            >
              {enBloqueo ? (
                <TimerIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
              ) : (
                <CircleAlertIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
              )}
              <p>
                {error}
                {enBloqueo ? (
                  <>
                    {" "}
                    Podrás intentar de nuevo en{" "}
                    <strong className="tabular-nums">{formatearEspera(espera)}</strong>.
                  </>
                ) : null}
              </p>
            </div>
          ) : null}
        </div>
      </form>
    </main>
  );
}
