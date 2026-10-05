# Checklist de release del MVP

Gate de la Fase 8 del [roadmap](../product/roadmap.md). El MVP se cierra cuando todo está marcado, no cuando se acaban las tareas.

Estado al 5 de octubre de 2026. Se marcó solo lo que está hecho y comprobado en el repositorio, con una nota de dónde. Lo que depende de una persona, un celular, el servidor o un objeto físico queda sin marcar hasta que se haga. Lo construido está en el [changelog](changelog.md).

## Producto

- [ ] El flujo principal de [mvp-scope.md](../product/mvp-scope.md) se completa en el entorno publicado, desde un celular y desde una computadora.
- [ ] Lo completa una persona que no escribió el código, con datos que ella misma elige.
- [ ] Las exclusiones del alcance se respetaron; lo que quedó a medias está registrado como deuda. *(Lo pendiente conocido está en «Conocido y pendiente» del changelog; falta la revisión final contra mvp-scope.)*

## Calidad

- [ ] La prueba del guion completo pasa. *(No existe todavía una sola prueba que recorra los seis pasos: TASK-F7-01.)*
- [ ] Cada permiso se verifica con una prueba, en el servidor, y los roles iniciales coinciden con la sección 8.2 de las reglas. *(TASK-F7-02; los roles iniciales están en `acceso/datos_prueba.py`.)*
- [ ] Cada pantalla tiene sus estados de carga, vacío y error. *(Existen los patrones en `componentes/ui`; falta la revisión pantalla por pantalla en celular y computadora: TASK-F7-04.)*
- [x] Pruebas, lint, verificación de tipos y construcción pasan. *(5 oct, en la rama de operaciones: `pytest` 1022 pruebas en verde, `ruff check` y `ruff format` limpios, `pnpm typecheck` y `pnpm build` sin errores. Volver a correrlos sobre la rama final antes de etiquetar.)*
- [ ] El motor de movimientos tuvo revisión independiente. *(TASK-F7-06.)*

## Operación

- [x] Las migraciones corren desde una base vacía. *(Cada corrida de pruebas recrea la base y aplica `alembic upgrade head`: `backend/tests/conftest.py`.)*
- [x] El script de datos de prueba es repetible. *(`python -m app.datos_prueba`, idempotente; corre al arrancar el contenedor con `CARGAR_DATOS_PRUEBA=true`.)*
- [ ] `.env.example` documenta cada variable; ningún secreto está en el repositorio. *(Faltan por agregar `RESPALDOS_DIR`, `RESPALDOS_CONSERVAR` y `APP_CONTENEDOR`, que hoy se documentan en [despliegue-local-cloudflare.md](../architecture/despliegue-local-cloudflare.md).)*
- [ ] El despliegue funciona con `docker compose up -d --build` en el servidor. *(Probado en la computadora de desarrollo; falta el servidor.)*
- [x] Los registros de la aplicación se pueden consultar. *(`docker compose logs -f app`; ver README raíz.)*
- [x] El respaldo y su restauración se probaron. *(Base y archivos respaldados y restaurados en otra base, con `respaldo.sh` y `.ps1` y `restaurar.sh` y `.ps1`; ver «Cómo se probó» en [despliegue-local-cloudflare.md](../architecture/despliegue-local-cloudflare.md#cómo-se-probó). Repetir en el servidor antes de la demostración.)*
- [x] La comparación entre bitácora y existencias no reporta diferencias. *(`python -m app.mantenimiento verificar` sale con 0 sobre los datos de prueba y sobre la base restaurada; `backend/tests/test_mantenimiento.py`. Correrlo también sobre la base real del servidor.)*

## Entregables que pide el PDF

- [ ] Prototipo funcional accesible desde celular y computadora: dirección publicada. *(Falta el token del túnel de Cloudflare.)*
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
