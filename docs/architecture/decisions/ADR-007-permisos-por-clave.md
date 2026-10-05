# ADR-007: Los permisos se verifican por clave y los roles son datos

## Estado

Aceptada (4 de octubre de 2026).

## Contexto

El PDF pide cuatro perfiles: almacenista, supervisor, Compras y Recursos Humanos. El equipo quiere que un administrador pueda crear roles y decidir qué hace y qué ve cada uno ([FEAT-006](../../features/FEAT-006-control-de-acceso-configurable.md)). La primera versión del plan comparaba el perfil del usuario en cada endpoint.

## Fuerzas y restricciones

- La verificación de permisos toca todos los endpoints: cambiarla después es caro.
- El editor de roles no lo califica la rúbrica, y el tiempo es de tres días más 24 horas.
- Hay reglas que ninguna configuración debe poder saltarse.
- El PDF exige que existan los cuatro perfiles y usuarios de prueba para cada uno.

## Alternativas consideradas

1. **Perfiles fijos en el código.** Es lo más rápido, pero FEAT-006 obligaría después a reescribir cada endpoint.
2. **Control de acceso configurable completo desde el MVP.** Es lo deseado, pero pone una pantalla de administración y sus pruebas en el camino crítico.
3. **Base ahora, editor después.** Desde la Fase 1 el servidor verifica permisos por clave y los roles se guardan como datos; la pantalla para editarlos llega con FEAT-006.

## Decisión

La alternativa 3.

- El **catálogo de permisos** es fijo y vive en el código, con claves `modulo.accion`. Hay permisos de acción y de información.
- Un **rol** es un conjunto de permisos con nombre, guardado en la base de datos. Cada usuario tiene un rol.
- El script de datos de prueba carga **cinco roles iniciales**: Administrador, con todos los permisos, y los cuatro del PDF.
- El servidor **nunca compara el nombre del rol**: pregunta si el usuario tiene el permiso.
- El **alcance por almacén** va aparte: cada usuario opera su almacén asignado, salvo que su rol tenga `almacenes.todos`.
- **No son configurables:** la bitácora no se edita, quien captura no se autoriza, un rojo de seguridad no se autoriza y un vale no muestra costos.

Las reglas son AC-01 a AC-13, y el catálogo con los roles iniciales está en la sección 8 de las [reglas de negocio](../../product/reglas-de-negocio.md).

## Justificación

Hecho desde el inicio, verificar por permiso cuesta casi lo mismo que verificar por perfil. Deja FEAT-006 como una pantalla más, cumple el PDF porque sus cuatro perfiles existen como roles iniciales, y crea el rol Administrador que le faltaba al plan.

## Consecuencias positivas

- FEAT-006 no toca los endpoints ya escritos.
- "El costo solo lo ve Compras" y "los datos personales solo los ve RH" pasan a ser permisos de información, con un solo mecanismo.
- La prueba de permisos se escribe por permiso y sigue sirviendo cuando cambien los roles.

## Consecuencias negativas

- Dos tablas más y un poco más de trabajo en la Fase 1.
- El servidor lee los permisos del rol en cada petición.
- Mientras no exista FEAT-006, cambiar un rol pide editar el script de datos.

## Señales para reevaluar

- La empresa necesita permisos por usuario o por registro, no solo por rol.
- El catálogo de permisos crece tanto que la matriz deja de ser legible.
