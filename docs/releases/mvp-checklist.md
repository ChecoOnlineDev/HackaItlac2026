# Checklist de release del MVP

Gate de la Fase 8 del [roadmap](../product/roadmap.md). El MVP se cierra cuando todo está marcado, no cuando se acaban las tareas.

## Producto

- [ ] El flujo principal de [mvp-scope.md](../product/mvp-scope.md) se completa en el entorno publicado, desde un celular y desde una computadora.
- [ ] Lo completa una persona que no escribió el código, con datos que ella misma elige.
- [ ] Las exclusiones del alcance se respetaron; lo que quedó a medias está registrado como deuda.

## Calidad

- [ ] La prueba del guion completo pasa.
- [ ] Cada permiso se verifica con una prueba, en el servidor, y los roles iniciales coinciden con la sección 8.2 de las reglas.
- [ ] Cada pantalla tiene sus estados de carga, vacío y error.
- [ ] Pruebas, lint, verificación de tipos y construcción pasan.
- [ ] El motor de movimientos tuvo revisión independiente.

## Operación

- [ ] Las migraciones corren desde una base vacía.
- [ ] El script de datos de prueba es repetible.
- [ ] `.env.example` documenta cada variable; ningún secreto está en el repositorio.
- [ ] El despliegue funciona con `docker compose up -d --build` en el servidor.
- [ ] Los registros de la aplicación se pueden consultar.
- [ ] El respaldo y su restauración se probaron.
- [ ] La comparación entre bitácora y existencias no reporta diferencias.

## Entregables que pide el PDF

- [ ] Prototipo funcional accesible desde celular y computadora: dirección publicada.
- [ ] Usuarios de prueba para cada rol, listados en el README raíz.
- [ ] Código fuente e instrucciones para instalar o desplegar, en el README raíz.
- [ ] Descripción breve de la estructura de datos: [data-model.md](../architecture/data-model.md).
- [ ] Respaldos y controles de acceso: [security-model.md](../architecture/security-model.md).
- [ ] Guía corta para el almacenista (entregar, devolver, trasladar y consultar): `docs/guia-almacenista.md`. Se escribe con las pantallas terminadas.

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

- [ ] Versión etiquetada en el repositorio.
- [ ] `docs/releases/changelog.md` con lo que incluye la versión.
- [ ] Roadmap actualizado con lo aprendido.
