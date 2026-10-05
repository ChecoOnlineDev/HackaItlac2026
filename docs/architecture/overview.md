# Mapa del sistema

Qué módulos existen, de qué se encarga cada uno y de quién depende. Es la orientación para cualquier tarea que cruce módulos.

Estado: es la estructura planeada. Se crea en la Fase 0; hoy el backend es un archivo de saludo y el frontend es la plantilla de React Router.

## Estructura del repositorio

```
backend/
  app/
    main.py          crea la aplicación; monta /api y la interfaz construida
    config.py        ajustes leídos de variables de entorno
    db.py            motor y sesión de base de datos
    seguridad.py     contraseñas, PIN y sesión
    modulos/         un directorio por dominio (ver tabla)
    datos_prueba.py  carga repetible de datos de prueba
  alembic/           migraciones
  tests/             pruebas
frontend/
  app/
    routes/          una ruta por pantalla
    componentes/     escáner, renglón con semáforo, fichas
    api/             cliente de la API
docs/                esta documentación
```

Cada módulo del backend tiene los mismos archivos: `router.py` (endpoints y permisos), `service.py` (reglas), `models.py` (tablas) y `schemas.py` (entrada y salida).

## Módulos del backend

| Módulo | Responsabilidad | Depende de |
|---|---|---|
| `acceso` | Usuarios, sesión, PIN, roles y el catálogo de permisos. Ofrece a los demás módulos la verificación de un permiso. | — |
| `almacenes` | Almacenes, ubicaciones y lectura de existencias. | `acceso` |
| `catalogo` | Categorías, artículos, piezas, registro de códigos; inactivar y reactivar; auditoría de cambios. | `acceso` |
| `trabajadores` | Personas, periodos de contrato, vigencia, baja y reingreso. | `acceso` |
| `movimientos` | El motor: evalúa el semáforo, confirma vales, escribe movimientos, actualiza existencias, asigna folios. | `catalogo`, `trabajadores`, `almacenes`, `autorizaciones` |
| `autorizaciones` | Solicitudes de autorización y su resolución, por PIN o a distancia. | `acceso` |
| `inspecciones` | Inspecciones y cambios de estado de pieza. | `catalogo` |
| `consulta` | Escaneo universal, búsqueda, fichas y reportes. Solo lee. | Todos |
| `importacion` | Vista previa y carga desde tabla; crea artículos y entradas a través de `catalogo` y `movimientos`. | `catalogo`, `movimientos` |

## Límites

- **Solo `movimientos` escribe** en vales, movimientos, existencias y en la ubicación de las piezas. Los demás módulos le piden la operación; nunca tocan esas tablas.
- **`consulta` no escribe nada.**
- **Cada endpoint declara su permiso en el `router.py`**, por clave; nunca se compara el nombre del rol. Las reglas de negocio van en `service.py`.
- **Los permisos de información** (costos, datos personales) se aplican al armar la respuesta, en `schemas.py`.

## Flujo de una entrega

```
Interfaz: escanea un código
  -> POST /api/vales/evaluar
       movimientos.service: identifica el código (catalogo), revisa al trabajador (trabajadores),
       existencias (almacenes), estado e inspección (catalogo), límites y requisitos
       -> devuelve nivel y motivos por renglón
Interfaz: firma y confirma
  -> POST /api/vales
       movimientos.service: bloquea filas, vuelve a evaluar, escribe vale y movimientos,
       actualiza existencias y ubicación de piezas, asigna folio
       -> devuelve el vale emitido
```

## Áreas del frontend

| Área | Rutas | Notas |
|---|---|---|
| Operación | `/entregar`, `/devolver`, `/trasladar`, `/recibir` | Comparten el escáner y la lista de renglones. |
| Consulta | `/consultar`, fichas de trabajador, artículo, pieza y vale | Solo lectura, con atajos a la operación. |
| Personas | `/trabajadores` | RH. |
| Inventario y catálogo | `/inventario`, `/entradas`, `/importar`, `/catalogo`, `/etiquetas` | Compras y supervisor. |
| Supervisión | `/autorizaciones`, `/reportes` | Autorizaciones, y los reportes que permite cada rol. |

## Cómo validar

Los comandos están en [AGENTS.md](../../AGENTS.md). El gate de cada fase está en el [roadmap](../product/roadmap.md).
