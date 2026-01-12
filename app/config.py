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
    
    # Claude API Configuration (for batch processing)
    anthropic_api_key: str
    
    # Vertex AI Configuration (for single request processing)
    google_project_id: str
    google_location: str = "us-central1"
    
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
