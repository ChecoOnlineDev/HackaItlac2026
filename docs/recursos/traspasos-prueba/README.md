# Excel de prueba para traspasos

Nueve archivos para probar **Traspasos > Enviar > Con una lista de Excel** entre los almacenes de la semilla. Usan los códigos y nombres reales de los datos de prueba, con las columnas `codigo | nombre | cantidad | codigo pieza | serie`.

> **Estado:** los resultados de abajo son lo que **se espera** según las reglas (X-02, X-03, X-04, TR-04 a TR-07) y las existencias de la semilla. **No se ejecutaron contra la aplicación**, porque la base estaba apagada al generarlos. Si algo sale distinto, anótalo: puede ser un error del archivo o un hallazgo del sistema.

## Antes de empezar
- Base **recién sembrada** (`uv run python -m app.datos_prueba`), sin traspasos adicionales. Si ya hiciste otros movimientos, las cantidades pueden no alcanzar.
- Cada archivo es **un traspaso**: el origen y el destino se eligen en la pantalla, no en el archivo.
- Quién envía y quién recibe (usuarios de la semilla): Kepler `supervisor`, Contratistas `sup_con`, Midrex `sup_mid`, HYL `sup_hyl`, Laminador `sup_lam`, Minas `sup_min`. El Administrador es `admin`.
- Después de enviar, el **destino** debe **recibir** el traspaso (Traspasos > Recibir) para que la mercancía quede en su almacén.

## Existencias de la semilla (resumen)
| Almacén | Qué tiene |
|---|---|
| Kepler | EPP completo (lentes 200, tapones 300, guante de carnaza 120, etc.), herramienta (flexómetro 30, marro 15, cincel 25, extensión 15, discos) y las **13 piezas** con serie |
| Contratistas | EPP parcial (lentes 50, tapones 80, guante de carnaza 40, respirador 10, cachucha 15, peto 10, polainas 10) y herramienta (flexómetro 8, marro 6, cincel 10, extensión 5, discos 30 y 60) |
| Midrex | **Vacío** |
| HYL | flexómetro 3, marro 2, cincel 3 |
| Laminador | flexómetro 2, extensión 2 |
| Minas | marro 2, cincel 3, extensión 2 |

## Los archivos

| # | Archivo | Origen → destino | Quién envía | Esperado |
|---|---|---|---|---|
| 01 | `01-kepler-a-contratistas-epp-y-piezas` | Kepler → Contratistas | `supervisor` | **Todo verde.** 9 artículos por cantidad y 9 piezas (arneses, bandola, gancho, retráctil, minipulidor y detectores). Se confirma; `sup_con` lo recibe |
| 02 | `02-contratistas-a-midrex-herramienta` | Contratistas → Midrex | `sup_con` | **Todo verde.** Herramienta y discos con lo que Contratistas ya tiene. `sup_mid` lo recibe |
| 03 | `03-contratistas-a-midrex-piezas-despues-del-01` | Contratistas → Midrex | `sup_con` | Verde **solo si ya se hizo y recibió el 01**. Si no, las piezas salen en rojo (X-02: la pieza no está en este almacén) |
| 04 | `04-kepler-a-contratistas-con-errores` | Kepler → Contratistas | `supervisor` | **Filas en rojo y no deja confirmar.** Ver abajo |
| 05 | `05-kepler-a-contratistas-con-avisos` | Kepler → Contratistas | `supervisor` | **Amarillos, sí se puede confirmar.** Ver abajo |
| 06 | `06-kepler-a-contratistas-grande-33-renglones` | Kepler → Contratistas | `supervisor` | Todo verde, para ver la **paginación**: 33 renglones = 3 páginas de 12. Úsalo en lugar del 01, no junto con él |
| 07 | `07-kepler-a-midrex-ruta-excepcional` | Kepler → Midrex | `admin` | Ruta que **no es padre-hijo**: solo el Administrador, con aviso amarillo y **observación obligatoria** (X-03). Con `supervisor` debe salir en rojo y responder 403 |
| 08 | `08-hyl-a-contratistas-retorno` | HYL → Contratistas | `sup_hyl` | Verde: el retorno va por la misma cadena (proyecto → Contratistas) |
| 09 | `09-hyl-a-laminador-ruta-lateral` | HYL → Laminador | `admin` | Ruta **entre proyectos**: no es habitual, solo el Administrador con observación |

### Detalle del 04 (errores)
Debe verse rojo y bloquear la confirmación (todo o nada, RG-09), salvo que se elija «Dejar fuera las filas con error».

| Renglón | Esperado |
|---|---|
| `LENTE-CL` 10 | Correcto |
| `FLEXOM` 500 | Rojo X-02: pides más de lo que hay (Kepler tiene 30) |
| `NOEXISTE-99` | Error: el código no existe en el catálogo |
| `MARRO-B` 2.5 | Error: la cantidad debe ser entera, nunca se redondea |
| `CINCEL` 0 | Error o ignorado: cantidad cero |
| `ALT-002` (dos veces) | Error: pieza repetida en el archivo |
| `ALT-999` | Error: la pieza no existe |
| Renglón sin código | Error o ignorado |

### Detalle del 05 (avisos)
| Renglón | Esperado |
|---|---|
| `LENTE-CL` 5 | Correcto |
| `FLEXOM` 3 y `FLEXOM` 2 | **Unido** en uno de 5 («Unido: filas 3 y 4») |
| `CACHUCHA` con nombre «Casco blanco» | Amarillo `NOMBRE_NO_COINCIDE` (TR-13): avisa, no bloquea |
| `ALT-003` | Amarillo X-04: pieza **no apta**, se traslada con aviso y conserva su estado |
| `ALT-005` | Amarillo: inspección **vencida** |
| Columna `observaciones` | Se ignora con aviso (no se usa) |

## Un recorrido sugerido
1. **01** (o **06**) como `supervisor`: Kepler → Contratistas. Recibe `sup_con`.
2. **04** y **05** como `supervisor`: ver el rojo y los avisos (**no confirmes el 04**).
3. **02** como `sup_con`: Contratistas → Midrex. Recibe `sup_mid`.
4. **03** como `sup_con` (ya con el 01 recibido): las piezas pasan a Midrex.
5. **08** como `sup_hyl`: retorno a Contratistas.
6. **07** y **09** como `admin`: rutas excepcionales; luego repetir **07** como `supervisor` para ver el bloqueo.

## Cómo se generaron
Con un script que usa los códigos de `backend/app/modulos/catalogo/datos_prueba.py`, `app/datos_prueba_piezas.py` y las existencias de `app/modulos/movimientos/datos_prueba.py`. Si cambia la semilla, hay que regenerarlos.
