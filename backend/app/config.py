"""Ajustes leídos de variables de entorno (y del archivo `.env` de la raíz del repositorio)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=RAIZ_REPOSITORIO / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Base de datos
    mysql_host: str = "localhost"
    mysql_puerto: int = 21001
    mysql_database: str = "imhotep"
    mysql_user: str = "imhotep"
    mysql_password: str = ""
    mysql_root_password: str = ""

    # Sesión
    clave_sesion: str = "cambia-esta-clave"
    sesion_horas: int = 12
    cookie_segura: bool = False
    cookie_nombre: str = "sesion"

    # Bloqueo por intentos fallidos (US-ACC-001)
    intentos_maximos: int = 5
    bloqueo_segundos: int = 300

    # Archivos (firmas y fotos)
    archivos_dir: Path = Path("./almacenamiento")
    archivo_tamano_maximo: int = 2 * 1024 * 1024

    # Datos de prueba (no son datos reales)
    clave_datos_prueba: str = "Prueba-2026!"
    pin_datos_prueba: str = "1234"

    # Pruebas automáticas
    test_db_suffix: str = "main"

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
