from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        case_sensitive=True,
        extra="ignore",
    )

    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Financial Reconciliation Platform"
    DATABASE_URL: str = "sqlite:///./frp.db"
    CORS_ORIGINS: str = "http://localhost:5173"
    FRP_DESKTOP: bool = False
    FRP_DESKTOP_TOKEN: str | None = None
    FRP_PORT: int = 8000

    @property
    def allowed_cors_origins(self) -> list[str]:
        origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        if "*" in origins:
            raise ValueError("CORS_ORIGINS 不允许使用通配符")
        if not self.FRP_DESKTOP:
            return origins
        desktop_origins = [
            "http://localhost:5174",
            "http://localhost:1420",
            "tauri://localhost",
            "http://tauri.localhost",
        ]
        for origin in desktop_origins:
            if origin not in origins:
                origins.append(origin)
        return origins


settings = Settings()
