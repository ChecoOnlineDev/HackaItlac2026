# Prompts de trabajo

Tres prompts para el ciclo de una tarea: planear, implementar y revisar. Sirven con cualquier agente. Se sustituye lo que va entre corchetes.

## 1. Planear una historia o feature

```
Trabaja en modo planificación. No modifiques archivos todavía.

Lee:
- AGENTS.md
- docs/architecture/overview.md
- [docs/stories/fase-N-….md, historia US-XXX-NNN | docs/features/FEAT-NNN-….md]
- Las reglas que cita la historia, en docs/product/reglas-de-negocio.md

Después inspecciona solo el código y las pruebas necesarias para validar el impacto.

Entrega:
1. Resumen del comportamiento actual.
2. Módulos y archivos afectados.
3. Módulos que no deberían cambiar.
4. Cambios de datos, API, interfaz y pruebas.
5. Riesgos, compatibilidad y migraciones.
6. Tareas ordenadas y pequeñas, con el formato TASK-[historia]-NN.
7. Validación esperada por tarea.
8. Preguntas realmente bloqueantes.

No amplíes el alcance ni propongas refactors opcionales.
```

## 2. Implementar una tarea

```
Implementa únicamente [TASK-XXX] del plan aprobado.

Reglas:
- Respeta alcance, exclusiones y criterios de aceptación.
- Sigue los patrones existentes y las reglas de AGENTS.md.
- No cambies arquitectura ni contratos no relacionados.
- Agrega o actualiza pruebas.
- Ejecuta las validaciones de AGENTS.md.
- Si aparece una dependencia no prevista, detente en esa parte y repórtala;
  no amplíes el cambio en silencio.

Entrega el reporte con el formato de docs/templates/reporte.md.
```

## 3. Revisión independiente

```
Revisa el diff de [TASK-XXX] sin modificar archivos.

Compara contra:
- la historia y sus criterios de aceptación
- el plan aprobado
- AGENTS.md y docs/architecture/overview.md
- los resultados de las pruebas

Busca:
- incumplimientos funcionales
- permisos o validación en el lugar equivocado
- regresiones y casos límite
- problemas de concurrencia o de datos
- complejidad innecesaria
- pruebas insuficientes
- cambios fuera de alcance

Clasifica cada hallazgo como bloqueante, importante o menor, con evidencia,
impacto y la corrección mínima sugerida.
```
