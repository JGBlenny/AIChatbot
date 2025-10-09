"""
Embedding API Service
統一的向量生成服務，支援快取
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from openai import OpenAI
import redis
import hashlib
import json
import os

app = FastAPI(
    title="Embedding API Service",
    description="統一的向量生成服務",
    version="1.0.0"
)

# 環境變數
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
EMBEDDING_MODEL = "text-embedding-3-small"
CACHE_TTL = 86400  # 24 小時

# OpenAI 客戶端
client = OpenAI(api_key=OPENAI_API_KEY)

# Redis 客戶端
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=False
    )
    redis_client.ping()
    print(f"✅ Redis 已連線: {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    print(f"⚠️  Redis 連線失敗: {e}")
    redis_client = None

# 資料模型
class EmbeddingRequest(BaseModel):
    text: str
    model: str = EMBEDDING_MODEL

class EmbeddingResponse(BaseModel):
    embedding: List[float]
    model: str
    dimensions: int
    cached: bool

@app.get("/")
async def root():
    return {
        "name": "Embedding API Service",
        "version": "1.0.0",
        "model": EMBEDDING_MODEL
    }

@app.get("/api/v1/health")
async def health_check():
    """健康檢查"""
    redis_status = "connected" if redis_client and redis_client.ping() else "disconnected"
    return {
        "status": "healthy",
        "redis": redis_status,
        "model": EMBEDDING_MODEL
    }

@app.post("/api/v1/embeddings", response_model=EmbeddingResponse)
async def create_embedding(request: EmbeddingRequest):
    """
    生成文字向量

    - **text**: 要轉換的文字
    - **model**: 使用的模型（預設: text-embedding-3-small）
    """
    try:
        # 生成快取 key
        cache_key = f"embedding:{request.model}:{hashlib.md5(request.text.encode()).hexdigest()}"

        # 檢查快取
        if redis_client:
            try:
                cached_embedding = redis_client.get(cache_key)
                if cached_embedding:
                    embedding = json.loads(cached_embedding)
                    return EmbeddingResponse(
                        embedding=embedding,
                        model=request.model,
                        dimensions=len(embedding),
                        cached=True
                    )
            except Exception as e:
                print(f"Redis 讀取失敗: {e}")

        # 呼叫 OpenAI API
        response = client.embeddings.create(
            model=request.model,
            input=request.text
        )

        embedding = response.data[0].embedding

        # 儲存到快取
        if redis_client:
            try:
                redis_client.setex(
                    cache_key,
                    CACHE_TTL,
                    json.dumps(embedding)
                )
            except Exception as e:
                print(f"Redis 寫入失敗: {e}")

        return EmbeddingResponse(
            embedding=embedding,
            model=request.model,
            dimensions=len(embedding),
            cached=False
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成向量失敗: {str(e)}")

@app.get("/api/v1/stats")
async def get_stats():
    """取得統計資訊"""
    cache_size = 0
    if redis_client:
        try:
            cache_keys = redis_client.keys("embedding:*")
            cache_size = len(cache_keys)
        except:
            pass

    return {
        "cache_size": cache_size,
        "model": EMBEDDING_MODEL
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 啟動 Embedding API Service...")
    print(f"📊 API 文件: http://localhost:5000/docs")
    print(f"🔑 模型: {EMBEDDING_MODEL}")
    uvicorn.run(app, host="0.0.0.0", port=5000)
