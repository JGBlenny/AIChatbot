"""
RAG Orchestrator 主服務
整合意圖分類、RAG 檢索、信心度評估和未釐清問題管理
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
from asyncpg.pool import Pool

# 導入服務
from services.intent_classifier import IntentClassifier
from services.rag_engine import RAGEngine
from services.confidence_evaluator import ConfidenceEvaluator
from services.unclear_question_manager import UnclearQuestionManager

# 導入路由
from routers import chat, unclear_questions

# 全局變數
db_pool: Pool = None
intent_classifier: IntentClassifier = None
rag_engine: RAGEngine = None
confidence_evaluator: ConfidenceEvaluator = None
unclear_question_manager: UnclearQuestionManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命週期管理"""
    # 啟動時初始化
    global db_pool, intent_classifier, rag_engine, confidence_evaluator, unclear_question_manager

    print("🚀 初始化 RAG Orchestrator...")

    # 建立資料庫連接池
    db_pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "postgres"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        min_size=2,
        max_size=10
    )
    print("✅ 資料庫連接池已建立")

    # 初始化服務
    intent_classifier = IntentClassifier()
    print("✅ 意圖分類器已初始化")

    rag_engine = RAGEngine(db_pool)
    print("✅ RAG 檢索引擎已初始化")

    confidence_evaluator = ConfidenceEvaluator()
    print("✅ 信心度評估器已初始化")

    unclear_question_manager = UnclearQuestionManager(db_pool)
    print("✅ 未釐清問題管理器已初始化")

    # 將服務注入到 app.state
    app.state.db_pool = db_pool
    app.state.intent_classifier = intent_classifier
    app.state.rag_engine = rag_engine
    app.state.confidence_evaluator = confidence_evaluator
    app.state.unclear_question_manager = unclear_question_manager

    print("🎉 RAG Orchestrator 啟動完成！")
    print(f"📝 API 文件: http://localhost:8100/docs")

    yield

    # 關閉時清理
    print("🔄 關閉 RAG Orchestrator...")
    await db_pool.close()
    print("👋 RAG Orchestrator 已關閉")


# 建立 FastAPI 應用
app = FastAPI(
    title="RAG Orchestrator",
    description="增強型 RAG 系統 - 意圖分類、檢索、信心度評估",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊路由
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(unclear_questions.router, prefix="/api/v1", tags=["unclear_questions"])


@app.get("/")
async def root():
    """根路徑"""
    return {
        "name": "RAG Orchestrator",
        "version": "1.0.0",
        "description": "增強型 RAG 系統",
        "docs": "/docs"
    }


@app.get("/api/v1/health")
async def health_check():
    """健康檢查"""
    try:
        # 測試資料庫連接
        async with app.state.db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")

        return {
            "status": "healthy",
            "database": "connected",
            "services": {
                "intent_classifier": "ready",
                "rag_engine": "ready",
                "confidence_evaluator": "ready",
                "unclear_question_manager": "ready"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@app.get("/api/v1/stats")
async def get_stats():
    """取得統計資訊"""
    try:
        # 對話記錄統計
        async with app.state.db_pool.acquire() as conn:
            total_conversations = await conn.fetchval(
                "SELECT COUNT(*) FROM conversation_logs"
            )

            # 意圖類型分布
            intent_dist = await conn.fetch("""
                SELECT intent_type, COUNT(*) as count
                FROM conversation_logs
                WHERE intent_type IS NOT NULL
                GROUP BY intent_type
                ORDER BY count DESC
            """)

            # 平均信心度
            avg_confidence = await conn.fetchval("""
                SELECT AVG(confidence_score)
                FROM conversation_logs
                WHERE confidence_score IS NOT NULL
            """)

            # 使用者評分
            avg_rating = await conn.fetchval("""
                SELECT AVG(user_rating)
                FROM conversation_logs
                WHERE user_rating IS NOT NULL
            """)

        # 未釐清問題統計
        unclear_stats = await app.state.unclear_question_manager.get_stats()

        return {
            "conversations": {
                "total": total_conversations,
                "avg_confidence": float(avg_confidence) if avg_confidence else 0.0,
                "avg_rating": float(avg_rating) if avg_rating else 0.0,
                "intent_distribution": {
                    row['intent_type']: row['count']
                    for row in intent_dist
                }
            },
            "unclear_questions": unclear_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8100,
        reload=True
    )
