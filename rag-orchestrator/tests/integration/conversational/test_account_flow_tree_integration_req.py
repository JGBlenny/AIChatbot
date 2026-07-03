"""integration:帳號面向全流程（account-conversational-facets 任務 4.1 / R2, R3, R4, R5）。

真 DB（種子＋知識批次已匯入）＋真引擎＋真 APICallHandler（jgb_contracts stub 參數感知）；
brain 腳本化。前置：account-knowledge-batch.json 已匯入 dev DB（掛面向知識是
category 收斂的資料源；未匯入時 grounding 斷言會失敗提示）。

驗證：註冊驗證兩輪分流→category 收斂（機制 facts 進底稿）；綁定異動→申請書
出口 token；團隊權限判因分流；登入排障候選路徑（物件名→列候選→選定→三分支）。
B.Bug 導客服屬 LLM 分流行為 → e2e 驗；此處驗其資料前提（脈絡含事故導客服條款）。
"""
import os

import pytest


pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _force_mock_jgb(monkeypatch):
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")

_MIG = os.path.join(os.path.dirname(__file__), "..", "..", "..", "database", "migrations")
_SEEDS = ["split_base_system_context_extract_presales.sql",
          "add_account_facet_categories.sql",
          "seed_account_facet_system_context.sql",
          "seed_account_facet_configs.sql"]


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
    n = await p.fetchval(
        "SELECT count(*) FROM knowledge_base WHERE categories && "
        "ARRAY['註冊驗證排障','帳號綁定異動','團隊成員權限']::text[] "
        "AND COALESCE(category,'') NOT IN ('對話規則','系統脈絡') AND is_active")
    if not n:
        pytest.skip("帳號知識批次未匯入（category 收斂無資料源）；先跑 import_facet_knowledge")
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


def _contract(**over):
    c = {"id": 84927, "title": "海大質感獨立套房", "status": 2, "bit_status": 3,
         "date_start": 20260101, "date_end": 20261231,
         "to_user_email": "tenant@example.com", "to_user_phone": "0912345678",
         "to_user_connect": 1, "is_tenant_registered": True,
         "to_user_login_email": "tenant@example.com"}
    c.update(over)
    return c


def _handler(contract_rows):
    from services.api_call_handler import APICallHandler
    handler = APICallHandler(db_pool=None)
    handler.jgb_api.use_mock = False

    async def fake_contracts(**kwargs):
        rows = contract_rows
        cid = kwargs.get("contract_ids")
        kw = kwargs.get("keyword")
        if cid:
            rows = [c for c in rows if str(c.get("id")) == str(cid)]
        elif kw:
            rows = [c for c in rows if kw in (c.get("title") or "")]
        return {"mapping": {}, "data": rows}

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


async def _cleanup(pool, sid):
    await pool.execute("DELETE FROM form_sessions WHERE session_id=$1", sid)


# ── 註冊驗證排障：兩輪分流 → category 收斂，機制 facts 進底稿（R2.1/R2.2）──
@pytest.mark.req("account-conversational-facets:2.2")
async def test_register_two_round_triage_then_category_grounding(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "註冊驗證排障")
    brain = _Brain([
        {"action": "ask", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {"symptom": "驗證碼一直失敗"},
         "next_question": "租客是用簡訊還是 Email 收驗證碼？"},
        {"action": "converge", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {"channel": "簡訊"}},
    ])
    eng = _engine(pool, brain, _handler([]))
    sid = "it-areg-" + os.urandom(3).hex()
    try:
        d1 = await eng.prepare(sid, "u1", 7, "租客說驗證碼一直打不對", config=cfg, role_id="20151")
        assert d1["kind"] == "ask"                                # 第一輪分流
        d2 = await eng.prepare(sid, "u1", 7, "簡訊", config=None, role_id="20151")
        assert d2["kind"] == "converge"
        g = d2["grounding"]
        # category 收斂資料源＝掛面向知識（target_user 明填修正後才查得到）
        assert "識別碼" in g, f"機制 facts 未進底稿（grounding target_user 修正失效？）：{g[:150]}"
        assert "120 秒" in g and ("5 分鐘" in g or "效期" in g)
    finally:
        await _cleanup(pool, sid)


# ── 綁定異動：申請書出口 token 進底稿（R4.2）──
@pytest.mark.req("account-conversational-facets:4.2")
async def test_binding_converge_carries_application_form_tokens(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "帳號綁定異動")
    brain = _Brain([
        {"action": "converge", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {"change_item": "手機換綁"}},
    ])
    eng = _engine(pool, brain, _handler([]))
    sid = "it-abind-" + os.urandom(3).hex()
    try:
        d = await eng.prepare(sid, "u1", 7, "租客手機被綁定過要換綁", config=cfg, role_id="20151")
        assert d["kind"] == "converge"
        g = d["grounding"]
        assert "service@jgbsmart.com" in g                         # 申請書關鍵 token
        assert "修改前後值" in g or ("修改" in g and "用印" in g)
        # 「不建議分身帳號」是 LLM 輸出紅線（e2e 驗）；底稿本就含禁止句，不在此斷言
    finally:
        await _cleanup(pool, sid)


# ── 團隊權限：判因分流收斂，最高頻真因進底稿（R5.1/R5.2）──
@pytest.mark.req("account-conversational-facets:5.1")
async def test_team_converge_carries_role_assignment_cause(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "團隊成員權限")
    brain = _Brain([
        {"action": "converge", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {"symptom": "成員看不到社區"}},
    ])
    eng = _engine(pool, brain, _handler([]))
    sid = "it-ateam-" + os.urandom(3).hex()
    try:
        d = await eng.prepare(sid, "u1", 7, "加了成員 他看不到社區", config=cfg, role_id="20151")
        assert d["kind"] == "converge"
        g = d["grounding"]
        assert "變更角色" in g                                     # 最高頻真因（invite 未指派）
        assert "3544" not in g and "3545" not in g                 # 不外洩內部 id
    finally:
        await _cleanup(pool, sid)


# ── 登入排障：物件名 → 列候選 → 選定 → 三分支 facts（R3.1/R3.3 候選路徑）──
@pytest.mark.req("account-conversational-facets:3.1")
async def test_login_candidate_path_then_ground(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "登入排障")
    rows = [_contract(id=84927, title="海大質感獨立套房A", is_tenant_registered=False,
                      to_user_login_email=None),
            _contract(id=84928, title="海大質感獨立套房B")]
    brain = _Brain([
        {"action": "converge", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {"contract_ref": "海大質感獨立套房"}},
    ])
    eng = _engine(pool, brain, _handler(rows))
    sid = "it-alogin2-" + os.urandom(3).hex()
    try:
        d1 = await eng.prepare(sid, "u1", 7, "海大那間的租客登不進去", config=cfg, role_id="20151")
        assert d1["kind"] == "ask" and d1.get("answer")            # 2 筆 → 列候選
        state = await eng.get_state(sid)
        labels = [c["label"] for c in (state.get("pending_candidates") or [])]
        assert len(labels) == 2 and any("套房A" in lb for lb in labels)

        d2 = await eng.prepare(sid, "u1", 7, "1", config=None, role_id="20151")
        assert d2["kind"] == "converge"
        g = d2["grounding"]
        assert "尚未註冊" in g or "未註冊" in g                     # A=未註冊分支
        assert "72 小時" in g
    finally:
        await _cleanup(pool, sid)


# ── B.Bug 導客服的資料前提：脈絡含事故特徵條款（行為本身 e2e 驗）（R2.4）──
@pytest.mark.req("account-conversational-facets:2.4")
async def test_register_context_carries_incident_clause(pool):
    from services import system_context as sc
    sc.reset_cache()
    md = await sc.get_system_context(pool, "註冊驗證排障")
    assert "金鑰" in md and "客服" in md
    assert "多位業者" in md or "全面錯誤" in md or "系統面事故" in md
