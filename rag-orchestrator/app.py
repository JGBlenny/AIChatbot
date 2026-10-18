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
from services.unclear_question_manager import UnclearQuestionManager
from services.cache_service import CacheService

# 導入路由
from routers import unclear_questions, vendors, knowledge_import, knowledge_export, knowledge_generation, cache, videos, images, business_types, document_converter, target_user_config, forms, api_endpoints, lookup, loops, loop_knowledge, system_health
from routers import platform_sop  # ⚠️ 平台管理員的 SOP 範本後台 CRUD（15 條路由）。
#    ⛔ **它不是對話鏈的一部分**——2026-09-11 砍舊鏈時被誤刪，同日還原。
#    誤刪原因：分桶時把它列為「舊線進入點」，依據是檔名有 sop，⛔ 不是依據它做什麼。
#    後台的 PlatformSOPView／PlatformSOPEditView 兩頁靠它；業者的
#    `/vendors/{id}/sop/copy-category/{platform_category_id}` 也要平台分類存在才有得複製。
from routers import ocr_mapping  # documind-ocr-mapping：DocuMind OCR → JGB 欄位草稿（同步端點）
from routers import agent as agent_router  # agentic-mcp-orchestration 1.8：/api/v1/agent/openapi.json・/health

# 全局變數
db_pool: Pool = None
unclear_question_manager: UnclearQuestionManager = None
cache_service: CacheService = None


def _agent_configured() -> bool:
    """任一 agent 開關為真 ⇒ agent 路徑「被使用」⇒ 組裝失敗要啟動紅；否則 fail-soft 只警告。

    🔴 2026-09-12 措辭更正：前一版寫「任一開關**有值**」，權威那支的 docstring
    卻明寫「⚠️ **不是**『任一有值』」——三把鍵（`AGENT_AUDIENCES`／
    `AGENT_SHADOW_AUDIENCES`／`AGENT_TURN_ENABLED`）是 `strip()` 後**不在
    `{"", "0", "false", "False"}`** 才算真。`AGENT_TURN_ENABLED=false` 有值但為假。
    （另更正一個錯字：「路徯」→「路徑」。）

    ⚠️ 薄別名（任務 4.1）：判準的**唯一權威**已搬到
    `services.agent.mcp_facade.agent_configured()`（health 也讀那一份，
    ⛔ 不在此重寫第二套判準）；名稱保留在此供既有測試沿用。
    """
    from services.agent.mcp_facade import agent_configured as _mcp_agent_configured
    return _mcp_agent_configured()


#: 啟動時要組大綱＋索引的受眾，**依序**（DSP-037／S1b）。
#: ⚠️ `prospect` 是**基準受眾**：它失敗＝整條 agent 路徑組不起來（啟動紅或 fail-soft
#: 停用，語義見 `_init_agent_runtime` 的外層 except，⛔ 不變）。其餘受眾失敗只跳過自己。
#: tenant 缺席是刻意的——正本（`canon/jgb/`）裡沒有任何 `target_user` 含 tenant 的細目，
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

    ⚠️ 旗的解析走 `services.agent.health.verifier_mode()`（**唯一讀值點**，⛔ 已不含舊旗
    `AGENT_VERIFIER_OBSERVE_ONLY` 的映射，2026-09-10 除役）——健檢印的與這裡判的必須
    是同一個答案，⛔ 不各寫一份解析。舊旗若仍被設定，本函式在啟動時印一次警告並忽略。

    守衛（F3，看**解析後**的 mode，⛔ 不綁舊 env 字面）：
      * `observe_only`（連機敏類都不擋）配非 mock ⇒ 啟動 raise；
      * `grounding_observe`（引用類觀察、機敏類照擋）配非 mock ⇒ **不阻起**，
        由健檢 `premise.red_flags` 記紅（`health.compute_agent_health`）。
    """
    from services.agent.health import verifier_mode, AGENT_VERIFIER_OBSERVE_ONLY_ENV

    if os.getenv(AGENT_VERIFIER_OBSERVE_ONLY_ENV) is not None:
        print(
            f"⚠️ [agent] {AGENT_VERIFIER_OBSERVE_ONLY_ENV} 已無效，請改用 AGENT_VERIFIER_MODE"
            "（本次啟動已忽略此舊名）",
            file=sys.stderr,
        )

    mode = verifier_mode()
    runtime.verifier.mode = mode   # 值域外會 raise（`OutputVerifier.mode` setter）
    if mode == "enforce":
        return
    mock_on = (os.getenv("USE_MOCK_JGB_API") or "").strip().lower() in ("1", "true", "yes", "on")
    if mode == "observe_only":
        if not mock_on:
            raise RuntimeError(
                "AGENT_VERIFIER_MODE=observe_only 只准在 USE_MOCK_JGB_API=true 下使用"
            )
        print("ℹ️ [agent] AGENT_VERIFIER_MODE=observe_only：Verifier 全類只觀察不擋"
              "（含機敏類；DSP-040 相容旗語義，只准配替身）", file=sys.stderr)
        return
    print("ℹ️ [agent] AGENT_VERIFIER_MODE=grounding_observe：引用解析與涵蓋類只記錄到 "
          "verdict.observed，極性類與機敏類照擋（DSP-040 正式組態）"
          + ("" if mock_on else "　⚠️ 非 mock：健檢 premise.red_flags 會記紅"),
          file=sys.stderr)

#: 開機那次 prepare 逾時後，背景重建的時限（秒）。正式機實測約需 3～4 分鐘。
INDEX_BACKGROUND_PREPARE_TIMEOUT_S = 900.0


async def _prepare_index_in_background(index, canon) -> None:
    """開機 prepare 逾時後在背景重建細目索引；成功或失敗都印一行（fail-soft，⛔ raise）。"""
    import asyncio

    try:
        await asyncio.wait_for(index.prepare(canon), INDEX_BACKGROUND_PREPARE_TIMEOUT_S)
        print(f"✅ [agent] 細目索引背景重建完成（state={index.state}）")
    except Exception as e:  # noqa: BLE001 — fail-soft，與開機那次同待遇
        print(f"⚠️ [agent] 細目索引背景重建失敗（state={index.state}）：{type(e).__name__}: {e}")


async def _init_agent_runtime(app: FastAPI) -> None:
    """建 `app.state.agent_runtime`／`agent_audiences`／`agent_indexes`／`outline_resolver`／`shadow_runner`。

    design 元件 5：啟動預算超限 ⇒ 啟動紅；Verifier 自證失敗 ⇒ 啟動紅（bootstrap）。
    但 agent 路徑在業主未跑 migration（`knowledge_base.outline_approved_by`）前組不起來，
    ⛔ 不能因此讓舊鏈也起不來 ⇒ 只在 `_agent_configured()` 為真時才把失敗升成啟動紅。

    啟動只驗預算、不預組任何受眾的整份篩選結果——`load_canon_or_die` →
    `register_canon` → `FineIndex.prepare` 之後，逐受眾只用 `_STATIC_TOC_IDENTITY`
    的靜態身分跑一次 `check_turn_budget(build_canon_sections(canon, identity,
    ids=<該受眾 canon_visible 為真的全部細目 id>), toc, …)`——**餵入集合＝可見已審
    全集**（⛔ 不是 `_axes_visible` 全集、⛔ 不是每回合 K 個候選），只為驗證「這個
    受眾在啟動時量測到的 K 上界／toc token 沒有超過預算」；每回合真正的候選節由
    `runtime._select_outline` 每回合從正本現組。通過的受眾進 `app.state.agent_audiences`
    （`frozenset`）——**這是唯一的權威旗標**。

    DSP-037／S1b：**逐受眾**組（`_AGENT_OUTLINE_AUDIENCES`）。非基準受眾（pm）失敗
    ⇒ **只跳過它**、記 warning，⛔ 不影響 prospect、⛔ 不 raise；它的 `agent.turn`
    隨後由門面 fail-closed 成 `AGENT_UNAVAILABLE`。

    DSP-058／9.6 S3：**正本只載一次、索引只建一次**（`canon/jgb/` 一份）——兩個受眾
    的 `register_index`／`selectors` 都指向**同一個** `FineIndex`（同一份正本、同一批
    向量）。正本載入失敗＝整條 agent 路徑不可用 ⇒ 交外層 except 決定啟動紅／fail-soft
    （⛔ 不逐受眾各自 fail-soft，那會讓「正本壞了」被降級成「某個受眾跳過」）。
    """
    app.state.agent_runtime = None
    app.state.shadow_runner = None
    app.state.agent_audiences = frozenset()
    app.state.agent_indexes = {}
    app.state.outline_resolver = None
    try:
        import asyncio

        from services.agent import bootstrap as _agent_bootstrap
        from services.agent import outline as _agent_outline_mod
        from services.agent.canon.canon_assembler import build_canon_sections as _build_canon_sections
        from services.agent.canon.canon_assembler import build_canon_toc as _build_canon_toc
        from services.agent.canon.canon_assembler import canon_visible as _canon_visible
        from services.agent.canon.canon_assembler import load_canon_or_die as _load_canon_or_die
        from services.agent.canon.canon_assembler import register_canon as _register_canon
        from services.agent.canon.canon_assembler import resolve_canon_dir as _resolve_canon_dir
        from services.agent.canon.candidate_selector import CandidateSelector as _CandidateSelector
        from services.agent.canon.fine_index import EmbeddingUtilsBackend as _EmbeddingUtilsBackend
        from services.agent.canon.fine_index import FineIndex as _FineIndex
        from services.agent.canon.fine_index import PREPARE_TOTAL_TIMEOUT_S as _PREPARE_TOTAL_TIMEOUT_S
        from services.agent.canon.fine_index import register_index as _register_index
        from services.agent.identity import Identity as _Identity
        from services.llm_provider import get_llm_provider as _get_llm_provider
        from services.llm_provider import agent_endpoint_host as _agent_endpoint_host
        from services.llm_provider import build_agent_provider_from_env as _build_agent_provider_from_env

        passed_audiences: set = set()
        indexes: dict = {}
        selectors: dict = {}

        # DSP-058：一份正本、一次載入（失敗 ⇒ 整條 agent 路徑不可用，交外層 except）。
        _canon = _load_canon_or_die(_resolve_canon_dir())
        _register_canon(_canon)

        # 任務 4.1（Plan §2.1-6）：細目索引——對**整份正本**建一次（兩受眾共用）。
        # `wait_for` 逾時 ⇒ 索引停在 `absent`（`prepare` 只在完成或 `_discard` 時改狀態，
        # 取消不留半份）；⛔ 不掛啟動、⛔ 不因此另加 API 把 `absent` 改寫成 `not_ready`——
        # 兩者對 selector／health 是同一種待遇（非 ready）。
        _index = _FineIndex(_EmbeddingUtilsBackend())
        try:
            await asyncio.wait_for(_index.prepare(_canon), _PREPARE_TOTAL_TIMEOUT_S)
        except Exception as e:  # noqa: BLE001 — 涵蓋 asyncio.TimeoutError 與其他失敗，皆 fail-soft
            print(f"⚠️ [agent] 細目索引 prepare 失敗（state={_index.state}）：{type(e).__name__}: {e}")
            # 2026-10-15 正式機實測：embedding 約 9.5 次／秒，2,082 項要 3～4 分鐘，開機 60 秒
            # 必逾時且原本不再重試 ⇒ 整段上線期間都只有目錄（toc-only）。改為開機後在背景重建，
            # ⛔ 不延長開機阻塞；建好後同一個 index 物件轉 ready，selector 每回合讀 state 即生效。
            app.state.agent_index_prepare_task = asyncio.create_task(
                _prepare_index_in_background(_index, _canon)
            )

        for _audience in _AGENT_OUTLINE_AUDIENCES:
            try:
                _static_identity = _Identity(**_agent_outline_mod._STATIC_TOC_IDENTITY[_audience])
                _vbt = _agent_outline_mod.resolve_vendor_business_types(_static_identity)
                # 餵入＝該受眾 canon_visible 為真的全部細目 id（⛔ 不是 _axes_visible
                # 全集——未審 id 會觸發 build_canon_sections 的 F1 raise；⛔ 不是每回合
                # K 個候選——`check_turn_budget` 本身已經只取最大 K 個節之和）。
                _visible_ids = [
                    fine.id for fine in _canon.fines()
                    if _canon_visible(_static_identity, fine, vendor_business_types=_vbt)
                ]
                _sections = _build_canon_sections(
                    _canon, _static_identity, _visible_ids, vendor_business_types=_vbt
                )
                _toc = _build_canon_toc(_canon, _static_identity, vendor_business_types=_vbt)
                _budget = _agent_outline_mod.check_turn_budget(
                    _sections, _toc,
                    k_limit=_agent_outline_mod.default_k_token_limit(_audience),
                    toc_limit=_agent_outline_mod.default_toc_token_limit(_audience),
                )
                print(f"ℹ️ [agent] {_audience} 大綱預算：k_upper={_budget.k_upper} "
                      f"toc_tokens={_budget.toc_tokens} toc_lines={_budget.toc_lines}")
            except Exception as e:  # noqa: BLE001
                if _audience == _AGENT_BASELINE_AUDIENCE:
                    raise           # 基準受眾失敗 ⇒ 交外層決定啟動紅／fail-soft（語義不變）
                print(f"⚠️ [agent] {_audience} 視圖未組成，跳過該受眾"
                      f"（agent.turn 對它回 AGENT_UNAVAILABLE）：{type(e).__name__}: {e}")
                continue

            # ⚠️ 兩受眾指向**同一個** index 物件（同一份正本）：`index_registry_states`
            # 的 entries／content_keys／prepared_sha 因此兩受眾相同，⛔ 不是受眾覆蓋率指標。
            _register_index(_audience, _index)
            passed_audiences.add(_audience)
            indexes[_audience] = _index
            selectors[_audience] = _CandidateSelector(_index)

        agent_audiences = frozenset(passed_audiences)
        index = indexes[_AGENT_BASELINE_AUDIENCE]   # ＝ `_index`（兩受眾共用同一份）
        # ⚠️ `candidate_selector=`（單數）留給既有的單一受眾接線與影子工廠；
        #    `candidate_selectors=`（複數）是**依受眾取用**的權威對照表
        #    （`AgentRuntime._selector_for`：對照表非空時它說了算，⛔ 不跨受眾回退）。
        candidate_selector = selectors[_AGENT_BASELINE_AUDIENCE]
        # plan-oss-wiring-step1-20261018 §3.1／§3.2：設了對話端點（`AGENT_LLM_BASE_URL`＋
        # `AGENT_LLM_API_KEY_FILE`）⇒ 對話專用 provider，並開推理清理；兩者皆未設 ⇒ `None`
        # ⇒ 照舊 `get_llm_provider()`、清理關閉（正式機路徑逐位不變）。組態錯誤的 raise 訊息
        # 只含原因代碼與路徑（下方外層 except 會印 `{e}`）。⛔ 印金鑰或其長度。
        _agent_provider = _build_agent_provider_from_env()
        provider = _agent_provider or _get_llm_provider()
        clean = _agent_provider is not None
        _agent_model = os.getenv("AGENT_MODEL") or "（未設）"
        if clean:
            _host = _agent_endpoint_host() or "?"
            _label = "Bedrock" if ("bedrock" in _host and _host.endswith(".amazonaws.com")) else "自訂端點"
            print(f"ℹ️ [agent] 對話端點：{_label}（{_host}） AGENT_MODEL={_agent_model} 推理清理=開")
        else:
            print(f"ℹ️ [agent] 對話端點：預設（get_llm_provider） AGENT_MODEL={_agent_model}")

        # 開發用：`AGENT_ATTEMPT_LOG_PATH` 設了就把每次嘗試（草稿句＋refs＋Verifier 判定＋解析錯誤）
        # 追加寫成 JSONL——W6 口語穩定度量測要看「什麼被拒」。預設不設＝關；⛔ 正式環境不設
        # （被拒草稿可能含錯誤的個資陳述，設計上不進 trace／不外送，見 runtime._emit_attempt）。
        attempt_sink = _make_attempt_sink(os.getenv("AGENT_ATTEMPT_LOG_PATH"))
        runtime = _agent_bootstrap.build_runtime(app.state.db_pool, provider, _mcp_registry,
                                                 candidate_selector=candidate_selector,
                                                 candidate_selectors=selectors,
                                                 attempt_sink=attempt_sink,
                                                 clean_llm_output=clean)
        # W6-b3：把解析後的 `AGENT_VERIFIER_MODE` 交給 Verifier（模式感知在 `verify()` 內部）；
        # `observe_only` 只准配 `USE_MOCK_JGB_API=true`（否則 raise），`grounding_observe`
        # 配真 API 不阻起、由健檢 `premise.red_flags` 記紅。被觀察而未擋的類別記在
        # `verdict.observed`，隨 attempt log 落地（`AGENT_ATTEMPT_LOG_PATH` 有設時）。
        _wrap_verifier_observe_only(runtime, attempt_sink)
        app.state.agent_audiences = agent_audiences
        app.state.agent_indexes = indexes
        app.state.outline_resolver = _agent_outline_mod.make_outline_resolver()
        app.state.agent_runtime = runtime
        try:
            from services.agent.shadow import ShadowRunner as _ShadowRunner   # 任務 4.1
            app.state.shadow_runner = _ShadowRunner(
                lambda readonly_view: _agent_bootstrap.build_runtime(
                    app.state.db_pool, provider, _mcp_registry,
                    candidate_selector=candidate_selector, candidate_selectors=selectors,
                    readonly_view=readonly_view, clean_llm_output=clean),
                app.state.db_pool)
        except ImportError:
            print("ℹ️ [agent] ShadowRunner 尚未落地（4.1），影子模式停用")
        print(f"✅ agent runtime 已初始化（rules_sha={runtime.rules_sha[:12]} outline_sha={_canon.canon_sha256[:12]} "
              f"canon_sha={_canon.canon_sha256[:12]} "
              f"index_state={index.state} audiences={sorted(agent_audiences)}）"
              "（各受眾 k_upper／toc_tokens／toc_lines 見上方逐受眾大綱預算行）")
    except Exception as e:  # noqa: BLE001
        if _agent_configured():
            raise RuntimeError(f"agent 路徑已啟用但組裝失敗（啟動紅）：{type(e).__name__}: {e}") from e
        print(f"⚠️ [agent] runtime 未初始化（agent 開關皆關，fail-soft）：{type(e).__name__}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命週期管理"""
    # 啟動時初始化
    global db_pool, unclear_question_manager, cache_service

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
    unclear_question_manager = UnclearQuestionManager(db_pool)
    print("✅ 未釐清問題管理器已初始化")

    # 初始化緩存服務
    cache_service = CacheService()

    # 新線自有的會話狀態層（舊鏈隔離 S3／D 案）：取代舊 `ConversationalEngine`
    # 的狀態子集，新線只需要 get_state/start/save/close 四個方法（見
    # services/agent/session_persistence.py 檔頭的取捨說明）。
    from services.agent.session_persistence import AgentSessionStore
    agent_session_store = AgentSessionStore(db_pool=db_pool)
    print("✅ agent 會話狀態層已初始化（session_persistence：取代舊引擎狀態子集）")

    # 將服務注入到 app.state
    app.state.db_pool = db_pool
    app.state.unclear_question_manager = unclear_question_manager
    app.state.cache_service = cache_service
    app.state.agent_session_store = agent_session_store

    # agent 路徑（agentic-mcp-orchestration 2.2／design 元件 8）：runtime／大綱／影子。
    await _init_agent_runtime(app)
    # 2026-10-15 選項 A：舊知識庫零列已審 ⇒ kb.search 不給模型（依資料狀態，重啟重判）。
    await _mcp_facade.gate_kb_search_on_reviewed_rows(_mcp_registry, db_pool)

    print("🎉 RAG Orchestrator 啟動完成！（含 Phase B 意圖建議 + agent 會話狀態層）")
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
    """`/mcp` 的**額度短路**（agentic-mcp-orchestration 1.7）；其餘路徑零觸碰。

    ⛔ **不 begin／finalize**：門面 `services/agent/mcp_facade.py` 是唯一寫入者
    （每次工具呼叫一列 `usage_events`，不變量 31）。這裡再落一次 ⇒ 一次呼叫兩列。
    身分與 key 屬性由 `McpServiceGate`（最外層 middleware）放進 `request.state`。

    ⚠️ **2026-09-11 舊鏈退役**：原本另有一條 `path == "/api/v1/message"` 的 REST 計量分支
    （一則訊息一列）。該端點已隨舊 REST 對話鏈刪除，但 middleware 跑在**路由之前**，
    分支因此仍會對 404 請求 `begin()`＋`quota_check()`＋`finalize("success", 404)`
    ——實測扣掉額度並寫下一列 `status='success'` 的事件，而該請求根本沒有服務產出
    （`vendor_id` 還取自請求 body ⇒ 可對任意業者扣額）。⇒ 整條移除。
    ⛔ 日後若重開 REST 入口，計量要重寫：**⛔ 不要在 middleware 層以路徑字串等值判斷**
    （字面量一改路徑就靜默停止計量，查無任何測試釘住它），改在端點內自記或用路由層判定。
    ⚠️ 另注意計費單位不同：REST 是一則訊息一列，MCP 是一次工具呼叫一列。
    """
    from services import usage_metering as _um
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
#      🔴 2026-09-12 更正：前一版註解寫「mcp==2.1.1 與 fastapi==0.104.1 相依衝突
#      （anyio<4 vs anyio>=4.9），故正式 image 目前未裝」——**那已經不成立**。
#      DSP-014 裁 A 升了 web stack：requirements.txt 現已釘 mcp==2.1.1、
#      fastapi 0.115.14／starlette 0.46／pydantic 2.13／anyio 4.15／uvicorn 0.52。
#      ⇒ `mcp_sdk_available()` 現在只是**防禦性守衛**（image 供裝出錯時讓三道閘
#      仍成立、工具面回 404，而不是整個 app 起不來），⛔ 不再代表「尚未安裝」。
#      正常部署下它必為可用；回不可用代表**供裝壞了**。
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
app.include_router(unclear_questions.router, prefix="/api/v1", tags=["unclear_questions"])
app.include_router(business_types.router, prefix="/api/v1", tags=["business_types"])  # Business Types (Read-only from config)
app.include_router(vendors.router, tags=["vendors"])  # Phase 1: Multi-Vendor Support
app.include_router(knowledge_import.router, tags=["knowledge_import"])  # Knowledge Import from LINE chats
app.include_router(knowledge_export.router, tags=["knowledge_export"])  # Knowledge Export to Excel
app.include_router(knowledge_generation.router, prefix="/api/v1", tags=["knowledge_generation"])  # AI Knowledge Generation
app.include_router(cache.router, tags=["cache"])  # Cache Management (事件驅動 + TTL 混合策略)
app.include_router(videos.router, tags=["videos"])  # Video Upload & Management (S3 Storage)
app.include_router(images.router, tags=["images"])  # Image Upload & Recognition (修繕圖片上傳)
app.include_router(document_converter.router, tags=["document_converter"])  # Document Converter (Word/PDF -> Q&A)
app.include_router(target_user_config.router, tags=["target_user_config"])  # Target User Configuration (用戶類型配置)
app.include_router(forms.router, prefix="/api/v1", tags=["forms"])  # Form Management (表單管理)
app.include_router(api_endpoints.router, prefix="/api/v1", tags=["api_endpoints"])  # API Endpoints Management (API 端點管理)
app.include_router(lookup.router, tags=["lookup"])  # Lookup Table System (通用查詢系統)
app.include_router(loops.router, prefix="/api/v1/loops", tags=["loops"])  # Knowledge Completion Loop Management (知識完善迴圈管理)
app.include_router(loop_knowledge.router, prefix="/api/v1/loops", tags=["loop_knowledge"])  # Loop Knowledge Review API (知識審核 API)
app.include_router(system_health.router, tags=["system_health"])  # Pipeline Health Dashboard (系統健康檢查)
app.include_router(platform_sop.router, tags=["platform_sop"])  # Platform SOP Template Management（2026-09-11 還原）
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
