"""
RAG Orchestrator 主服務
整合意圖分類、RAG 檢索、信心度評估和未釐清問題管理
"""
import os
from contextlib import AsyncExitStack, asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
from asyncpg.pool import Pool

# 導入服務
from services.intent_classifier import IntentClassifier
from services.confidence_evaluator import ConfidenceEvaluator
from services.unclear_question_manager import UnclearQuestionManager
from services.llm_answer_optimizer import LLMAnswerOptimizer
from services.intent_suggestion_engine import IntentSuggestionEngine
from services.vendor_config_service import VendorConfigService
from services.cache_service import CacheService
from services.form_manager import FormManager
from services.sop_orchestrator import SOPOrchestrator

# 導入路由
from routers import chat, unclear_questions, knowledge, vendors, knowledge_import, knowledge_export, knowledge_generation, platform_sop, cache, videos, images, business_types, document_converter, target_user_config, forms, api_endpoints, lookup, loops, loop_knowledge, system_health, conversational_configs
from routers import ocr_mapping  # documind-ocr-mapping：DocuMind OCR → JGB 欄位草稿（同步端點）
from routers import agent as agent_router  # agentic-mcp-orchestration 1.8：/api/v1/agent/openapi.json・/health

# 全局變數
db_pool: Pool = None
intent_classifier: IntentClassifier = None
confidence_evaluator: ConfidenceEvaluator = None
unclear_question_manager: UnclearQuestionManager = None
llm_answer_optimizer: LLMAnswerOptimizer = None
suggestion_engine: IntentSuggestionEngine = None
vendor_config_service: VendorConfigService = None
cache_service: CacheService = None
form_manager: FormManager = None
sop_orchestrator: SOPOrchestrator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命週期管理"""
    # 啟動時初始化
    global db_pool, intent_classifier, confidence_evaluator, unclear_question_manager, llm_answer_optimizer, suggestion_engine, vendor_config_service, cache_service, form_manager, sop_orchestrator

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

    # 初始化 SOP 編排器（SOP Next Action 功能）
    sop_orchestrator = SOPOrchestrator(form_manager=form_manager)
    print("✅ SOP 編排器已初始化（SOP Next Action 功能 - 4 種觸發模式 + 3 種後續動作）")

    # 初始化對話式回答引擎（option-routing R14–R19｜售前為首例）
    from services.conversational_engine import ConversationalEngine
    from services.conversational_rules import load_rules as conversational_load_rules
    from services.system_context import get_system_context as conversational_get_system_context
    from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2
    from services.api_call_handler import get_api_call_handler
    conversational_engine = ConversationalEngine(
        db_pool=db_pool,
        optimizer=llm_answer_optimizer,
        retriever=VendorKnowledgeRetrieverV2(),
        get_system_context=conversational_get_system_context,
        rules_loader=conversational_load_rules,
        api_handler=get_api_call_handler(db_pool),  # 診斷型對話 API grounding 用
    )
    print("✅ 對話式回答引擎已初始化（conversational：多輪自適應問答→收斂，售前為首例）")

    # 將服務注入到 app.state
    app.state.db_pool = db_pool
    app.state.intent_classifier = intent_classifier
    app.state.confidence_evaluator = confidence_evaluator
    app.state.unclear_question_manager = unclear_question_manager
    app.state.llm_answer_optimizer = llm_answer_optimizer
    app.state.vendor_config_service = vendor_config_service
    app.state.suggestion_engine = suggestion_engine
    app.state.cache_service = cache_service
    app.state.form_manager = form_manager
    app.state.sop_orchestrator = sop_orchestrator
    app.state.conversational_engine = conversational_engine

    print("🎉 RAG Orchestrator 啟動完成！（含 Phase 3 LLM 優化 + Phase B 意圖建議 + 表單填寫功能 + SOP Next Action）")
    print(f"📝 API 文件: http://localhost:8100/docs")

    # MCP session manager（agentic-mcp-orchestration 1.7）：⚠️ **必須**進 lifespan，
    # 否則第一個 /mcp 請求會 RuntimeError: Task group is not initialized（research 主題 1）。
    # SDK 未安裝時 app.state.mcp_server 為 None，這段整個略過。
    async with AsyncExitStack() as _mcp_stack:
        _mcp_srv = getattr(app.state, "mcp_server", None)
        if _mcp_srv is not None:
            await _mcp_stack.enter_async_context(_mcp_srv.session_manager.run())
            print("✅ MCP session manager 已啟動")
        yield

    # 關閉時清理
    print("🔄 關閉 RAG Orchestrator...")
    # kb.get 走同步 psycopg2，另有一個延遲建立的連線池（agentic-mcp-orchestration 1.7）
    _kb_pool = globals().get("_mcp_kb_pool")
    if _kb_pool is not None:
        try:
            _kb_pool.closeall()
        except Exception as _e:          # 收尾失敗不擋關機
            print(f"⚠️ [mcp] kb 連線池關閉失敗（忽略）：{_e}")
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

# ── 服務對服務 API Key 認證（金鑰存 DB；RAG_API_AUTH_ENFORCE 關→不強制，安全上線）──
from fastapi import Request
from fastapi.responses import JSONResponse
from services.api_key_auth import is_exempt, auth_enforced, verify_api_key

if auth_enforced():
    print("🔒 [security] rag API Key 認證【已啟用】，金鑰來源＝api_keys 表")
else:
    print("⚠️ [security] RAG_API_AUTH_ENFORCE 未開 → API Key 認證【停用】，rag 對外無保護。正式環境務必開啟。")


@app.middleware("http")
async def usage_metering_middleware(request: Request, call_next):
    """usage-metering（spec usage-metering 2.1）：/api/v1/message 進場建計量
    context、出場落事件（fire-and-forget）。串流回應（SSE）由 generator finally
    落點（finalize 冪等使雙落點安全）；其餘路徑零觸碰；任何失敗不影響回應。"""
    from services import usage_metering as _um
    # ── /mcp：**只做額度短路**（agentic-mcp-orchestration 1.7）──
    # ⛔ 不 begin／finalize：門面 services/agent/mcp_facade.py 是唯一寫入者
    #    （每次工具呼叫一列 usage_events，不變量 31）。這裡再落一次 ⇒ 一次呼叫兩列。
    # 身分與 key 屬性由 McpServiceGate（最外層 middleware）放進 request.state。
    if request.url.path.startswith("/mcp"):
        _mcp_call = getattr(request.state, "mcp_call", None)
        if _mcp_call is not None and _um.is_enabled():
            _qs = await _um.quota_check(getattr(request.app.state, "db_pool", None),
                                        _mcp_call.identity.vendor_id, _mcp_call.is_internal)
            if _qs.state == "blocked":
                return JSONResponse(status_code=429,
                                    content={"detail": "QUOTA_EXCEEDED",
                                             "code": "QUOTA_EXCEEDED"})
        return await call_next(request)
    metered = (request.url.path == "/api/v1/message" and request.method == "POST"
               and _um.is_enabled())
    if metered:
        try:
            import json as _json
            _body = await request.body()
            # ⚠️ BaseHTTPMiddleware 讀 body 會吃掉 receive channel，下游 handler
            #    等 body 永久卡死（實測）——回灌 _receive 供下游重читать
            async def _replay():
                return {"type": "http.request", "body": _body, "more_body": False}
            request._receive = _replay
            _fields = _json.loads(_body) if _body else {}
            _um.begin(_fields if isinstance(_fields, dict) else {})
        except Exception:
            _fields = {}
            _um.begin({})
    _pool = getattr(request.app.state, "db_pool", None)
    _quota = None
    if metered:
        # quota-management：達限短路（進檢索/LLM 前，零成本，R4.1）；fail-open
        _ctx_obj = _um._ctx.get()
        _quota = await _um.quota_check(_pool, (_fields or {}).get("vendor_id"),
                                       bool(_ctx_obj and _ctx_obj.is_internal))
        if _quota.state == "blocked":
            _um.set_path("quota_blocked")
            _um.finalize("blocked", 200, db_pool=_pool)      # 記事件供舉證（R4.6）
            _body_dict = _um.quota_blocked_body(
                _ctx_obj.user_type if _ctx_obj else "unknown", _quota, _fields or {})
            return JSONResponse(status_code=200, content=_body_dict)
    try:
        response = await call_next(request)
    except Exception:
        if metered:
            _um.finalize("error", 500, db_pool=_pool)
        raise
    if metered:
        _ctype = response.headers.get("content-type", "")
        if "text/event-stream" not in _ctype:      # 串流由 generator finally 收尾
            _um.finalize("success" if response.status_code < 500 else "error",
                         response.status_code, db_pool=_pool)
            # quota 警示：2026-07-06 改判——警示不進對話（改寄信），
            # env QUOTA_WARN_IN_CHAT=true 可重新啟用對話內提示
            if (os.getenv("QUOTA_WARN_IN_CHAT", "false").lower() == "true"
                    and _quota is not None and _quota.state == "warn"
                    and "application/json" in _ctype and response.status_code == 200):
                _ctx_obj = _um._ctx.get()
                _ut = _ctx_obj.user_type if _ctx_obj else "unknown"
                _raw = b""
                async for _chunk in response.body_iterator:
                    _raw += _chunk
                _new_raw = _um.append_quota_hint(_raw, _ut, _quota)
                from starlette.responses import Response as _Resp
                _hdrs = dict(response.headers)
                _hdrs.pop("content-length", None)      # 重算（research 風險 2）
                return _Resp(content=_new_raw if _new_raw is not None else _raw,
                             status_code=response.status_code, headers=_hdrs,
                             media_type="application/json")
    return response


@app.middleware("http")
async def api_key_guard(request: Request, call_next):
    if auth_enforced() and request.method != "OPTIONS" and not is_exempt(request.url.path):
        pool = getattr(request.app.state, "db_pool", None)
        if not await verify_api_key(pool, request.headers.get("x-api-key")):
            return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})
    return await call_next(request)


# ══════════════════════════════════════════════════════════════════════
# MCP 門面（spec agentic-mcp-orchestration 任務 1.7｜design 元件 4）
# ══════════════════════════════════════════════════════════════════════
# 兩件事，刻意分開：
#   ① **服務層閘**（McpServiceGate）——`/mcp` 與 `/api/v1/agent/*` 無條件要求
#      有效 X-API-Key＋Origin 三態＋X-JGB-Identity fail-closed。**永遠掛**，
#      與 MCP SDK 是否安裝無關（不變量 28：enforce 關時 /mcp 仍 401）。
#      這個 middleware 最後加 ⇒ 在 middleware 堆疊最外層 ⇒ 先於
#      api_key_guard 與 usage_metering_middleware 跑。
#   ② **工具面**（Mount("/mcp", …)）——只有 MCP SDK 可匯入時才掛。
#      2026-09-04 實查：mcp==2.1.1 與 fastapi==0.104.1 相依衝突
#      （anyio<4 vs anyio>=4.9），故正式 image 目前未裝，詳見 requirements.txt。
from starlette.routing import Mount
from services.agent import mcp_facade as _mcp_facade

# MCP_ALLOWED_ORIGINS 未設定 ⇒ **啟動即 raise**（design 元件 4：必須明示；
# `-` 代表空集合＝任何帶 Origin 的請求都拒）。
_mcp_facade.load_allowed_origins()

app.add_middleware(_mcp_facade.McpServiceGate,
                   get_pool=lambda: getattr(app.state, "db_pool", None))

_mcp_retriever = None


def _get_mcp_retriever():
    """`kb.search` 用的檢索器（延遲建立，避免 import 期做初始化 I/O）。"""
    global _mcp_retriever
    if _mcp_retriever is None:
        from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2
        _mcp_retriever = VendorKnowledgeRetrieverV2()
    return _mcp_retriever


_mcp_sdk_ok, _mcp_sdk_reason = _mcp_facade.mcp_sdk_available()
if _mcp_sdk_ok:
    _mcp_kb_pool = _mcp_facade.LazyPsycopg2Pool()
    _mcp_deps = _mcp_facade.FacadeDeps(
        get_db_pool=lambda: getattr(app.state, "db_pool", None),
        get_kb_pool=lambda: _mcp_kb_pool,
        get_retriever=_get_mcp_retriever,
        stage=_mcp_facade.current_stage(),
    )
    _mcp_registry = _mcp_facade.build_registry(_mcp_deps)
    _mcp_server = _mcp_facade.build_mcp_server(_mcp_registry, _mcp_deps)
    # 子 app 的路徑與 DNS-rebinding 設定見 mcp_facade.build_asgi_app 的 docstring
    #（兩個參數都 ⛔ 不可省，否則不是 /mcp/mcp 就是全部 421）。
    app.router.routes.append(Mount("/mcp", app=_mcp_facade.build_asgi_app(_mcp_server)))
    app.state.mcp_server = _mcp_server
    print("✅ MCP 門面已掛載於 /mcp（工具面 + 服務層閘）")
else:
    app.state.mcp_server = None
    print(f"⚠️ [mcp] MCP SDK 不可用（{_mcp_sdk_reason}）→ /mcp 工具面未掛載；"
          f"服務層閘仍生效（缺／錯 X-API-Key 一律 401）")


# 註冊路由
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(unclear_questions.router, prefix="/api/v1", tags=["unclear_questions"])
app.include_router(business_types.router, prefix="/api/v1", tags=["business_types"])  # Business Types (Read-only from config)
app.include_router(knowledge.router, tags=["knowledge"])
app.include_router(vendors.router, tags=["vendors"])  # Phase 1: Multi-Vendor Support
app.include_router(knowledge_import.router, tags=["knowledge_import"])  # Knowledge Import from LINE chats
app.include_router(knowledge_export.router, tags=["knowledge_export"])  # Knowledge Export to Excel
app.include_router(knowledge_generation.router, prefix="/api/v1", tags=["knowledge_generation"])  # AI Knowledge Generation
app.include_router(platform_sop.router, tags=["platform_sop"])  # Platform SOP Template Management
app.include_router(cache.router, tags=["cache"])  # Cache Management (事件驅動 + TTL 混合策略)
app.include_router(videos.router, tags=["videos"])  # Video Upload & Management (S3 Storage)
app.include_router(images.router, tags=["images"])  # Image Upload & Recognition (修繕圖片上傳)
app.include_router(document_converter.router, tags=["document_converter"])  # Document Converter (Word/PDF -> Q&A)
app.include_router(target_user_config.router, tags=["target_user_config"])  # Target User Configuration (用戶類型配置)
app.include_router(conversational_configs.router, tags=["conversational_configs"])  # 對話式回答設定管理
app.include_router(forms.router, prefix="/api/v1", tags=["forms"])  # Form Management (表單管理)
app.include_router(api_endpoints.router, prefix="/api/v1", tags=["api_endpoints"])  # API Endpoints Management (API 端點管理)
app.include_router(lookup.router, tags=["lookup"])  # Lookup Table System (通用查詢系統)
app.include_router(loops.router, prefix="/api/v1/loops", tags=["loops"])  # Knowledge Completion Loop Management (知識完善迴圈管理)
app.include_router(loop_knowledge.router, prefix="/api/v1/loops", tags=["loop_knowledge"])  # Loop Knowledge Review API (知識審核 API)
app.include_router(system_health.router, tags=["system_health"])  # Pipeline Health Dashboard (系統健康檢查)
app.include_router(ocr_mapping.router, tags=["ocr-mapping"])  # documind-ocr-mapping（prefix 在 router 內）
app.include_router(agent_router.router, tags=["agent"])  # agentic-mcp-orchestration 1.8（prefix 在 router 內）


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
    # 只在開發環境啟用 reload，生產環境應禁用以避免 DNS 解析問題
    reload_enabled = os.getenv("UVICORN_RELOAD", "false").lower() == "true"
    workers = int(os.getenv("UVICORN_WORKERS", "4"))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8100,
        reload=reload_enabled,
        workers=1 if reload_enabled else workers
    )
