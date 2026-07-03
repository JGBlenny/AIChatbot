"""integration:帳務面向資料四件套整合驗證（billing-conversational-facets 任務 4.4 / R1, R7.5, R8.1）。

真 DB＋真 get_system_context＋真 config_for_category＋真引擎（brain 腳本化、jgb2 stub）：
  五面向進場；三層脈絡疊加（不含售前段、不含合約領域層）；_domain_faces 5 面向；
  面向內切換保留已鎖定帳單；secondary_call attach 生效（金流事件進底稿）；
  設定引導 scope=switch。fixture 冪等套用三支種子；無法連 DB → skip。
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
FACETS = ["繳費金流排障", "帳單異常", "發票", "滯納金", "帳單設定引導"]
_SEEDS = ["split_base_system_context_extract_presales.sql",
          "add_billing_facet_categories.sql",
          "seed_billing_facet_system_context.sql",
          "seed_billing_facet_configs.sql"]


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


def _handler(bill_rows, logs=None):
    """真實 APICallHandler＋stub 端點（參數感知當裁判；payment_logs 供 secondary）。"""
    from services.api_call_handler import APICallHandler
    handler = APICallHandler(db_pool=None)

    async def fake_bills(**kwargs):
        ref = str(kwargs.get("bill_ref") or "")
        hit = (not ref) or any(str(b.get("id")) == ref for b in bill_rows)
        return {"mapping": {}, "data": bill_rows if hit else []}

    async def fake_bill_detail(role_id, bill_id, **kwargs):
        for b in bill_rows:
            if b.get("id") == bill_id:
                return {"success": True, "data": b}
        return {"success": False}

    async def fake_payment_logs(**kwargs):
        return {"success": True,
                "data": {"payments": [], "payment_logs": logs or [],
                         "summary": {"has_successful_payment": bool(logs)}}}

    handler.api_registry["jgb_bills"] = fake_bills
    handler.api_registry["jgb_payment_logs"] = fake_payment_logs
    # 識別 adapter 的 bill_detail 直查也要參數感知
    handler.jgb_api.get_bill_detail = fake_bill_detail
    handler.jgb_api.use_mock = False
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


_BILL = {"id": 714100, "title": "2026-07 租金", "bit_status": 8, "total": 20000,
         "date_expire": 20260705, "pay_at": "2026-07-02 10:00:00",
         "online_payment_action": "cvs_barcode", "invoice_status": 0}


# ── 五面向進場＋persona 規則載入（R1.2/R1.6）──
@pytest.mark.req("billing-conversational-facets:1.2")
async def test_all_five_facets_enter_by_category(pool):
    from services import conversational_config as cc
    from services.conversational_rules import load_rules
    for facet in FACETS:
        cfg = await cc.config_for_category(pool, facet)
        assert cfg is not None and cfg.enabled, f"{facet} 進場 config 缺"
        assert cfg.persona_role.startswith("pm_billing_")
        rules = await load_rules(pool, cfg.persona_role)
        assert rules and "JGB" in rules


# ── 三層脈絡：base＋母系統帳務＋命中子；不含售前、不含合約領域層（R1.3）──
@pytest.mark.req("billing-conversational-facets:1.3")
async def test_three_layer_context_isolated(pool):
    from services import system_context as sc
    markers = {"繳費金流排障": "5、15、25", "帳單異常": "付款方", "發票": "差額發票",
               "滯納金": "不累加", "帳單設定引導": "一元帳單"}
    for facet, marker in markers.items():
        sc.reset_cache()
        md = await sc.get_system_context(pool, facet)
        assert "待對帳" in md, f"{facet} 缺母『系統帳務』層"
        assert marker in md, f"{facet} 缺自身子面向層"
        for pm in ("競品處理協定", "CTA 出口", "功能對照索引"):
            assert pm not in md
        assert "12 里程碑" not in md, "混入合約領域層"


# ── 面向內切換保留已鎖定帳單＋secondary attach 生效（R7.5/R8.1）──
@pytest.mark.req("billing-conversational-facets:8.1")
async def test_face_switch_keeps_bill_and_secondary_attaches(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "繳費金流排障")
    logs = [{"action": "取號", "created_at": "2026-07-01 09:00:00"},
            {"action": "cvs notify", "created_at": "2026-07-02 10:00:00"}]
    handler = _handler([_BILL], logs=logs)
    brain = _Brain([  # 第 1 輪帶編號走確定性填槽不經 brain；brain 只在第 2 輪被呼叫
        {"action": "converge", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {}, "face": "發票"},
    ])
    eng = _engine(pool, brain, handler)
    sid = "it-billsw-" + os.urandom(3).hex()
    try:
        d1 = await eng.prepare(sid, "u1", 7, "租客說繳了 714100 怎麼還沒入帳",
                               config=cfg, role_id="20151")
        assert d1["kind"] == "converge"
        # secondary_call attach：金流事件與超商時程進底稿（真 builder 經 face 分流）
        assert "最後金流事件" in d1["grounding"] and "cvs notify" in d1["grounding"]
        assert "5、15、25" in d1["grounding"]
        await eng._finalize_converge(d1)

        d2 = await eng.prepare(sid, "u1", 7, "那這筆的發票開了嗎", config=None, role_id="20151")
        assert d2 is not None and d2["kind"] == "converge"
        await eng._finalize_converge(d2)
        state = await eng.get_state(sid)
        assert state["collected_fields"]["bill_ref"] == "714100"   # 帳單鎖定保留
        assert state["face"] == "發票"
        assert "發票" in d2["grounding"]                            # 發票 builder 接手
    finally:
        await _cleanup(pool, sid)


# ── 設定引導 scope=switch 關會話（R8.2 前半：跨面向/跨域交 chat.py 重路由）──
@pytest.mark.req("billing-conversational-facets:8.1")
async def test_setup_guide_scope_switch_closes_session(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "帳單設定引導")
    brain = _Brain([
        {"action": "ask", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {}, "next_question": "請問要設定收款帳戶還是繳費週期？"},
        {"action": "converge", "converge_kind": "answer", "scope": "switch",
         "extracted_fields": {}},
    ])
    eng = _engine(pool, brain, _handler([]))
    sid = "it-bsetup-" + os.urandom(3).hex()
    try:
        d1 = await eng.prepare(sid, "u1", 7, "帳單設定要怎麼弄", config=cfg, role_id="20151")
        assert d1["kind"] == "ask"
        d2 = await eng.prepare(sid, "u1", 7, "我那筆 714100 為什麼沒入帳", config=None, role_id="20151")
        assert d2 is None
        n = await pool.fetchval(
            "SELECT count(*) FROM form_sessions WHERE session_id=$1 AND form_id='conversational' "
            "AND state='COLLECTING'", sid)
        assert n == 0
    finally:
        await _cleanup(pool, sid)
