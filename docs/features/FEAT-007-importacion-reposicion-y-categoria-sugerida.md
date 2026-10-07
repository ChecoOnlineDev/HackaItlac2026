# FEAT-007: Importación con reposición y categoría sugerida

> **Relación.** [FEAT-009](FEAT-009-traspasos-por-lista-de-excel.md) (propuesta) reutiliza la lectura del `.xlsx` y la vista previa en tabla de esta importación para armar la salida de un traspaso. El traspaso **no** es un tercer modo de `/api/importacion` (que sigue con `ALTA` y `REPOSICION` y el permiso `inventario.entradas`): tiene endpoints propios con `traspasos.operar`, y quien escribe el vale es `movimientos`.

## Problema u oportunidad

La importación de inventario (US-IMP-001) sirve para la carga inicial, pero una lista real de la planta trae cientos de renglones sin categoría ni código, con la misma herramienta repetida en varias filas, con servicios mezclados y con cantidades como `0.25`. Y cuando llega material de artículos que ya existen, importar la misma tabla en modo «alta» podría crear duplicados por un error de captura. Hace falta separar la carga inicial de la reposición, ayudar a clasificar sin decidir por la persona y cerrar los huecos de seguridad de una tabla ajena.

## Objetivo

Que Compras cargue o reponga inventario desde Excel viendo, antes de guardar, qué fila crea un artículo, cuál suma a uno existente, cuál se unió con otras y cuál tiene error, sin que el sistema aplique nada que la persona no haya visto.

## Historia de usuario

Ver [US-IMP-001](../stories/fase-6-consulta-reportes-e-importacion.md) (alta y carga inicial, con categoría sugerida y consolidación) y US-IMP-002 (reposición), en el mismo archivo.

## Alcance incluido

- Dos modos, `ALTA` (por omisión) y `REPOSICION` (I-10), con plantilla descargable por modo.
- Permisos: los dos exigen `inventario.entradas`; el alta que crea artículos exige además `catalogo.administrar` (cambio de política).
- Reglas I-10 a I-14: modos, tope de cantidad por fila, aviso de archivo ya importado, cantidades solo enteras y categoría sugerida.
- Consolidación de filas del mismo artículo por cantidad y almacén (I-06).
- Código del artículo generado cuando el archivo no lo trae: `PREFIJO-NNNN`.
- Vista previa en tabla con estados, saldo antes y después, resumen y categoría sugerida editable por fila.
- Seguridad: neutralizar celdas peligrosas en la descarga de errores; avisar de diferencias de nombre, marca o categoría sin actualizar nada; prueba de concurrencia entre lotes.
- Un anexo con el diccionario de inferencia de categoría (abajo).

## Fuera de alcance

- Actualizar nombre, marca, categoría o costo de un artículo que ya existe.
- Guardar relaciones de columnas o diccionarios propios por empresa (el diccionario es del sistema; cambiarlo es un cambio de este documento y del código).
- Aprendizaje automático o servicios externos para clasificar: es un reglamento de palabras.
- Importar trabajadores; fijar existencias a un valor.
- Códigos generados para categorías sin prefijo (las creadas por la empresa): ahí el código se pide.

## Criterios de aceptación

Los de US-IMP-001 y US-IMP-002. En resumen:

- Una fila de reposición con un código que no existe es error y no crea nada.
- Una cantidad `0.25` o `0,25` se rechaza y nunca se redondea; `1,250` vale 1250; más de 100 000 se rechaza.
- Las filas 2, 5 y 9 del mismo artículo y almacén salen como «Unido: filas 2, 5, 9»; un código de pieza repetido sigue siendo error.
- La categoría sugerida se muestra con su motivo, se puede cambiar por fila, y lo que no coincide queda «por revisar» y no entra.
- Un archivo ya importado avisa y pide `confirmar_repetido`.
- Una celda que empieza con `=`, `+`, `-`, `@`, tabulador o retorno de carro sale con apóstrofo en la descarga de errores.
- Dos lotes simultáneos con los mismos artículos no duplican artículos ni piezas.

## Módulos relacionados conocidos

`importacion` (vista previa, confirmación, plantilla, huella y diccionario), `catalogo` (crear artículos, consecutivo de códigos), `movimientos` (los vales de entrada; es el único que escribe), `auditoria` (`importacion.confirmar` con `despues.huella`).

## Cambios de datos o API esperados

- API: campo `modo`, `categoria_por_fila` y `confirmar_repetido` en el cuerpo; `estado`, `saldo_antes`, `saldo_despues`, `unida_de`, `categoria_sugerida` y `motivo_sugerencia` en la salida; `GET /api/importacion/plantilla?modo=`; error 409 `ARCHIVO_REPETIDO`. Detalle en [api-contracts.md](../architecture/api-contracts.md#importación).
- Datos: ninguna tabla nueva ni migración. La huella se guarda en `despues.huella` de la auditoría. El consecutivo por categoría se calcula dentro de la transacción de la confirmación con la categoría bloqueada. El tope de cantidad es un ajuste general de configuración.

## Restricciones y compatibilidad

- Sin `modo`, el cuerpo se interpreta como `ALTA`: los clientes anteriores siguen funcionando.
- La sugerencia nunca se aplica sola. Solo cuenta lo que la interfaz manda en `categoria_por_fila`.
- El costo solo se captura en el alta de artículos nuevos con `catalogo.costos`; la reposición nunca lo cambia (I-04, RG-12).
- Los textos que ve la persona van en español llano.

## Riesgos

- El diccionario es una **sugerencia**, no un criterio: la clave UNSPSC sola no sirve (por ejemplo, `31162800` es un cajón de sastre) y el resultado depende de cómo escribe cada empresa la descripción. Por eso la persona siempre lo ve y lo puede cambiar.
- Reguladores, sopletes y manómetros en «Equipo de alto valor» y la soldadura en «Consumibles de trabajo» son **supuestos** que la empresa puede cambiar; también hay unos diez casos discutibles (pinza de tierra, candados, mezcladora, vanderola, cerradura).
- Una carrera entre dos lotes puede duplicar un artículo si el bloqueo se omite: por eso es criterio de aceptación.
- Un archivo ajeno puede traer fórmulas: la lectura no las ejecuta y la descarga las neutraliza.

## Validaciones requeridas

- Una prueba por regla I-10 a I-14, con su ID en el nombre.
- Prueba de concurrencia entre dos lotes (artículos nuevos y piezas).
- Prueba de la neutralización de las cinco clases de celdas.
- Prueba del diccionario: cada regla con un ejemplo, y el orden («la primera que coincide gana»).
- Ensayo con un Excel que el equipo no preparó.

## Documentos globales que podrían actualizarse

[reglas-de-negocio.md](../product/reglas-de-negocio.md) (I-06, I-10 a I-14, secciones 5.4 y 8.2), [api-contracts.md](../architecture/api-contracts.md), [app-flow.md](../product/app-flow.md) (flujo 5), [ui-ux.md](../product/ui-ux.md), [guia-por-rol.md](../guia-por-rol.md), el [changelog](../releases/changelog.md) cuando se construya, y `AGENTS.md` si cambia la lista de rutas que verifican permisos en el servicio.

---

## Anexo: diccionario de inferencia de categoría (I-14)

Solo aplica en el modo `ALTA`, a artículos nuevos cuyo archivo no trae categoría. El servidor **sugiere**; nunca aplica.

### Cómo se evalúa

1. Se toma la descripción del artículo, se pasa a mayúsculas y se le quitan los acentos.
2. Se recorren las reglas **en orden**; **la primera que coincide gana**.
3. Los nombres de categoría son los de la sección 5.1 de las reglas de negocio: EPP básico, EPP de dotación, Equipo de alturas, Herramienta manual, Herramienta eléctrica, Equipo de alto valor y Consumibles de trabajo. En las tablas de abajo, «Consumibles» es «Consumibles de trabajo».
4. El motivo que se muestra es la palabra que coincidió («La descripción dice «arnés»»). Si ninguna regla coincide, la fila queda «por revisar».
5. Si el archivo trae categoría, esa manda y no se evalúa nada.

### Reglas, en orden

Las expresiones son regulares sobre la descripción ya normalizada. `\b` es límite de palabra.

1. `\bSERVICIO\b` → **EXCLUIR** (no es un artículo; se excluye con aviso). Respaldo: la clave UNSPSC empieza con `78`.
2. `CUERDA DE RAPEL|LINEA DE VIDA|\bARNES\b|BANDOLA|RETRACTIL|GANCHO DOBLE` → **Equipo de alturas**.
3. `GAS LENS|ANTORCHA TIG|\bTIG\b|BOQUILLA|SOLDADURA|MORDAZA|\bCERAMICA\b` → **Consumibles de trabajo**.
4. `PORTA ?ELECTRODO|PINZA DE TIERRA` → **Herramienta eléctrica**.
5. `REGULADOR|SOPLETE|MANOMETRO|DETECTOR DE GASES|\bRADIO\b` → **Equipo de alto valor**.
6. `RESPIRADOR|BARBOQUEJO|\bCASCO\b|\bPETO\b|POLAINAS` → **EPP básico**.
7. `CRISTAL .*CARETA|\bFILTRO\b.*(VAP|PARTIC|GAS ACIDOS|OZONO|CART)|\bFILTRO/CART|\bLENTE\b|ANTEOJO|CACHUCHA|\bGUANTE|TAPON AUDITIVO|OVEROL|CAMISOLA|\bBOTA|CALZADO|\bFAJA\b|CHALECO` → **EPP de dotación**.
8. `HOJA DE LIJA|\bLIJA\b|\bDISCO\b|RUEDA FLAP|SEGUETA|\bBROCA\b|JUEGO DE BROCAS|REPUESTO` → **Consumibles de trabajo**.
9. `TALADRO|TALABRO|ROTOMARTILLO|PULIDOR|ESMERIL|SIERRA|LLAVE DE IMPACTO|BOMBA .*NEUMATICA|BOMBA ENGRAS|LINTERNA|\bLAMPARA(?! *BTICINO)|REFLECTOR` → **Herramienta eléctrica**.
10. `ARANA|\bLLANA\b|CHAROLA|CEPILLO DE ALAMBRE|MULTICONTACTO|EXTENSION DE \d` → **Herramienta manual**.
11. `PORTA LAMPARA|CHALUPA|ARRANCADOR|\bFOCO\b|\bPILA\b|CINTA|FIBRA VERDE|PUNTA DE (3|CRUZ)|JUEGO DE (\d+ )?PUNTAS|\bPUNTAS\b|\bCARBON\b|\bCARDA\b` → **Consumibles de trabajo**.
12. Consumibles varios: `PINTURA|SILICON|SELLADOR|PEGAMENTO|ESPUMA|ACEITE|LUBRICANTE|AFLOJATODO|ACIDO|LIQUIDO PARA|PLASTI|KOLA LOKA|NO MAS CLAVOS|\bYESO\b|CLORO|MARCADOR|ALAMBRE|\bLONA\b|BOLSA|TRAPO|\bPIJA\b|TORNILLO|TUERCA|CLAVO|TAQUETE|ESPARRAGO|CINCHO|ABRAZADERA|ARMELLA|CANDADO|CERRADURA|CHAPA|PASADOR|MENSULA|NIPLE|COPLE|MANGUERA|MEZCLADORA|PLAGAFIN|RAFIA|BROCHA|RODILLO|SILIC|PENS|TEFLON` → **Consumibles de trabajo**.
13. `ESCALERA|CARRETILLA|\bLLANTA\b|BOMBA PRETUL|INFLADOR|ATOMIZADOR|VANDEROLA` → **Herramienta manual**.
14. `\bLLAVE\b|\bDADO\b|NUDO|MATRACA|MARTILLO|\bPINZA|CUTTER|NIVEL|FLEXOMETRO|DESARMADOR|BARRETA|\bPALA\b|AZADON|TALACHO|ZAPAPICO|\bHACHA\b|CAVADOR|CAVAHOYOS|\bLIMA\b|ESCUADRA|\bESCOBA|RECOGEDOR|TRAPIADOR|DOBLADOR|MANERAL|ADAPTADOR|\bMARRO\b|CABO PARA|MARTELINA|CUCHARA|RASPADOR|TIJERA|NAVAJA|CEPILLO|ENGRAPADORA|PISTOLA|\bPUNTA\b` → **Herramienta manual**.
15. Respaldo por prefijo de la clave UNSPSC, solo si el archivo la trae y ninguna regla anterior coincidió:
    - `46` → EPP de dotación.
    - `2711`, `2713`, `2410` → Herramienta manual.
    - `23101` → Herramienta eléctrica.
    - `2327`, `3119`, `3120`, `3126`, `3116`, `3912`, `4014`, `1110` → Consumibles de trabajo.
    - Si nada coincide → **por revisar**.

### Qué hay que tener presente

- **La clave UNSPSC sola no sirve.** Por ejemplo, `31162800` es un cajón de sastre: tornillos, herrajes y cosas muy distintas. Por eso es solo el último respaldo.
- **El reglamento es una sugerencia**, no una clasificación oficial. La persona la ve y la cambia en la vista previa.
- **Son supuestos de la empresa**, que puede cambiarlos: reguladores, sopletes y manómetros en Equipo de alto valor; la soldadura en Consumibles de trabajo.
- **Casos discutibles (unos diez):** pinza de tierra, candados, mezcladora, vanderola, cerradura, entre otros. Con la primera regla que coincide, quedan donde dice el orden de arriba; si no convienen, se cambia la categoría de esa fila.
- **El orden importa.** Por ejemplo, «pinza de tierra» cae en la regla 4 (Herramienta eléctrica) antes de que la regla 14 (`\bPINZA`) la mande a Herramienta manual.

### Limpieza del nombre

Antes de comparar y de mostrar, el servidor limpia el nombre de lo que no es parte de él:

- Quita los prefijos `/T/` y `/SP/`.
- Quita las claves internas entre paréntesis como `(RF005)`.
- Quita el sufijo « .» (un espacio y un punto al final).
- Reduce los espacios múltiples a uno.

La limpieza no cambia lo que dice el archivo original; solo el nombre del artículo nuevo y la comparación para unir filas (I-06).

### Marcas conocidas

Lista para reconocer la marca dentro del nombre (comparada sin acentos ni mayúsculas): TRUPER, URREA, PRETUL, BOSCH, DEWALT, VOLTECK, FIERO, SURTEK, INFRA, AUSTROMEX, HECORT, TENAZIT, FANDELI, NICHOLSON, STANLEY, IRWIN, FOSET, DOGO TOOLS, VICTOR, HARRIS, 3M, LAKELAND, LINMEX, INGERSOLL, PHILLIPS, HERMEX, FORTE, PENNSYLVANIA, SIKA, LENOX, SCOTCH, TUK, KLINTEK, BARDAHL, LUBCO, DEACERO, FISCHER, TULMEX, CUERVO, ELPRO, RIPOLL, TANGIT, DEVCON, BTICINO, CORTEC, VIZZION y FASTRAC.

Para qué sirve: cuando el archivo no trae marca, una de estas palabras en el nombre sirve para proponerla. Está por decidirse si la propuesta se expone como campo de la vista previa o solo se usa para comparar con el artículo existente; hasta entonces no se aplica ninguna marca que la persona no haya visto.
