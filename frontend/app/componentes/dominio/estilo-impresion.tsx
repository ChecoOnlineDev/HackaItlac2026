/**
 * Hoja carta para imprimir solo lo marcado con la clase `zona-impresion`: oculta todo lo demás
 * (menús, botones, avisos) y quita los encabezados del navegador con un margen de página propio.
 * Se pone una vez por componente imprimible; repetirlo no estorba.
 */
export const CLASE_IMPRESION = "zona-impresion";

export function EstiloImpresion() {
  return (
    <style>{`
      @media print {
        @page { size: letter; margin: 12mm; }
        html, body { background: #fff !important; height: auto !important; overflow: visible !important; }
        body *:not(.${CLASE_IMPRESION}):not(.${CLASE_IMPRESION} *):not(:has(.${CLASE_IMPRESION})) { display: none !important; }
        /* Los contenedores que quedan alrededor de la hoja pierden marcos, rellenos y fondos. */
        body:has(.${CLASE_IMPRESION}), body *:has(.${CLASE_IMPRESION}) {
          display: block !important; position: static !important; width: auto !important; max-width: none !important;
          height: auto !important; min-height: 0 !important; margin: 0 !important; padding: 0 !important;
          border: 0 !important; border-radius: 0 !important; background: transparent !important; box-shadow: none !important;
          overflow: visible !important; transform: none !important;
        }
        .${CLASE_IMPRESION} { -webkit-print-color-adjust: exact; print-color-adjust: exact; color: #000; box-shadow: none !important; }
      }
    `}</style>
  );
}
