"""Configuración central de la app Ayni.

Lee variables de entorno (o del archivo .env en local). En Render se definen
como Environment Variables del servicio.
"""
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Base de datos. En local usa SQLite (cero configuración).
    # En Render, Postgres inyecta DATABASE_URL automáticamente.
    database_url: str = "sqlite:///./ayni.db"

    # Seguridad JWT. CAMBIAR jwt_secret en producción (Render → Environment).
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 días

    # CORS: orígenes permitidos separados por coma, o "*" para todos.
    cors_origins: str = "*"

    # Si es True, al iniciar siembra datos de demo (barrios, categorías, usuarios).
    seed_on_startup: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("database_url")
    @classmethod
    def normalize_db_url(cls, v: str) -> str:
        # Render entrega URLs con prefijo postgres:// o postgresql://.
        # SQLAlchemy + psycopg3 necesita postgresql+psycopg://.
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+psycopg://", 1)
        if v.startswith("postgresql://") and "+psycopg" not in v:
            return v.replace("postgresql://", "postgresql+psycopg://", 1)
        return v

    @property
    def cors_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
