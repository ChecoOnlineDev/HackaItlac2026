# FEAT-006: Control de acceso configurable

## Problema u oportunidad

El MVP nace con cinco roles cargados por un script. Cada empresa reparte el trabajo de forma distinta, y el patrocinador quiere seguir agregando módulos después (plática min 40). En la plática quedó abierta, además, la pregunta de qué datos del trabajador debe ver el almacenista (min 28). Hoy cualquiera de esos cambios pediría editar el script, y los usuarios tampoco se pueden crear desde la pantalla.

## Objetivo

Que un administrador cree roles, decida qué puede hacer y qué información puede ver cada uno, y administre a los usuarios, sin tocar el código.

## Historia de usuario

Como administrador, quiero crear roles y activar o quitar permisos por módulo, para adaptar el sistema a como trabaja la empresa.

Como administrador, quiero dar de alta usuarios y asignarles rol y almacén, para no depender de un script.

## Alcance incluido

- **Roles.** Crear, renombrar, duplicar e inactivar; activar o quitar permisos en una matriz agrupada por módulo.
- **Usuarios.** Alta, edición, rol, almacén asignado, inactivar, y restablecer contraseña y PIN.
- **Asignación de personal.** Ver quién está en cada almacén y moverlo, en una lista con un selector de almacén por usuario. Tiene su propio permiso, `almacenes.asignar_personal`, para que un supervisor lo haga sin acceso a roles ni permisos (AC-12, AC-13). Un almacén puede tener varios almacenistas; un almacenista, un solo almacén.
- **Roles iniciales.** Se pueden editar; el Administrador está protegido.
- **Registro de cambios** de roles, permisos y usuarios.
- **Restablecer.** Un comando regresa los cinco roles iniciales a como nacieron.

El catálogo de permisos, sus dos clases (de acción y de información) y lo que trae cada rol inicial ya existen desde el MVP: están en la sección 8 de las [reglas de negocio](../product/reglas-de-negocio.md). Esta feature agrega la pantalla para cambiarlos.

Ejemplo guía: el administrador activa `trabajadores.ver_datos_personales` en el rol Almacenista, y desde la siguiente consulta el almacenista ve esos datos en la ficha.

## Fuera de alcance

- Permisos por usuario individual; se asignan por rol.
- Varios roles por usuario.
- Permisos por registro, como un trabajador o un artículo en particular.
- Crear permisos nuevos desde la pantalla: el catálogo lo define el sistema.
- Tablero general por almacén.
- Inicio de sesión con cuentas externas.
- Arrastrar y soltar para mover personal: el uso principal es el celular y la tableta.
- Que un usuario vea un subconjunto de almacenes: hoy ve el suyo o todos (AC-06).
- Alertas de cobertura de turnos.

## Criterios de aceptación

- Dado un rol nuevo sin permisos, cuando un usuario con ese rol entra, entonces no ve ningún módulo y toda petición responde 403.
- Dado que el administrador activa `trabajadores.ver_datos_personales` en el rol Almacenista, entonces la siguiente consulta del almacenista incluye CURP y NSS; al quitarlo, dejan de enviarse.
- Dado un permiso de acción quitado, entonces su botón desaparece y su endpoint responde 403.
- El cambio aplica en la siguiente petición, sin cerrar la sesión.
- Antes de guardar, la pantalla muestra qué gana y qué pierde el rol.
- No se puede quitar al rol Administrador el permiso `acceso.administrar`, ni inactivar al último usuario que lo tiene.
- Un rol con usuarios asignados no se puede inactivar ni eliminar hasta reasignarlos.
- La pantalla no ofrece ningún permiso para editar o borrar movimientos, autorizarse a sí mismo, autorizar un rojo de seguridad ni mostrar costos en un vale.
- Cada cambio queda en el registro de cambios, con quién, cuándo, valor anterior y valor nuevo.
- Sin tocar nada, los cinco roles iniciales siguen pasando la prueba de permisos del MVP.
- Dado un almacenista asignado a un almacén, cuando un usuario con `almacenes.asignar_personal` lo mueve a otro, entonces su siguiente petición opera el almacén nuevo y el cambio queda en el registro de cambios, con el almacén anterior y el nuevo.
- Dado un vale a medio capturar en el almacén anterior, entonces al confirmar se rechaza con `ALMACEN_CAMBIO` y el borrador se conserva.
- Un almacén puede tener varios almacenistas; un almacenista tiene un solo almacén.
- Quien tiene `almacenes.asignar_personal` y no `acceso.administrar` no puede crear usuarios ni cambiar roles o permisos.
- Los movimientos y vales anteriores conservan el almacén en el que se hicieron.

## Módulos relacionados conocidos

`acceso` (roles, permisos y usuarios) y una pantalla nueva de administración. Los demás módulos no cambian: ya piden permisos por clave ([ADR-007](../architecture/decisions/ADR-007-permisos-por-clave.md)).

## Cambios de datos o API esperados

- Sin tablas nuevas: `rol`, `rol_permiso` y `usuario.rol_id` existen desde la Fase 1.
- `GET /api/permisos`; `GET`, `POST` y `PATCH /api/roles`; `PUT /api/roles/{id}/permisos`; `GET`, `POST` y `PATCH /api/usuarios`; `POST /api/usuarios/{id}/contrasena`. Todos piden `acceso.administrar`, salvo `GET /api/personal` y `PATCH /api/usuarios/{id}/almacen`, que piden `almacenes.asignar_personal`.
- **Estado: construida.** La lista de personal, la reasignación de almacén, las altas y ediciones de usuario y el restablecimiento de contraseña están en [Usuarios y personal](../architecture/api-contracts.md#usuarios-y-personal); `GET /api/permisos` y `GET`, `POST`, `PATCH`, `PUT /api/roles/{id}/permisos` y `DELETE /api/roles` en [Roles y permisos](../architecture/api-contracts.md#roles-y-permisos). Pantallas: `/personal`, `/usuarios`, `/roles` y `/roles/:id` ([app-flow.md](../product/app-flow.md), flujos 17 y 18).
- **Decisiones al construirla.** (1) Los cinco roles iniciales se pueden ajustar pero no se eliminan ni se renombran (el script de datos los identifica por nombre). (2) Cada permiso de acción declara qué permisos de ver necesita (`requiere`); la pantalla los activa juntos y no deja quitar el de ver mientras otro lo necesita; el servidor lo vuelve a validar (422). (3) Duplicar un rol es crear uno nuevo con los permisos del original. (4) Si un rol recibe `almacenes.todos`, sus usuarios dejan el almacén asignado; si lo pierde, quedan sin almacén hasta que alguien los asigne en Personal. (5) El comando para restablecer los cinco roles iniciales sigue **pendiente**: no se construyó (se vuelve a cargar con el script de datos de prueba, que reemplaza sus permisos).

## Restricciones y compatibilidad

- Se puede construir en paralelo, en una rama o worktree aparte, a partir del cierre de la Fase 1: solo toca el módulo `acceso` y una pantalla nueva.
- Las reglas que protegen la bitácora y la seguridad no son permisos y no se pueden desactivar (AC-07).
- Un permiso de acción incluye el de ver su módulo; la pantalla no deja quitar el segundo si el primero sigue activo.

## Riesgos

- **Quedarse sin administrador** o dejar un rol que bloquee la operación. Lo cubren las protecciones del Administrador y el comando para restablecer los roles iniciales.
- **Más configuración, más formas de equivocarse.** La pantalla muestra el efecto del cambio antes de guardar.
- **Quitarle tiempo al flujo principal.** Por eso va fuera del orden de la segunda ola y en paralelo.

## Validaciones requeridas

- Prueba de las protecciones del Administrador.
- Prueba de que un cambio de permisos aplica en la siguiente petición.
- Prueba de que un rol con usuarios no se inactiva.
- La prueba de permisos del MVP sigue pasando con los roles iniciales.

## Documentos globales que podrían actualizarse

`reglas-de-negocio.md` (AC-08 a AC-13), `api-contracts.md`, `security-model.md`, `app-flow.md` y `ui-ux.md` (pantalla de administración).
