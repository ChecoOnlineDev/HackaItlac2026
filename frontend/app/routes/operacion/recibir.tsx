import { InboxIcon, RefreshCwIcon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router";

import { apiGet } from "~/api/cliente";
import { mensajeDeError } from "~/api/errores";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { Escaner } from "~/componentes/dominio/escaner";
import { reproducir } from "~/componentes/dominio/sonido";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { idDeTraspasoPorToken } from "~/componentes/traspasos/buscar-traspaso";
import { tokenDeLectura } from "~/componentes/traspasos/formato";
import { TarjetaTraspaso } from "~/componentes/traspasos/tarjeta-traspaso";
import type { PorRecibirApi } from "~/componentes/traspasos/tipos";
import { aviso } from "~/componentes/ui/aviso";
import { Boton } from "~/componentes/ui/boton";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { refrescarContadores } from "~/sesion/contadores";
import { useSesionActiva } from "~/sesion/sesion";

export const handle: ManejadorRuta = { permiso: "traspasos.operar" };

export default function Recibir() {
  const { puede } = useSesionActiva();
  const navegar = useNavigate();
  const operaTodos = puede("almacenes.todos");
  const consulta = useConsulta((signal) => apiGet<PorRecibirApi>("/traspasos/por-recibir", undefined, signal), "por-recibir");
  const [abriendo, setAbriendo] = useState(false);

  // Al volver a esta pestaña se actualiza la lista y el contador del inicio.
  const { recargar } = consulta;
  useEffect(() => {
    const alVolver = () => {
      if (document.visibilityState === "visible") recargar();
    };
    document.addEventListener("visibilitychange", alVolver);
    return () => document.removeEventListener("visibilitychange", alVolver);
  }, [recargar]);

  const actualizar = useCallback(() => {
    recargar();
    refrescarContadores();
  }, [recargar]);

  const alLeer = async (codigo: string) => {
    const token = tokenDeLectura(codigo);
    if (!token) {
      reproducir("aviso");
      aviso({ titulo: "Ese código no es de un traspaso", descripcion: "Escanea el código QR del vale del traspaso.", tipo: "aviso" });
      return;
    }
    setAbriendo(true);
    try {
      const id = await idDeTraspasoPorToken(token, consulta.datos?.elementos ?? null);
      if (id) {
        reproducir("ok");
        void navegar(`/recibir/${id}`);
      } else {
        reproducir("aviso");
        aviso({ titulo: "Ese vale no es un traspaso", tipo: "aviso" });
      }
    } catch (causa) {
      reproducir("bloqueo");
      aviso({ titulo: "No pudimos abrir el traspaso", descripcion: mensajeDeError(causa), tipo: "error" });
    } finally {
      setAbriendo(false);
    }
  };

  const lista = consulta.datos?.elementos ?? [];

  return (
    <Pantalla
      titulo="Recibir"
      descripcion="Escanea el vale de un traspaso o elige uno de la lista."
      acciones={
        <Boton variante="contorno" onClick={actualizar} disabled={consulta.cargando} aria-label="Actualizar la lista">
          <RefreshCwIcon aria-hidden="true" />
          <span className="hidden sm:inline">Actualizar</span>
        </Boton>
      }
    >
      <div className="grid grid-cols-1 gap-6 md:grid-cols-[minmax(0,1fr)_20rem] md:items-start">
        <div className="order-2 min-w-0 md:order-1">
          {consulta.error ? (
            <EstadoError error={consulta.error} alReintentar={actualizar} />
          ) : consulta.cargando && !consulta.datos ? (
            <Esqueleto tipo="lista" cantidad={3} />
          ) : lista.length === 0 ? (
            <EstadoVacio
              icono={InboxIcon}
              titulo="No hay traspasos por recibir"
              descripcion="Cuando otro almacén te envíe algo, aparecerá aquí."
            />
          ) : (
            <ul aria-label="Traspasos en camino" className="flex flex-col gap-3">
              {lista.map((t) => (
                <TarjetaTraspaso key={t.id} traspaso={t} mostrarDestino={operaTodos} />
              ))}
            </ul>
          )}
        </div>
        <div className="order-1 flex flex-col gap-3 md:sticky md:top-4 md:order-2">
          <Escaner
            activo={!abriendo}
            onCodigo={(codigo) => void alLeer(codigo)}
            etiquetaCampo="Escribir el código del vale"
            placeholderCampo="Código del vale"
          />
        </div>
      </div>
    </Pantalla>
  );
}
