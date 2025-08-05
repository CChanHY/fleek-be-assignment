from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    database_url: str = "postgres://user:password@localhost:5432/mediagendb"
    redis_url: str = "redis://localhost:6379/0"
    
    replicate_api_token: str
    media_generator_provider: str = "replicate"
    
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key_id: str = "minioadmin"
    s3_secret_access_key: str = "minioadmin"
    s3_bucket_name: str = "media-generation"
    s3_region_name: str = "us-east-1"
    
    app_env: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    initial_retry_delay: int = 5
    max_retry_delay: int = 3600

    class Config:
        env_file = [".env", ".env.development"]
        case_sensitive = False


settings = Settings()