# ADR-004: Primero en línea; sin sincronización en el MVP

## Estado

Aceptada (3 de octubre de 2026). **Reemplazada en parte** el 8 de octubre de 2026 por [ADR-015](ADR-015-operacion-sin-conexion-del-almacenista.md): la web sigue primero en línea; la app de Android del almacenista opera sin conexión lo que define FEAT-020. Se cumplió la señal para reevaluar «en operación real los cortes son largos y frecuentes».

## Contexto

En la planta el Internet falla. Las notas del equipo decían que se requería sincronización, pero en la grabación el patrocinador pide tableta o celular porque el Internet falla para tener una computadora de escritorio; no pide trabajar sin conexión.

## Fuerzas y restricciones

- El PDF no menciona el modo sin conexión y la rúbrica no lo califica.
- Los conflictos de sincronización consumen muchas horas: la misma pieza entregada desde dos dispositivos, límites evaluados con datos viejos, folios consecutivos.
- El tiempo es de tres días más 24 horas.

## Alternativas consideradas

1. **Sin conexión desde el inicio**, con cola local y resolución de conflictos.
2. **Solo en línea**, sin ninguna tolerancia a cortes.
3. **En línea, tolerante a cortes breves.**

## Decisión

La alternativa 3. Toda operación se valida y se guarda en el servidor. El borrador del vale se conserva en el dispositivo y cada confirmación lleva un identificador único, de modo que reintentar no duplica.

## Justificación

Cubre lo que se califica y evita la parte más cara. La bitácora de solo inserción y el identificador por vale dejan preparado el camino si después se agrega sincronización.

## Consecuencias positivas

- Las reglas se evalúan siempre con datos actuales.
- Los folios son consecutivos sin trucos.
- Un corte de segundos no pierde lo capturado.

## Consecuencias negativas

- Sin red, la captura se detiene.
- La demostración depende de la conexión del lugar; hay que llevar un punto de acceso y un video de respaldo.

## Señales para reevaluar

- En operación real los cortes son largos y frecuentes.
- La empresa confirma que los contenedores de área no tienen cobertura.
