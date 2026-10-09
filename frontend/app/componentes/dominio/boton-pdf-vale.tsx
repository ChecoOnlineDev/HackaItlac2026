import { useEffect, useRef, useState } from "react";
import { Boton } from "~/componentes/ui/boton";
import { useSesionActiva } from "~/sesion/sesion";

export function BotonPdfVale({ id, lote = false }: { id: string; lote?: boolean }) {
  const { sesion } = useSesionActiva(); const control = useRef<AbortController | null>(null);
  const [progreso, setProgreso] = useState<string | null>(null); const [error, setError] = useState(false);
  useEffect(() => () => control.current?.abort(), [id]);
  const descargar = async () => {
    if (control.current) return;
    control.current = new AbortController(); setError(false); setProgreso("Armando el PDF…");
    try { const { descargarPdfVale } = await import("./pdf-vale"); await descargarPdfVale(id, sesion.usuario.nombre, control.current.signal, setProgreso, lote); }
    catch (causa) { if (!(causa instanceof DOMException && causa.name === "AbortError")) setError(true); }
    finally { control.current = null; setProgreso(null); }
  };
  return <div><Boton variante="contorno" disabled={Boolean(progreso)} onClick={() => void descargar()}>{lote ? "Descargar PDF del lote" : error ? "Reintentar PDF" : "Descargar PDF"}</Boton>
    {progreso ? <><p role="status" className="text-sm">{progreso}</p><Boton variante="texto" onClick={() => control.current?.abort()}>Cancelar PDF</Boton></> : null}
    {error ? <p role="alert" className="text-sm text-destructive">No se pudo armar el PDF. Revisa la conexión y vuelve a intentar.</p> : null}</div>;
}
