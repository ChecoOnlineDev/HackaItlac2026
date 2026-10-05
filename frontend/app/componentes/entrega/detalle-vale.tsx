import { BanIcon } from "lucide-react";

import { apiGet } from "~/api/cliente";
import { esErrorApi } from "~/api/errores";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { ValeImprimible } from "~/componentes/dominio/vale-imprimible";
import { Boton } from "~/componentes/ui/boton";
import { Cargando } from "~/componentes/ui/cargando";
import { EstadoError } from "~/componentes/ui/estado-error";
import { useSesionActiva } from "~/sesion/sesion";
import type { ValeDetalleApi } from "./tipos";
import { aValeImprimible } from "./vale-adaptador";

interface PropiedadesDetalleVale {
  /** `GET /api/vales/{id}` o `GET /api/vales/por-token/{token}`. */
  ruta: string;
}

/**
 * Detalle real de un vale (folio, renglones, responsable, QR) con "Imprimir". Quien puede cancelar
 * ve "Cancelar vale", todavía deshabilitado: la cancelación se integra en otra entrega.
 */
export function DetalleVale({ ruta }: PropiedadesDetalleVale) {
  const { puede } = useSesionActiva();
  const { datos, cargando, error, recargar } = useConsulta((signal) => apiGet<ValeDetalleApi>(ruta, undefined, signal), ruta);

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

  const puedeCancelar = puede("vales.cancelar") || puede("vales.cancelar_todos");
  return (
    <ValeImprimible
      vale={aValeImprimible(datos)}
      acciones={
        puedeCancelar && datos.estado !== "CANCELADO" ? (
          <div className="flex flex-wrap items-center gap-3">
            <Boton variante="contorno" disabled aria-describedby="nota-cancelar">
              <BanIcon aria-hidden="true" />
              Cancelar vale
            </Boton>
            <span id="nota-cancelar" className="text-sm font-semibold text-muted-foreground">
              Pronto
            </span>
          </div>
        ) : null
      }
    />
  );
}
