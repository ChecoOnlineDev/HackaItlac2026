import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import {
  api,
  registrarManejadorSesionRenovada,
  registrarManejadorSesionVencida,
} from "~/api/cliente";
import { esErrorApi } from "~/api/errores";
import { cancelarAvisos, registrarAvisosConPermiso } from "~/pwa/avisos";
import type { Permiso, Sesion } from "~/api/tipos";

type Estado = "cargando" | "autenticada" | "anonima";

interface ValorSesion {
  /** `cargando` mientras se pregunta al servidor; `anonima` si no hay sesión. */
  estado: Estado;
  /**
   * Por qué no hay sesión: `salio` si cerró sesión él mismo (no hay ruta a la que volver);
   * `vencida` si el servidor ya no pudo renovarla (venció o la cerraron desde otro dispositivo).
   */
  motivoSinSesion: "inicial" | "salio" | "vencida";
  /** La sesión, o null si no hay. Dentro de una pantalla protegida siempre existe: usa `useSesionActiva`. */
  sesion: Sesion | null;
  /** `true` si el usuario tiene el permiso. Es lo único que decide qué se muestra; nunca el nombre del rol. */
  puede: (permiso: Permiso) => boolean;
  /** `true` si tiene al menos uno de los permisos. */
  puedeAlguno: (permisos: readonly Permiso[]) => boolean;
  iniciarSesion: (usuario: string, contrasena: string) => Promise<Sesion>;
  /** Cierra la sesión de ESTE dispositivo. */
  cerrarSesion: () => Promise<void>;
  /** Cierra las sesiones de todos los dispositivos, también esta. Lanza si el servidor no responde. */
  cerrarTodas: () => Promise<void>;
  recargar: () => Promise<void>;
  cambiarAlmacen: (almacenId: string) => Promise<void>;
}

/** Los borradores de vale guardan la ficha del trabajador y la firma: al salir o vencer la sesión se borran. */
function borrarBorradoresLocales() {
  try {
    const claves: string[] = [];
    for (let i = 0; i < window.localStorage.length; i++) {
      const clave = window.localStorage.key(i);
      if (clave?.startsWith("imhotep.borrador.")) claves.push(clave);
    }
    claves.forEach((c) => window.localStorage.removeItem(c));
  } catch {
    // Sin almacenamiento no hay nada que borrar.
  }
}

const ContextoSesion = createContext<ValorSesion | null>(null);

export function SesionProvider({ children }: { children: ReactNode }) {
  const [estado, setEstado] = useState<Estado>("cargando");
  const [sesion, setSesion] = useState<Sesion | null>(null);
  const [motivoSinSesion, setMotivo] = useState<ValorSesion["motivoSinSesion"]>("inicial");

  // Para que una petición rezagada (un conteo que sigue en vuelo) no marque como «vencida» una
  // sesión que la persona acaba de cerrar ella misma.
  const hayRef = useRef(false);

  const aplicar = useCallback((nueva: Sesion | null) => {
    hayRef.current = nueva !== null;
    setSesion(nueva);
    setEstado(nueva ? "autenticada" : "anonima");
  }, []);

  const recargar = useCallback(async () => {
    try {
      aplicar(await api<Sesion>("/sesion", { sinRedirigir: true }));
    } catch (error) {
      // Sin conexión no equivale a "sin sesión": se conserva lo que había.
      if (esErrorApi(error) && error.sinConexion) {
        setEstado((actual) => (actual === "cargando" ? "anonima" : actual));
        return;
      }
      aplicar(null);
    }
  }, [aplicar]);

  useEffect(() => {
    void recargar();
  }, [recargar]);

  // Si una llamada responde 401 y la renovación automática tampoco funciona, la sesión venció:
  // la guardia lleva a Entrar (con el mensaje y la ruta a la que volver).
  useEffect(() => {
    registrarManejadorSesionVencida(() => {
      if (!hayRef.current) return;
      borrarBorradoresLocales();
      setMotivo("vencida");
      aplicar(null);
    });
    return () => registrarManejadorSesionVencida(null);
  }, [aplicar]);

  // Cada renovación trae los permisos y el almacén al día; solo se actualiza si algo cambió.
  useEffect(() => {
    registrarManejadorSesionRenovada((nueva) => {
      setSesion((actual) => (actual && JSON.stringify(actual) !== JSON.stringify(nueva) ? nueva : actual));
    });
    return () => registrarManejadorSesionRenovada(null);
  }, []);

  const iniciarSesion = useCallback(
    async (usuario: string, contrasena: string) => {
      const nueva = await api<Sesion>("/sesion", {
        metodo: "POST",
        cuerpo: { usuario, contrasena },
        sinRedirigir: true,
        sinRenovar: true,
      });
      aplicar(nueva);
      return nueva;
    },
    [aplicar],
  );

  const cerrarSesion = useCallback(async () => {
    await cancelarAvisos().catch(() => undefined);
    try {
      // Cierra solo la sesión de ESTE dispositivo; las de los demás siguen abiertas.
      await api("/sesion", { metodo: "DELETE", sinRedirigir: true });
    } catch {
      // Aunque falle la red, se sale de la interfaz; la sesión vence sola.
    }
    borrarBorradoresLocales();
    setMotivo("salio");
    aplicar(null);
  }, [aplicar]);

  const cerrarTodas = useCallback(async () => {
    await cancelarAvisos().catch(() => undefined);
    await api("/sesion/todas", { metodo: "DELETE", sinRedirigir: true });
    borrarBorradoresLocales();
    setMotivo("salio");
    aplicar(null);
  }, [aplicar]);

  const cambiarAlmacen = useCallback(async (almacenId: string) => {
    const nueva = await api<Sesion>("/sesion/almacen", { metodo: "PUT", cuerpo: { almacen_id: almacenId } });
    aplicar(nueva);
  }, [aplicar]);

  useEffect(() => {
    if (sesion?.permisos.includes("autorizaciones.resolver")) void registrarAvisosConPermiso().catch(() => undefined);
  }, [sesion?.usuario.id, sesion?.permisos]);

  const valor = useMemo<ValorSesion>(() => {
    const permisos = new Set(sesion?.permisos ?? []);
    return {
      estado,
      motivoSinSesion,
      sesion,
      puede: (permiso) => permisos.has(permiso),
      puedeAlguno: (lista) => lista.some((p) => permisos.has(p)),
      iniciarSesion,
      cerrarSesion,
      cerrarTodas,
      recargar,
      cambiarAlmacen,
    };
  }, [estado, motivoSinSesion, sesion, iniciarSesion, cerrarSesion, cerrarTodas, recargar, cambiarAlmacen]);

  return <ContextoSesion.Provider value={valor}>{children}</ContextoSesion.Provider>;
}

export function useSesion(): ValorSesion {
  const valor = useContext(ContextoSesion);
  if (!valor) throw new Error("useSesion se usa dentro de SesionProvider");
  return valor;
}

/** Para pantallas protegidas: la sesión siempre existe ahí. */
export function useSesionActiva(): ValorSesion & { sesion: Sesion } {
  const valor = useSesion();
  if (!valor.sesion) throw new Error("useSesionActiva se usa solo dentro de una pantalla protegida");
  return valor as ValorSesion & { sesion: Sesion };
}

/** Acepta solo rutas internas para volver tras entrar. */
export function rutaDeRegreso(valor: string | null): string {
  if (!valor || !valor.startsWith("/") || valor.startsWith("//") || valor.startsWith("/entrar")) {
    return "/";
  }
  return valor;
}
