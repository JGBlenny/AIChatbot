"""
FastAPI 應用主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import async_engine, Base
from app.api import conversations, processing, knowledge


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命週期管理"""
    # 啟動時：建立資料庫表（開發環境）
    if settings.DEBUG:
        async with async_engine.begin() as conn:
            # await conn.run_sync(Base.metadata.drop_all)  # 小心使用！
            await conn.run_sync(Base.metadata.create_all)

    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 啟動成功！")
    print(f"📝 API 文件: http://localhost:8000/docs")

    yield

    # 關閉時：清理資源
    await async_engine.dispose()
    print("👋 應用已關閉")


# 建立 FastAPI 應用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI 對話資料管理與 RAG 知識庫系統",
    lifespan=lifespan,
)

# CORS 中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== 路由 ==========

@app.get("/")
async def root():
    """API 根路徑"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """健康檢查"""
    return {"status": "healthy"}


# 註冊 API 路由
app.include_router(conversations.router, prefix="/api/conversations", tags=["Conversations"])
app.include_router(processing.router, prefix="/api/processing", tags=["AI Processing"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["Knowledge Base"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
