import type { Condicion } from "~/componentes/dominio/tipos";
import type { ValeDetalle } from "~/componentes/dominio/vale-imprimible";
import type { ValeDetalleApi } from "./tipos";

/**
 * Convierte lo que responde `GET /api/vales/{id}` (o `por-token`) a la forma que pinta `ValeImprimible`.
 * La imagen de la firma no viaja en el detalle (solo `tiene_firma`): si la pantalla ya la tiene (porque
 * acaba de capturarla), se pasa en `firmaImagen`; si no, se pide a `GET /api/vales/{id}/firma` (mismo
 * alcance que el vale, con la sesión) y, mientras no carga o si falla, el vale dice "Firmado en pantalla".
 */
export function aValeImprimible(api: ValeDetalleApi, firmaImagen?: string | null): ValeDetalle {
  return {
    folio: api.folio,
    tipo: api.tipo,
    creado_en: api.creado_en,
    token: api.token,
    estado: api.estado,
    almacen: api.almacen,
    destino_almacen: api.destino_almacen,
    trabajador: api.trabajador
      ? {
          nombre: api.trabajador.nombre,
          numero_empleado: api.trabajador.numero_empleado,
          puesto: api.trabajador.puesto,
          area_obra: api.trabajador.area_obra,
        }
      : null,
    responsable: { nombre: api.responsable.nombre },
    autorizacion: api.valido ? { autorizado_por: { nombre: api.valido.autorizo.nombre }, motivo: api.valido.motivo } : null,
    observacion: api.observacion,
    firma: firmaImagen
      ? { imagen: firmaImagen }
      : api.tiene_firma
        ? { imagen: `/api/vales/${api.id}/firma` }
        : null,
    vale_origen_folio: api.vale_origen_folio,
    renglones: api.renglones.map((r) => ({
      renglon: r.renglon,
      articulo: { nombre: r.articulo, marca: r.marca, talla: r.talla },
      codigo: r.codigo_pieza ?? r.codigo_articulo,
      numero_serie: r.numero_serie,
      cantidad: r.cantidad,
      condicion: (r.condicion as Condicion | null) ?? null,
    })),
    cancelacion: api.cancelacion
      ? { motivo: api.cancelacion.motivo, folio: api.cancelacion.folio, creado_en: api.cancelacion.creado_en }
      : api.estado === "CANCELADO"
        ? {}
        : null,
  };
}
