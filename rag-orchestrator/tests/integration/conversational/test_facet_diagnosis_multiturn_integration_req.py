"""integration:合約診斷面向化多輪流程（真 DB + 真引擎 + mock jgb2 + 腳本化 brain）。

驗證 domain-conversational-facets（面向化三層 + 候選辨識 + 混合 grounding + 面向衍生 + scope 切換）
在**真實 DB（含 5 支種子）＋ 真 ConversationalEngine ＋ 真 get_system_context ＋ 真 _ground_by_api**
下的多輪行為；jgb2 走 mock（USE_MOCK_JGB_API），brain（conversational_step/合成 LLM）腳本化（無 OpenAI）。

前置（部署到測試 DB，冪等）：
  split_base_system_context_extract_presales.sql、add_contract_facet_categories.sql、
  seed_domain_contract_system_context.sql、seed_conversational_diagnosis_contract_rule.sql、
  backfill_contract_knowledge_diagnosis_category.sql；套用後清快取。
需 RUN_INTEGRATION=1 + 可連 DB；設定未就緒 → 自動 skip（不誤判失敗）。
"""
import os

import pytest
from unittest.mock import AsyncMock, MagicMock

# 本檔設計即走 mock jgb2（腳本化、決定性）；用硬設而非 setdefault——
# 在常駐容器（USE_MOCK_JGB_API=false 打真 API）跑時 setdefault 蓋不掉，會變成打真 API 的不決定性測試。
os.environ["USE_MOCK_JGB_API"] = "true"

pytestmark = pytest.mark.integration


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"), password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


@pytest.fixture
async def pool():
    import asyncpg
    from services import conversational_config as cc, system_context as sc
    try:
        p = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=3)
    except Exception as e:
        pytest.skip(f"無法連 DB：{e}")
        return
    cc.reset_cache(); sc.reset_cache()
    cfg = await cc.config_for_category(p, "狀態判斷")
    ok_ctx = await p.fetchval(
        "SELECT count(*) FROM knowledge_base WHERE category='系統脈絡' AND is_active "
        "AND ('系統合約'=ANY(categories) OR '狀態判斷'=ANY(categories))")
    if cfg is None or not ok_ctx:
        await p.close()
        pytest.skip("面向診斷設定未就緒（狀態判斷 config / 系統合約·狀態判斷 系統脈絡）；請套 5 支種子並清快取")
        return
    yield p
    await p.close()


class _Brain:
    """腳本化 brain：第1輪追問，之後收斂（帶 scope/face）。可覆寫 scope 以驗切換。"""
    def __init__(self, scope="stay", face="狀態判斷"):
        self.turn = 0
        self._scope, self._face = scope, face
        self.seen = {}

    def conversational_step(self, rules, system_md, state, msg, faces=None):
        self.turn += 1
        # 三層脈絡標記＝現行種子（seed_domain_contract_system_context.sql）的獨有語句：
        #   母『系統合約』＝12 里程碑表；子『狀態判斷』＝以系統判定為準（原始 bit_status 已改由 formatter 解碼，不再進脈絡）
        self.seen = {"faces": faces, "base": "金箍棒" in system_md,
                     "parent": "12 里程碑" in system_md, "child": "不要自行推斷操作條件" in system_md}
        if self.turn == 1:
            return {"action": "ask", "converge_kind": "answer", "extracted_fields": {},
                    "next_question": "請問哪一份合約？", "scope": "stay"}
        return {"action": "converge", "converge_kind": "answer",
                "extracted_fields": {"contract_ref": msg}, "scope": self._scope, "face": self._face}


def _engine(pool, brain, api_handler=None):
    from services.conversational_engine import ConversationalEngine
    from services import system_context as sc
    from services.conversational_rules import load_rules
    from services.api_call_handler import APICallHandler
    return ConversationalEngine(
        db_pool=pool, optimizer=brain, retriever=None,
        get_system_context=sc.get_system_context, rules_loader=load_rules,
        api_handler=api_handler or APICallHandler(db_pool=None))


async def _cleanup(pool, sid):
    await pool.execute("DELETE FROM form_sessions WHERE session_id=$1", sid)


# ── 多輪：模糊→追問→候選帶區別欄位；面向衍生 + 三層脈絡注入 ──
@pytest.mark.req("domain-conversational-facets:8.1")
async def test_multiturn_ambiguous_then_distinguishing_candidates(pool):
    from services import conversational_config as cc
    cc.reset_cache()
    cfg = await cc.config_for_category(pool, "狀態判斷")
    brain = _Brain()
    eng = _engine(pool, brain)
    sid = "it-cand-" + os.urandom(3).hex()
    try:
        d1 = await eng.prepare(sid, "u1", 7, "我的合約狀態怪怪的", config=cfg, role_id="20151")
        assert d1["kind"] == "ask"

        d2 = await eng.prepare(sid, "u1", 7, "套房", config=None, role_id="20151")
        assert d2["kind"] == "ask"        # mock 回多筆 → 列候選
        state = await eng.get_state(sid)
        labels = [c["label"] for c in (state.get("pending_candidates") or [])]
        assert len(labels) >= 2
        # 候選帶區別欄位（title｜date_start｜date_end，日期 Ymd→Y/m/d）
        assert all("｜" in lb for lb in labels)
        assert any("/" in lb for lb in labels)
        # 面向集合由 category_config 衍生、三層脈絡注入 brain
        # 面向集合由 category_config 衍生（contract-conversational-facets 上庫後擴為 6 面向，
        #   本測試意圖＝「集合有衍生且注入 brain」，不鎖面向數）
        assert "狀態判斷" in (brain.seen["faces"] or [])
        assert brain.seen["base"] and brain.seen["parent"] and brain.seen["child"]
    finally:
        await _cleanup(pool, sid)


# ── 單筆收斂：混合 grounding（API 現值）＋ 三層面向 system_md（真 get_system_context）──
@pytest.mark.req("domain-conversational-facets:5.3")
async def test_single_row_converges_with_hybrid_three_level_context(pool):
    from services import conversational_config as cc
    cc.reset_cache()
    cfg = await cc.config_for_category(pool, "狀態判斷")
    # 注入單筆 API 回傳（模擬真 jgb2 對 contract_ids 的過濾；mock 本身不過濾）
    handler = MagicMock()
    handler.execute_api_call = AsyncMock(return_value={
        "success": True, "data": {"data": [{"id": 678, "title": "信義區套房A", "bit_status": 47}]},
        "formatted_response": "狀態：bit_status=47（雙方簽名完成+已發點交+租客同意點交），月租 25,000"})
    brain = _Brain()
    brain.turn = 1  # 直接進收斂輪（已有識別）
    eng = _engine(pool, brain, api_handler=handler)
    sid = "it-conv-" + os.urandom(3).hex()
    try:
        d = await eng.prepare(sid, "u1", 7, "信義區套房 678 狀態", config=cfg, role_id="20151")
        assert d["kind"] == "converge"
        # 混合底稿：API 現值（bit_status=47）
        assert "bit_status=47" in d["grounding"]
        # 三層面向 system_md：base + 母共用(12 里程碑) + 子面向(以系統判定為準)
        smd = d["system_md"]
        assert "金箍棒" in smd and "12 里程碑" in smd and "不要自行推斷操作條件" in smd
    finally:
        await _cleanup(pool, sid)


# ── scope=switch：brain 判離題 → 關會話（供 chat.py 重路由）──
@pytest.mark.req("mid-session-switch:3.3")
async def test_scope_switch_closes_session(pool):
    from services import conversational_config as cc
    cc.reset_cache()
    cfg = await cc.config_for_category(pool, "狀態判斷")
    brain = _Brain(scope="switch")
    eng = _engine(pool, brain)
    sid = "it-switch-" + os.urandom(3).hex()
    try:
        await eng.prepare(sid, "u1", 7, "我的合約狀態怪怪的", config=cfg, role_id="20151")  # 起會話
        d2 = await eng.prepare(sid, "u1", 7, "其實我想問這個月帳單怎麼繳", config=None, role_id="20151")
        assert d2 is None  # scope=switch → 回 None（chat.py 落回重路由）
        # 會話已關（無 COLLECTING）
        n = await pool.fetchval(
            "SELECT count(*) FROM form_sessions WHERE session_id=$1 AND form_id='conversational' AND state='COLLECTING'",
            sid)
        assert n == 0
    finally:
        await _cleanup(pool, sid)
