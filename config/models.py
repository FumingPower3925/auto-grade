from pydantic import BaseModel

class ServerConfig(BaseModel):
    host: str = "localhost"
    port: int = 8080

class LLMConfig(BaseModel):
    provider: str = "openai"
    model: str = "o4-mini"

class RedisConfig(BaseModel):
    host: str = "localhost"
    port: int = 6379

class DBConfig(BaseModel):
    provider: str = "redis"
    db: int = 0

class VDBConfig(BaseModel):
    provider: str = "redis"
    db: int = 1

class CacheConfig(BaseModel):
    provider: str = "redis"
    db: int = 2