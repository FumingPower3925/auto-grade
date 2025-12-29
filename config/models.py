from pydantic import BaseModel


class ServerConfig(BaseModel):
    host: str = "localhost"
    port: int = 8080


class LLMConfig(BaseModel):
    provider: str = "openai"
    default_model: str = "o4-mini"
    smart_model: str = "gpt-5.2"
    base_url: str = "https://api.openai.com/v1"


class OCRConfig(BaseModel):
    provider: str = "mistral"
    model: str = "mistral-ocr-latest"
    base_url: str = "https://api.mistral.ai/v1"


class EmbeddingConfig(BaseModel):
    provider: str = "openai"
    model: str = "text-embedding-3-small"
    dimensions: int = 1536
    chunk_size: int = 1000
    chunk_overlap: int = 200


class DatabaseConfig(BaseModel):
    type: str = "ferretdb"
    host: str = "localhost"
    port: int = 27017
    name: str = "autograde"
    username: str | None = None
    password: str | None = None
