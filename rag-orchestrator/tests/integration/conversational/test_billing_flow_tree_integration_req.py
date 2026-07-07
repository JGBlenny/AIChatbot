"""integration:繳費金流排障全流程（billing-conversational-facets 任務 6.1 / R2.1–2.3, R8.2）。

真 DB（config/脈絡/persona 種子）＋真引擎＋真 APICallHandler＋真 builder（face 貫穿）；
jgb2 端點 stub（參數感知當裁判）、brain 腳本化。

驗證：追問識別 → adapter 三路鎖定（編號直查/合約解析）→ secondary attach →
分支 facts（超商時程/查無繳費引導/未知導客服）→ 跨域 switch 雙向。
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
          "add_billing_facet_categories.sql",
          "seed_billing_facet_system_context.sql",
          "seed_billing_facet_configs.sql",
          "add_contract_facet_categories.sql",
          "add_contract_facet_categories_v2.sql",
          "seed_domain_contract_system_context.sql",
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


_BILL_CVS = {"id": 714100, "title": "2026-07 租金", "bit_status": 8, "status": 8,
             "total": 20000, "date_expire": 20260705,
             "pay_at": "2026-07-02 10:00:00", "complete_at": None,
             "online_payment_action": "cvs_barcode", "invoice_status": 0}
_BILL_READY = {"id": 714096, "title": "2026-08 租金", "bit_status": 2, "status": 2,
               "total": 20000, "date_expire": 20260805, "pay_at": None,
               "complete_at": None, "online_payment_action": None, "invoice_status": 0}
_LOGS = [{"action": "取號", "created_at": "2026-07-01 09:00:00"},
         {"action": "cvs notify", "created_at": "2026-07-02 10:00:00"}]


def _handler(bills, contracts=None, logs=None):
    """真實 handler＋參數感知 stub：bill_detail 直查／contracts 解析／bills 列表／payment_logs。"""
    from services.api_call_handler import APICallHandler
    handler = APICallHandler(db_pool=None)
    handler.jgb_api.use_mock = False

    async def fake_bill_detail(role_id, bill_id, **kw):
        for b in bills:
            if b["id"] == bill_id:
                return {"success": True, "data": b}
        return {"success": False}

    async def fake_contracts_fn(role_id, user_id=None, contract_ids=None, keyword=None, **kw):
        rows = contracts or []
        if contract_ids:
            rows = [c for c in rows if str(c.get("id")) == str(contract_ids)]
        elif keyword:
            rows = [c for c in rows if keyword in (c.get("title") or "")]
        return {"success": True, "data": rows}

    async def fake_bills_request(path, params):
        if path.endswith("/bills"):
            cid = params.get("contract_ids")
            rows = [b for b in bills if not cid or b.get("contract_id") == cid or True]
            return {"success": True, "data": rows}
        return {"success": True, "data": []}

    async def fake_payment_logs(**kw):
        return {"success": True, "data": {"payments": [], "payment_logs": logs or [],
                                          "summary": {"has_successful_payment": bool(logs)}}}

    handler.jgb_api.get_bill_detail = fake_bill_detail
    handler.jgb_api.get_contracts = fake_contracts_fn
    handler.jgb_api._request = fake_bills_request
    handler.api_registry["jgb_bills"] = handler.jgb_api.get_bills   # 走真 adapter
    handler.api_registry["jgb_payment_logs"] = fake_payment_logs
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


# ── 全流程：追問識別 → 編號直查（adapter 路徑一）→ secondary attach → 超商時程分支 ──
@pytest.mark.req("billing-conversational-facets:2.2")
async def test_flow_ask_then_direct_hit_with_cvs_schedule(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "繳費金流排障")
    brain = _Brain([
        {"action": "ask", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {}, "next_question": "請提供帳單編號，或合約/物件名稱？"},
    ])
    eng = _engine(pool, brain, _handler([_BILL_CVS], logs=_LOGS))
    sid = "it-bflow-" + os.urandom(3).hex()
    try:
        d1 = await eng.prepare(sid, "u1", 7, "租客說繳了錢還沒進來", config=cfg, role_id="20151")
        assert d1["kind"] == "ask"                              # 追問識別

        d2 = await eng.prepare(sid, "u1", 7, "714100", config=None, role_id="20151")
        assert d2["kind"] == "converge"                          # 編號直查單筆收斂
        g = d2["grounding"]
        assert "已完成繳費" in g and "5、15、25" in g            # 超商撥付時程分支
        assert "最後金流事件" in g and "cvs notify" in g          # secondary attach
        assert "客服" not in g                                    # 正常時程不導客服
    finally:
        await _cleanup(pool, sid)


# ── adapter 路徑三：物件名稱 → 合約解析 → 帳單候選 ──
@pytest.mark.req("billing-conversational-facets:2.1")
async def test_flow_contract_name_resolves_to_bill_candidates(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "繳費金流排障")
    brain = _Brain([
        {"action": "converge", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {"bill_ref": "基隆溫馨一人宅套房"}, "face": "繳費金流排障"},
    ])
    eng = _engine(pool, brain,
                  _handler([_BILL_CVS, _BILL_READY],
                           contracts=[{"id": 84981, "title": "基隆溫馨一人宅套房"}]))
    sid = "it-bname-" + os.urandom(3).hex()
    try:
        d = await eng.prepare(sid, "u1", 7, "基隆那間的帳單錢一直沒進來", config=cfg, role_id="20151")
        assert d["kind"] == "ask" and d.get("answer")            # 2 筆 → 列候選
        state = await eng.get_state(sid)
        labels = [c["label"] for c in (state.get("pending_candidates") or [])]
        assert len(labels) == 2
        assert any("2026-07 租金" in lb for lb in labels)
        assert any("20,000" in lb or "20000" in lb for lb in labels)   # label 帶金額
    finally:
        await _cleanup(pool, sid)


# ── 查無繳費分支：READY 無 pay_at → 核對引導（不導客服不臆測）──
@pytest.mark.req("billing-conversational-facets:2.2")
async def test_flow_ready_bill_gives_verification_guidance(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "繳費金流排障")
    brain = _Brain([{"action": "ask", "converge_kind": "answer", "scope": "stay",
                     "extracted_fields": {}, "next_question": "請提供帳單編號？"}])
    eng = _engine(pool, brain, _handler([_BILL_READY]))
    sid = "it-bready-" + os.urandom(3).hex()
    try:
        await eng.prepare(sid, "u1", 7, "租客說有繳但沒紀錄", config=cfg, role_id="20151")
        d = await eng.prepare(sid, "u1", 7, "714096", config=None, role_id="20151")
        assert d["kind"] == "converge"
        g = d["grounding"]
        assert "查無" in g and ("帳號" in g or "上限" in g)       # 核對引導
        assert "重發" in g                                        # 收回重發解法
    finally:
        await _cleanup(pool, sid)


# ── 跨域 switch：帳務 → 合約（雙向之一；另一向由合約建約引導測試覆蓋）──
@pytest.mark.req("billing-conversational-facets:8.2")
async def test_cross_domain_switch_billing_to_contract(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "繳費金流排障")
    brain = _Brain([
        {"action": "ask", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {}, "next_question": "請提供帳單編號？"},
        {"action": "converge", "converge_kind": "answer", "scope": "switch",
         "extracted_fields": {}},                                # 話題跳合約 → 轉出
    ])
    eng = _engine(pool, brain, _handler([_BILL_CVS]))
    sid = "it-bswitch-" + os.urandom(3).hex()
    try:
        d1 = await eng.prepare(sid, "u1", 7, "租客繳不了費", config=cfg, role_id="20151")
        assert d1["kind"] == "ask"
        d2 = await eng.prepare(sid, "u1", 7, "對了我想改這份合約的租期", config=None, role_id="20151")
        assert d2 is None                                        # switch → 關會話重路由
        n = await pool.fetchval(
            "SELECT count(*) FROM form_sessions WHERE session_id=$1 AND form_id='conversational' "
            "AND state='COLLECTING'", sid)
        assert n == 0
    finally:
        await _cleanup(pool, sid)
