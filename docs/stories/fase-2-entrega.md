# Historias de la Fase 2 — Entrega

Gate de la fase: [roadmap](../product/roadmap.md). Reglas citadas: [reglas-de-negocio.md](../product/reglas-de-negocio.md).

---

## US-TRB-001: Dar de alta a un trabajador

Como RH, quiero registrar a un trabajador con su periodo de contrato y ligar su credencial, para que cualquier almacén lo reconozca al escanearla.

**Criterios de aceptación**

- Captura nombre, número de empleado, puesto, área u obra, y periodo de inicio y fin. CURP, NSS y tallas son opcionales.
- El número de empleado no se repite; si ya existe, se ofrece la ficha de esa persona en lugar de crear otra.
- La fecha de fin no puede ser anterior a la de inicio.
- Puede ligar la credencial escaneándola, o generar un QR propio. Un código ya usado se rechaza indicando a quién pertenece.
- Al guardar, el trabajador queda Activo; es vigente si hoy cae dentro de su periodo.
- Dado un almacenista que escanea la credencial, entonces ve foto, nombre, número, puesto, área y vigencia, y no ve CURP ni NSS.
- Puede tomar la foto del trabajador con la cámara del dispositivo o subir una imagen. Es opcional: sin foto, la ficha dice "Sin foto registrada".
- Se rechazan archivos que no son imagen o que pesan más del tamaño permitido; el navegador reduce la imagen antes de subirla.
- RH puede reemplazar la foto; el cambio queda en el registro de cambios. La foto solo la ve quien tiene `trabajadores.ver`.

**Reglas:** T-01, T-03, T-05, T-06, T-07, T-09, RG-13.

**Fuera de alcance:** reingreso (US-TRB-002); exigir la foto; carta de aceptación; importar trabajadores.

**Casos límite:** un periodo que inicia en el futuro crea al trabajador, pero todavía no es vigente.

**Evidencia:** paso 1 del guion automatizado; alta desde computadora y escaneo desde celular.

---

## US-INV-001: Registrar una entrada de inventario

Como Compras, quiero registrar lo que entra a un almacén, para que haya existencias que entregar.

**Criterios de aceptación**

- Elige el almacén (Kepler por defecto) y agrega renglones escaneando o buscando el artículo.
- Artículo por cantidad: captura la cantidad.
- Artículo por pieza: captura un código por pieza y su número de serie. Un código repetido se rechaza.
- Dado un artículo que requiere inspección, puede capturar la inspección inicial; sin ella, la pieza entra pendiente y no se puede entregar.
- Un artículo inactivo se rechaza.
- Al confirmar se emite un vale de entrada con folio y suben las existencias de ese almacén.
- La pantalla de inventario muestra las existencias por almacén.
- El costo unitario lo captura y lo ve solo quien tiene el permiso de costos; de inicio, Compras.

**Reglas:** I-01 a I-04, I-09, RG-01, RG-06, RG-09, RG-12.

**Fuera de alcance:** importación (US-IMP-001); solicitud de compra; mínimos.

**Casos límite:** un renglón con error impide guardar todo el vale y se marca.

**Evidencia:** prueba: entrada de diez guantes y dos arneses; se verifican existencias y piezas creadas.

---

## US-ENT-001: Entregar por escaneo

Como almacenista, quiero entregar equipo escaneando la credencial del trabajador y los artículos, para registrar la entrega en segundos y sin escribir.

**Criterios de aceptación**

- Identifica al trabajador escaneando su credencial, tecleando su número o buscándolo por nombre.
- Ve su ficha breve: foto, nombre, puesto, vigencia y lo que ya tiene en resguardo. Si no tiene foto, dice "Sin foto registrada" y la entrega continúa.
- Dado un trabajador no vigente, entonces la entrega no continúa y se muestra el motivo.
- Cada código leído aparece como renglón con su nivel y sus motivos en menos de un segundo.
- Código desconocido: rojo. Pieza que no está en este almacén: rojo, con su ubicación. Cantidad mayor a la existencia: rojo.
- Volver a escanear una pieza no la duplica. Volver a escanear un artículo por cantidad suma 1; la cantidad también se ajusta con + y −, o se teclea al tocar el número.
- Escanear solo agrega el renglón a un borrador: no se escribe nada y las existencias no cambian hasta confirmar el vale.
- Cada renglón tiene "Quitar", y al agregarlo aparece "Deshacer" durante 5 segundos.
- Dado un artículo con aviso de cantidad inusual, cuando el renglón alcanza esa cantidad, entonces se pide confirmarla antes de continuar.
- La lectura funciona con cámara, con pistola lectora y con teclado, sin cambiar de pantalla.
- No se puede continuar mientras haya un renglón en rojo.
- Al confirmar, un retornable pasa del almacén al trabajador y un consumible pasa a Consumido con el trabajador anotado.
- Las existencias del almacén bajan y el resguardo del trabajador sube en la misma operación.

**Reglas:** E-01 a E-04, E-15 a E-18, E-20 a E-22, E-27, E-28, RG-07 a RG-09.

**Fuera de alcance:** límites y autorización (Fase 3); dotación; exigir la foto para entregar.

**Casos límite:** si otra persona entregó la misma pieza mientras se capturaba, al confirmar se responde con el cambio y el renglón se marca; un doble toque en "Confirmar" no crea dos vales; una pieza con la etiqueta ilegible se agrega buscándola por su número de serie.

**Evidencia:** paso 2 del guion automatizado; entrega manual cronometrada desde un celular.

---

## US-ENT-002: Impedir la entrega de equipo no apto

Como almacenista, quiero que el sistema me impida entregar equipo de alturas no apto o sin inspección vigente, para que nadie trabaje con equipo inseguro.

**Criterios de aceptación**

- Dada una pieza No apta, En mantenimiento, En calibración o en Baja, entonces el renglón queda en rojo con su estado.
- Dada una pieza de un artículo que requiere inspección y no tiene una vigente, entonces el renglón queda en rojo con la fecha de vencimiento o "sin inspección".
- Al leer la pieza, la pantalla muestra su estado y su inspección antes de agregarla.
- Un rojo de seguridad no ofrece "Pedir autorización", y la API tampoco lo acepta con una autorización.
- Dada una pieza apta con inspección vigente, entonces el renglón es verde.

**Reglas:** E-05, E-06, SM-04, A-06, P-02.

**Fuera de alcance:** aviso de inspección por vencer (E-11); habilitación del trabajador.

**Casos límite:** una inspección que vence hoy todavía es vigente.

**Evidencia:** paso 3 del guion, con tres piezas de los datos de prueba: apta, no apta y vencida.

---

## US-INS-001: Inspeccionar una pieza

Como almacenista, quiero registrar la inspección de una pieza y marcarla no apta si veo un daño, para que el sistema sepa qué equipo se puede entregar.

**Criterios de aceptación**

- Desde la ficha de la pieza registra una inspección: revisa etiquetas, costuras, cintas, herrajes y conectores, elige Apto o No apto y anota observaciones.
- Resultado Apto: la pieza queda Apta y vigente hasta hoy más la vigencia de su artículo.
- Resultado No apto: exige observación y la pieza queda No apta.
- Puede marcar una pieza como No apta sin hacer inspección, con observación.
- Una pieza No apta solo regresa a Apta con una inspección.
- La inspección y el cambio de estado aparecen en el historial de la pieza, con fecha y usuario.
- La siguiente lectura de esa pieza ya usa el estado nuevo.
- Un supervisor o un administrador puede ajustar la fecha de vigencia de la inspección de una pieza, con un motivo obligatorio. Quien no tiene el permiso no ve la acción, y la API responde 403.
- El ajuste no cambia el resultado de la inspección ni regresa a Apta a una pieza No apta. Aparece en el historial con la fecha anterior, la nueva, el motivo y el usuario.
- Acortar la vigencia se permite; alargarla más allá de la inspección más la vigencia del artículo se rechaza. Quien registró la inspección no puede ajustar la suya.
- La siguiente lectura de la pieza usa la fecha nueva.

**Reglas:** P-01 a P-03, P-07, CF-06.

**Fuera de alcance:** mantenimiento y calibración (FEAT-004); baja definitiva; aviso de vencimiento en campo.

**Casos límite:** una pieza que está con un trabajador también puede inspeccionarse o marcarse.

**Evidencia:** prueba: pieza vencida, inspección con resultado Apto y entrega en verde.

---

## US-ENT-003: Firmar y emitir el vale

Como almacenista, quiero que el trabajador firme en la pantalla y que la entrega quede en un vale con folio, para tener constancia de lo que recibió.

**Criterios de aceptación**

- Antes de confirmar se muestran el resumen de artículos, la leyenda de responsabilidad y un recuadro para firmar.
- Sin firma, "Confirmar entrega" está deshabilitado y la API rechaza la entrega.
- El vale emitido tiene folio consecutivo por almacén y tipo, fecha y hora del servidor, trabajador, área u obra, descripción con marca, código o serie, cantidad, condición y responsable.
- El vale no muestra costos.
- El vale muestra un QR; al escanearlo desde la aplicación se abre ese vale.
- La firma queda guardada y ligada al vale; el responsable es el usuario de la sesión.
- El vale se puede imprimir desde el navegador.
- El vale aparece en la ficha del trabajador.

**Reglas:** F-02 (en pantalla), F-03, F-05, F-12, E-22, E-24, RG-06, RG-11.

**Fuera de alcance:** sello, comprobante público, ticket en dos copias y firma en papel (FEAT-001).

**Casos límite:** una firma vacía se rechaza; se puede borrar y volver a firmar.

**Evidencia:** vale emitido en el guion; QR leído desde otro dispositivo.
