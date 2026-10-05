# FEAT-005: Identidad con foto

> **Estado:** pasó al MVP como foto opcional en el alta (T-09, US-TRB-001 y US-ENT-001). Este brief queda como referencia de su alcance y sus criterios.

## Problema u oportunidad

El patrocinador quiere tener controlado que el almacén le entrega a quien corresponde (plática min 16). Con la credencial sola, cualquiera que la traiga recibe el equipo. La huella quedó descartada ([ADR-005](../architecture/decisions/ADR-005-evidencia-del-vale.md)).

## Objetivo

Que el almacenista confirme con la vista que quien recibe es el titular de la credencial.

## Historia de usuario

Como almacenista, quiero ver la foto del trabajador al escanear su credencial, para entregarle solo a la persona correcta.

## Alcance incluido

- En el alta o en la ficha, RH toma la foto con la cámara del dispositivo o sube una imagen.
- Al identificar al trabajador en una entrega, la ficha breve muestra su foto en grande.
- Un trabajador sin foto muestra un aviso "Sin foto registrada" y la entrega continúa.

## Fuera de alcance

- Reconocimiento facial o cualquier comparación automática.
- Foto del momento de la entrega.
- Exigir foto para poder entregar.

## Criterios de aceptación

- Dado un trabajador con foto, cuando se escanea su credencial, entonces la foto aparece junto a su nombre antes de escanear artículos.
- La foto solo la ve quien tiene el permiso `trabajadores.ver`; el comprobante público no la muestra.
- Se rechazan archivos que no son imagen o que pesan más del tamaño permitido.
- La foto se puede reemplazar; el cambio queda en el registro de cambios.

## Módulos relacionados conocidos

`trabajadores` (foto), interfaz de alta y de entrega.

## Cambios de datos o API esperados

- `trabajador.foto_adjunto_id`; `adjunto.tipo` admite FOTO_TRABAJADOR.
- `POST /api/trabajadores/{id}/foto`; la ficha responde la dirección de la foto.

## Restricciones y compatibilidad

- La foto es un dato personal: se guarda en el volumen de archivos y se entrega solo con sesión.

## Riesgos

- Fotos pesadas en una red lenta: se reducen en el navegador antes de subirlas.

## Validaciones requeridas

- Prueba de permisos sobre la foto.
- Toma de foto real desde un celular.

## Documentos globales que podrían actualizarse

`data-model.md`, `api-contracts.md`, `security-model.md`, `ui-ux.md` (ficha breve).
