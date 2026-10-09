import { useState } from "react";
import { textoMedioValido } from "~/componentes/traspasos/formato";
import { cn } from "cn";
import { BanIcon, PrinterIcon } from "lucide-react";

import { Boton } from "~/componentes/ui/boton";
import { useImagenAutenticada } from "~/movil/imagen";
import { CodigoQR, urlDeVale } from "./codigo-qr";
import { CLASE_IMPRESION, EstiloImpresion } from "./estilo-impresion";
import { formatearFechaHora } from "./fechas";
import type { Condicion } from "./tipos";

export type TipoVale = "ENTRADA" | "ENTREGA" | "DEVOLUCION" | "TRASPASO" | "RECEPCION" | "NO_ADEUDO" | "CANCELACION" | "AJUSTE";

export const NOMBRE_TIPO_VALE: Record<TipoVale, string> = {
  ENTRADA: "Entrada de inventario",
  ENTREGA: "Vale de entrega",
  DEVOLUCION: "Vale de devolución",
  TRASPASO: "Traspaso entre almacenes",
  RECEPCION: "Recepción de traspaso",
  NO_ADEUDO: "Constancia de no adeudo",
  CANCELACION: "Cancelación de vale",
  AJUSTE: "Ajuste por faltante de almacén",
};

const NOMBRE_CONDICION: Record<Condicion, string> = {
  BUENO: "Bueno",
  DESGASTE: "Desgaste por uso",
  DANADO: "Dañado",
};

/** La firma guardada; si la imagen no carga, el vale dice "Firmado en pantalla" en vez de mostrar un icono roto. */
function ImagenDeFirma({ src, alt }: { src: string; alt: string }) {
  const [fallo, setFallo] = useState(false);
  const imagen = useImagenAutenticada(src);
  if (fallo || !imagen) return <p className="pb-2 text-sm font-semibold text-neutral-700">Firmado en pantalla</p>;
  return <img src={imagen} alt={alt} onError={() => setFallo(true)} className="max-h-full max-w-full object-contain" />;
}

/** Leyenda que firma el trabajador al recibir (F-02). La pantalla de firma debe mostrar la misma. */
export const LEYENDA_RESPONSABILIDAD =
  "Recibo el equipo descrito en este vale en las condiciones indicadas y me hago responsable de su uso y cuidado. " +
  "Me comprometo a devolverlo cuando se me solicite o al terminar mi relación de trabajo.";

export interface RenglonVale {
  renglon: number;
  articulo: { nombre: string; marca?: string | null; talla?: string | null };
  /** Código de la pieza o del artículo. */
  codigo: string;
  numero_serie?: string | null;
  cantidad: number;
  condicion?: Condicion | null;
}

/**
 * Detalle de un vale para pantalla y papel. Es la forma esperada de `GET /api/vales/{id}`
 * (api-contracts.md, Vales). NO tiene campos de costo, a propósito: ningún vale muestra costos (F-12).
 */
export interface ValeDetalle {
  despacho?: { modo: "APROBADO" | "PROPIO" | "AUTONOMO" | null; aprobo: { nombre: string } | null } | null;
  folio: string;
  tipo: TipoVale;
  /** Instante UTC en ISO; se muestra en hora de México. */
  creado_en: string;
  /** Token del QR (`/v/{token}`). */
  token: string;
  estado?: string;
  almacen?: { clave?: string; nombre: string } | null;
  destino_almacen?: { clave?: string; nombre: string } | null;
  trabajador?: { nombre: string; numero_empleado: string; puesto?: string | null; area_obra?: string | null } | null;
  responsable: { nombre: string };
  /** Quien autorizó (un renglón naranja), si hubo autorización. */
  autorizacion?: { autorizado_por: { nombre: string }; motivo?: string | null; medio?: string | null } | null;
  observacion?: string | null;
  /**
   * Firma del trabajador: la imagen (`data:image/png;base64,…` o una dirección). `imagen` va en null
   * cuando el vale sí está firmado pero el servidor no entrega la imagen (el detalle solo dice `tiene_firma`).
   */
  firma?: { imagen: string | null } | null;
  /** Folio del vale al que corresponde (por ejemplo, el vale que cancela una cancelación). */
  vale_origen_folio?: string | null;
  renglones: RenglonVale[];
  /** Presente solo si el vale está cancelado. El motivo y el folio de la cancelación son opcionales: el detalle del servidor aún no los trae. */
  cancelacion?: { motivo?: string | null; folio?: string | null; creado_en?: string } | null;
}

interface PropiedadesValeImprimible {
  vale: ValeDetalle;
  /** Muestra el botón "Imprimir" arriba. Por omisión `true`. */
  botonImprimir?: boolean;
  /** Botones extra junto a "Imprimir" (por ejemplo "Cancelar vale"). */
  acciones?: React.ReactNode;
  className?: string;
}

function Dato({ etiqueta, children }: { etiqueta: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col">
      <dt className="text-xs font-semibold tracking-wide text-neutral-600 uppercase">{etiqueta}</dt>
      <dd className="text-base leading-snug font-medium text-black">{children}</dd>
    </div>
  );
}

/**
 * El documento del vale. Es un solo diseño: en pantalla es una hoja blanca; al imprimir (hoja carta)
 * desaparecen menús y botones. Muestra folio, tipo, fecha en hora de México, trabajador o almacenes,
 * renglones, leyenda de responsabilidad, firma, responsable, quién validó y el QR. Nunca muestra costos.
 *
 * ```tsx
 * <ValeImprimible vale={detalle} />
 * ```
 */
export function ValeImprimible({ vale, botonImprimir = true, acciones, className }: PropiedadesValeImprimible) {
  const cancelado = Boolean(vale.cancelacion);
  const esEntrega = vale.tipo === "ENTREGA";
  const mostrarCondicion = vale.renglones.some((r) => r.condicion);

  return (
    <div className={cn("flex flex-col gap-4", className)}>
      <EstiloImpresion />
      {botonImprimir || acciones ? (
        <div className="flex flex-wrap items-center gap-3 print:hidden">
          {botonImprimir ? (
            <Boton variante="normal" onClick={() => window.print()}>
              <PrinterIcon aria-hidden="true" />
              Imprimir
            </Boton>
          ) : null}
          {acciones}
        </div>
      ) : null}

      <article
        aria-label={`${NOMBRE_TIPO_VALE[vale.tipo]} ${vale.folio}`}
        className={cn(
          CLASE_IMPRESION,
          "mx-auto flex w-full max-w-[816px] flex-col gap-5 rounded-xl border bg-white p-5 text-black shadow-sm sm:p-8 print:max-w-none print:rounded-none print:border-0 print:p-0",
        )}
      >
        {cancelado ? (
          <div
            role="alert"
            className="flex items-start gap-3 rounded-lg border-2 border-semaforo-rojo bg-semaforo-rojo px-4 py-3 text-white"
          >
            <BanIcon aria-hidden="true" className="mt-0.5 size-6 shrink-0" strokeWidth={3} />
            <div className="flex flex-col">
              <p className="text-lg font-extrabold tracking-wide uppercase">Cancelado</p>
              {vale.cancelacion!.motivo ? <p className="text-base">Motivo: {vale.cancelacion!.motivo}</p> : null}
              {vale.cancelacion!.folio ? (
                <p className="text-sm font-semibold">Folio de la cancelación: {vale.cancelacion!.folio}</p>
              ) : null}
            </div>
          </div>
        ) : null}

        <header className="flex items-start justify-between gap-4 border-b-2 border-black pb-4">
          <div className="flex flex-col gap-1">
            <img src="/logo-imhotep.png" alt="IMHOTEP" width={96} height={90} className="h-auto w-16 sm:w-20" />
            <h2 className="mt-1 text-xl leading-tight font-bold text-black">{NOMBRE_TIPO_VALE[vale.tipo]}</h2>
            <p className="text-sm text-neutral-700">{formatearFechaHora(vale.creado_en)} (hora del centro de México)</p>
          </div>
          <div className="flex flex-col items-end gap-1 text-right">
            <p className="text-xs font-semibold tracking-wide text-neutral-600 uppercase">Folio</p>
            <p className="text-xl font-bold tracking-wide break-all text-black">{vale.folio}</p>
            <CodigoQR valor={urlDeVale(vale.token)} tamano={104} nivel="M" titulo={`Código QR del folio ${vale.folio}`} className="print:w-[28mm]" />
          </div>
        </header>

        <dl className="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
          {vale.trabajador ? (
            <>
              <Dato etiqueta="Trabajador">{vale.trabajador.nombre}</Dato>
              <Dato etiqueta="Número de empleado">{vale.trabajador.numero_empleado}</Dato>
              {vale.trabajador.puesto ? <Dato etiqueta="Puesto">{vale.trabajador.puesto}</Dato> : null}
              {vale.trabajador.area_obra ? <Dato etiqueta="Área u obra">{vale.trabajador.area_obra}</Dato> : null}
            </>
          ) : null}
          {vale.vale_origen_folio ? <Dato etiqueta="Vale original">{vale.vale_origen_folio}</Dato> : null}
          {vale.almacen ? <Dato etiqueta={vale.destino_almacen ? "Almacén de origen" : "Almacén"}>{vale.almacen.nombre}</Dato> : null}
          {vale.destino_almacen ? <Dato etiqueta="Almacén de destino">{vale.destino_almacen.nombre}</Dato> : null}
        </dl>

        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-[13px] sm:text-sm print:text-sm">
            <caption className="sr-only">Artículos del vale</caption>
            <thead>
              <tr className="border-y-2 border-black bg-neutral-100 print:bg-neutral-100">
                <th scope="col" className="hidden px-1.5 py-2 font-bold sm:table-cell sm:px-2 print:table-cell">N.º</th>
                <th scope="col" className="px-1.5 py-2 sm:px-2 font-bold">Descripción</th>
                <th scope="col" className="px-1.5 py-2 sm:px-2 font-bold">Código o serie</th>
                <th scope="col" className="px-1.5 py-2 text-right font-bold sm:px-2">
                  <span className="sm:hidden print:hidden" aria-hidden="true">Cant.</span>
                  <span className="sr-only sm:not-sr-only print:not-sr-only">Cantidad</span>
                </th>
                {mostrarCondicion ? <th scope="col" className="px-1.5 py-2 sm:px-2 font-bold">Condición</th> : null}
              </tr>
            </thead>
            <tbody>
              {vale.renglones.map((r) => (
                <tr key={r.renglon} className="border-b border-neutral-400 align-top">
                  <td className="hidden px-1.5 py-2 tabular-nums sm:table-cell sm:px-2 print:table-cell">{r.renglon}</td>
                  <td className="px-1.5 py-2 sm:px-2">
                    <span className="font-semibold">{r.articulo.nombre}</span>
                    {r.articulo.marca || r.articulo.talla ? (
                      <span className="block text-neutral-700">
                        {[r.articulo.marca, r.articulo.talla ? `Talla ${r.articulo.talla}` : null].filter(Boolean).join(" · ")}
                      </span>
                    ) : null}
                  </td>
                  <td className="px-1.5 py-2 sm:px-2 [overflow-wrap:anywhere]">
                    {r.codigo}
                    {r.numero_serie ? <span className="block text-neutral-700">Serie {r.numero_serie}</span> : null}
                  </td>
                  <td className="px-1.5 py-2 sm:px-2 text-right font-semibold tabular-nums">{r.cantidad}</td>
                  {mostrarCondicion ? <td className="px-1.5 py-2 sm:px-2">{r.condicion ? NOMBRE_CONDICION[r.condicion] : ""}</td> : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {vale.observacion ? (
          <p className="text-sm">
            <span className="font-bold">Observación: </span>
            {vale.observacion}
          </p>
        ) : null}

        {esEntrega ? <p className="text-sm leading-relaxed text-black">{LEYENDA_RESPONSABILIDAD}</p> : null}

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 print:grid-cols-2">
          {vale.trabajador || vale.firma ? (
            <div className="flex flex-col gap-1">
              <div className="flex h-28 items-end justify-center border-b-2 border-black">
                {vale.firma?.imagen ? (
                  <ImagenDeFirma src={vale.firma.imagen} alt={`Firma de ${vale.trabajador?.nombre ?? "quien recibió"}`} />
                ) : vale.firma ? (
                  <p className="pb-2 text-sm font-semibold text-neutral-700">Firmado en pantalla</p>
                ) : null}
              </div>
              <p className="text-center text-sm font-semibold">
                {vale.trabajador ? `Firma de ${vale.trabajador.nombre}` : "Firma"}
              </p>
            </div>
          ) : null}
          <div className="flex flex-col gap-3">
            <Dato etiqueta="Responsable del almacén">{vale.responsable.nombre}</Dato>
            {vale.autorizacion ? (
              <Dato etiqueta="Validó">
                {vale.autorizacion.autorizado_por.nombre}
                {textoMedioValido(vale.autorizacion.medio) ? ` (${textoMedioValido(vale.autorizacion.medio)})` : ""}
                {vale.autorizacion.motivo ? <span className="block text-sm font-normal text-neutral-700">Motivo: {vale.autorizacion.motivo}</span> : null}
              </Dato>
            ) : null}
          </div>
        </div>
      </article>
    </div>
  );
}
