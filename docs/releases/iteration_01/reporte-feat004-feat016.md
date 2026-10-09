# Informe FEAT-004 y FEAT-016

Fecha: 2026-10-08. Trabajo local, sin commit ni push.

## Tarea y cambios

FEAT-004 incorpora mínimos por almacén/artículo con GET/PUT y permiso `inventario.minimos`, filtro de inventario bajo mínimo, existencias disponibles/no disponibles y advertencias E-14/X-05 sin bloquear. Actualiza el marcado de mantenimiento/calibración y el retorno al servicio condicionado por inspección. Migración 0013 y prueba `test_minimos_feat004.py`.

FEAT-016 incorpora `dias_aviso_inspeccion` nullable en categoría y artículo; resolución viva ARTICULO/CATEGORIA/GENERAL (general `INSPECCION_AVISO_DIAS=7`, válido 1–90); conteo real de artículos con aviso propio. Nuevos `repository_pendientes.py`/`service_pendientes.py` agregan y paginan en SQL; no cargan toda la planta para paginar. GET `/api/inspecciones/pendientes` devuelve conteos, elementos y total; `solo_contar=true` devuelve solo conteos, y `contar_resumen` permite reutilizarlo en el Inicio.

POST individual `/api/piezas/{id}/inspecciones` exige cinco puntos booleanos/null, acepta id_cliente y foto dataURL. Devuelve 201 al insertar o 200 con repetida=true al reutilizar exactamente UUID, actor, pieza y contenido. La huella rechaza reutilización con contenido distinto. La foto se guarda con la inspección en la misma transacción; GET `/api/inspecciones/{id}/foto` protege contenido por `inspecciones.ver` y alcance de lectura. Inspección, estado y auditoría se confirman juntos. Fotos con formato inválido o más de 3 MB revierten la inspección; un archivo huérfano en volumen puede quedar si falló después de escribirlo, igual que el patrón existente de firmas.

POST `/api/inspecciones/lotes` recibe `{id_lote,piezas:[{codigo,id_cliente,resultado,puntos,observacion?,foto?}]}`. Máximo 50. Responde resultados GUARDADA/REPETIDA/RECHAZADA y totales guardadas/repetidas/rechazadas. Cada pieza confirma o revierte separadamente; un rechazo no borra las anteriores. El identificador id_lote se devuelve como envoltura; la deduplicación persistente ocurre por id_cliente de cada pieza.

P-17 responde 409 PIEZA_EN_TRANSITO o PIEZA_EN_MANTENIMIENTO; Baja conserva rechazo. I-03 fecha futura devuelve 422 FECHA_FUTURA. Retirar mantenimiento/calibración a NO_APTO usa piezas.marcar_estado; el nuevo examen usa piezas.inspeccionar. Ficha de pieza suma periodo/aviso/origen/días restantes/vigencia si Apta hoy/inspeccion_posible; historial y última inspección suman foto/puntos/id.

## Archivos y decisiones

Cambios circunscritos a almacenes/catalogo/inspecciones/archivos/acceso/consulta; hooks puntuales de evaluación/cargador/traspaso de FEAT-004 coordinados con la tarea principal. Nuevos modelos registrados mediante imports ya existentes; no se modificó main.py. Se mantuvo `catalogo/models_minimos.py` para evitar un cambio de ubicación ajeno a la funcionalidad; el límite entre módulos se atiende por `AlmacenService.minimo`.

Permisos nuevos: `inventario.minimos` (Compras/Admin) y `inspecciones.ver` (Almacenista/Supervisor/Admin). La tarea principal integra documentación global y permisos del tablero. Los cinco puntos son explícitos: null significa No aplica y se conserva; no significa omitido.

## Validación

- FEAT-004, almacenes, privacidad VI y módulo inspecciones: 64 pruebas aprobadas antes de iniciar 016.
- Inspecciones existentes + FEAT-004 tras 016: 47 aprobadas.
- Nuevas FEAT-016: seis aprobadas.
- Regresión catálogo/trazabilidad/límites: 77 aprobadas, dos fallos por fixtures sin proyecto requerido por PR-11; comunicados a la tarea principal.
- Ruff en módulos/archivos tocados y pruebas específicas: aprobado.
- Migración 0015 upgrade/down 0014/upgrade, solo base `_test_feat016mig`: aprobado.
- Frontend 004/016 construido por otro agente, tipos aprobados según su reporte; recorrido manual físico pendiente.

## Riesgos y siguiente acción

P-15 notificaciones locales depende de FEAT-020 y no se acredita. Falta demostrar recorrido visual con permisos y volumen grande de piezas. La definición de terminado global requiere corregir fixtures PR-11 y ejecutar la suite final, tipos y construcción desde la tarea principal. Auditoría inicial 001–020 conservada en `estado-features-001-020.md` como línea base y no como estado final.
