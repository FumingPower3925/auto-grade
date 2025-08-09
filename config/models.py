from pydantic import BaseModel


class ServerConfig(BaseModel):
    host: str = "localhost"
    port: int = 8080


class LLMConfig(BaseModel):
    provider: str = "openai"
    model: str = "o4-mini"
