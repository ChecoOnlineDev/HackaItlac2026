/** Los archivos autenticados llegan por el fetch nativo, con las cookies de sesión. */
let limpiezaEnCurso: Promise<void> | undefined;

export function limpiarCompartidos(): Promise<void> {
  limpiezaEnCurso ??= borrarCompartidosAntiguos().finally(() => { limpiezaEnCurso = undefined; });
  return limpiezaEnCurso;
}

async function borrarCompartidosAntiguos(): Promise<void> {
  const { Filesystem, Directory } = await import("@capacitor/filesystem");
  const carpeta = await Filesystem.readdir({ path: "compartidos", directory: Directory.Cache })
    .catch(() => ({ files: [] }));
  for (const archivo of carpeta.files) {
    const coincide = /^(\d+)-[0-9a-f-]{36}$/.exec(archivo.name);
    if (!coincide || Date.now() - Number(coincide[1]) < 3_600_000) continue;
    await Filesystem.rmdir({ path: `compartidos/${archivo.name}`, directory: Directory.Cache, recursive: true });
  }
}

export async function compartirArchivo(blob: Blob, nombre: string): Promise<void> {
  const [{ Filesystem, Directory }, { Share }] = await Promise.all([
    import("@capacitor/filesystem"), import("@capacitor/share"),
  ]);
  const datos = await new Promise<string>((resolve, reject) => {
    const lector = new FileReader();
    lector.onerror = () => reject(new Error("No pudimos preparar el archivo."));
    lector.onload = () => resolve(String(lector.result).split(",")[1]);
    lector.readAsDataURL(blob);
  });
  const seguro = nombre.replace(/[^\p{L}\p{N}._ -]/gu, "_").slice(0, 120) || "archivo";
  await limpiarCompartidos();
  const path = `compartidos/${Date.now()}-${crypto.randomUUID()}/${seguro}`;
  const { uri } = await Filesystem.writeFile({ path, data: datos, directory: Directory.Cache, recursive: true });
  // El selector vuelve antes de que el receptor termine de copiar. Retener temporalmente;
  // al abrir la app o compartir de nuevo se limpian exportaciones de más de una hora.
  await Share.share({ title: seguro, files: [uri] });
}
