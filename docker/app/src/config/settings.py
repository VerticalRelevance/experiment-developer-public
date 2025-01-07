from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class BaseAppSettings(BaseSettings):
    """Base settings class with common configuration."""
    model_config = SettingsConfigDict()

class ModelSettings(BaseAppSettings):
    """Settings for model configuration."""
    openai_api_key: Optional[str] = None
    openai_model_name: Optional[str] = "gpt-4o"
    openai_embedding_model_name: Optional[str] = "text-embedding-3-small"
    bedrock_model_id: Optional[str] = None
    embedding_summarize: bool = True

class StorageSettings(BaseAppSettings):
    """Settings for storage configuration."""
    bucket: str = None
    db_path: str = "vector_dbs"
    persist_directory: str = f"./tmp/{db_path}/codebase_chroma"
    uningested_path: str = "uningested"

class LoggingSettings(BaseAppSettings):
    """TODO. Not used"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"

class Settings:
    """Global settings container."""
    def __init__(self):
        self.model = ModelSettings()
        self.storage = StorageSettings()
        self.logging = LoggingSettings()

    @classmethod
    def get_settings(cls) -> "Settings":
        """Get singleton instance of settings."""
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance
