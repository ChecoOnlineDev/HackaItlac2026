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
- El servidor verifica el permiso en cada endpoint. La interfaz solo oculta lo que el rol no permite.
- Cada usuario opera su almacén asignado, salvo que su rol tenga `almacenes.todos` (AC-06).
- Los datos reservados piden un permiso de información; sin él, el dato no se envía (AC-05).
- Hay cuatro cosas que ningún rol puede hacer, porque no son permisos (AC-07): editar o borrar movimientos, autorizarse a sí mismo, autorizar un rojo de seguridad y mostrar costos en un vale.
- Una prueba por permiso comprueba que el endpoint responde con él y da 403 sin él; otra compara los roles iniciales contra las reglas.

## Amenazas y controles

| Amenaza | Control |
|---|---|
| Alterar o borrar un vale para ocultar un faltante. | Los movimientos solo se insertan; no hay endpoint que los edite. Respaldo periódico. El sello encadenado llega con FEAT-001. |
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
| Pérdida de datos. | Respaldo con restauración probada; las existencias se reconstruyen desde la bitácora. |

## Datos personales

- Se guarda lo mínimo: nombre, número de empleado, puesto y periodo. CURP y NSS son opcionales.
- La firma es dato personal: se guarda como archivo en el volumen, ligado a su vale.
- El almacenista no ve CURP, NSS ni sueldo; el sistema no guarda sueldos (RG-13).
- La huella dactilar no se usa.
- Para operar con datos reales, la empresa debe entregar su aviso de privacidad al trabajador.

## Respaldos

- Un comando genera el volcado de MySQL y copia el volumen de archivos.
- La restauración se prueba antes del release y se documenta en el README.
- En el prototipo el respaldo se lanza a mano; programarlo queda para producción.

## Riesgos aceptados en el MVP

- Sin sello contra alteración hasta FEAT-001: quien tenga acceso directo a la base podría modificar un registro sin dejar rastro.
- Sin segundo factor de autenticación.
- Sin administración de usuarios ni de roles en pantalla hasta FEAT-006.
