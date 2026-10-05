import { CameraIcon, ImageUpIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Avatar } from "~/componentes/ui/avatar";
import { Boton } from "~/componentes/ui/boton";

const LADO_MAXIMO = 640;
const CALIDAD_JPEG = 0.8;

/** Reduce la imagen en el navegador (lado mayor 640 px, JPEG) antes de subirla (T-09). */
export async function reducirImagen(archivo: File): Promise<File> {
  const bitmap = await createImageBitmap(archivo, { imageOrientation: "from-image" });
  try {
    const escala = Math.min(1, LADO_MAXIMO / Math.max(bitmap.width, bitmap.height));
    const ancho = Math.max(1, Math.round(bitmap.width * escala));
    const alto = Math.max(1, Math.round(bitmap.height * escala));
    const lienzo = document.createElement("canvas");
    lienzo.width = ancho;
    lienzo.height = alto;
    const contexto = lienzo.getContext("2d");
    if (!contexto) throw new Error("sin lienzo");
    contexto.fillStyle = "#ffffff";
    contexto.fillRect(0, 0, ancho, alto);
    contexto.drawImage(bitmap, 0, 0, ancho, alto);
    const blob = await new Promise<Blob | null>((resolver) => lienzo.toBlob(resolver, "image/jpeg", CALIDAD_JPEG));
    if (!blob) throw new Error("sin imagen");
    return new File([blob], "foto.jpg", { type: "image/jpeg" });
  } finally {
    bitmap.close();
  }
}

interface PropiedadesSelectorFoto {
  nombre: string;
  /** Foto ya guardada (para la ficha); si hay `archivo`, manda la vista previa del archivo. */
  fotoActualUrl?: string | null;
  archivo: File | null;
  /** Recibe la imagen ya reducida, o null si no se pudo leer. */
  alElegir: (archivo: File | null, error?: string) => void;
  deshabilitado?: boolean;
}

/** Foto del trabajador: tomar con la cámara o elegir una imagen; vista previa y reemplazo. */
export function SelectorFoto({ nombre, fotoActualUrl, archivo, alElegir, deshabilitado }: PropiedadesSelectorFoto) {
  const camara = useRef<HTMLInputElement>(null);
  const galeria = useRef<HTMLInputElement>(null);
  const [vista, setVista] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);

  useEffect(() => {
    if (!archivo) {
      setVista(null);
      return;
    }
    const url = URL.createObjectURL(archivo);
    setVista(url);
    return () => URL.revokeObjectURL(url);
  }, [archivo]);

  async function alCambiar(evento: React.ChangeEvent<HTMLInputElement>) {
    const elegido = evento.target.files?.[0];
    evento.target.value = "";
    if (!elegido) return;
    setProcesando(true);
    try {
      alElegir(await reducirImagen(elegido));
    } catch {
      alElegir(null, "No pudimos leer esa imagen. Prueba con otra foto.");
    } finally {
      setProcesando(false);
    }
  }

  const tieneFoto = Boolean(vista ?? fotoActualUrl);
  return (
    <div className="flex flex-wrap items-center gap-4">
      <Avatar nombre={nombre || "Trabajador"} fotoUrl={vista ?? fotoActualUrl} tamano="lg" className="size-24" />
      <div className="flex flex-wrap gap-2">
        <Boton type="button" variante="secundario" onClick={() => camara.current?.click()} disabled={deshabilitado} cargando={procesando}>
          <CameraIcon aria-hidden="true" />
          {tieneFoto ? "Tomar otra foto" : "Tomar foto"}
        </Boton>
        <Boton type="button" variante="contorno" onClick={() => galeria.current?.click()} disabled={deshabilitado || procesando}>
          <ImageUpIcon aria-hidden="true" />
          Elegir imagen
        </Boton>
      </div>
      <input ref={camara} type="file" accept="image/*" capture="user" className="sr-only" tabIndex={-1} aria-hidden="true" onChange={alCambiar} />
      <input ref={galeria} type="file" accept="image/png,image/jpeg,image/webp" className="sr-only" tabIndex={-1} aria-hidden="true" onChange={alCambiar} />
    </div>
  );
}
