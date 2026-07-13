from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Financial Reconciliation Platform"
    
    # Database Settings
    # Default to local SQLite for easy MVP dev setup
    DATABASE_URL: str = "sqlite:///./frp.db"
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
