/** Un paso del recorrido: qué elemento se resalta y qué se le dice a la persona. */
export interface Paso {
  /** Valor del atributo `data-tutorial` del elemento que se resalta. */
  ancla: string;
  /** Una o dos frases en español llano. */
  texto: string;
  /** Pantalla a la que se navega antes de buscar el ancla (opcional). */
  ruta?: string;
  /** `tocar`: un clic en el elemento avanza el paso. `leer`: el globo trae «Siguiente». */
  modo: "tocar" | "leer";
  /**
   * Botón extra del globo, por ejemplo «Escanear un ejemplo». En modo `tocar`, al ejecutarse
   * el paso avanza (hace las veces del toque); en modo `leer` no avanza.
   */
  /**
   * Solo en modo `tocar`: el toque avanza únicamente cuando esto devuelve `true` (se revisa unos instantes
   * después del toque). Sirve cuando tocar no basta, por ejemplo la firma, que pide un trazo.
   */
  listo?: () => boolean;
  accionSimulada?: { etiqueta: string; ejecutar: () => void };
}

/** Un recorrido guiado. Solo aparece si la sesión tiene su permiso (nunca por el nombre del rol). */
export interface Recorrido {
  id: string;
  titulo: string;
  /** Clave `modulo.accion`. Sin permiso, el recorrido lo ve cualquier usuario con sesión. */
  permiso?: string;
  pasos: Paso[];
}
