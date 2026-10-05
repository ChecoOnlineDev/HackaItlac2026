import { Confirmacion } from "~/componentes/ui/confirmacion";

interface PropiedadesConfirmarCantidad {
  abierta: boolean;
  /** Se llama con `false` al tocar "Corregir" o al cerrar; la pantalla decide qué hacer (ver `alCorregir`). */
  alCambiar: (abierta: boolean) => void;
  /** Cantidad del renglón. */
  cantidad: number;
  /** Nombre del artículo, tal como se lee en la frase: "guantes". */
  articulo: string;
  /** Unidad opcional: "pares de" da "¿Entregar 10 pares de guantes?". */
  unidad?: string;
  /** Verbo de la frase. Por omisión "Entregar". */
  verbo?: string;
  alConfirmar: () => void;
  /** Se llama cuando la persona toca "Corregir" o cierra la ventana. */
  alCorregir?: () => void;
}

/**
 * Ventana de confirmación para una cantidad inusual (E-27). Se muestra solo cuando el servidor marca
 * `requiere_confirmacion` en un renglón; no decide nada por su cuenta.
 *
 * ```tsx
 * <ConfirmarCantidad abierta={r.requiere_confirmacion} cantidad={r.cantidad} articulo="guantes" unidad="pares de" ... />
 * ```
 */
export function ConfirmarCantidad({
  abierta,
  alCambiar,
  cantidad,
  articulo,
  unidad,
  verbo = "Entregar",
  alConfirmar,
  alCorregir,
}: PropiedadesConfirmarCantidad) {
  const frase = `¿${verbo} ${cantidad}${unidad ? ` ${unidad}` : ""} ${articulo}?`;
  return (
    <Confirmacion
      abierta={abierta}
      alCambiar={(valor) => {
        alCambiar(valor);
        if (!valor) alCorregir?.();
      }}
      mensaje={frase}
      detalle="Es más de lo que se entrega normalmente. Revisa que la cantidad sea la correcta."
      etiquetaConfirmar="Sí, confirmar"
      etiquetaCancelar="Corregir"
      alConfirmar={alConfirmar}
    />
  );
}
