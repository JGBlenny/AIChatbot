"""integration:合約異動樹全流程（contract-conversational-facets 任務 5.1 / R2.1–2.4, R2.7）。

真 DB（config＋系統脈絡＋persona 種子）＋真 ConversationalEngine＋真 APICallHandler＋
真 formatter（face 貫穿 → build_change_exit_facts）；jgb2 端點 stub、brain 腳本化。

流程驗證：
  - 追問「要改什麼」→ 鎖定合約 → 三出口 facts 依 status 決定性分流（1/2/8）；
  - 已簽分支收集申請書槽位（缺 → 追問；齊 → 收斂），收斂底稿含出口 facts、
    system_md 含申請書三段骨架（可抄錄產出的素材面；合成文字斷言屬 5.2 e2e）；
  - 轉歷史/刪除訴求走共用出口（歷史列 → 申請書 facts）。
無法連 DB → skip。
"""
import os

import pytest
from unittest.mock import AsyncMock, MagicMock


pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _force_mock_jgb(monkeypatch):
    # 僅在本檔測試執行期間生效：模組層 os.environ 會在全套收集時污染
    # 同進程的 e2e（真 jgb2 變 mock），改用 monkeypatch 隔離。
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")

_MIG = os.path.join(os.path.dirname(__file__), "..", "..", "..", "database", "migrations")
_SEEDS = ["split_base_system_context_extract_presales.sql",
          "add_contract_facet_categories.sql",
          "seed_domain_contract_system_context.sql",
          "add_contract_facet_categories_v2.sql",
          "seed_contract_facet_system_context.sql",
          "seed_contract_facet_configs.sql"]


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
    from services import conversational_rules as cr
    try:
        p = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=3)
    except Exception as e:
        pytest.skip(f"無法連 DB：{e}")
        return
    for name in _SEEDS:
        with open(os.path.join(_MIG, name), encoding="utf-8") as f:
            await p.execute(f.read())
    cc.reset_cache(); sc.reset_cache(); cr.reset_cache()
    yield p
    cc.reset_cache(); sc.reset_cache(); cr.reset_cache()
    await p.close()


class _Brain:
    def __init__(self, steps):
        self.steps, self.turn = steps, 0

    def conversational_step(self, rules, system_md, state, msg, faces=None):
        step = self.steps[min(self.turn, len(self.steps) - 1)]
        self.turn += 1
        return dict(step)


def _real_handler(row):
    """真實 APICallHandler＋stub jgb_contracts 端點（jgb 形狀 → 走真 formatter/face 分發）。

    參數感知（後端當裁判）：只有 contract_ids/keyword 真的對得上這列才回資料——
    否則回 0 筆。這使「槽位回答含數字（如日期 2027）觸發的切換探查」被正確拒絕、
    引擎回滾保留原合約（先搜後提交），與真 jgb2 行為一致。
    """
    from services.api_call_handler import APICallHandler
    handler = APICallHandler(db_pool=None)

    async def fake_contracts(**kwargs):
        ids = str(kwargs.get("contract_ids") or "")
        kw = str(kwargs.get("keyword") or "")
        hit = (ids == str(row["id"])) or (kw and kw in row["title"]) \
            or (not ids and not kw)
        return {"mapping": {}, "data": [row] if hit else []}

    handler.api_registry["jgb_contracts"] = fake_contracts
    return handler


def _engine(pool, brain, handler):
    from services.conversational_engine import ConversationalEngine
    from services import system_context as sc
    from services.conversational_rules import load_rules
    return ConversationalEngine(
        db_pool=pool, optimizer=brain, retriever=None,
        get_system_context=sc.get_system_context, rules_loader=load_rules,
        api_handler=handler)


def _row(status, **over):
    r = {"id": 83315, "title": "基隆物件", "status": status, "bit_status": 15,
         "is_history": 0, "date_start": 20260101, "date_end": 20270101,
         "rent": 20000, "to_user_connect": 1}
    r.update(over)
    return r


async def _cleanup(pool, sid):
    await pool.execute("DELETE FROM form_sessions WHERE session_id=$1", sid)


# ── 三出口 facts 依 status 決定性分流（真 formatter、face 貫穿，R2.2）──
@pytest.mark.req("contract-conversational-facets:2.2")
@pytest.mark.parametrize("status,marker", [
    (1, "可直接編輯"),
    (2, "取消簽約、退回「待發送」"),
    (8, "資料異動申請書"),
])
async def test_three_exit_facts_flow_by_status(pool, status, marker):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "合約異動")
    brain = _Brain([{"action": "converge", "converge_kind": "answer", "scope": "stay",
                     "extracted_fields": {"contract_ref": "基隆物件"}, "face": "合約異動"}])
    eng = _engine(pool, brain, _real_handler(_row(status)))
    sid = "it-exit-" + os.urandom(3).hex()
    try:
        d = await eng.prepare(sid, "u1", 7, "我想改基隆那份合約的租期", config=cfg, role_id="20151")
        assert d["kind"] == "converge"
        assert marker in d["grounding"]                    # builder facts 進收斂底稿
        assert "83315" in d["grounding"]                   # 底稿頭帶識別（id｜名稱）
    finally:
        await _cleanup(pool, sid)


# ── 追問「要改什麼」→ 鎖定 → 已簽分支收申請書槽位（缺→追問；齊→收斂）（R2.1, R2.4）──
@pytest.mark.req("contract-conversational-facets:2.4")
async def test_application_slot_collection_then_converge(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "合約異動")
    # 注意輪次：第 2 輪「83315 想改租期」帶明確編號 → 走確定性填槽直接收斂，不經 brain；
    # brain 只在第 1、3、4 輪被呼叫。
    brain = _Brain([
        # brain 第1次（第1輪）：訴求不明 → 追問要改什麼
        {"action": "ask", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {}, "next_question": "請問要修改合約的哪個項目？"},
        # brain 第2次（第3輪）：抽異動項目、申請書槽位缺 → 追問異動前後
        {"action": "ask", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {"change_item": "租期"},
         "next_question": "請提供異動前與異動後的內容？"},
        # brain 第3次（第4輪）：槽位齊 → 收斂產申請書內容
        {"action": "converge", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {"change_before": "租期至 2027/8/31",
                              "change_after": "租期至 2029/8/31"},
         "face": "合約異動"},
    ])
    eng = _engine(pool, brain, _real_handler(_row(8)))
    sid = "it-slots-" + os.urandom(3).hex()
    try:
        d1 = await eng.prepare(sid, "u1", 7, "我的合約想改內容", config=cfg, role_id="20151")
        assert d1["kind"] == "ask" and "哪個項目" in d1["answer"]      # 追問要改什麼

        d2 = await eng.prepare(sid, "u1", 7, "83315 想改租期", config=None, role_id="20151")
        assert d2["kind"] == "converge"
        assert "資料異動申請書" in d2["grounding"]                     # 已簽 → 申請書出口
        await eng._finalize_converge(d2)

        d3 = await eng.prepare(sid, "u1", 7, "那要怎麼申請？", config=None, role_id="20151")
        assert d3["kind"] == "ask" and "異動前" in d3["answer"]        # 槽位缺 → 追問

        d4 = await eng.prepare(sid, "u1", 7, "租期 2027/8/31 改 2029/8/31",
                               config=None, role_id="20151")
        assert d4["kind"] == "converge"
        await eng._finalize_converge(d4)
        state = await eng.get_state(sid)
        cf = state["collected_fields"]
        assert cf["contract_ref"] == "83315" and cf["change_item"] == "租期"
        assert cf["change_before"] and cf["change_after"]              # 槽位齊備入 state
        # 可抄錄產出素材面：脈絡帶申請書三段骨架＋提交指引（合成文字驗證屬 5.2 e2e）
        smd = d4["system_md"]
        for token in ("【申請書填寫內容】", "異動前", "異動後", "service@jgbsmart.com", "團隊擁有者"):
            assert token in smd, f"申請書骨架缺 token：{token}"
    finally:
        await _cleanup(pool, sid)


# ── 轉歷史/刪除訴求 → 共用出口（歷史列 → 申請書 facts，R2.7）──
@pytest.mark.req("contract-conversational-facets:2.7")
async def test_history_deletion_request_shared_exit(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "合約異動")
    brain = _Brain([{"action": "converge", "converge_kind": "answer", "scope": "stay",
                     "extracted_fields": {"contract_ref": "83315"}, "face": "合約異動"}])
    eng = _engine(pool, brain, _real_handler(_row(128, is_history=1)))
    sid = "it-hist-" + os.urandom(3).hex()
    try:
        d = await eng.prepare(sid, "u1", 7, "這份歷史合約想刪掉資料", config=cfg, role_id="20151")
        assert d["kind"] == "converge"
        assert "歷史合約" in d["grounding"]
        assert "資料異動申請書" in d["grounding"]          # 共用出口
        assert "可直接編輯" not in d["grounding"]
    finally:
        await _cleanup(pool, sid)
