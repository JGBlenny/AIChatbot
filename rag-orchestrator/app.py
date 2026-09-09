"""
RAG Orchestrator 主服務
整合意圖分類、RAG 檢索、信心度評估和未釐清問題管理
"""
import os
import sys
from contextlib import AsyncExitStack, asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
from asyncpg.pool import Pool
from PIL import Image

# W9-4（解壓縮炸彈防線）：行程啟動最早處釘 Image.MAX_IMAGE_PIXELS，照片線（s3_image_service.
# downscale_image）與文件頁圖線共用同一道防線——全 repo 原本沒有此防線，Image.open 對不可信
# bytes 直接開啟。40M 級：照片線 downscale 目標 ≤1024px，文件頁圖同級，40M 已足夠餘裕。
# 回退：刪除本常數與下一行賦值即可。
IMAGE_MAX_PIXELS = 40_000_000
Image.MAX_IMAGE_PIXELS = IMAGE_MAX_PIXELS

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


def _agent_configured() -> bool:
    """任一 agent 開關有值 ⇒ agent 路徯「被使用」⇒ 組裝失敗要啟動紅；否則 fail-soft 只警告。

    ⚠️ 薄別名（任務 4.1）：判準的**唯一權威**已搬到
    `services.agent.mcp_facade.agent_configured()`（health 也讀那一份，
    ⛔ 不在此重寫第二套判準）；名稱保留在此供既有測試沿用。
    """
    from services.agent.mcp_facade import agent_configured as _mcp_agent_configured
    return _mcp_agent_configured()


#: 啟動時要組大綱＋索引的受眾，**依序**（DSP-037／S1b）。
#: ⚠️ `prospect` 是**基準受眾**：它失敗＝整條 agent 路徑組不起來（啟動紅或 fail-soft
#: 停用，語義見 `_init_agent_runtime` 的外層 except，⛔ 不變）。其餘受眾失敗只跳過自己。
#: tenant 缺席是刻意的——它沒有 git 正本（`canon/` 只有 prospect／property_manager），
#: `AGENT_TURN_SPEC` 也永不對它開鍵。
_AGENT_BASELINE_AUDIENCE = "prospect"
_AGENT_OUTLINE_AUDIENCES = (_AGENT_BASELINE_AUDIENCE, "property_manager")


def _make_attempt_sink(path):
    """`AGENT_ATTEMPT_LOG_PATH` → 每筆 attempt 追加一行 JSON（加 `ts`）；未設回 None。
    寫檔失敗只 warning（runtime 端本來就吞 sink 例外），⛔ 不影響回合。"""
    if not path:
        return None
    import json as _json, time as _time
    def _sink(record):
        try:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(_json.dumps({"ts": round(_time.time(), 3), **record}, ensure_ascii=False) + "\n")
        except Exception:  # noqa: BLE001
            print("⚠️ [agent] attempt sink 寫檔失敗", file=sys.stderr)
    return _sink

def _wrap_verifier_observe_only(runtime, attempt_sink):
    """把解析後的 `AGENT_VERIFIER_MODE` **交給 Verifier**，並守住只准配 mock 的組態。

    ⚠️ W6-b3 之後這裡只是**相容層**：⛔ 不再包 `verify()`、⛔ 不再翻判定
    （security-reviewer r1 F1——`verify()` 是短路的，外層翻 `ok=False`⇒`ok=True` 會讓
    先命中的引用類把機敏類整段跳過，翻出來的 `ok=True` 不代表機敏類看過）。
    模式感知在 `OutputVerifier.verify()` 內部。

    ⚠️ 旗的解析走 `services.agent.health.verifier_mode()`（**唯一讀值點**，含相容舊旗
    `AGENT_VERIFIER_OBSERVE_ONLY`）——健檢印的與這裡判的必須是同一個答案，
    ⛔ 不各寫一份解析。

    守衛（F3，看**解析後**的 mode，⛔ 不綁舊 env 字面）：
      * `observe_only`（連機敏類都不擋）配非 mock ⇒ 啟動 raise；
      * `grounding_observe`（引用類觀察、機敏類照擋）配非 mock ⇒ **不阻起**，
        由健檢 `premise.red_flags` 記紅（`health.compute_agent_health`）。
    """
    from services.agent.health import verifier_mode

    mode = verifier_mode()
    runtime.verifier.mode = mode   # 值域外會 raise（`OutputVerifier.mode` setter）
    if mode == "enforce":
        return
    mock_on = (os.getenv("USE_MOCK_JGB_API") or "").strip().lower() in ("1", "true", "yes", "on")
    if mode == "observe_only":
        if not mock_on:
            raise RuntimeError(
                "AGENT_VERIFIER_MODE=observe_only（含相容旗 AGENT_VERIFIER_OBSERVE_ONLY）"
                "只准在 USE_MOCK_JGB_API=true 下使用"
            )
        print("ℹ️ [agent] AGENT_VERIFIER_MODE=observe_only：Verifier 全類只觀察不擋"
              "（含機敏類；DSP-040 相容旗語義，只准配替身）", file=sys.stderr)
        return
    print("ℹ️ [agent] AGENT_VERIFIER_MODE=grounding_observe：引用解析與涵蓋類只記錄到 "
          "verdict.observed，極性類與機敏類照擋（DSP-040 正式組態）"
          + ("" if mock_on else "　⚠️ 非 mock：健檢 premise.red_flags 會記紅"),
          file=sys.stderr)

async def _init_agent_runtime(app: FastAPI) -> None:
    """建 `app.state.agent_runtime`／`agent_outlines`／`agent_indexes`／`outline_resolver`／`shadow_runner`。

    design 元件 5：大綱超出 token 預算 ⇒ 啟動紅；Verifier 自證失敗 ⇒ 啟動紅（bootstrap）。
    但 agent 路徑在業主未跑 migration（`knowledge_base.outline_approved_by`）前組不起來，
    ⛔ 不能因此讓舊鏈也起不來 ⇒ 只在 `_agent_configured()` 為真時才把失敗升成啟動紅。

    DSP-037／S1b：**逐受眾**組（`_AGENT_OUTLINE_AUDIENCES`）。非基準受眾（pm）的正本
    缺檔／載入失敗 ⇒ **只跳過它**、記 warning，⛔ 不影響 prospect、⛔ 不 raise；
    它的 `agent.turn` 隨後由門面 fail-closed 成 `AGENT_UNAVAILABLE`（⛔ 不改塞 prospect 大綱）。
    """
    app.state.agent_runtime = None
    app.state.agent_outline = None
    app.state.agent_outlines = {}
    app.state.agent_indexes = {}
    app.state.outline_resolver = None
    app.state.shadow_runner = None
    try:
        import asyncio

        from services.agent import bootstrap as _agent_bootstrap
        from services.agent import outline as _agent_outline_mod
        from services.agent.canon.canon_assembler import get_canon as _get_canon
        from services.agent.canon.candidate_selector import CandidateSelector as _CandidateSelector
        from services.agent.canon.fine_index import EmbeddingUtilsBackend as _EmbeddingUtilsBackend
        from services.agent.canon.fine_index import FineIndex as _FineIndex
        from services.agent.canon.fine_index import PREPARE_TOTAL_TIMEOUT_S as _PREPARE_TOTAL_TIMEOUT_S
        from services.agent.canon.fine_index import register_index as _register_index
        from services.llm_provider import get_llm_provider as _get_llm_provider

        outlines: dict = {}
        indexes: dict = {}
        selectors: dict = {}
        for _audience in _AGENT_OUTLINE_AUDIENCES:
            try:
                _doc = await _agent_outline_mod.build_audience_outline(_audience, _mcp_kb_pool)
                _agent_outline_mod.check_budget(
                    _doc, _agent_outline_mod.default_token_limit(_audience))
            except Exception as e:  # noqa: BLE001
                if _audience == _AGENT_BASELINE_AUDIENCE:
                    raise           # 基準受眾失敗 ⇒ 交外層決定啟動紅／fail-soft（語義不變）
                print(f"⚠️ [agent] {_audience} 大綱未組成，跳過該受眾"
                      f"（agent.turn 對它回 AGENT_UNAVAILABLE）：{type(e).__name__}: {e}")
                continue

            # 任務 4.1（Plan §2.1-6）：細目索引——`register_canon(<audience>, …)` 已在
            # `build_audience_outline` 內完成，這裡只取已註冊的那份 `CanonDoc` 來 `prepare`。
            # `wait_for` 逾時 ⇒ 索引停在 `absent`（`prepare` 只在完成或 `_discard` 時改狀態，
            # 取消不留半份）；⛔ 不掛啟動、⛔ 不因此另加 API 把 `absent` 改寫成 `not_ready`——
            # 兩者對 selector／health 是同一種待遇（非 ready）。
            _canon = _get_canon(_audience)
            _index = _FineIndex(_EmbeddingUtilsBackend())
            try:
                await asyncio.wait_for(_index.prepare(_canon), _PREPARE_TOTAL_TIMEOUT_S)
            except Exception as e:  # noqa: BLE001 — 涵蓋 asyncio.TimeoutError 與其他失敗，皆 fail-soft
                print(f"⚠️ [agent] {_audience} 細目索引 prepare 失敗"
                      f"（state={_index.state}）：{type(e).__name__}: {e}")
            _register_index(_audience, _index)
            outlines[_audience] = _doc
            indexes[_audience] = _index
            selectors[_audience] = _CandidateSelector(_index)

        outline_doc = outlines[_AGENT_BASELINE_AUDIENCE]
        index = indexes[_AGENT_BASELINE_AUDIENCE]
        # ⚠️ `candidate_selector=`（單數）留給既有的單一受眾接線與影子工廠；
        #    `candidate_selectors=`（複數）是**依受眾取用**的權威對照表
        #    （`AgentRuntime._selector_for`：對照表非空時它說了算，⛔ 不跨受眾回退）。
        candidate_selector = selectors[_AGENT_BASELINE_AUDIENCE]
        provider = _get_llm_provider()

        # 開發用：`AGENT_ATTEMPT_LOG_PATH` 設了就把每次嘗試（草稿句＋refs＋Verifier 判定＋解析錯誤）
        # 追加寫成 JSONL——W6 口語穩定度量測要看「什麼被拒」。預設不設＝關；⛔ 正式環境不設
        # （被拒草稿可能含錯誤的個資陳述，設計上不進 trace／不外送，見 runtime._emit_attempt）。
        attempt_sink = _make_attempt_sink(os.getenv("AGENT_ATTEMPT_LOG_PATH"))
        runtime = _agent_bootstrap.build_runtime(app.state.db_pool, provider, _mcp_registry,
                                                 outline_doc=outline_doc,
                                                 candidate_selector=candidate_selector,
                                                 candidate_selectors=selectors,
                                                 attempt_sink=attempt_sink)
        # W6-b3：把解析後的 `AGENT_VERIFIER_MODE` 交給 Verifier（模式感知在 `verify()` 內部）；
        # `observe_only` 只准配 `USE_MOCK_JGB_API=true`（否則 raise），`grounding_observe`
        # 配真 API 不阻起、由健檢 `premise.red_flags` 記紅。被觀察而未擋的類別記在
        # `verdict.observed`，隨 attempt log 落地（`AGENT_ATTEMPT_LOG_PATH` 有設時）。
        _wrap_verifier_observe_only(runtime, attempt_sink)
        app.state.agent_outline = outline_doc       # 相容：舊呼叫端仍讀單數＝prospect
        app.state.agent_outlines = outlines
        app.state.agent_indexes = indexes
        app.state.outline_resolver = _agent_outline_mod.make_outline_resolver(dict(outlines))
        app.state.agent_runtime = runtime
        try:
            from services.agent.shadow import ShadowRunner as _ShadowRunner   # 任務 4.1
            app.state.shadow_runner = _ShadowRunner(
                lambda readonly_view: _agent_bootstrap.build_runtime(
                    app.state.db_pool, provider, _mcp_registry, outline_doc=outline_doc,
                    candidate_selector=candidate_selector, candidate_selectors=selectors,
                    readonly_view=readonly_view),
                app.state.db_pool)
        except ImportError:
            print("ℹ️ [agent] ShadowRunner 尚未落地（4.1），影子模式停用")
        print(f"✅ agent runtime 已初始化（rules_sha={runtime.rules_sha[:12]} outline_sha={runtime.outline_sha[:12]} "
              f"sections={len(outline_doc.sections)} tokens={outline_doc.token_count} "
              f"index_state={index.state} audiences={sorted(outlines)}）")
    except Exception as e:  # noqa: BLE001
        if _agent_configured():
            raise RuntimeError(f"agent 路徑已啟用但組裝失敗（啟動紅）：{type(e).__name__}: {e}") from e
        print(f"⚠️ [agent] runtime 未初始化（agent 開關皆關，fail-soft）：{type(e).__name__}: {e}")


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

    # agent 路徑（agentic-mcp-orchestration 2.2／design 元件 8）：runtime／大綱／影子。
    await _init_agent_runtime(app)

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
# registry 與 deps 一律建（agent 路徑 2.2 也用同一份 registry——design 元件 2「實作一份」）；
# 只有 MCP server／Mount 受 SDK 可用性左右。
_mcp_kb_pool = _mcp_facade.LazyPsycopg2Pool()
_mcp_deps = _mcp_facade.FacadeDeps(
    get_db_pool=lambda: getattr(app.state, "db_pool", None),
    get_kb_pool=lambda: _mcp_kb_pool,
    get_retriever=_get_mcp_retriever,
    stage=_mcp_facade.current_stage(),
    get_app=lambda: app,                                                       # 2.6 agent.turn
    get_outline_resolver=lambda: getattr(app.state, "outline_resolver", None),  # 3.2／kb.get("outline:*")
)
_mcp_registry = _mcp_facade.build_registry(_mcp_deps)
app.state.tool_registry = _mcp_registry
if _mcp_sdk_ok:
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
