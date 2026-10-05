import { BanIcon, RotateCcwIcon } from "lucide-react";
import { useState } from "react";

import { apiGet } from "~/api/cliente";
import { esErrorApi } from "~/api/errores";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { ValeImprimible } from "~/componentes/dominio/vale-imprimible";
import { Boton } from "~/componentes/ui/boton";
import { Cargando } from "~/componentes/ui/cargando";
import { EstadoError } from "~/componentes/ui/estado-error";
import { useSesionActiva } from "~/sesion/sesion";
import { CancelarVale, esCancelable } from "./cancelar-vale";
import { sePuedeRehacer } from "./rehacer";
import type { ValeDetalleApi } from "./tipos";
import { aValeImprimible } from "./vale-adaptador";

interface PropiedadesDetalleVale {
  /** `GET /api/vales/{id}` o `GET /api/vales/por-token/{token}`. */
  ruta: string;
}

/**
 * Detalle real de un vale (folio, renglones, responsable, QR) con "Imprimir". Quien puede cancelar ve
 * "Cancelar vale" y, en entregas y devoluciones, "Cancelar y rehacer" (K-05). Un vale cancelado muestra la
 * banda "Cancelado" con el motivo y el folio de su cancelación.
 */
export function DetalleVale({ ruta }: PropiedadesDetalleVale) {
  const { puede, sesion } = useSesionActiva();
  const { datos, cargando, error, recargar } = useConsulta((signal) => apiGet<ValeDetalleApi>(ruta, undefined, signal), ruta);
  const [cancelando, setCancelando] = useState<{ rehacer: boolean } | null>(null);

  if (error) {
    const noExiste = esErrorApi(error) && error.status === 404;
    return (
      <EstadoError
        error={noExiste ? undefined : error}
        mensaje={noExiste ? "No encontramos ese vale. Revisa el código o el enlace." : undefined}
        alReintentar={noExiste ? undefined : recargar}
      />
    );
  }
  if (cargando && !datos) return <Cargando variante="en-linea" texto="Abriendo el vale…" />;
  if (!datos) return null;

  // `vales.cancelar` cubre los propios; `vales.cancelar_todos`, los de cualquiera (K-01). El servidor lo vuelve a verificar.
  const esPropio = datos.responsable.id === sesion.usuario.id;
  const puedeCancelar = puede("vales.cancelar_todos") || (puede("vales.cancelar") && esPropio);
  const mostrarCancelar = puedeCancelar && esCancelable(datos);
  return (
    <>
      <ValeImprimible
        vale={aValeImprimible(datos)}
        acciones={
          mostrarCancelar ? (
            <div className="flex flex-wrap items-center gap-3">
              <Boton variante="contorno" onClick={() => setCancelando({ rehacer: false })}>
                <BanIcon aria-hidden="true" />
                Cancelar vale
              </Boton>
              {sePuedeRehacer(datos.tipo) ? (
                <Boton variante="contorno" onClick={() => setCancelando({ rehacer: true })}>
                  <RotateCcwIcon aria-hidden="true" />
                  Cancelar y rehacer
                </Boton>
              ) : null}
            </div>
          ) : null
        }
      />
      <CancelarVale
        vale={cancelando ? { id: datos.id, folio: datos.folio, tipo: datos.tipo, estado: datos.estado } : null}
        rehacer={cancelando?.rehacer ?? false}
        alCerrar={() => setCancelando(null)}
        alCancelar={recargar}
      />
    </>
  );
}
