import { CameraIcon, PrinterIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { CodigoQR, urlDeVale } from "~/componentes/dominio/codigo-qr";
import { EstiloImpresion, ImpresionAparte, CLASE_IMPRESION } from "~/componentes/dominio/estilo-impresion";
import { formatearFechaHora } from "~/componentes/dominio/formato";
import { reducirFoto } from "~/componentes/devolucion/foto";
import { Boton } from "~/componentes/ui/boton";
import { EstadoError } from "~/componentes/ui/estado-error";
import type { EvaluacionApi } from "./tipos";

export interface ReservaPapel {
  id: string;
  folio: string;
  token: string;
  vence_en: string;
  evaluacion: EvaluacionApi;
  ticket: {
    creado_en: string;
    trabajador: { nombre: string; numero_empleado: string } | null;
    proyecto: { clave: string; nombre: string } | null;
    articulos: { renglon: number; codigo: string; nombre: string; marca?: string | null; modelo?: string | null; talla?: string | null; numero_serie?: string | null; cantidad: number }[];
    observacion: string | null;
    leyenda: string;
  };
}

/** Se imprime exclusivamente el snapshot reservado por el servidor, dos ejemplares del mismo folio. */
function DosCopias({ reserva }: { reserva: ReservaPapel }) {
  return <div className={`${CLASE_IMPRESION} space-y-5 bg-white text-black`}>
    {["Copia del trabajador", "Copia del almacén"].map((copia) => <section key={copia} className="break-inside-avoid border-b border-dashed border-black pb-5">
      <header className="flex items-start justify-between gap-4"><div><h2 className="text-base font-semibold">IMHOTEP · Vale de entrega</h2><p className="text-xl font-bold">{reserva.folio}</p><p className="text-xs">{copia} · {formatearFechaHora(reserva.ticket.creado_en)}</p></div><CodigoQR valor={urlDeVale(reserva.token)} tamano={92} /></header>
      <p className="mt-3 font-semibold">{reserva.ticket.trabajador?.nombre} · N.º {reserva.ticket.trabajador?.numero_empleado}</p>
      {reserva.ticket.proyecto ? <p className="text-sm">Proyecto: {reserva.ticket.proyecto.clave} · {reserva.ticket.proyecto.nombre}</p> : null}
      <table className="my-3 w-full text-sm"><thead><tr className="border-b border-black"><th className="py-2 text-left">Equipo</th><th className="py-2 text-right">Cantidad</th></tr></thead><tbody>{reserva.ticket.articulos.map((a) => <tr key={a.renglon} className="border-b border-neutral-300"><td className="py-2">{[a.nombre, a.marca, a.modelo, a.talla].filter(Boolean).join(" · ")}<span className="block text-xs">{a.codigo}{a.numero_serie ? ` · Serie ${a.numero_serie}` : ""}</span></td><td className="py-2 text-right tabular-nums">{a.cantidad}</td></tr>)}</tbody></table>
      {reserva.ticket.observacion ? <p className="text-sm">Observación: {reserva.ticket.observacion}</p> : null}
      <p className="my-3 text-sm">{reserva.ticket.leyenda}</p><div className="mt-8 border-t border-black pt-1 text-center text-sm">Firma del trabajador</div>
    </section>)}
  </div>;
}

export function FirmaEnPapel({ reserva, foto, preparar, alFoto, deshabilitado }: { reserva: ReservaPapel | null; foto?: string; preparar: () => Promise<void>; alFoto: (foto?: string) => void; deshabilitado: boolean }) {
  const [ahora, setAhora] = useState(Date.now());
  const [error, setError] = useState<unknown>(null);
  const [leyendo, setLeyendo] = useState(false);
  const fotoSecuencia = useRef(0);
  useEffect(() => { const id = setInterval(() => setAhora(Date.now()), 1000); return () => { clearInterval(id); fotoSecuencia.current++; }; }, []);
  useEffect(() => { fotoSecuencia.current++; setLeyendo(false); }, [reserva?.id]);
  const vencida = reserva && new Date(reserva.vence_en).getTime() <= ahora;
  useEffect(() => { if (vencida && foto) alFoto(undefined); }, [vencida, foto, alFoto]);
  const cargar = async (archivo: File) => {
    const mia = ++fotoSecuencia.current;
    setError(null);
    setLeyendo(true);
    try { const imagen = await reducirFoto(archivo); if (mia === fotoSecuencia.current) alFoto(imagen); }
    catch { if (mia === fotoSecuencia.current) setError(new Error("No pudimos abrir esa foto. Prueba otra imagen.")); }
    finally { if (mia === fotoSecuencia.current) setLeyendo(false); }
  };
  return <section className="flex flex-col gap-3 rounded-xl border p-4">
    <h2 className="text-base font-semibold text-marino">Firma en papel</h2>
    <p>Prepara e imprime dos copias. Pide al trabajador que firme y toma una foto de la copia firmada antes de confirmar.</p>
    {!reserva || vencida ? <><p role="status" className="text-sm text-muted-foreground">{vencida ? "Este ticket venció. Prepara otro, imprímelo y pide una nueva firma." : "Todavía no se ha preparado el ticket."}</p><Boton variante="secundario" disabled={deshabilitado} onClick={() => void preparar()}><PrinterIcon aria-hidden="true" />{vencida ? "Preparar otro ticket" : "Preparar ticket"}</Boton></> : <>
      <p className="font-semibold">Folio {reserva.folio}</p><p className="text-sm">Confirma antes de {formatearFechaHora(reserva.vence_en)}. Reservar e imprimir todavía no entrega el equipo.</p>
      <Boton variante="contorno" disabled={deshabilitado} onClick={() => window.print()}><PrinterIcon aria-hidden="true" />Imprimir dos copias</Boton>
      <ImpresionAparte><EstiloImpresion /><DosCopias reserva={reserva} /></ImpresionAparte>
      <label className="flex min-h-12 cursor-pointer items-center justify-center gap-2 rounded-xl border px-4 py-3 font-semibold has-[:focus-visible]:ring-2 has-[:disabled]:cursor-default has-[:disabled]:opacity-50"><CameraIcon aria-hidden="true" className="size-5" />{leyendo ? "Preparando foto…" : foto ? "Cambiar foto del ticket firmado" : "Tomar o elegir foto del ticket firmado"}<input className="sr-only" type="file" accept="image/*" capture="environment" disabled={deshabilitado || leyendo} onChange={(e) => { const archivo = e.target.files?.[0]; e.target.value = ""; if (archivo) void cargar(archivo); }} /></label>
      {foto ? <><img src={foto} alt="Foto del ticket firmado por el trabajador" className="max-h-80 self-center rounded-lg object-contain" /><Boton variante="texto" disabled={deshabilitado} onClick={() => alFoto(undefined)}>Quitar foto</Boton></> : null}
    </>}
    {error ? <EstadoError error={error} /> : null}
  </section>;
}
