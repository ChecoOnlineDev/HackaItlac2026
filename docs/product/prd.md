# PRD — Control de herramientas y EPP (Reto IMHOTEP)

Fuente de verdad de producto. Describe qué se construye y por qué; el cómo está en el [TRD](../architecture/trd.md). Nombre comercial: pendiente.

## 1. Resumen

Aplicación web para que Mantenimiento Industrial IMHOTEP sepa, en todo momento, qué herramienta y equipo de protección personal (EPP) hay en cada almacén, quién tiene cada artículo y qué debe devolver cada trabajador al terminar su contrato. Las entregas, devoluciones y traspasos se capturan escaneando un QR o un código de barras con el celular o una pistola lectora, y cada operación deja un vale foliado y firmado.

## 2. Problema

- El almacén se lleva en libreta. Se pierde o la roban, y con ella el control (plática min 39).
- Al terminar un mantenimiento solo se ve lo que quedó: nadie sabe quién perdió qué (min 33).
- Los trabajadores se van sin devolver y regresan en otro contrato acumulando pendientes (min 9).
- Hay consumo sin explicación: más de mil pares de guantes en un mes (min 35).
- El equipo caro, como un detector de gases de 30 mil pesos, regresa cambiado por otro (min 37).
- La empresa no sabe cuánto vale lo que tiene en almacén (min 39).
- El vale necesita firma para servir como prueba, y hoy es papel (min 22).

## 3. Usuarios y roles

| Rol | Qué busca | Dónde lo usa |
|---|---|---|
| Almacenista | Entregar, devolver y trasladar en segundos; saber qué debe cada trabajador. | Celular o tableta en el mostrador; pistola lectora. |
| Supervisor | Autorizar excepciones sin ir al almacén; revisar lo irregular cuando tenga tiempo. | Celular, en campo. |
| Compras | Conocer existencias y faltantes, registrar entradas, mantener el catálogo y saber cuánto vale el inventario. | Computadora. |
| Recursos Humanos | Dar de alta y reingresar trabajadores; saber si alguien tiene pendientes antes de finiquitarlo. | Computadora o celular. |
| Administrador | Dar de alta usuarios y decidir qué puede hacer y ver cada rol. | Computadora. En el MVP solo carga los datos iniciales. |
| Trabajador | Recibir su equipo rápido y tener constancia de lo que recibió y devolvió. | No usa el sistema; firma y se lleva copia. |

## 4. Propuesta de valor

**El vale digital que sí sirve como prueba, capturado en segundos.**

1. **Captura por escaneo.** El almacenista escanea la credencial y los artículos; el sistema hace el resto.
2. **Trazabilidad total.** Una bitácora que no se edita registra cada movimiento: qué, cuánto, de dónde a dónde, quién y en qué estado.
3. **Evidencia para los dos lados.** El vale queda firmado y sellado, y el trabajador se lleva su copia.
4. **Reglas que ajusta la empresa.** Categorías, requisitos especiales y límites se cambian desde una pantalla, sin programador. En la segunda ola, también los roles y lo que puede ver cada uno.

## 5. Objetivos

| # | Objetivo | Cómo se comprueba |
|---|---|---|
| O1 | Saber quién tiene un artículo, o qué tiene un trabajador, en menos de 10 segundos. | Búsqueda o escaneo cronometrado. |
| O2 | Registrar una entrega de cinco artículos en menos de un minuto. | Cronómetro en la demostración. |
| O3 | Ninguna entrega sale sin vale foliado y firmado. | El sistema no cierra un vale sin firma. |
| O4 | Ningún equipo de alturas no apto sale del almacén. | Prueba automática del bloqueo. |
| O5 | Ningún trabajador se finiquita con pendientes sin que RH lo vea. | Consulta de RH y vale de no adeudo. |
| O6 | Al cerrar un mantenimiento, cada faltante tiene nombre. | Reporte de cierre. |
| O7 | La empresa cambia categorías, requisitos y límites sin tocar código. | Se cambia en pantalla y la siguiente entrega lo respeta. |

## 6. No objetivos

- Sustituir un ERP, la nómina o la contabilidad.
- Calcular finiquitos o descuentos por pérdida. La empresa no cobra el daño.
- Controlar el acceso a la planta ni integrarse a sus torniquetes.
- Administrar el mantenimiento o la calibración; solo se registra el estado de la pieza.
- Gestionar compras completas: proveedores, órdenes y facturas.
- Identificar al trabajador con biometría.

## 7. Capacidades del producto

La columna "Etapa" indica cuándo entra: **MVP**, **Ola 2** (features posteriores al núcleo) o **Futuro**.

| Dominio | Capacidad | Etapa |
|---|---|---|
| Acceso | Usuario y contraseña; cinco roles iniciales con permisos por clave | MVP |
| Acceso | Roles y permisos que define un administrador; usuarios en pantalla | Ola 2 |
| Catálogo | Categorías con plantilla de reglas; artículos; piezas con código único | MVP |
| Catálogo | Requisitos especiales por artículo; inactivar y reactivar | MVP |
| Catálogo | Etiquetas QR para credenciales, piezas y estantes | MVP |
| Trabajadores | Alta, reingreso, vigencia por periodo de contrato | MVP |
| Trabajadores | Foto para verificar identidad | Ola 2 |
| Inventario | Entradas, existencias por almacén, importación desde Excel | MVP |
| Inventario | Mínimos por almacén y alertas; estados de mantenimiento y calibración | Ola 2 |
| Entrega | Captura por escaneo con semáforo, firma en pantalla y vale foliado | MVP |
| Entrega | Límite por artículo y autorización del supervisor | MVP |
| Entrega | Dotación por puesto y avisos no bloqueantes | Ola 2 |
| Devolución | Por escaneo, con condición al volver; rechazo de equipo ajeno | MVP |
| Traspaso | Salida, tránsito y recepción entre almacenes | MVP |
| Seguridad | Inspección de piezas y bloqueo de equipo no apto | MVP |
| Baja | Pendientes del trabajador y vale de no adeudo | MVP |
| Consulta | Escaneo universal, búsqueda por texto, historial de pieza | MVP |
| Reportes | Existencias, movimientos y adeudos | MVP |
| Evidencia | Sello contra alteración, comprobante público por QR, ticket imprimible, firma en papel | Ola 2 |
| Cierre | Cierre de almacén de proyecto y valor del inventario | Ola 2 |
| Corrección | Cancelación de un vale con movimientos inversos | MVP |
| Revisión | Lista de revisión, cierre sin devolución, pérdidas | Futuro |
| Reportes | Consumo por periodo y EPP entregado por trabajador | Futuro |
| Compras | Solicitud de compra urgente del supervisor o el almacenista | MVP |
| Tablero | Vista general por almacén para el administrador | Futuro |
| Operación | Modo sin conexión con sincronización | Futuro |

## 8. Reglas de negocio

Las reglas completas, con su origen y prioridad, están en [reglas-de-negocio.md](reglas-de-negocio.md). Los principios que no cambian con la interfaz:

- Todo es un movimiento de una ubicación a otra, y el trabajador es una ubicación.
- La bitácora no se edita ni se borra; un error se corrige con un movimiento inverso.
- El sistema bloquea solo lo que exige el PDF o lo que es de seguridad; lo demás se resuelve con observación.
- Un rojo de seguridad no lo autoriza nadie en el mostrador.
- Una devolución nunca se bloquea.
- Lo que cada rol puede hacer y ver se decide por permisos. De inicio, el costo solo lo ve Compras y los datos personales solo RH.

## 9. Flujos principales

Están detallados en [app-flow.md](app-flow.md): alta de trabajador, entrada de inventario, entrega, autorización, devolución, traspaso, baja con vale de no adeudo, consulta y administración del catálogo. En [escenarios.md](escenarios.md) esos flujos se prueban contra situaciones reales de la planta.

## 10. Métricas de éxito

Para el hackathon, la rúbrica del PDF:

| Criterio | Peso |
|---|---|
| Funcionamiento de entregas, devoluciones, traspasos y existencias | 35 % |
| Captura rápida con QR o código de barras | 20 % |
| Reglas de entrega, autorizaciones y baja de trabajadores | 15 % |
| Facilidad de uso en celular y computadora | 15 % |
| Seguridad, trazabilidad y posibilidad de implementación | 15 % |

Para el producto en operación: tiempo por entrega, porcentaje de vales firmados, faltantes sin explicar al cierre y pendientes de trabajadores inactivos.

## 11. Riesgos y supuestos

Los supuestos y riesgos completos están en [01-descubrimiento.md](../01-descubrimiento.md). Los que más pesan:

- El alcance crece y ningún flujo queda confiable.
- La credencial de la planta podría no ser legible con cámara.
- El formato de los datos de la demostración es desconocido.
- El supervisor podría no estar disponible para autorizar.

## 12. Preguntas abiertas

Las cinco preguntas para el patrocinador están en [01-descubrimiento.md](../01-descubrimiento.md). Ninguna bloquea: cada una tiene un plan B.

## 13. Fuera de alcance de la visión actual

- Aplicación nativa para celular.
- Varias empresas en una misma instalación.
- Firma electrónica avanzada o constancias NOM-151 emitidas por el sistema.
- Analítica predictiva de consumo.
- Integración con nómina, compras o sistemas de la planta.
