# Checklist de release del MVP

Gate de la Fase 8 del [roadmap](../product/roadmap.md). El MVP se cierra cuando todo está marcado, no cuando se acaban las tareas.

Estado al 5 de octubre de 2026 (actualizado tras la prueba de calidad y el despliegue publicado). Se marcó solo lo que está hecho y comprobado en el repositorio, con una nota de dónde. Lo que depende de una persona, un celular, el servidor o un objeto físico queda sin marcar hasta que se haga. Lo construido está en el [changelog](changelog.md).

## Producto

- [ ] El flujo principal de [mvp-scope.md](../product/mvp-scope.md) se completa en el entorno publicado, desde un celular y desde una computadora. *(Recorrido completo en una copia aislada con el navegador (prueba de calidad del 5 oct): RH, entrega con vale, autorización, traspaso con recepción parcial, baja y no adeudo. Falta repetirlo en el sitio publicado desde un celular real, con cámara.)*
- [ ] Lo completa una persona que no escribió el código, con datos que ella misma elige.
- [x] Las exclusiones del alcance se respetaron; lo que quedó a medias está registrado como deuda. *(Revisado el 5 oct: se agregaron la aplicación instalable (sin modo sin conexión), la pantalla de Personal y la credencial con QR; lo demás excluido sigue fuera. Lo pendiente conocido está en «Conocido y pendiente» del changelog)*

## Calidad

- [x] La prueba del guion completo pasa. *(`backend/tests/test_guion_pdf.py` recorre los seis pasos; pasa en la suite completa (1376 pruebas el 5 oct))*
- [x] Cada permiso se verifica con una prueba, en el servidor, y los roles iniciales coinciden con la sección 8.2 de las reglas. *(`backend/tests/test_permisos_sistematicos.py` prueba cada permiso con y sin él, y compara los roles iniciales con la 8.2)*
- [ ] Cada pantalla tiene sus estados de carga, vacío y error. *(Revisado en la prueba de calidad del 5 oct en teléfono y por barrido en tableta y escritorio; falta confirmar en un teléfono real)*
- [x] Pruebas, lint, verificación de tipos y construcción pasan. *(5 oct, rama `backend/mvp`: `pytest` 1376 pruebas en verde, `ruff check` y `ruff format` limpios, `pnpm typecheck` y `pnpm build` sin errores.)*
- [x] El motor de movimientos tuvo revisión independiente. *(Revisión independiente de seguridad del backend (concurrencia, idempotencia, firma, permisos) con hallazgos corregidos y pruebas de regresión en `tests/seguridad`; segunda pasada sobre lo nuevo el 5 oct)*

## Operación

- [x] Las migraciones corren desde una base vacía. *(Cada corrida de pruebas recrea la base y aplica `alembic upgrade head`: `backend/tests/conftest.py`.)*
- [x] El script de datos de prueba es repetible. *(`python -m app.datos_prueba`, idempotente; corre al arrancar el contenedor con `CARGAR_DATOS_PRUEBA=true`.)*
- [x] `.env.example` documenta cada variable; ningún secreto está en el repositorio. *(Incluye `RESPALDOS_DIR`, `RESPALDOS_CONSERVAR` y `APP_CONTENEDOR`; ningún secreto está en el repositorio, y las credenciales de prueba van en un archivo local ignorado)*
- [ ] El despliegue funciona con `docker compose up -d --build` en el servidor. *(Funciona en la computadora de desarrollo con `docker compose --profile tunel up -d --build`; falta el servidor definitivo)*
- [x] Los registros de la aplicación se pueden consultar. *(`docker compose logs -f app`; ver README raíz.)*
- [x] El respaldo y su restauración se probaron. *(Base y archivos respaldados y restaurados en otra base, con `respaldo.sh` y `.ps1` y `restaurar.sh` y `.ps1`; ver «Cómo se probó» en [despliegue-local-cloudflare.md](../architecture/despliegue-local-cloudflare.md#cómo-se-probó). Repetir en el servidor antes de la demostración.)*
- [x] La comparación entre bitácora y existencias no reporta diferencias. *(`python -m app.mantenimiento verificar` sale con 0 sobre los datos de prueba y sobre la base restaurada; `backend/tests/test_mantenimiento.py`. Correrlo también sobre la base real del servidor.)*

## Entregables que pide el PDF

- [x] Prototipo funcional accesible desde celular y computadora: dirección publicada. *(Publicado en https://imhotep.checodev.top por el túnel de Cloudflare, con HTTPS y aplicación instalable; falta probarlo desde un celular real)*
- [x] Usuarios de prueba para cada rol, listados en el README raíz. *(Sección «Usuarios de prueba»: los diez, con almacén, contraseña y PIN de prueba.)*
- [x] Código fuente e instrucciones para instalar o desplegar, en el README raíz.
- [x] Descripción breve de la estructura de datos: [data-model.md](../architecture/data-model.md).
- [x] Respaldos y controles de acceso: [security-model.md](../architecture/security-model.md).
- [x] Guía corta para el almacenista (entregar, devolver, trasladar y consultar): [guia-almacenista.md](../guia-almacenista.md). *(Escrita con las pantallas construidas; falta que la lea un almacenista.)*

## Demostración

- [ ] Etiquetas QR impresas y pegadas en objetos reales: casco, guantes, arnés o su equivalente.
- [ ] Credenciales de prueba impresas.
- [ ] Dos celulares: almacenista y supervisor. Una computadora para Compras y RH.
- [ ] Pistola lectora, si se consigue.
- [ ] Importación ensayada con un Excel que el equipo no preparó.
- [ ] Ensayo cronometrado del flujo principal desde una base vacía.
- [ ] Punto de acceso propio por si falla la red del lugar.
- [ ] Video de respaldo de la demostración completa.

## Pitch

- [ ] Guion de siete minutos: problema, prueba en vivo, diferenciadores, implementación.
- [ ] Al menos tres ensayos con cronómetro.
- [ ] Respuestas de una frase para las preguntas previsibles: sin Internet, herramienta sin etiqueta, validez de la firma, identidad del trabajador, supervisor ausente.

## Cierre

- [ ] Versión etiquetada en el repositorio. *(La crea el equipo: `0.1.0`.)*
- [x] `docs/releases/changelog.md` con lo que incluye la versión. *([changelog.md](changelog.md).)*
- [ ] Roadmap actualizado con lo aprendido.
