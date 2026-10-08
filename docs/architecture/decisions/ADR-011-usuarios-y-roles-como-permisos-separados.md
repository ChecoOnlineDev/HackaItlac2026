# ADR-011: Usuarios y roles pasan a permisos separados

## Estado

Aceptada (7 de octubre de 2026). Extiende [ADR-007](ADR-007-permisos-por-clave.md).

## Contexto

`acceso.administrar` abría a la vez las pantallas de usuarios y de roles. [FEAT-011](../../features/FEAT-011-entrada-por-kepler-trazabilidad-y-menu.md) pide que quien da de alta usuarios no tenga que poder cambiar permisos, y que el menú «Personas y accesos» se muestre según lo que cada persona puede hacer. También pide separar los límites de entrega del resto del catálogo.

## Alternativas consideradas

1. **Dejar `acceso.administrar` y agregar los nuevos como adorno.** Los nuevos no separarían nada.
2. **Quitar `acceso.administrar` y usar solo los nuevos.** Rompe la regla AC-09 («siempre queda un administrador») y a las bases que ya tienen filas con esa clave.
3. **Conservarlo como marca del administrador del sistema y partir lo que abre.**

## Decisión

La alternativa 3.

- `/usuarios` y sus rutas piden `acceso.usuarios`. `/roles` y el catálogo de permisos (`GET /api/permisos`) piden `acceso.roles`.
- `acceso.administrar` no abre ninguna ruta. Solo marca al administrador del sistema: AC-09 sigue contando usuarios con este permiso, y el rol Administrador no puede perderlo.
- El Administrador (protegido) tampoco pierde `acceso.usuarios`, `acceso.roles`, `almacenes.todos` ni `almacenes.administrar` (AC-32).
- `catalogo.limites` separa los límites de entrega de `catalogo.administrar`. El servicio del catálogo lo exige, además del permiso de la ruta, al crear o editar un límite en una categoría o un artículo.
- La migración `0008_permisos_feat011` no quita acceso a nadie: da `acceso.usuarios` y `acceso.roles` a todo rol que tenía `acceso.administrar`, y `catalogo.limites` a todo rol con `catalogo.administrar` salvo el Supervisor, a quien AC-31 se lo quita a propósito.
- El script de datos de prueba ya no reemplaza los permisos de los roles iniciales: solo agrega lo que falta (AC-33).
- Las rutas que aceptan uno de dos permisos nuevos (`bitacora.ver` o `reportes.movimientos`; `reportes.existencias` o `resguardo.ver`) lo declaran en el router con `requiere_alguno(...)`, no en el servicio. Los IDs de esta feature son AC-30 a AC-35 porque AC-24 ya era de las cookies de sesión.

## Consecuencias

- Positivas: se puede crear un rol que da de alta usuarios sin tocar permisos y al revés; el menú y las pruebas se escriben por permiso.
- Negativas: un rol que solo tenga `acceso.administrar` ya no entra a ninguna pantalla; la interfaz debe usar los permisos nuevos para mostrar «Usuarios» y «Roles».
- Cambia el permiso de 5 rutas de usuarios y 7 de roles (con el catálogo de permisos), y el contrato de `GET /api/permisos` (campos `grupo` y `disponible`).

## Señales para reevaluar

- Si ningún cliente necesita `acceso.administrar` como marca, AC-09 puede apoyarse en `acceso.roles` y eliminarlo.
