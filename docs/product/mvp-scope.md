# Alcance del MVP

Decide qué se construye primero y, sobre todo, qué no. Las exclusiones son límites de autoridad: ningún agente ni integrante las agrega sin cambiar antes este documento.

## Hipótesis a comprobar

Un almacenista sin capacitación puede registrar entregas, devoluciones y traspasos escaneando, en segundos, y desde ese momento la empresa sabe quién tiene cada cosa y qué debe devolver.

## Ciclo mínimo de valor

El almacenista identifica al trabajador, escanea los artículos y obtiene un vale foliado y firmado; a partir de ahí, cualquier usuario con permiso puede ver quién tiene cada artículo y qué debe devolver.

## Flujo principal

Es la prueba que describe el PDF (p.2), más el caso de alturas:

1. RH registra a un trabajador.
2. El almacenista le surte EPP y una herramienta por escaneo.
3. Intenta entregar un arnés no apto: el sistema lo impide.
4. Intenta una entrega que excede el límite: el sistema la bloquea hasta que el supervisor autoriza.
5. Registra un traspaso entre almacenes y el destino lo recibe.
6. Al procesar la baja, el sistema muestra los pendientes; tras devolverlos, emite el vale de no adeudo.

## Incluido

Corresponde a la prioridad P0 de las [reglas de negocio](reglas-de-negocio.md).

- **Acceso.** Usuario y contraseña. Cinco roles iniciales: Administrador y los cuatro que pide el PDF (almacenista, supervisor, Compras y RH). El servidor verifica permisos por clave y el menú muestra solo lo que el rol permite.
- **Catálogo configurable.** Categorías con plantilla de reglas; artículos por pieza o por cantidad, retornables o consumibles; requisitos de inspección y de autorización por artículo; inactivar y reactivar con motivo; registro de cambios.
- **Etiquetas.** Hoja imprimible de QR para credenciales, piezas y estantes.
- **Trabajadores.** Alta, reingreso y vigencia por periodo de contrato; foto opcional tomada en el alta.
- **Inventario.** Entrada manual, importación desde una tabla de Excel y existencias por almacén.
- **Entrega.** Escaneo con cámara, pistola o teclado; semáforo; firma en pantalla; vale con folio y QR.
- **Límite y autorización.** Límite por artículo, en posesión o por periodo; autorización del supervisor desde su celular o con PIN.
- **Seguridad.** Inspección de piezas; bloqueo de equipo no apto o sin inspección vigente; ajuste de la vigencia de una inspección por el supervisor o el administrador, con motivo.
- **Devolución.** Por escaneo de la pieza o desde la lista del trabajador; condición al volver; rechazo de equipo ajeno.
- **Traspasos.** Salida, tránsito y recepción con QR.
- **Baja.** Pendientes del trabajador, vale de no adeudo y paso a inactivo.
- **Consulta y reportes.** Escaneo universal, búsqueda por texto, historial de pieza; reportes de existencias, movimientos, adeudos y consumo, con descarga en CSV.
- **Corrección.** Cancelación de un vale con sus movimientos inversos, con motivo; cancelar y rehacer con los mismos renglones; y la lista de los movimientos del día de cada usuario.

## Segunda ola

Son los diferenciadores (prioridad P1). Se construyen como features, una por una y en este orden, **solo después** de que el flujo principal pase su gate de confiabilidad. Cada uno tiene su brief en [features/](../features/).

1. [FEAT-001](../features/FEAT-001-vale-como-prueba.md): vale como prueba.
2. [FEAT-002](../features/FEAT-002-cierre-de-almacen.md): cierre de almacén de proyecto y valor del inventario.
3. [FEAT-003](../features/FEAT-003-dotacion-por-puesto.md): dotación por puesto y avisos no bloqueantes.
4. [FEAT-004](../features/FEAT-004-minimos-y-estados.md): mínimos, estados de pieza y alertas.
5. [FEAT-005](../features/FEAT-005-identidad-con-foto.md): identidad con foto. **Pasó al MVP** como foto opcional en el alta (T-09); el brief queda como referencia.

Aparte está [FEAT-006](../features/FEAT-006-control-de-acceso-configurable.md), control de acceso configurable. No compite por ese orden: toca solo el módulo de acceso y puede avanzar en paralelo, en una rama aparte, desde el cierre de la Fase 1. Su base, los permisos por clave, ya es parte del MVP ([ADR-007](../architecture/decisions/ADR-007-permisos-por-clave.md)).

## Excluido explícitamente

- Modo sin conexión y sincronización.
- Aplicación nativa; lectura de huella o cualquier biometría.
- Notificaciones push, correo, SMS o WhatsApp.
- Integración con nómina, torniquetes o sistemas de la planta.
- Cálculo de descuentos, cargos o finiquitos.
- Órdenes de compra, proveedores y facturas.
- Firma electrónica avanzada y constancias NOM-151.
- Impresión directa a impresoras térmicas; se imprime desde el navegador.
- Administración de usuarios y de roles desde la interfaz; en el MVP se crean con el script de datos de prueba. Llega con FEAT-006.
- Niveles del semáforo configurables por regla.
- Límites sumados por categoría.
- Rutas de traspaso obligatorias; una ruta inusual solo avisa.
- Tema oscuro, varios idiomas y personalización visual.
- Ubicación dentro del almacén, como estante o pasillo: la ubicación llega hasta el almacén o el trabajador.

## Pospuesto

Probable en fases posteriores; hoy no tiene brief.

- Lista de revisión para el supervisor.
- Cierre sin devolución y equipo dado por perdido.
- Reporte de EPP entregado por trabajador.
- Que un usuario vea un subconjunto de almacenes; hoy ve el suyo o todos.
- Habilitaciones del trabajador, como la capacitación de alturas.
- Solicitud de compra.
- Carta de aceptación como requisito del alta.
- Importación de trabajadores desde Excel.
- Tablero general para el administrador, con una pestaña por almacén: Kepler, Contratistas y los almacenes de área.
- Entrega de turno entre almacenistas, con conteo y firma de los dos.
- Solicitud de surtido de un almacén a otro.
- Aviso de que a un almacén le falta cobertura de turnos. Los almacenes operan las 24 horas con varios almacenistas, cada uno con su cuenta y su dispositivo, pero el MVP no vigila que estén cubiertos.

## Restricciones

- **Tiempo.** Tres días previos (4 al 6 de octubre de 2026) y las 24 horas del hackathon (7 y 8 de octubre).
- **Plataformas.** Navegador web. Chrome en Android es la referencia para el almacenista; computadora para Compras y RH.
- **Operación manual aceptada.** Usuarios creados por script; etiquetas impresas en papel común; respaldo lanzado a mano.
- **Calidad mínima.** Permisos verificados en el servidor; estados de carga, vacío y error en cada pantalla; el guion del PDF como prueba automática.

## Condición de éxito del producto

Un evaluador que no conoce el sistema completa el flujo principal desde un celular, con los datos que él mismo entregue, sin que nadie del equipo toque la base de datos.

## Condición de salida técnica

- La prueba automática del guion completo pasa.
- El flujo principal se completa a mano en el entorno desplegado, desde un celular y desde una computadora.
- Los entregables del PDF están listos (ver [mvp-checklist.md](../releases/mvp-checklist.md)).

## Riesgos aceptados

- Sin modo sin conexión: si se cae la red, la captura se detiene. El borrador del vale se conserva en el dispositivo.
- La firma en pantalla es firma electrónica simple; su fuerza depende de la evidencia que la acompaña.
- Sin administración de usuarios en pantalla.
- Los parámetros generales son valores fijos de configuración.
