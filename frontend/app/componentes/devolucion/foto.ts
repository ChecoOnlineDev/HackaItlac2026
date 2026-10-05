/** Lado más largo de la foto del daño, en píxeles. Basta para ver el daño y pesa poco. */
const LADO_MAXIMO = 1024;

interface ImagenCargada {
  fuente: CanvasImageSource;
  ancho: number;
  alto: number;
  liberar: () => void;
}

async function cargarImagen(archivo: File): Promise<ImagenCargada> {
  if (typeof createImageBitmap === "function") {
    try {
      const mapa = await createImageBitmap(archivo, { imageOrientation: "from-image" });
      return { fuente: mapa, ancho: mapa.width, alto: mapa.height, liberar: () => mapa.close() };
    } catch {
      // Se prueba con el elemento de imagen.
    }
  }
  const url = URL.createObjectURL(archivo);
  try {
    const imagen = new Image();
    await new Promise<void>((resolver, rechazar) => {
      imagen.onload = () => resolver();
      imagen.onerror = () => rechazar(new Error("imagen inválida"));
      imagen.src = url;
    });
    return {
      fuente: imagen,
      ancho: imagen.naturalWidth,
      alto: imagen.naturalHeight,
      liberar: () => URL.revokeObjectURL(url),
    };
  } catch (causa) {
    URL.revokeObjectURL(url);
    throw causa;
  }
}

/**
 * Reduce una foto del daño (de la cámara o de un archivo) a un JPEG de ~1024 px y la devuelve como
 * `data:image/jpeg;base64,…`, que es lo que espera `renglones[i].foto` de la devolución.
 */
export async function reducirFoto(archivo: File): Promise<string> {
  const origen = await cargarImagen(archivo);
  try {
    const escala = Math.min(1, LADO_MAXIMO / Math.max(origen.ancho, origen.alto));
    const ancho = Math.max(1, Math.round(origen.ancho * escala));
    const alto = Math.max(1, Math.round(origen.alto * escala));
    const lienzo = document.createElement("canvas");
    lienzo.width = ancho;
    lienzo.height = alto;
    const contexto = lienzo.getContext("2d");
    if (!contexto) throw new Error("sin lienzo");
    contexto.fillStyle = "#ffffff";
    contexto.fillRect(0, 0, ancho, alto);
    contexto.drawImage(origen.fuente, 0, 0, ancho, alto);
    return lienzo.toDataURL("image/jpeg", 0.8);
  } finally {
    origen.liberar();
  }
}
