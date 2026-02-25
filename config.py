# Configuration management for the ML Celery project.

import os
from dataclasses import dataclass


@dataclass
class Config:
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6389/0")
    RESULT_BACKEND: str = os.getenv("RESULT_BACKEND", "redis://localhost:6389/1")

    # Model storage
    MODEL_DIR: str = os.getenv("MODEL_DIR", "models")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")

    # API
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", 8090))


config = Config()
