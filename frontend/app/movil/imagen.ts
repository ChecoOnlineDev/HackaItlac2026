import { useEffect, useState } from "react";
import { imagenApi } from "~/api/cliente";
import { esAppNativa } from "./plataforma";

/** En Android un <img> no pasa por CapacitorHttp: cargar primero el recurso protegido. */
export function useImagenAutenticada(src: string | null | undefined): string | undefined {
  const nativa = esAppNativa() && Boolean(src?.startsWith("/api/"));
  const [imagen, setImagen] = useState<{ src: string; url: string } | null>(null);
  useEffect(() => {
    if (!nativa || !src) return;
    const cancelar = new AbortController();
    let vigente = true;
    let url: string | undefined;
    void imagenApi(src, cancelar.signal).then((blob) => {
      if (!vigente) return;
      url = URL.createObjectURL(blob);
      setImagen({ src, url });
    }).catch(() => { /* La foto usa iniciales y la firma su leyenda de respaldo. */ });
    return () => {
      vigente = false;
      cancelar.abort();
      if (url) URL.revokeObjectURL(url);
    };
  }, [nativa, src]);
  return nativa ? (imagen && imagen.src === src ? imagen.url : undefined) : src ?? undefined;
}
