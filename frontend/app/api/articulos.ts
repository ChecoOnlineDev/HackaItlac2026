import { apiPost } from "~/api/cliente";

/** Lo mínimo que la pantalla necesita de un artículo recién creado. */
export interface ArticuloCreado {
  id: string;
  codigo: string;
  nombre: string;
  control: "PIEZA" | "CANTIDAD";
  unidad: string;
}

export interface DatosArticuloNuevo {
  nombre: string;
  categoria_id: string;
  unidad: string;
  /** Solo si la categoría no genera códigos; en las demás lo genera el servidor (EK-07). */
  codigo?: string;
}

/** `POST /api/articulos`: da de alta un artículo con la plantilla de su categoría (EK-07). */
export const crearArticulo = (datos: DatosArticuloNuevo) => apiPost<ArticuloCreado>("/articulos", datos);
