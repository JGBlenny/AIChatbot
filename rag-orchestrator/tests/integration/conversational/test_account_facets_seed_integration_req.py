"""integration:帳號面向資料四件套整合驗證（account-conversational-facets 任務 2.4 / R1, R3, R7）。

真 DB＋真 get_system_context＋真 config_for_category＋真引擎（brain 腳本化、jgb2 stub）：
  四面向進場；三層脈絡疊加（母薄層＋子；不含售前/合約/帳務層；外部/內部類互不滲透）；
  登入排障 identify→ground→三分支 facts（accounts.py builder 經 face 分流）；
  面向互轉（註冊→綁定異動）已蒐集線索保留；跨域 switch（簽約頁話題）關會話。
  fixture 冪等套用三支種子；無法連 DB → skip。
"""
import os

import pytest


pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _force_mock_jgb(monkeypatch):
    # 僅在本檔測試執行期間生效（模組層 os.environ 會污染全套收集的 e2e）
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")

_MIG = os.path.join(os.path.dirname(__file__), "..", "..", "..", "database", "migrations")
FACETS = ["註冊驗證排障", "登入排障", "帳號綁定異動", "團隊成員權限"]
EXTERNAL = ["註冊驗證排障", "登入排障"]
INTERNAL = ["帳號綁定異動", "團隊成員權限"]
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
    """真實 APICallHandler＋jgb_contracts stub（contract_ids/keyword 參數感知當裁判）。"""
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
        return {"success": False, "data": []}   # G-A1 不可用 → 走合約層三分支（本檔驗合約層）

    handler.api_registry["jgb_tenant_registration"] = fake_registration_empty
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


# ── 四面向進場＋persona 規則載入（R1.2/R1.6）──
@pytest.mark.req("account-conversational-facets:1.2")
async def test_all_four_facets_enter_by_category(pool):
    from services import conversational_config as cc
    from services.conversational_rules import load_rules
    for facet in FACETS:
        cfg = await cc.config_for_category(pool, facet)
        assert cfg is not None and cfg.enabled, f"{facet} 進場 config 缺"
        assert cfg.persona_role.startswith("pm_account_")
        rules = await load_rules(pool, cfg.persona_role)
        assert rules and "JGB" in rules
        assert "驗證碼" in rules                                  # 紅線在四 persona 全掛


# ── 三層脈絡：base＋母帳號中心（薄）＋命中子；不含他域層；兩類互不滲透（R1.3）──
@pytest.mark.req("account-conversational-facets:1.3")
async def test_three_layer_context_isolated(pool):
    from services import system_context as sc
    markers = {"註冊驗證排障": "識別碼", "登入排障": "確切寫法",
               "帳號綁定異動": "service@jgbsmart.com", "團隊成員權限": "變更角色"}
    for facet, marker in markers.items():
        sc.reset_cache()
        md = await sc.get_system_context(pool, facet)
        assert "一人一個主帳號" in md, f"{facet} 缺母『帳號中心』層"
        assert marker in md, f"{facet} 缺自身子面向層"
        for pm in ("競品處理協定", "CTA 出口", "功能對照索引"):
            assert pm not in md                                   # 不含售前 append
        assert "12 里程碑" not in md, "混入合約領域層"
        assert "待對帳" not in md, "混入帳務領域層"
    # 兩類互不滲透：外部面向不含內部機制詞、內部面向不含外部機制詞
    for facet in EXTERNAL:
        sc.reset_cache()
        md = await sc.get_system_context(pool, facet)
        assert "申請書" not in md, f"外部面向「{facet}」滲入內部類機制"
    for facet in INTERNAL:
        sc.reset_cache()
        md = await sc.get_system_context(pool, facet)
        assert "驗證碼" not in md, f"內部面向「{facet}」滲入外部類機制"


# ── 登入排障：identify→ground→三分支 facts（R3.3；accounts.py 經 face 分流）──
@pytest.mark.req("account-conversational-facets:3.3")
@pytest.mark.parametrize("row,expect,forbid", [
    (_contract(is_tenant_registered=False, to_user_login_email=None),
     ["尚未註冊", "72 小時"], ["登錯"]),
    (_contract(to_user_login_email="other.person@gmail.com"),
     ["登錯", "o***@gmail.com"], ["other.person@gmail.com"]),
    (_contract(),
     ["一致", "忘記密碼"], ["登錯"]),
])
async def test_login_trouble_grounds_three_branches(pool, row, expect, forbid):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "登入排障")
    brain = _Brain([{"action": "converge", "converge_kind": "answer", "scope": "stay",
                     "extracted_fields": {}}])
    eng = _engine(pool, brain, _handler([row]))
    sid = "it-alogin-" + os.urandom(3).hex()
    try:
        d = await eng.prepare(sid, "u1", 7, "租客說他登不進去 合約 84927",
                              config=cfg, role_id="20151")
        assert d["kind"] == "converge"
        g = d["grounding"]
        for token in expect:
            assert token in g, f"缺分支 token「{token}」：{g[:200]}"
        for token in forbid:
            assert token not in g, f"不應出現「{token}」：{g[:200]}"
    finally:
        await _cleanup(pool, sid)


# ── 面向互轉（註冊→綁定異動）：已蒐集線索保留不重問（R7.1）──
@pytest.mark.req("account-conversational-facets:7.1")
async def test_face_switch_register_to_binding_keeps_clues(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "註冊驗證排障")
    brain = _Brain([
        {"action": "ask", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {"symptom": "顯示此手機已註冊"},
         "next_question": "租客是用簡訊還是 Email 註冊？"},
        {"action": "ask", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {}, "face": "帳號綁定異動",
         "next_question": "要換綁的手機修改前後號碼是？"},
    ])
    eng = _engine(pool, brain, _handler([]))
    sid = "it-aswitch-" + os.urandom(3).hex()
    try:
        d1 = await eng.prepare(sid, "u1", 7, "租客註冊說手機已註冊過", config=cfg, role_id="20151")
        assert d1["kind"] == "ask"
        d2 = await eng.prepare(sid, "u1", 7, "那要怎麼把那支手機解綁改綁", config=None, role_id="20151")
        assert d2 is not None and d2["kind"] == "ask"             # 同域互轉不關會話
        state = await eng.get_state(sid)
        assert state["face"] == "帳號綁定異動"                     # 面向已切換
        assert state["collected_fields"]["symptom"] == "顯示此手機已註冊"   # 線索保留
    finally:
        await _cleanup(pool, sid)


# ── 跨域 switch：簽約頁話題 → 關會話交 chat.py 重路由（→ 合約簽署排障）（R7.2）──
@pytest.mark.req("account-conversational-facets:7.2")
async def test_cross_domain_switch_to_contract_sign(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "登入排障")
    brain = _Brain([
        {"action": "ask", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {}, "next_question": "是完全登不進去，還是登入後看不到資料？"},
        {"action": "converge", "converge_kind": "answer", "scope": "switch",
         "extracted_fields": {}},
    ])
    eng = _engine(pool, brain, _handler([]))
    sid = "it-axd-" + os.urandom(3).hex()
    try:
        d1 = await eng.prepare(sid, "u1", 7, "租客登不進去", config=cfg, role_id="20151")
        assert d1["kind"] == "ask"
        d2 = await eng.prepare(sid, "u1", 7, "他是在簽約頁面上傳身分證一直跳錯誤",
                               config=None, role_id="20151")
        assert d2 is None                                         # switch → 關會話重路由
        n = await pool.fetchval(
            "SELECT count(*) FROM form_sessions WHERE session_id=$1 AND form_id='conversational' "
            "AND state='COLLECTING'", sid)
        assert n == 0
    finally:
        await _cleanup(pool, sid)
