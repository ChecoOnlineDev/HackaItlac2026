# Contexto del Proyecto — Hacka ITLAC 2026

## 1. Contexto general

Este proyecto se desarrolla en el marco de **Hacka ITLAC 2026**, dentro de un desafío orientado a mejorar la gestión, control y trazabilidad de materiales e inventario dentro de una operación real.

La propuesta del equipo parte de la necesidad de reducir procesos manuales, mejorar la visibilidad sobre los movimientos de materiales y contar con información confiable sobre qué ocurre dentro de la operación: qué material entra, qué material sale, quién realizó cada acción y cuándo ocurrió.

El objetivo no es construir únicamente un sistema de inventario tradicional, sino una herramienta operativa que permita registrar movimientos de forma rápida, sencilla y trazable, pensando en entornos donde los usuarios necesitan realizar acciones con la menor fricción posible.

Para el hackatón se priorizará un prototipo funcional, demostrable y coherente, evitando agregar funcionalidades que no aporten directamente al problema principal.

---

## 2. Objetivo general

Desarrollar una plataforma que permita **gestionar y registrar movimientos de materiales**, manteniendo trazabilidad sobre las operaciones realizadas y facilitando la interacción de los empleados con el sistema.

La solución debe permitir conocer de manera clara:

- qué materiales existen dentro de la operación;
- qué movimientos se han realizado;
- quién realizó cada movimiento;
- cuándo ocurrió;
- qué tipo de operación se realizó;
- y cuál es el estado actual de los materiales registrados.

---

## 3. Alcance general del proyecto

El proyecto contempla una solución centralizada para la gestión operativa de materiales e inventario.

El alcance general incluye:

- registro y consulta de materiales;
- control de entradas y salidas;
- actualización de existencias a partir de los movimientos realizados;
- bitácora de movimientos;
- identificación del empleado responsable de cada operación;
- consulta del historial de actividad;
- manejo de usuarios, empleados y roles;
- visualización general del estado del inventario;
- mecanismos rápidos de interacción para el personal operativo;
- generación de información útil para supervisión y seguimiento.

La identificación rápida de empleados podrá plantearse mediante códigos, credenciales digitales, QR, códigos de barras o dispositivos especializados como equipos Zebra. Para efectos del prototipo del hackatón, este flujo puede demostrarse utilizando dispositivos móviles convencionales.

---

## 4. Enfoque del prototipo

La solución debe priorizar tres principios:

**Rapidez operativa.**  
Registrar un movimiento debe requerir pocos pasos y ser viable desde un dispositivo móvil.

**Trazabilidad.**  
Cada movimiento debe dejar evidencia suficiente para conocer qué ocurrió y quién fue responsable.

**Claridad.**  
La información del sistema debe poder ser entendida rápidamente tanto por operadores como por responsables de supervisión.

El prototipo debe demostrar un flujo completo desde la identificación del empleado hasta el registro de una operación y su posterior consulta dentro de la bitácora.

---

## 5. Usuarios principales

De forma general se consideran dos tipos de interacción:

### Personal operativo

Usuarios responsables de realizar movimientos físicos de materiales y registrarlos dentro del sistema.

Su experiencia debe estar enfocada en rapidez, simplicidad y reducción de pasos.

### Personal administrativo o de supervisión

Usuarios encargados de consultar inventario, revisar movimientos, administrar información y supervisar la actividad registrada.

Su experiencia debe estar enfocada en visibilidad, control y trazabilidad.

---

## 6. Fuera de alcance inicial

Para mantener un alcance viable durante el hackatón, inicialmente no se busca desarrollar:

- un ERP completo;
- procesos financieros o contables;
- facturación;
- logística avanzada;
- integraciones empresariales complejas;
- hardware especializado obligatorio;
- automatizaciones industriales completas;
- analítica predictiva avanzada;
- una solución preparada para producción a gran escala.

Estas funcionalidades pueden considerarse como posibles extensiones futuras, pero no forman parte del núcleo del prototipo.

---

## 7. Resultado esperado

Al finalizar el hackatón se espera contar con un prototipo funcional capaz de demostrar de manera clara el siguiente flujo:

**identificación del empleado → selección del material → registro del movimiento → actualización del inventario → generación de registro en bitácora → consulta y supervisión de la actividad.**

El valor principal de la propuesta se encuentra en combinar **control de inventario, trazabilidad de operaciones e identificación rápida del personal** dentro de una experiencia sencilla y orientada a la operación real.
