"""
應用配置管理
"""
from typing import List
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl


class Settings(BaseSettings):
    """應用設定"""

    # 基本設定
    APP_NAME: str = "AIChatbot Admin"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 資料庫
    DATABASE_URL: str
    SYNC_DATABASE_URL: str

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_ORG_ID: str | None = None

    # 向量資料庫
    PINECONE_API_KEY: str | None = None
    PINECONE_ENVIRONMENT: str | None = None
    PINECONE_INDEX_NAME: str = "aichatbot-knowledge"
    VECTOR_DIMENSION: int = 3072

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # 安全
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173"
    ]

    # 檔案路徑
    KNOWLEDGE_BASE_PATH: str = "../knowledge-base"
    UPLOAD_DIR: str = "./uploads"

    # 處理設定
    BATCH_SIZE: int = 10
    MAX_CONCURRENT_JOBS: int = 3
    PROCESSING_TIMEOUT: int = 300

    # AI 模型設定
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    EMBEDDING_DIMENSIONS: int = 3072
    CHAT_MODEL: str = "gpt-4-turbo-preview"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    class Config:
        env_file = ".env"
        case_sensitive = True


# 單例配置實例
settings = Settings()
