import type { jsPDF } from "jspdf";

let fuente: Promise<string> | null = null;
export async function prepararFuentePdf(doc: jsPDF): Promise<void> {
  fuente ??= fetch("/fuentes/Poppins-Regular.ttf").then(async (respuesta) => {
    if (!respuesta.ok) throw new Error("No pudimos cargar la letra del documento.");
    const datos = new Uint8Array(await respuesta.arrayBuffer());
    let texto = "";
    for (let i = 0; i < datos.length; i += 8192) texto += String.fromCharCode(...datos.subarray(i, i + 8192));
    return btoa(texto);
  }).catch((error) => { fuente = null; throw error; });
  doc.addFileToVFS("Poppins-Regular.ttf", await fuente);
  doc.addFont("Poppins-Regular.ttf", "Poppins", "normal");
  doc.setFont("Poppins", "normal");
}
