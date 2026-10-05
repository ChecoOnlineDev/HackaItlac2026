# ADR-005: Evidencia del vale: firma simple acompañada, no firma avanzada ni huella

## Estado

Aceptada (4 de octubre de 2026). No es asesoría legal; la empresa debe validarlo con su abogado.

## Contexto

El patrocinador explicó que el vale debe firmarse porque, sin firma, el trabajador puede decir que no sacó el equipo. También dijo que el trabajador desconfía del registro electrónico y quiere una copia en su poder. El equipo exploró la huella dactilar.

## Fuerzas y restricciones

- La captura debe ser rápida y no generar fricción con el trabajador.
- No todos los almacenes tienen impresora.
- Una página web no puede leer un lector de huella, y la huella es un dato personal sensible.
- El trabajador no trae su firma electrónica del SAT al mostrador.

## Alternativas consideradas

1. **Papel firmado**, como hoy. Tiene peso legal, pero es lento y se pierde.
2. **Huella dactilar.** Exige programa instalado, lector y resguardo de datos sensibles.
3. **Firma electrónica avanzada.** Es la más fuerte, pero impracticable para un operario en un mostrador.
4. **Firma en pantalla acompañada de evidencia**, con el papel como opción.

## Decisión

La alternativa 4, en capas:

1. Firma en pantalla en cada entrega, debajo de la lista de artículos y la leyenda de responsabilidad. Entra en el MVP.
2. El almacenista firma con su sesión; el supervisor, solo al autorizar.
3. Sello: huella criptográfica del vale encadenada con la del anterior. Llega con FEAT-001.
4. El trabajador se lleva copia: ticket impreso o comprobante abierto desde el QR. Llega con FEAT-001.
5. Firma en papel como segundo modo, con foto del ticket firmado. Llega con FEAT-001.

## Justificación

La ley laboral mexicana admite documentos digitales y firma electrónica como prueba, y valora que el documento esté íntegro y sea atribuible. Una firma en pantalla sola es débil; con lectura de credencial, sello y copia para el trabajador, gana fuerza sin frenar la captura.

## Consecuencias positivas

- El vale sale en segundos y con evidencia.
- El sello responde al temor de manipulación.
- La empresa puede seguir usando papel donde quiera.

## Consecuencias negativas

- Es firma electrónica simple: si el trabajador la niega, la empresa debe probarla.
- Mientras FEAT-001 no esté lista, no hay sello ni copia para el trabajador.

## Señales para reevaluar

- El abogado de la empresa pide un nivel de firma mayor.
- Se requiere constancia de conservación NOM-151 emitida por un prestador autorizado.
