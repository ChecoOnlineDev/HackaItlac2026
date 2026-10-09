import { DownloadIcon } from "lucide-react";
import { useRef, useState } from "react";
import type { VistaPreviaTraspasoApi } from "~/api/traspasos-lista";
import { descargarBlob } from "~/componentes/dominio/credencial-png";
import { Boton } from "~/componentes/ui/boton";
import { EstadoError } from "~/componentes/ui/estado-error";
import { crearExcelLista } from "./excel-lista";

export function BotonExcelLista({ vista, folio, observacion, filasExcluidas, disabled }: { vista: VistaPreviaTraspasoApi; folio?: string; observacion?: string; filasExcluidas?: number[]; disabled?: boolean }) {
  const [error, setError] = useState<unknown>(null);
  const [descargando, setDescargando] = useState(false);
  const ocupado = useRef(false);
  const descargar = async () => {
    if (ocupado.current) return;
    ocupado.current = true; setDescargando(true); setError(null);
    try {
      const nombre = (folio ?? `${vista.origen.clave}-${vista.destino.clave}-vista-previa`).replace(/[^a-zA-Z0-9_-]/g, "-");
      await descargarBlob(crearExcelLista(vista, { folio, observacion, filasExcluidas }), `lista-traspaso-${nombre}.xlsx`);
    } catch (causa) { setError(causa); }
    finally { ocupado.current = false; setDescargando(false); }
  };
  return <div className="flex flex-col gap-2"><Boton variante="contorno" disabled={disabled} cargando={descargando} onClick={() => void descargar()}><DownloadIcon aria-hidden="true" />Descargar lista para imprimir (Excel)</Boton>{error ? <EstadoError error={error} /> : null}</div>;
}
