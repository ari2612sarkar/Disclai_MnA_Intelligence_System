from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Hugging Face
    hf_api_key: str = ""
    hf_model_id: str = "mistralai/Mistral-7B-Instruct-v0.2"

    # Database
    database_url: str = "sqlite:///./disclai.db"

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # Ingestion
    chunk_max_tokens: int = 512
    chunk_overlap_tokens: int = 50

    # Retrieval
    retrieval_top_k: int = 10
    bm25_weight: float = 0.5
    embedding_weight: float = 0.5
    enable_embeddings: bool = True

    # Extraction
    extraction_max_retries: int = 3
    extraction_temperature: float = 0.1

    # Evaluation
    evaluation_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()