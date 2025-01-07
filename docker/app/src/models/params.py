from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel, Field


class FunctionGuidelines(BaseModel):
    name: str = Field(description="The name of the function.")
    purpose: str = Field(
        description="The purpose of this function. Summarize intended goals."
    )
    services: list[str] = Field(description="The AWS services expected to be used")


class GenerationParams(BaseSettings, FunctionGuidelines):
    model_config = SettingsConfigDict()
    timestamp: str


class ModelParams(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="apd_", validate_default=False)

    bedrock_model_id: str = None
    openai_api_key: str = None
    openai_model_name: str = None
    openai_embedding_model_name: str = "text-embedding-3-small"


class ChromaParams(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="chroma_", validate_default=False)

    bucket: str = None
    db_path: str = "vector_dbs"
    uningested_path: str = None
    summarize: bool = True
    persist_directory: str = f"./tmp/{db_path}/codebase_chroma"
    trigger_file: str = None
