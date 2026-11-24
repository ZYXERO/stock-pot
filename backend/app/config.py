"""Environment-driven settings. Nothing secret is hardcoded here."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # .env lives in the repo root; scripts usually run from backend/, so check both places.
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    databaseUrl: str = Field(default="", alias="DATABASE_URL")

    openaiApiKey: str = Field(default="", alias="OPENAI_API_KEY")
    openaiEmbeddingModel: str = Field(default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL")
    openaiChatModel: str = Field(default="gpt-4o-mini", alias="OPENAI_CHAT_MODEL")

    localEmbeddingModel: str = Field(default="BAAI/bge-small-en-v1.5", alias="LOCAL_EMBEDDING_MODEL")
    ollamaBaseUrl: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    generationModel: str = Field(default="openai", alias="GENERATION_MODEL")

    staples: str = Field(default="salt,pepper,oil,water,butter,sugar,flour", alias="STAPLES")

    @property
    def stapleList(self) -> list[str]:
        """STAPLES as a clean list: 'salt, Pepper' -> ['salt', 'pepper']."""
        return [s.strip().lower() for s in self.staples.split(",") if s.strip()]


@lru_cache
def getSettings() -> Settings:
    """Load settings once and reuse them everywhere."""
    return Settings()