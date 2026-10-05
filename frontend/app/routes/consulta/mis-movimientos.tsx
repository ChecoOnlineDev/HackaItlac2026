import { BanIcon, ChevronRightIcon, History, RefreshCwIcon, RotateCcwIcon } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";

import { apiGet } from "~/api/cliente";
import type { Pagina } from "~/api/tipos";
import { useConsulta } from "~/componentes/catalogo/usar-consulta";
import { formatearFechaHora, hoyMexico } from "~/componentes/dominio/fechas";
import type { TipoVale } from "~/componentes/dominio/vale-imprimible";
import { CancelarVale, esCancelable } from "~/componentes/entrega/cancelar-vale";
import { sePuedeRehacer } from "~/componentes/entrega/rehacer";
import type { ValeListaApi } from "~/componentes/entrega/tipos";
import { Pantalla, type ManejadorRuta } from "~/componentes/pantalla";
import { Boton } from "~/componentes/ui/boton";
import { EstadoError } from "~/componentes/ui/estado-error";
import { EstadoVacio } from "~/componentes/ui/estado-vacio";
import { Esqueleto } from "~/componentes/ui/esqueleto";
import { Insignia } from "~/componentes/ui/insignia";
import { useSesionActiva } from "~/sesion/sesion";

export const handle: ManejadorRuta = { permiso: "vales.ver" };

const TEXTO_TIPO: Record<TipoVale, string> = {
  ENTRADA: "Entrada",
  ENTREGA: "Entrega",
  DEVOLUCION: "Devolución",
  TRASPASO: "Traspaso",
  RECEPCION: "Recepción",
  NO_ADEUDO: "No adeudo",
  CANCELACION: "Cancelación",
};

const TEXTO_ESTADO: Record<ValeListaApi["estado"], string> = {
  EMITIDO: "Emitido",
  EN_TRANSITO: "En tránsito",
  RECIBIDO: "Recibido",
  RECIBIDO_CON_DIFERENCIAS: "Recibido con diferencias",
  CANCELADO: "Cancelado",
};

/** "14:32" de un instante UTC, en hora del centro de México. */
function horaDe(iso: string): string {
  return formatearFechaHora(iso).slice(11);
}

export default function MisMovimientos() {
  const { sesion, puede } = useSesionActiva();
  const hoy = hoyMexico();
  const [cancelando, setCancelando] = useState<{ vale: ValeListaApi; rehacer: boolean } | null>(null);
  // Todos los vales de esta lista son del usuario: `vales.cancelar` basta (K-01); el servidor lo vuelve a verificar.
  const puedeCancelar = puede("vales.cancelar") || puede("vales.cancelar_todos");
  const { datos, cargando, error, recargar } = useConsulta(
    (signal) =>
      apiGet<Pagina<ValeListaApi>>("/vales", { usuario_id: sesion.usuario.id, desde: hoy, hasta: hoy, tamano: 100 }, signal),
    `${sesion.usuario.id}|${hoy}`,
  );

  return (
    <Pantalla
      titulo="Mis movimientos de hoy"
      descripcion="Los vales que hiciste hoy. Ábrelos para verlos o imprimirlos."
      ancho="formulario"
      acciones={
        <Boton variante="contorno" onClick={recargar} disabled={cargando}>
          <RefreshCwIcon aria-hidden="true" />
          Actualizar
        </Boton>
      }
    >
      {error ? (
        <EstadoError error={error} alReintentar={recargar} />
      ) : cargando && !datos ? (
        <Esqueleto tipo="lista" cantidad={4} />
      ) : datos && datos.elementos.length === 0 ? (
        <EstadoVacio icono={History} titulo="Todavía no has hecho movimientos hoy" descripcion="Cuando emitas un vale, aparecerá aquí." />
      ) : (
        <ul className="flex flex-col gap-3" aria-label="Vales de hoy">
          {(datos?.elementos ?? []).map((v) => (
            <li key={v.id} className="flex flex-col overflow-hidden rounded-xl border bg-card">
              <Link
                to={`/vales/${v.id}`}
                className="flex min-h-16 items-center gap-3 p-3 hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
              >
                <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                  <p className="flex flex-wrap items-baseline gap-x-2">
                    <span className="text-xl font-bold text-marino">{v.folio}</span>
                    <span className="text-base text-muted-foreground">
                      {TEXTO_TIPO[v.tipo]} · {horaDe(v.creado_en)}
                    </span>
                  </p>
                  <p className="truncate text-base">
                    {v.trabajador ? `${v.trabajador.nombre}${v.numero_empleado ? ` (${v.numero_empleado})` : ""}` : v.almacen.nombre}
                  </p>
                </div>
                <Insignia estado="neutra">{TEXTO_ESTADO[v.estado]}</Insignia>
                <ChevronRightIcon aria-hidden="true" className="size-5 shrink-0 text-muted-foreground" />
              </Link>
              {puedeCancelar && esCancelable(v) ? (
                <div className="flex flex-wrap gap-2 border-t px-3 py-2">
                  <Boton variante="texto" aria-label={`Cancelar el vale ${v.folio}`} onClick={() => setCancelando({ vale: v, rehacer: false })}>
                    <BanIcon aria-hidden="true" />
                    Cancelar
                  </Boton>
                  {sePuedeRehacer(v.tipo) ? (
                    <Boton variante="texto" aria-label={`Cancelar y rehacer el vale ${v.folio}`} onClick={() => setCancelando({ vale: v, rehacer: true })}>
                      <RotateCcwIcon aria-hidden="true" />
                      Cancelar y rehacer
                    </Boton>
                  ) : null}
                </div>
              ) : null}
            </li>
          ))}
        </ul>
      )}
      <CancelarVale
        vale={cancelando ? { id: cancelando.vale.id, folio: cancelando.vale.folio, tipo: cancelando.vale.tipo, estado: cancelando.vale.estado } : null}
        rehacer={cancelando?.rehacer ?? false}
        alCerrar={() => setCancelando(null)}
        alCancelar={recargar}
      />
    </Pantalla>
  );
}
