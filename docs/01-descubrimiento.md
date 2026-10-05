# Descubrimiento

Paso 2 de la guía: qué quedó respondido, qué se asume y qué sigue abierto antes de comprometer el producto. Fecha: 4 de octubre de 2026.

## Fuentes

| Fuente | Qué aporta |
|---|---|
| [HackaItlacTrack3_2026.pdf](HackaItlacTrack3_2026.pdf) | El reto: ocho funciones indispensables, guion de la prueba, entregables y rúbrica. Manda sobre todo lo demás. |
| [transcripcion_track.md](info_track/transcripcion_track.md) | La plática del patrocinador: sus dolores y aclaraciones. Se cita por minuto. |
| [anotaciones-exposicion.md](info_track/anotaciones-exposicion.md), [anotaciones-video.md](info_track/anotaciones-video.md) | Notas del equipo. Donde difieren de la grabación, manda la grabación. |
| [context.md](context.md) | La idea original del equipo, anterior al reto. Queda como antecedente. |

## Respuestas por área

**Usuario**

- El PDF pide cuatro perfiles: almacenista, supervisor, Compras y Recursos Humanos (función 1). En el sistema son roles, y se agrega un quinto: Administrador.
- El trabajador no usa el sistema: recibe equipo, firma y se lleva una copia.
- El personal de almacén está poco familiarizado con la tecnología (min 11).
- El supervisor está en campo y casi no tiene tiempo para el sistema (min 42).

**Problema**

- Hoy el almacén se lleva en libreta; se pierde o la roban (min 39).
- Al terminar un mantenimiento solo se ve lo que quedó: no se sabe quién perdió qué (min 33).
- Los trabajadores acumulan pendientes entre contratos (min 9).
- Hay consumo excesivo sin explicación: más de mil pares de guantes en un mes (min 35).
- El equipo caro regresa cambiado por otro (min 37).
- La empresa no sabe cuánto vale su almacén (min 39).

**Flujo**

- Alta en RH, equipo básico en Kepler, herramienta y equipo de alturas en el almacén del área (min 2–8).
- La herramienta no se devuelve a diario; puede quedarse todo el proyecto (min 4 y 52).
- Al terminar, el trabajador devuelve todo, Kepler le da el vale de no adeudo y RH lo finiquita (min 4 y 8).
- El personal es rotativo: regresa en otro contrato y RH lo reingresa (min 18).

**Reglas**

- Límite por artículo: por periodo en consumibles, en posesión en retornables (min 10 y 36).
- Equipo de alturas: por pieza, con inspección; si no es apto no se entrega (PDF p.2).
- Contrato vencido: el sistema no entrega nada (min 18).
- Las reglas completas están en [reglas-de-negocio.md](product/reglas-de-negocio.md).

**Confianza**

- Sin firma, el trabajador puede decir que no sacó el equipo (min 22).
- El trabajador desconfía del registro electrónico y quiere una copia en su poder (min 23).
- Hay que verificar que se entrega a quien corresponde (min 16).
- Hay quien intenta sacar herramienta sin contrato vigente (min 17).
- Se preguntó qué datos del trabajador debe ver el almacenista, y la respuesta quedó incompleta (min 28).

**Operación**

- No se cobra el daño ni el desgaste; solo se anota (min 41).
- Hay equipo que se queda instalado en planta por instrucción (min 43).
- Hay equipo en mantenimiento o calibración que no está ni en almacén ni con un trabajador (min 46).
- Los almacenes de área son contenedores temporales (min 32 y 49) que operan las 24 horas, con almacenistas asignados al proyecto (min 33).

**Negocio**

- El ganador debe poder llevarlo a producción; después se agregan módulos (min 39–40).
- La rúbrica pesa 35 % operaciones, 20 % captura por escaneo, 15 % reglas y baja, 15 % facilidad de uso y 15 % seguridad, trazabilidad e implementación (PDF p.2).

**Técnica**

- Web, en la nube y sin instalar (min 26). Tableta o celular como equipo principal (min 10).
- Captura con cámara del celular o pistola lectora (PDF p.8).
- Sin tiempo real estricto, sin pagos, sin geolocalización. Hay datos personales y fotos.

## Contradicciones entre fuentes

| Tema | PDF | Plática | Cómo se resolvió |
|---|---|---|---|
| Supervisor | Autoriza el exceso de límite. | No tiene tiempo. | Autoriza solo eso, desde su celular o con PIN. Lo demás lo resuelve el almacenista con observación. |
| Baja | "Al iniciar la baja" sugiere que la inicia RH. | El trabajador va a Kepler por su vale de no adeudo. | La inician RH o el almacén; el vale lo emite el almacén. |
| Plazo | El vale lleva fecha prevista de devolución. | No hay límite de tiempo. | Sin plazo por préstamo; el plazo es el fin del contrato. |
| Costos | Muestra el costo del EPP por trabajador. | El costo no debe ir en el vale. | El costo existe, pero solo lo ve Compras. |
| Almacenes de área | Cuatro almacenes fijos. | Son temporales, por proyecto. | Son un catálogo; el cierre de almacén queda como feature. |
| Etiquetas | QR en cada artículo. | Un marro o un cincel no admiten etiqueta. | QR de estante para artículos por cantidad. |
| Firma | "Firmas de quien entrega y quien recibe". | Vale físico; aceptan firma con el dedo. | Dos modos: en pantalla o en ticket impreso. |
| Sincronización | No la menciona. | No la pide; pide celular porque el Internet falla en PC. | Primero en línea. |

## Supuestos de trabajo

No hay forma de preguntarle al patrocinador por ahora. Cada punto lleva el supuesto que tomamos y cómo queda cubierto si resulta distinto.

| Tema | Supuesto | Si resulta distinto |
|---|---|---|
| Credencial de la planta | Trae un código legible con cámara o pistola. | Se teclea el número o se imprime un QR propio. |
| Datos de ejemplo | Llegan en Excel, con columnas que no conocemos. | La importación deja elegir qué columna es cada dato; también hay captura manual. |
| Quién autoriza el exceso | Un supervisor que puede no estar en el almacén. | Autoriza desde su celular o con PIN en el mostrador. |
| Impresora | No la hay en todos los almacenes. | Firma en pantalla y copia por QR; el ticket impreso es opcional. |
| Equipo perdido | Impide el vale de no adeudo hasta que un supervisor lo dé por perdido. | Es una sola regla (V-13, P-05). |
| Qué es retornable | Casco y respirador regresan; botas, camisola, overol y guantes no. | Es una casilla por artículo. |
| Habilitación de alturas | La prueba revisa el estado de la pieza, no la capacitación del trabajador. | El requisito de habilitación queda como opcional. |
| Firma del supervisor | Valida solo excepciones, no cada vale. | Se puede exigir autorización por artículo (CF-06). |
| Vigencia de inspección | 180 días. | Es un campo por artículo. |
| Categorías iniciales | Las siete de la sección 5.1 de las reglas. | La empresa las cambia desde el catálogo. |

## Riesgos

| Riesgo | Efecto | Mitigación |
|---|---|---|
| Alcance excesivo | Muchos módulos a medias y ningún flujo confiable. | Exclusiones escritas en [mvp-scope.md](product/mvp-scope.md) y gates por fase. |
| La cámara no abre | Sin HTTPS el celular no deja usarla. | Túnel con HTTPS desde la Fase 0 y prueba de cámara en su gate. |
| Datos de la demo desconocidos | No poder cargar lo que entreguen. | Importación con mapeo de columnas y ensayo con un Excel ajeno. |
| Red del lugar | La demo se cae. | Punto de acceso del celular y video de respaldo. |
| Colusión almacenista y trabajador | Devoluciones registradas sin recibir el equipo. | Bitácora inalterable, sesión como firma y cierre de almacén. |
| Complejidad para el almacenista | No lo usan. | Una acción principal por pantalla y captura por escaneo. |

## Preguntas abiertas para el patrocinador

1. ¿La credencial de la planta trae código de barras o QR, o solo chip de proximidad?
2. ¿Pueden compartir ya la base de Excel?
3. ¿Quién autoriza el exceso de límite y dónde está en ese momento?
4. ¿Los almacenes tienen impresora, y el ticket en papel es obligatorio?
5. ¿Un equipo perdido impide el vale de no adeudo?

## Preguntas que se difieren

- Cómo se integra con la nómina y con el control de acceso de la planta.
- Qué formato exacto de constancia necesita la Comisión Mixta de Seguridad.
- Cómo se manejará el modo sin conexión.
- Si el límite debe poder sumarse por categoría y no solo por artículo.

## Gate de descubrimiento

- [x] Usuarios y roles identificados.
- [x] Problema y resultado deseado identificados.
- [x] Principales incógnitas listadas, con un supuesto para cada una.
- [ ] Preguntas abiertas respondidas por el patrocinador. No bloquea: hay plan B para cada una.
