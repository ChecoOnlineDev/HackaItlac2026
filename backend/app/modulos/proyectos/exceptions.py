from app.core.excepciones import Conflicto, DatosInvalidos


class ClaveRepetida(Conflicto):
    codigo = "CLAVE_REPETIDA"
    mensaje_defecto = "Ya existe un proyecto con esa clave."


class ProyectoCerrado(Conflicto):
    codigo = "PROYECTO_CERRADO"
    mensaje_defecto = "Reabre el proyecto antes de editarlo."


class ProyectoConVales(Conflicto):
    codigo = "PROYECTO_CON_VALES"
    mensaje_defecto = "El proyecto ya tiene vales; su clave y almacén no pueden cambiar."


class ProyectoInvalido(DatosInvalidos):
    codigo = "PROYECTO_INVALIDO"
    mensaje_defecto = "Elige un proyecto abierto cuyo fin estimado no haya pasado."


class ProyectoRequerido(DatosInvalidos):
    codigo = "PROYECTO_REQUERIDO"
    mensaje_defecto = "Elige el proyecto del trabajador."


class AsignacionRepetida(Conflicto):
    codigo = "ASIGNACION_REPETIDA"
    mensaje_defecto = "El trabajador ya está asignado a ese proyecto."
