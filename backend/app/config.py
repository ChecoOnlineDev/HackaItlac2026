"""Ajustes leídos de variables de entorno (y del archivo `.env` de la raíz del repositorio)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]

# Una clave de sesión debe tener al menos tantos caracteres (python -c "import secrets;
# print(secrets.token_urlsafe(48))" da 64) y no ser un valor de ejemplo (siempre empiezan igual).
CLAVE_SESION_LARGO_MINIMO = 32
PREFIJO_CLAVES_DE_EJEMPLO = "cambia-"


class ConfiguracionInsegura(RuntimeError):
    """El entorno es `produccion` y la configuración no es segura: la aplicación no arranca."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=RAIZ_REPOSITORIO / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Entorno: `desarrollo` (por defecto) solo avisa de una configuración insegura; `produccion`
    # se niega a arrancar con ella y apaga la documentación interactiva de la API.
    entorno: Literal["desarrollo", "produccion"] = "desarrollo"

    # Base de datos
    mysql_host: str = "localhost"
    mysql_puerto: int = 21001
    mysql_database: str = "imhotep"
    mysql_user: str = "imhotep"
    mysql_password: str = ""
    mysql_root_password: str = ""

    # Sesión (AC-14 a AC-24): token de acceso corto + token de renovación opaco por dispositivo.
    clave_sesion: str = "cambia-esta-clave"
    # OBSOLETO: antes fijaba la vida del único token de sesión (12 h). Ya no se usa; la vida de la
    # sesión sale de ACCESO_MINUTOS, REFRESH_DIAS y REFRESH_TOPE_DIAS. Se acepta para que un `.env`
    # viejo no falle al arrancar.
    sesion_horas: int | None = None
    # Vida del token de acceso, en minutos. Al vencer, la interfaz lo renueva sola.
    acceso_minutos: int = Field(default=15, ge=1, le=120)
    # Días que dura el token de renovación sin usarse; cada renovación los vuelve a dar completos.
    refresh_dias: int = Field(default=7, ge=1, le=30)
    # Tope absoluto, en días desde que se inició la sesión: pasado el tope hay que entrar de nuevo
    # aunque se use a diario.
    refresh_tope_dias: int = Field(default=30, ge=1, le=90)
    # Segundos tras una renovación en que el token ya rotado todavía se acepta (dos pestañas que
    # renuevan a la vez, un reintento de red) sin tomarlo por robado.
    refresh_tolerancia_segundos: int = Field(default=10, ge=0, le=60)
    cookie_segura: bool = False
    cookie_nombre: str = "sesion"
    # Cookie del token de renovación (solo viaja a /api/sesion).
    cookie_refresh_nombre: str = "sesion_renovar"

    # Bloqueo por intentos fallidos (US-ACC-001)
    intentos_maximos: int = 5
    bloqueo_segundos: int = 300

    # Vigencia de una solicitud de autorización, en minutos (A-03, US-AUT-001)
    autorizacion_vigencia_minutos: int = 15

    # Archivos (firmas y fotos)
    archivos_dir: Path = Path("./almacenamiento")
    archivo_tamano_maximo: int = 2 * 1024 * 1024

    # Límites de tamaño del cuerpo de una petición, en bytes (413 `CUERPO_MUY_GRANDE`). El de
    # JSON vale para todo lo que no tenga uno propio; los otros se fijan por ruta.
    limite_cuerpo_json: int = 1 * 1024 * 1024
    limite_cuerpo_vale: int = 12 * 1024 * 1024  # POST /api/vales y /api/vales/evaluar
    limite_cuerpo_foto_trabajador: int = 3 * 1024 * 1024
    limite_cuerpo_importacion: int = 6 * 1024 * 1024

    # Interfaz construida (frontend/build/client). En la imagen vive en /app/interfaz; si la
    # carpeta no existe (desarrollo, pruebas) el servidor solo ofrece la API.
    interfaz_dir: Path = Path("/app/interfaz")

    # Datos de prueba (no son datos reales). `CARGAR_DATOS_PRUEBA=true` los carga al arrancar el
    # contenedor (lo lee el script de arranque); aquí solo se usa para validar la configuración.
    cargar_datos_prueba: bool = False
    clave_datos_prueba: str = "Prueba-2026!"
    pin_datos_prueba: str = "1234"

    # Pruebas automáticas
    test_db_suffix: str = "main"

    @model_validator(mode="after")
    def _validar_sesion(self) -> Settings:
        if self.refresh_tope_dias < self.refresh_dias:
            raise ValueError("REFRESH_TOPE_DIAS no puede ser menor que REFRESH_DIAS.")
        if self.cookie_refresh_nombre == self.cookie_nombre:
            raise ValueError("COOKIE_REFRESH_NOMBRE debe ser distinta de COOKIE_NOMBRE.")
        return self

    @property
    def es_produccion(self) -> bool:
        return self.entorno == "produccion"

    def problemas_de_arranque(self) -> list[str]:
        """Lo inseguro de esta configuración, en español. En `produccion` impide el arranque."""
        problemas: list[str] = []
        clave = self.clave_sesion
        if clave.lower().startswith(PREFIJO_CLAVES_DE_EJEMPLO):
            problemas.append(
                "CLAVE_SESION es la de ejemplo. Genera una con: "
                'python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        elif len(clave) < CLAVE_SESION_LARGO_MINIMO:
            problemas.append(
                f"CLAVE_SESION tiene menos de {CLAVE_SESION_LARGO_MINIMO} caracteres. "
                'Genera una con: python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        if not self.cookie_segura:
            problemas.append("COOKIE_SEGURA debe ser true (la sesión viaja por HTTPS).")
        if self.cargar_datos_prueba and not self.clave_datos_prueba.strip():
            problemas.append(
                "CARGAR_DATOS_PRUEBA=true con CLAVE_DATOS_PRUEBA vacía crearía usuarios sin "
                "contraseña real. Define CLAVE_DATOS_PRUEBA o pon CARGAR_DATOS_PRUEBA=false."
            )
        return problemas

    @property
    def database_url(self) -> URL:
        return URL.create(
            "mysql+pymysql",
            username=self.mysql_user,
            password=self.mysql_password,
            host=self.mysql_host,
            port=self.mysql_puerto,
            database=self.mysql_database,
            query={"charset": "utf8mb4"},
        )

    def url_servidor(self, usuario: str, clave: str) -> URL:
        """URL sin base de datos, para crear bases (pruebas)."""
        return URL.create(
            "mysql+pymysql",
            username=usuario,
            password=clave,
            host=self.mysql_host,
            port=self.mysql_puerto,
            query={"charset": "utf8mb4"},
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
