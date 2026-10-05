# Historias de la Fase 1 — Acceso y catálogo

Gate de la fase: [roadmap](../product/roadmap.md). Reglas citadas: [reglas-de-negocio.md](../product/reglas-de-negocio.md).

---

## US-ACC-001: Entrar y ver solo lo que permite mi rol

Como usuario del sistema, quiero entrar con mi usuario y contraseña y ver solo lo que permite mi rol, para trabajar sin pasos de más y sin acceso a lo que no me toca.

**Criterios de aceptación**

- Dado un usuario activo, cuando escribe su usuario y contraseña correctos, entonces llega al inicio de su rol.
- Dadas credenciales incorrectas, entonces ve "Usuario o contraseña incorrectos", sin indicar cuál falló.
- Dados cinco intentos fallidos seguidos, entonces debe esperar cinco minutos.
- Tras cargar los datos de prueba existen los cinco roles iniciales, con los permisos de la sección 8.2 de las reglas, y un usuario de cada uno.
- La sesión devuelve los permisos del usuario, y el menú muestra solo las secciones que esos permisos abren.
- Dado un usuario cuyo rol no tiene el permiso de un endpoint, cuando lo pide, entonces recibe 403 aunque la interfaz no muestre el botón.
- El servidor decide por el permiso, no por el nombre del rol: un rol de prueba con un solo permiso puede usar ese endpoint y ningún otro.
- Dado un usuario con almacén asignado, entonces la pantalla lo muestra y solo opera ese almacén; quien tiene `almacenes.todos` elige el almacén.
- Sin el permiso de información, el dato no se envía: el costo y los datos personales no llegan a quien no debe verlos.
- Dado alguien sin sesión que abre una ruta, entonces llega a Entrar y después regresa a esa ruta.
- "Salir" cierra la sesión.

**Reglas:** AC-01 a AC-07, RG-07, RG-12, RG-13.

**Fuera de alcance:** pantalla para administrar roles, permisos y usuarios (FEAT-006); recuperar contraseña; segundo factor.

**Casos límite:** un usuario inactivo no entra; si la sesión vence a mitad de un vale, el borrador se conserva; un cambio en los permisos de un rol aplica en la siguiente petición, sin volver a entrar.

**Evidencia:** una prueba por permiso (con él, el endpoint responde; sin él, 403); prueba de que los roles iniciales coinciden con las reglas; entrada manual con los cinco usuarios de prueba.

---

## US-CAT-001: Definir categorías con su plantilla

Como responsable del catálogo (Compras o supervisor), quiero crear categorías con sus reglas, para que los artículos nuevos nazcan con el control correcto.

**Criterios de aceptación**

- Puede crear una categoría con nombre, tipo (EPP o Herramienta) y plantilla: control, retorno, inspección con su vigencia, autorización con su motivo, límite y aviso de cantidad inusual.
- El nombre de una categoría no se repite.
- Dado que crea un artículo en esa categoría, entonces el formulario aparece con la plantilla ya puesta.
- Editar la plantilla no cambia los artículos que ya existen.
- Tras cargar los datos de prueba existen las siete categorías iniciales.
- Cada cambio queda en el registro de cambios.

**Reglas:** CF-01, CF-02, CF-15.

**Fuera de alcance:** reaplicar la plantilla a todos los artículos (CF-04); inactivar categorías (CF-14).

**Casos límite:** una plantilla con inspección en una categoría por cantidad se rechaza, porque la inspección solo aplica a artículos por pieza.

**Evidencia:** prueba: crear categoría, crear artículo y comparar sus reglas con la plantilla.

---

## US-CAT-002: Administrar artículos y sus requisitos especiales

Como responsable del catálogo, quiero dar de alta artículos y decidir cuáles piden un trato especial, para que el sistema aplique las reglas de la empresa sin depender de un programador.

**Criterios de aceptación**

- Crea un artículo con código, nombre, marca, categoría, control, retorno, talla y unidad. Quien tiene el permiso de costos captura además el costo; de inicio, Compras.
- El código no puede repetir ningún código existente de artículo, pieza o credencial.
- Puede activar o quitar "inspección vigente", con su vigencia en días, y "autorización del supervisor", y escribir el motivo que verá el almacenista.
- Puede fijar o quitar el límite: cantidad y periodo en días. Periodo vacío significa "en posesión".
- Puede fijar o quitar el aviso de cantidad inusual: la cantidad a partir de la cual el renglón pide confirmación al entregar (E-27).
- Dado un artículo con movimientos, entonces control y retorno aparecen bloqueados con su explicación y la API rechaza el cambio.
- Dado un cambio de reglas, entonces la siguiente evaluación lo respeta y los vales anteriores no cambian.
- Sin el permiso de costos se edita todo menos el costo, que no se ve. De inicio es el caso del supervisor.
- Cada cambio queda en el registro de cambios con el valor anterior y el nuevo.

**Reglas:** CF-02, CF-05 a CF-09, CF-15, L-05, RG-10, RG-12.

**Fuera de alcance:** mover de categoría reaplicando reglas (CF-03); habilitaciones del trabajador; mínimos por almacén.

**Casos límite:** activar la inspección en un artículo con piezas en almacén las deja sin entregar hasta inspeccionarlas; las que están con trabajadores no se recogen.

**Evidencia:** prueba: cambiar el límite y volver a evaluar; prueba: intentar cambiar el control de un artículo con movimientos responde 409.

---

## US-CAT-003: Inactivar y reactivar artículos

Como responsable del catálogo, quiero inactivar un artículo que ya no se usa y poder reactivarlo, para que deje de entregarse sin perder su historial.

**Criterios de aceptación**

- Inactivar pide un motivo; sin motivo no procede.
- Dado un artículo inactivo, cuando se escanea en una entrega, entonces el renglón queda en rojo con el motivo.
- Dado un artículo inactivo, entonces una entrada lo rechaza.
- Dado un artículo inactivo con equipo en manos de trabajadores, entonces su devolución se recibe normal.
- Sus existencias siguen visibles en el inventario, marcadas como inactivas, y se pueden trasladar.
- En el catálogo aparece atenuado; el filtro por defecto muestra solo los activos.
- Reactivar lo regresa a operar con las reglas que tenía.
- Dado un artículo sin movimientos, se puede eliminar. Con movimientos, la API responde 409 y solo se puede inactivar.
- Inactivar, reactivar y eliminar quedan en el registro de cambios.

**Reglas:** CF-10 a CF-13, CF-15, E-19, I-09, X-09, SM-05.

**Fuera de alcance:** inactivar categorías; inactivar varios artículos a la vez.

**Casos límite:** inactivar un artículo que está en un vale a medio capturar: al confirmar, el servidor lo rechaza y marca el renglón.

**Evidencia:** prueba de las cuatro operaciones contra un artículo inactivo: entrega, entrada, devolución y traspaso. La entrega y la entrada se completan cuando existan sus fases; aquí se prueba la regla en el evaluador.

---

## US-ETQ-001: Imprimir etiquetas QR

Como Compras o RH, quiero imprimir hojas de QR para piezas, estantes y credenciales, para que todo lo que se opera pueda escanearse.

**Criterios de aceptación**

- Elige qué imprimir: piezas (un QR por pieza), estantes (un QR por artículo por cantidad) o credenciales (un QR por trabajador sin credencial legible).
- Cada etiqueta muestra el QR y, en texto legible, el nombre y el código.
- Basta el permiso `etiquetas.imprimir` (Supervisor, Compras y RH) para los tres tipos; una credencial lleva solo nombre y número de empleado, nunca CURP ni NSS.
- La hoja se imprime desde el navegador en papel carta, sin menús ni encabezados.
- El QR contiene exactamente el código registrado; lo leen la cámara del celular y la pistola.

**Reglas:** I-07, T-05, RG-10.

**Fuera de alcance:** impresoras de etiquetas; códigos de barras lineales; diseño de credencial.

**Casos límite:** sin elementos, muestra "No hay nada que imprimir".

**Evidencia:** hoja impresa leída con un celular.
