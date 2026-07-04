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

    async def fake_registration_empty(role_id, email=None, phone=None, **kw):
        return {"success": False, "data": []}   # G-A1 不可用 → secondary 降級、走合約層

    handler.api_registry["jgb_tenant_registration"] = fake_registration_empty
    return handler


def _handler_with_ga1(contract_rows, reg_by_email):
    """合約 stub＋G-A1（tenants/registration-status）參數感知 stub（secondary_call 用）。"""
    handler = _handler(contract_rows)

    async def fake_registration(role_id, email=None, phone=None, **kw):
        r = reg_by_email.get((email or "").strip())
        return {"success": True, "data": [r] if r else []}

    handler.api_registry["jgb_tenant_registration"] = fake_registration
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


# ── 團隊權限：無角色（未指派）→ 決定性解釋「沒開檢視權限」（R5.1）──
@pytest.mark.req("account-conversational-facets:5.1")
async def test_team_member_no_permission_flags(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "團隊成員權限")
    members = [{"member_user_id": 700, "character_name": "新進", "is_owner": False,
                "match_field": "name", "_name": "李四", "_email": "li@x.com"}]
    perms = {700: {"character_name": "新進",
                   "abilities": {"show_bill": False, "show_owner_bill": False,
                                 "show_estate": False, "show_owner_estate": False}}}
    handler = _handler_team(members, perms, {})
    brain = _Brain([{"action": "converge", "converge_kind": "answer", "scope": "stay",
                     "extracted_fields": {"member_ref": "李四"}}])
    eng = _engine(pool, brain, handler)
    sid = "it-ateam-" + os.urandom(3).hex()
    try:
        d = await eng.prepare(sid, "u1", 7, "李四 加了之後什麼都看不到", config=cfg, role_id="20151")
        assert d["kind"] == "converge"
        g = d["grounding"]
        assert "沒有" in g and "變更角色" in g                     # 沒開權限 → 指路變更角色
        assert "700" not in g                                      # 遮罩 user_id
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


# ── 登入排障 G-A1 附掛：secondary_call 三態排查＋嚴格遮罩（account 6.2* / R9.2）──
@pytest.mark.req("account-conversational-facets:9.2")
async def test_login_ga1_secondary_three_state_and_masking(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "登入排障")
    # 合約層說已註冊，但 G-A1 說沒完成註冊（85366 真實錯配態）→ 以 G-A1 為準
    c = _contract(id=84927, title="海大質感獨立套房",
                  to_user_email="tenant@example.com", is_tenant_registered=True)
    reg = {"tenant@example.com": {"found": True, "is_bound": True, "is_registered": False,
                                  "lessee_email_verify_status": 0,
                                  "lessee_user_id": 99999, "lessee_name": "王小明"}}
    brain = _Brain([{"action": "converge", "converge_kind": "answer", "scope": "stay",
                     "extracted_fields": {"contract_ref": "84927"}}])
    eng = _engine(pool, brain, _handler_with_ga1([c], reg))
    sid = "it-alogin-ga1-" + os.urandom(3).hex()
    try:
        d = await eng.prepare(sid, "u1", 7, "海大那間租客登不進去 84927", config=cfg, role_id="20151")
        assert d["kind"] == "converge"
        g = d["grounding"]
        assert "未完成註冊" in g or "尚未" in g                      # G-A1 覆寫合約層
        assert "邀請連結" in g
        assert "王小明" not in g and "99999" not in g               # 嚴格遮罩：名字/user_id 不出口
    finally:
        await _cleanup(pool, sid)


# ── 團隊權限完整版：T1 成員→兩 secondary（旗標＋T2 可見性）三跳＋遮罩（account 5.1）──
def _handler_team(members, perms_by_uid, visible_bill_ids):
    """T1 成員查詢＋permissions＋bill_visibility 三個參數感知 stub。"""
    from services.api_call_handler import APICallHandler
    handler = APICallHandler(db_pool=None)
    handler.jgb_api.use_mock = False

    async def fake_members(role_id, keyword=None, **kw):
        kw_s = (keyword or "").strip()
        rows = [m for m in members if kw_s and (kw_s in (m.get("_name") or "") or kw_s in (m.get("_email") or ""))]
        # 去掉測試輔助欄位
        return {"success": True, "data": [{k: v for k, v in m.items() if not k.startswith("_")} for m in rows]}

    async def fake_perms(role_id, user_id=None, **kw):
        p = perms_by_uid.get(int(user_id)) if user_id else None
        return {"success": True, "data": [p] if p else []}

    async def fake_visibility(role_id, viewer_user_id=None, bill_id=None, **kw):
        if not bill_id:
            return {"success": False, "data": []}   # 無具體資源 → 降級不 attach
        vis = str(bill_id) in {str(b) for b in visible_bill_ids.get(int(viewer_user_id), [])}
        return {"success": True, "data": [{"id": bill_id}] if vis else []}

    handler.api_registry["jgb_team_members"] = fake_members
    handler.api_registry["jgb_member_permissions"] = fake_perms
    handler.api_registry["jgb_bill_visibility"] = fake_visibility
    return handler


@pytest.mark.req("account-conversational-facets:5.1")
async def test_team_permission_full_three_hop_owner_scoped_invisible(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "團隊成員權限")
    members = [{"member_user_id": 292, "character_id": 1151, "character_name": "檢視者",
                "is_owner": False, "match_field": "email", "_name": "張三", "_email": "zhang@x.com"}]
    perms = {292: {"character_name": "檢視者",
                   "abilities": {"show_bill": False, "show_owner_bill": True}}}
    # 292 對 716478 不可見（未指派）
    handler = _handler_team(members, perms, visible_bill_ids={292: []})
    brain = _Brain([{"action": "converge", "converge_kind": "answer", "scope": "stay",
                     "extracted_fields": {"member_ref": "張三", "resource_ref": "716478"}}])
    eng = _engine(pool, brain, handler)
    sid = "it-team-" + os.urandom(3).hex()
    try:
        d = await eng.prepare(sid, "u1", 7, "張三看不到 716478 這張帳單", config=cfg, role_id="20151")
        assert d["kind"] == "converge"
        g = d["grounding"]
        assert "檢視者" in g                                       # 角色名（顯示）
        assert "只看" in g or "經手" in g                          # show_owner 機制
        assert "看不到" in g and "指派" in g                       # T2 確認＋解法
        assert "292" not in g                                      # 遮罩 user_id
    finally:
        await _cleanup(pool, sid)


@pytest.mark.req("account-conversational-facets:5.1")
async def test_team_permission_candidate_list_multiple_members(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "團隊成員權限")
    members = [{"member_user_id": 292, "character_name": "檢視者", "is_owner": False,
                "match_field": "name", "_name": "張三", "_email": "z1@x.com"},
               {"member_user_id": 445, "character_name": "店長", "is_owner": False,
                "match_field": "name", "_name": "張三", "_email": "z2@x.com"}]
    handler = _handler_team(members, {}, {})
    brain = _Brain([{"action": "converge", "converge_kind": "answer", "scope": "stay",
                     "extracted_fields": {"member_ref": "張三"}}])
    eng = _engine(pool, brain, handler)
    sid = "it-teamcand-" + os.urandom(3).hex()
    try:
        d = await eng.prepare(sid, "u1", 7, "張三 權限有問題", config=cfg, role_id="20151")
        assert d["kind"] == "ask" and d.get("answer")             # 同名兩位 → 列候選
        state = await eng.get_state(sid)
        assert len(state.get("pending_candidates") or []) == 2
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
