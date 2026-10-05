# Modelo de seguridad

Quién puede hacer qué, qué puede salir mal y con qué se controla. Es también el entregable del PDF "controles de acceso".

## Actores

| Actor | Confianza |
|---|---|
| Almacenista | Opera su almacén. Puede equivocarse o coludirse con un trabajador. |
| Supervisor | Autoriza excepciones y administra el catálogo. |
| Compras | Ve costos y carga inventario. |
| RH | Ve datos personales. |
| Administrador | Tiene todos los permisos. En el MVP solo carga los datos iniciales; con FEAT-006 administra roles y usuarios. |
| Trabajador | No tiene cuenta. Puede intentar sacar equipo sin derecho o devolver equipo ajeno. |
| Externo | Cualquiera en Internet: el sistema está publicado. |

## Qué se protege

- **La bitácora.** Si se puede alterar, deja de servir como prueba.
- **Los datos personales** de los trabajadores: CURP, NSS, firma.
- **Los costos**, que no deben llegar al trabajador (RG-12).
- **Las existencias**, que deben coincidir con la realidad.

## Control de acceso

- El acceso se decide por permisos con clave, no por el nombre del rol ([ADR-007](decisions/ADR-007-permisos-por-clave.md)). El catálogo de permisos y lo que trae cada rol inicial están en la sección 8 de las [reglas de negocio](../product/reglas-de-negocio.md).
- El servidor verifica el permiso en cada endpoint. La interfaz solo oculta lo que el rol no permite. Seis rutas lo verifican en el servicio en vez de en el router, porque depende del tipo de vale o del usuario (`POST /api/vales`, `POST /api/vales/evaluar`, `GET /api/escaneo/{codigo}`, `GET /api/busqueda`, `GET /api/autorizaciones/{id}` y `POST /api/autorizaciones/{id}/resolucion`); responden 403 igual que las demás.
- Cada usuario opera su almacén asignado, salvo que su rol tenga `almacenes.todos` (AC-06).
- Los datos reservados piden un permiso de información; sin él, el dato no se envía (AC-05).
- Hay cuatro cosas que ningún rol puede hacer, porque no son permisos (AC-07): editar o borrar movimientos, autorizarse a sí mismo, autorizar un rojo de seguridad y mostrar costos en un vale.
- Una prueba por permiso comprueba que el endpoint responde con él y da 403 sin él; otra compara los roles iniciales contra las reglas.

## Amenazas y controles

| Amenaza | Control |
|---|---|
| Alterar o borrar un vale para ocultar un faltante. | Los movimientos solo se insertan; no hay endpoint que los edite. Respaldo periódico (`scripts/respaldo.*`) y `app.mantenimiento verificar`, que descubre existencias que no cuadran con la bitácora. El sello encadenado llega con FEAT-001. |
| Registrar una devolución sin recibir el equipo. | Cada vale lleva al responsable por su sesión; el cierre de almacén (FEAT-002) descubre lo que el sistema dice que hay y no aparece. |
| Sacar equipo con contrato vencido. | La vigencia se evalúa en el servidor con su propia fecha (E-02). |
| Presentar la credencial de otro. | El almacenista ve los datos del trabajador y su foto (T-09). |
| Devolver equipo de otra compañía. | Un código desconocido se rechaza (V-12). |
| Autorizarse a sí mismo un excedente. | Quien captura no puede autorizar (A-05). |
| Darse permisos de más, o dejar un rol que exponga datos. | Solo quien tiene `acceso.administrar` cambia roles, y cada cambio queda en el registro de cambios. Hasta FEAT-006, los roles solo cambian por el script de datos. |
| Dejar al sistema sin administrador. | El rol Administrador no pierde `acceso.administrar`, y no se inactiva al último usuario que lo tiene (AC-09). |
| Adivinar una contraseña o un PIN. | Argon2; bloqueo de cinco minutos tras cinco intentos; mensaje de error genérico. |
| Robo de sesión. | Cookie `HttpOnly`, `Secure` y `SameSite=Lax`; la sesión vence. |
| Peticiones falsas desde otro sitio. | Un solo origen y `SameSite=Lax`. |
| Inyección de SQL o de código en pantalla. | Consultas por ORM; React escapa el texto; ningún HTML llega de los datos. |
| Subir un archivo dañino como firma o foto. | Se validan tipo y tamaño; se guarda con nombre generado, fuera de la carpeta pública. |
| Ver un vale ajeno adivinando su dirección. | El token del vale tiene 128 bits aleatorios; en el MVP además pide sesión. |
| Fuga de secretos. | `.env` fuera del repositorio; `.env.example` sin valores reales. |
| Acceso directo a la base de datos. | MySQL no se publica por el túnel y solo escucha en la máquina local. |
| Pérdida de datos. | Respaldo de la base y de los archivos con `scripts/respaldo.sh` o `respaldo.ps1`; restauración probada en otra base con `restaurar.*`; las existencias se pueden verificar y reconstruir desde la bitácora. |

## Datos personales

- Se guarda lo mínimo: nombre, número de empleado, puesto y periodo. CURP y NSS son opcionales.
- La firma es dato personal: se guarda como archivo en el volumen, ligado a su vale.
- El almacenista no ve CURP, NSS ni sueldo; el sistema no guarda sueldos (RG-13).
- La huella dactilar no se usa.
- Para operar con datos reales, la empresa debe entregar su aviso de privacidad al trabajador.

## Respaldos y recuperación

Lo que existe hoy:

- **Respaldo.** `scripts/respaldo.sh` (bash) y `scripts/respaldo.ps1` (PowerShell) generan, con la misma marca de fecha, un `bd-MARCA.sql.gz` (volcado de MySQL con `mysqldump --single-transaction --routines --triggers`, ejecutado dentro del contenedor de la base) y un `archivos-MARCA.tar.gz` (firmas y fotos). Van a `respaldos/` o a `RESPALDOS_DIR`; la carpeta está en `.gitignore`. `RESPALDOS_CONSERVAR=N` conserva solo los N más recientes. Ninguna contraseña aparece en la línea de comandos ni en el registro: `mysqldump` lee la clave de root del entorno del propio contenedor.
- **Restauración.** `scripts/restaurar.sh` y `restaurar.ps1` restauran los dos archivos. Piden confirmación explícita antes de sobrescribir la base de producción (hay que escribir su nombre). Con `--base OTRA` restauran en una base distinta, sin tocar producción, que es como se prueba. Se probó respaldando una base y restaurándola en otra: los conteos de vales, movimientos y existencias coincidieron y `verificar` dio 0 en ambas.
- **Verificación.** `python -m app.mantenimiento verificar` (solo lectura) comprueba las invariantes de [data-model.md](data-model.md) sobre la base real y sale con código 1 si encuentra diferencias. Conviene correrlo después de cada restauración.
- **Reconstrucción de existencias.** `python -m app.mantenimiento reconstruir-existencias` calcula lo que valdrían las existencias desde la bitácora. Con `--simular` no escribe. Con `--aplicar` las reescribe, y es **la única operación que escribe `existencia` fuera del motor de `movimientos`**: se permite porque es una recuperación (la bitácora es la verdad y las existencias son su suma guardada, ADR-001), solo existe por línea de comandos, exige escribir una frase de confirmación en una terminal interactiva, se niega si la bitácora arrojaría una existencia negativa y deja un renglón en `auditoria`. Nunca toca vales ni movimientos.
- **Programación.** El respaldo diario se programa con el Programador de tareas de Windows o con cron; los pasos están en [despliegue-local-cloudflare.md](despliegue-local-cloudflare.md).

Lo que falta: el respaldo se lanza a mano o con la tarea programada del equipo, y las copias quedan en la misma máquina; copiarlas a otro equipo o a la nube es decisión de operación. No hay verificación periódica automática de la consistencia.

## Riesgos aceptados en el MVP

- Sin sello contra alteración hasta FEAT-001: la inmutabilidad de vales y movimientos la garantiza solo el código (no hay endpoint que los edite y los servicios no los actualizan), no la base de datos. Quien tenga acceso directo a MySQL podría modificar un registro sin dejar rastro; `verificar` detecta los cambios que rompen las invariantes (por ejemplo, existencias que ya no suman), pero no una edición que las deje cuadradas.
- Sin segundo factor de autenticación.
- Sin administración de usuarios ni de roles en pantalla hasta FEAT-006.
