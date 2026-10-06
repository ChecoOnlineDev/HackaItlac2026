/** Una persona de `GET /api/personal`: quien opera un almacén, con su rol y su almacén actual. */
export interface PersonaAlmacen {
  id: string;
  nombre: string;
  usuario: string;
  rol: { id: string; nombre: string };
  almacen: { id: string; clave: string; nombre: string } | null;
  activo: boolean;
}

export interface AlmacenOpcion {
  id: string;
  clave: string;
  nombre: string;
  estado: string;
}

export const TEXTO_SIN_ALMACEN = "Sin almacén";
export const TAMANO_PAGINA_PERSONAL = 20;
