"""
Configuration Management Module
Handles all application settings and environment variables
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # MongoDB Configuration
    mongodb_connection_string: str
    mongodb_database_name: str = "markazmongodbprod"
    mongodb_collection_name: str = "productsV2"
    
    # Gemini API Configuration (for single and batch request processing)
    gemini_api_key: str
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
