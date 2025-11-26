from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str
    
    MONGO_URI: str
    MONGO_DB_NAME: str
    
    ADMIN_SECRET: str

    PRESIGNED_EXPIRY: int = 3600
    MINIO_SECURE: bool = True
    
    REDIS_URL: str = "redis://localhost:6379/0"
    CLAMAV_HOST: str = "192.168.0.153"
    CLAMAV_PORT: int = 3310

    class Config:
        env_file = ".env"


settings = Settings()
