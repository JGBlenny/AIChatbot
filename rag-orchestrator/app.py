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
from services.llm_answer_optimizer import LLMAnswerOptimizer
from services.intent_suggestion_engine import IntentSuggestionEngine
from services.vendor_config_service import VendorConfigService
from services.cache_service import CacheService
from services.form_manager import FormManager

# 導入路由
from routers import chat, chat_stream, unclear_questions, suggested_intents, intents, knowledge, vendors, knowledge_import, knowledge_export, knowledge_generation, platform_sop, cache, videos, business_types, document_converter, target_user_config, forms, api_endpoints

# 全局變數
db_pool: Pool = None
intent_classifier: IntentClassifier = None
rag_engine: RAGEngine = None
confidence_evaluator: ConfidenceEvaluator = None
unclear_question_manager: UnclearQuestionManager = None
llm_answer_optimizer: LLMAnswerOptimizer = None
suggestion_engine: IntentSuggestionEngine = None
vendor_config_service: VendorConfigService = None
cache_service: CacheService = None
form_manager: FormManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命週期管理"""
    # 啟動時初始化
    global db_pool, intent_classifier, rag_engine, confidence_evaluator, unclear_question_manager, llm_answer_optimizer, suggestion_engine, vendor_config_service, cache_service, form_manager

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

    # Phase 3 擴展：配置 LLM 答案優化器（含答案合成功能）
    llm_optimizer_config = {
        "enable_synthesis": os.getenv("ENABLE_ANSWER_SYNTHESIS", "false").lower() == "true",
        "synthesis_threshold": float(os.getenv("SYNTHESIS_THRESHOLD", "0.7")),
        "synthesis_min_results": int(os.getenv("SYNTHESIS_MIN_RESULTS", "2")),
        "synthesis_max_results": int(os.getenv("SYNTHESIS_MAX_RESULTS", "3"))
    }

    llm_answer_optimizer = LLMAnswerOptimizer(config=llm_optimizer_config)

    if llm_optimizer_config["enable_synthesis"]:
        print(f"✅ LLM 答案優化器已初始化 (Phase 3 + 答案合成功能已啟用)")
        print(f"   合成閾值: {llm_optimizer_config['synthesis_threshold']}")
        print(f"   合成來源數: {llm_optimizer_config['synthesis_min_results']}-{llm_optimizer_config['synthesis_max_results']}")
    else:
        print("✅ LLM 答案優化器已初始化 (Phase 3，答案合成功能停用)")

    suggestion_engine = IntentSuggestionEngine()
    print("✅ 意圖建議引擎已初始化 (Phase B)")

    vendor_config_service = VendorConfigService(db_pool)
    print("✅ 業者配置服務已初始化 (Vendor Configs 整合)")

    # 初始化緩存服務
    cache_service = CacheService()

    # 初始化表單管理器（Phase X: 表單填寫對話功能 + 方案 B: 資料庫配置）
    form_manager = FormManager(db_pool=db_pool)
    print("✅ 表單管理器已初始化（表單填寫功能 + 資料庫配置支援）")

    # 將服務注入到 app.state
    app.state.db_pool = db_pool
    app.state.intent_classifier = intent_classifier
    app.state.rag_engine = rag_engine
    app.state.confidence_evaluator = confidence_evaluator
    app.state.unclear_question_manager = unclear_question_manager
    app.state.llm_answer_optimizer = llm_answer_optimizer
    app.state.vendor_config_service = vendor_config_service
    app.state.suggestion_engine = suggestion_engine
    app.state.cache_service = cache_service
    app.state.form_manager = form_manager

    print("🎉 RAG Orchestrator 啟動完成！（含 Phase 3 LLM 優化 + Phase B 意圖建議 + 表單填寫功能）")
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
app.include_router(chat_stream.router, prefix="/api/v1", tags=["chat_stream"])  # ⚠️ 暫時廢棄 2026-01-09（代碼保留，觀察期至 2026-07-09）
app.include_router(unclear_questions.router, prefix="/api/v1", tags=["unclear_questions"])
app.include_router(suggested_intents.router, prefix="/api/v1", tags=["suggested_intents"])
app.include_router(intents.router, prefix="/api/v1", tags=["intents"])
app.include_router(business_types.router, prefix="/api/v1", tags=["business_types"])  # Business Types (Read-only from config)
app.include_router(knowledge.router, tags=["knowledge"])
app.include_router(vendors.router, tags=["vendors"])  # Phase 1: Multi-Vendor Support
app.include_router(knowledge_import.router, tags=["knowledge_import"])  # Knowledge Import from LINE chats
app.include_router(knowledge_export.router, tags=["knowledge_export"])  # Knowledge Export to Excel
app.include_router(knowledge_generation.router, prefix="/api/v1", tags=["knowledge_generation"])  # AI Knowledge Generation
app.include_router(platform_sop.router, tags=["platform_sop"])  # Platform SOP Template Management
app.include_router(cache.router, tags=["cache"])  # Cache Management (事件驅動 + TTL 混合策略)
app.include_router(videos.router, tags=["videos"])  # Video Upload & Management (S3 Storage)
app.include_router(document_converter.router, tags=["document_converter"])  # Document Converter (Word/PDF -> Q&A)
app.include_router(target_user_config.router, tags=["target_user_config"])  # Target User Configuration (用戶類型配置)
app.include_router(forms.router, prefix="/api/v1", tags=["forms"])  # Form Management (表單管理)
app.include_router(api_endpoints.router, prefix="/api/v1", tags=["api_endpoints"])  # API Endpoints Management (API 端點管理)


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
                "unclear_question_manager": "ready",
                "llm_answer_optimizer": "ready (Phase 3)",
                "suggestion_engine": "ready (Phase B)"
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
