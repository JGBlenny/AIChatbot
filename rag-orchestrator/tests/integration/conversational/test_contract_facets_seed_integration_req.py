"""integration:合約 5 子面向資料四件套整合驗證（contract-conversational-facets 任務 3.4 / R1.2–1.4, R8.1, R8.2）。

真 DB＋真 get_system_context＋真 config_for_category＋真 ConversationalEngine（brain 腳本化、jgb2 mock）：
  - 五面向 config_for_category 進場（純資料成立，零引擎程式修改）；
  - 三層脈絡疊加正確（base＋母系統合約＋命中子面向）且不含售前內容；
  - _domain_faces 由 category_config 衍生含 6 面向；
  - 面向內 face 切換保留已鎖定合約不重問（collected_fields 續存、face 傳抵 handler）；
  - 建約引導 scope=switch 關會話（供 chat.py 重路由）。

fixture 直接冪等套用三支種子（本 spec migrations 1–3）後清快取；無法連 DB → skip。
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
FACETS = ["合約異動", "退租收尾", "續約", "建約引導", "簽署排障"]
# 前置種子（domain-conversational-facets，皆冪等）＋本 spec 三支（migrations 1–3）
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
    # 冪等套用本 spec 三支種子（WHERE NOT EXISTS，可重複執行）
    for name in _SEEDS:
        with open(os.path.join(_MIG, name), encoding="utf-8") as f:
            await p.execute(f.read())
    cc.reset_cache(); sc.reset_cache(); cr.reset_cache()
    yield p
    cc.reset_cache(); sc.reset_cache(); cr.reset_cache()
    await p.close()


class _Brain:
    """腳本化 brain：依輪次回放 steps（dict 序列）；記錄看到的 faces/system_md 標記。"""
    def __init__(self, steps):
        self.steps, self.turn, self.seen = steps, 0, []

    def conversational_step(self, rules, system_md, state, msg, faces=None):
        self.seen.append({"faces": faces, "md": system_md, "rules": rules})
        step = self.steps[min(self.turn, len(self.steps) - 1)]
        self.turn += 1
        return dict(step)


def _engine(pool, brain, api_handler):
    from services.conversational_engine import ConversationalEngine
    from services import system_context as sc
    from services.conversational_rules import load_rules
    return ConversationalEngine(
        db_pool=pool, optimizer=brain, retriever=None,
        get_system_context=sc.get_system_context, rules_loader=load_rules,
        api_handler=api_handler)


def _mock_handler(rows):
    handler = MagicMock()
    handler.execute_api_call = AsyncMock(return_value={
        "success": True, "data": {"data": rows}, "formatted_response": "FACTS"})
    return handler


async def _cleanup(pool, sid):
    await pool.execute("DELETE FROM form_sessions WHERE session_id=$1", sid)


# ── 五面向 config_for_category 進場（R1.2；零引擎修改＝純資料成立）──
@pytest.mark.req("contract-conversational-facets:1.2")
async def test_all_five_facets_enter_by_category(pool):
    from services import conversational_config as cc
    for facet in FACETS:
        cfg = await cc.config_for_category(pool, facet)
        assert cfg is not None and cfg.enabled, f"{facet} 進場 config 缺"
        assert cfg.topic_scope["category"] == facet
        select = (cfg.grounding_scope or {}).get("select")
        assert select == ("category" if facet == "建約引導" else "api")
        # persona 規則列可由 load_rules 以面向專屬鍵載入（不共用 property_manager）
        from services.conversational_rules import load_rules
        rules = await load_rules(pool, cfg.persona_role)
        assert rules and "JGB" in rules


# ── 三層脈絡疊加：base＋母＋命中子面向；不含售前（R1.3）──
@pytest.mark.req("contract-conversational-facets:1.3")
async def test_three_layer_context_per_facet_without_presales(pool):
    from services import system_context as sc
    markers = {"合約異動": "service@jgbsmart.com", "退租收尾": "帳單總表",
               "續約": "續約增補", "建約引導": "兩輪", "簽署排障": "72 小時"}
    for facet, marker in markers.items():
        sc.reset_cache()
        md = await sc.get_system_context(pool, facet)
        assert "12 里程碑" in md, f"{facet} 缺母『系統合約』層"
        assert marker in md, f"{facet} 缺自身子面向層"
        # 不含售前段（split_base 定義的售前獨有節：競品協定/CTA 出口/功能索引；
        #   §5 合規鐵則屬通用 base，本就含導購連結，不算售前段）
        for pm in ("競品處理協定", "CTA 出口", "功能對照索引"):
            assert pm not in md, f"混入售前內容：{pm}"
        # 只疊命中的子面向：不含其他子面向的獨有內容
        others = {"合約異動": "帳單總表", "退租收尾": "service@jgbsmart.com"}
        if facet in others:
            assert others[facet] not in md


# ── _domain_faces 衍生：任一面向進場 → 6 面向集合（R8.1）──
@pytest.mark.req("contract-conversational-facets:8.1")
async def test_domain_faces_contains_all_six(pool):
    from services import conversational_config as cc
    from services.conversational_engine import _domain_faces
    cfg = await cc.config_for_category(pool, "合約異動")
    faces = await _domain_faces(pool, cfg)
    assert set(faces) >= {"狀態判斷", *FACETS}


# ── 面向內 face 切換：保留已鎖定合約不重問；face 傳抵 handler（R8.2）──
@pytest.mark.req("contract-conversational-facets:8.2")
async def test_face_switch_keeps_locked_contract(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "合約異動")
    handler = _mock_handler([{"id": 83315, "title": "基隆物件", "status": 8, "bit_status": 15}])
    # 第一輪「我想改 83315 的租期」走確定性填槽（pre-LLM）直接收斂，不經 brain；
    # brain 只在第二輪被呼叫 → 腳本單步：換面向、不重給識別。
    brain = _Brain([
        {"action": "converge", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {}, "face": "退租收尾"},
    ])
    eng = _engine(pool, brain, handler)
    sid = "it-facesw-" + os.urandom(3).hex()
    try:
        d1 = await eng.prepare(sid, "u1", 7, "我想改 83315 的租期", config=cfg, role_id="20151")
        assert d1["kind"] == "converge"
        await eng._finalize_converge(d1)                     # 收斂後會話續存

        d2 = await eng.prepare(sid, "u1", 7, "那這份退租要怎麼收尾", config=None, role_id="20151")
        assert d2 is not None and d2["kind"] == "converge"   # 不重問識別，直接單筆收斂
        await eng._finalize_converge(d2)                     # 保存本輪 state（含 face）
        state = await eng.get_state(sid)
        assert state["collected_fields"]["contract_ref"] == "83315"   # 合約鎖定保留
        assert state["face"] == "退租收尾"
        # face 貫穿：第二輪 API 呼叫收到 face=退租收尾（任務 1.1 鏈路 × 真設定）
        assert handler.execute_api_call.call_args.kwargs.get("face") == "退租收尾"
        # 換面向後脈絡換成退租收尾層
        assert "帳單總表" in d2["system_md"]
    finally:
        await _cleanup(pool, sid)


# ── 建約引導 scope=switch → 關會話（chat.py 對當前訊息重路由）（R8.1）──
@pytest.mark.req("contract-conversational-facets:8.1")
async def test_create_guide_scope_switch_closes_session(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "建約引導")
    brain = _Brain([
        {"action": "ask", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {}, "next_question": "請問要用電子簽新約還是紙本上傳？"},
        {"action": "converge", "converge_kind": "answer", "scope": "switch",
         "extracted_fields": {}},                            # 涉及特定合約現況 → 轉出
    ])
    eng = _engine(pool, brain, _mock_handler([]))
    sid = "it-cgsw-" + os.urandom(3).hex()
    try:
        d1 = await eng.prepare(sid, "u1", 7, "我要建一份合約", config=cfg, role_id="20151")
        assert d1["kind"] == "ask"
        d2 = await eng.prepare(sid, "u1", 7, "我那份 83315 現在能改嗎", config=None, role_id="20151")
        assert d2 is None                                    # switch → None（落回重路由）
        n = await pool.fetchval(
            "SELECT count(*) FROM form_sessions WHERE session_id=$1 AND form_id='conversational' "
            "AND state='COLLECTING'", sid)
        assert n == 0                                        # 會話已關
    finally:
        await _cleanup(pool, sid)
