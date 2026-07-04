"""integration:物件面向資料四件套整合驗證（estate-conversational-facets 任務 2.4 / R1, R2, R4, R5.3）。

真 DB＋真 get_system_context＋真 config_for_category＋真引擎＋真 get_estate_status adapter
（stub 到 jgb_api._request 層，wrapper 的 token 過濾與 sentinel 真跑）；brain 腳本化。

驗證：兩面向進場；三層脈絡疊加（母薄層＋子；不含他域層與售前）；
現況診斷 identify→過濾→候選/直中→detail attach→facts；**sentinel 案**（查無→
非刊登中口徑、不出引擎通用「查無資料」句）；引導 category 收斂（target_user 明填
生效；fixture 自插測試知識不依賴第 3 節）；跨域 switch。無法連 DB → skip。
"""
import os

import pytest
from unittest.mock import AsyncMock

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _force_mock_jgb(monkeypatch):
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")

_MIG = os.path.join(os.path.dirname(__file__), "..", "..", "..", "database", "migrations")
FACETS = ["物件操作引導", "物件現況診斷"]
_SEEDS = ["split_base_system_context_extract_presales.sql",
          "add_estate_facet_categories.sql",
          "seed_estate_facet_system_context.sql",
          "seed_estate_facet_configs.sql"]

_TEST_KB_SUMMARY = "IT測試-對外顯示地址教學"   # fixture 自插（teardown 刪）


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
    await p.execute(
        "INSERT INTO knowledge_base (question_summary, answer, category, categories, target_user, is_active) "
        "SELECT $1, '對外顯示地址測試內容：只作用在對外廣告頁，後台恆顯完整地址。', '一般知識', "
        "ARRAY['物件操作引導']::text[], ARRAY['property_manager']::text[], TRUE "
        "WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary=$1)", _TEST_KB_SUMMARY)
    cc.reset_cache(); sc.reset_cache(); cr.reset_cache()
    yield p
    await p.execute("DELETE FROM knowledge_base WHERE question_summary=$1", _TEST_KB_SUMMARY)
    cc.reset_cache(); sc.reset_cache(); cr.reset_cache()
    await p.close()


class _Brain:
    def __init__(self, steps):
        self.steps, self.turn = steps, 0

    def conversational_step(self, rules, system_md, state, msg, faces=None):
        step = self.steps[min(self.turn, len(self.steps) - 1)]
        self.turn += 1
        return dict(step)


def _estate(**over):
    e = {"id": 8801, "serial_id": "E-8801", "title": "新莊富貴500-14B05",
         "status": 2, "use_for": "residential",
         "address": "新北市新莊區富貴路500號14樓B05室",
         "full_address": "新北市新莊區富貴路500號14樓B05室",
         "display_address": "新北市新莊區富貴路",
         "rent": 15800, "currency": "TWD"}
    e.update(over)
    return e


def _handler(estate_rows, detail_row=None):
    """真實 APICallHandler＋真 adapter：stub 到 _request 層（endpoint 感知——
    index 回列表、show 回單物件；wrapper 的過濾/sentinel/正規化真跑）。"""
    from services.api_call_handler import APICallHandler
    handler = APICallHandler(db_pool=None)
    handler.jgb_api.use_mock = False

    async def _req(path, params=None, **kw):
        if "/estates/" in path:   # show 單筆
            if detail_row is None:
                return {"success": False}
            return {"success": True, "data": detail_row}
        return {"success": True, "data": estate_rows}
    handler.jgb_api._request = AsyncMock(side_effect=_req)
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


# ── 兩面向進場＋persona 規則載入（R1.2/R1.6）──
@pytest.mark.req("estate-conversational-facets:1.2")
async def test_both_facets_enter_by_category(pool):
    from services import conversational_config as cc
    from services.conversational_rules import load_rules
    for facet in FACETS:
        cfg = await cc.config_for_category(pool, facet)
        assert cfg is not None and cfg.enabled, f"{facet} 進場 config 缺"
        assert cfg.persona_role.startswith("pm_estate_")
        rules = await load_rules(pool, cfg.persona_role)
        assert rules and "JGB" in rules
        assert "不代" in rules or "只指路" in rules


# ── 三層脈絡：base＋母物件管理（薄）＋命中子；不含他域層（R1.3）──
@pytest.mark.req("estate-conversational-facets:1.3")
async def test_three_layer_context_isolated(pool):
    from services import system_context as sc
    markers = {"物件操作引導": "完整地址", "物件現況診斷": "已刪除"}
    for facet, marker in markers.items():
        sc.reset_cache()
        md = await sc.get_system_context(pool, facet)
        assert "兩條獨立軸" in md or "獨立軸" in md, f"{facet} 缺母『物件管理』層"
        assert marker in md, f"{facet} 缺自身子面向層"
        for pm in ("競品處理協定", "CTA 出口", "功能對照索引"):
            assert pm not in md                                # 不含售前 append
        assert "12 里程碑" not in md, "混入合約領域層"
        assert "自動復電" not in md, "混入 IoT 領域層"
        assert "一人一個主帳號" not in md, "混入帳號領域層"


# ── 現況診斷：identify→過濾→直中＋detail attach→facts（R4.1/R4.2）──
@pytest.mark.req("estate-conversational-facets:4.2")
async def test_diag_flow_status_and_missing_fields(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "物件現況診斷")
    rows = [_estate()]
    detail = _estate(description="近捷運", contract_required_fields={
        "all_filled": False, "fields": [
            {"field": "size", "label": "面積", "is_filled": False},
            {"field": "title", "label": "物件名稱", "is_filled": True}]})
    brain = _Brain([
        {"action": "ask", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {}, "next_question": "請問是哪個物件（名稱或編號）？"},
        {"action": "converge", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {"estate_ref": "新莊富貴500"}},
    ])
    eng = _engine(pool, brain, _handler(rows, detail))
    sid = "it-est-" + os.urandom(3).hex()
    try:
        d1 = await eng.prepare(sid, "u1", 7, "這個物件為什麼不能建約", config=cfg, role_id="37305")
        assert d1["kind"] == "ask"
        d2 = await eng.prepare(sid, "u1", 7, "新莊富貴500那間", config=None, role_id="37305")
        assert d2["kind"] == "converge"
        g = d2["grounding"]
        assert "刊登中" in g                                   # status 轉譯
        assert "面積" in g                                     # 缺欄列舉（detail attach 生效）
        assert "富貴路500號14樓B05室" not in g                 # 個資紅線：完整地址不出口
    finally:
        await _cleanup(pool, sid)


@pytest.mark.req("estate-conversational-facets:4.1")
async def test_diag_flow_multiple_candidates_with_status_label(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "物件現況診斷")
    rows = [_estate(id=8801, title="富貴500-14B05", status=2),
            _estate(id=8802, title="富貴500-14B06", status=8)]
    brain = _Brain([{"action": "converge", "converge_kind": "answer", "scope": "stay",
                     "extracted_fields": {"estate_ref": "富貴500"}}])
    eng = _engine(pool, brain, _handler(rows))
    sid = "it-estc-" + os.urandom(3).hex()
    try:
        d = await eng.prepare(sid, "u1", 7, "富貴500的物件現在什麼狀態", config=cfg, role_id="37305")
        assert d["kind"] == "ask" and d.get("answer")          # 2 筆 → 列候選
        state = await eng.get_state(sid)
        labels = [c["label"] for c in (state.get("pending_candidates") or [])]
        assert len(labels) == 2
        assert any("租約中" in lb for lb in labels)            # label 帶 status_zh 轉譯
    finally:
        await _cleanup(pool, sid)


# ── sentinel：查無→非刊登中口徑，不出引擎通用句（design Issue 1 / R4.2）──
@pytest.mark.req("estate-conversational-facets:4.2")
async def test_diag_sentinel_not_generic_message(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "物件現況診斷")
    rows = [_estate(id=8801, title="基隆海大套房A1")]          # 與 keyword 不匹配 → sentinel
    brain = _Brain([{"action": "converge", "converge_kind": "answer", "scope": "stay",
                     "extracted_fields": {"estate_ref": "不存在的華廈999"}}])
    eng = _engine(pool, brain, _handler(rows))
    sid = "it-ests-" + os.urandom(3).hex()
    try:
        d = await eng.prepare(sid, "u1", 7, "不存在的華廈999現在什麼狀態", config=cfg, role_id="37305")
        assert d["kind"] == "converge", "sentinel 應走收斂而非引擎 0-row 短路"
        g = d["grounding"]
        assert "非刊登中" in g and "名稱" in g                  # builder 口徑
        assert "已刪除" not in g                               # 紅線
        assert "查無對應的資料" not in g                        # 不出引擎通用句
    finally:
        await _cleanup(pool, sid)


# ── 引導：category 收斂（target_user 明填生效）（R2.1/R1.7）──
@pytest.mark.req("estate-conversational-facets:2.1")
async def test_guide_category_convergence_has_grounding(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "物件操作引導")
    brain = _Brain([{"action": "converge", "converge_kind": "answer", "scope": "stay",
                     "extracted_fields": {"topic": "對外顯示地址"}}])
    eng = _engine(pool, brain, _handler([]))
    sid = "it-estg-" + os.urandom(3).hex()
    try:
        d = await eng.prepare(sid, "u1", 7, "改了對外顯示地址怎麼沒生效", config=cfg, role_id="37305")
        assert d["kind"] == "converge"
        g = d.get("grounding") or ""
        # category 選材有上限（不保證特定筆入選）——斷言面向知識底稿成立（target_user 明填生效）
        assert len(g) > 50 and ("刊登" in g or "對外" in g or "物件" in g), f"grounding 空或無面向知識：{g[:80]}"
    finally:
        await _cleanup(pool, sid)


# ── 4.1 引導兩輪分流→收斂吃真面向知識（匯入批次後，非 fixture）（R2.1/R2.2）──
@pytest.mark.req("estate-conversational-facets:2.2")
async def test_guide_two_turn_triage_then_converge_real_knowledge(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "物件操作引導")
    brain = _Brain([
        {"action": "ask", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {}, "next_question": "想了解對外顯示還是刊登操作？"},
        {"action": "converge", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {"topic": "對外顯示地址"}},
    ])
    eng = _engine(pool, brain, _handler([]))
    sid = "it-estg2-" + os.urandom(3).hex()
    try:
        d1 = await eng.prepare(sid, "u1", 7, "物件對外的資訊怪怪的", config=cfg, role_id="37305")
        assert d1["kind"] == "ask"
        d2 = await eng.prepare(sid, "u1", 7, "改了對外顯示地址沒生效", config=None, role_id="37305")
        assert d2["kind"] == "converge"
        g = d2.get("grounding") or ""
        # 分流→收斂鏈成立且底稿為面向知識（選材上限不保證特定筆——批次知識檢索命中由路由回歸/e2e 驗）
        assert len(g) > 50 and ("刊登" in g or "物件" in g), f"兩輪收斂底稿異常：{g[:80]}"
    finally:
        await _cleanup(pool, sid)


# ── 4.1 診斷 status=4：兩軸不混講（builder 混軸 bug 回歸釘）（R4.2）──
@pytest.mark.req("estate-conversational-facets:4.2")
async def test_diag_status4_negotiating_no_axis_confusion(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "物件現況診斷")
    rows = [_estate(status=4)]
    detail = _estate(status=4, contract_required_fields={"all_filled": True, "fields": []})
    brain = _Brain([{"action": "converge", "converge_kind": "answer", "scope": "stay",
                     "extracted_fields": {"estate_ref": "新莊富貴500"}}])
    eng = _engine(pool, brain, _handler(rows, detail))
    sid = "it-est4-" + os.urandom(3).hex()
    try:
        d = await eng.prepare(sid, "u1", 7, "新莊富貴500那間現在什麼狀態", config=cfg, role_id="37305")
        assert d["kind"] == "converge"
        g = d["grounding"]
        assert "洽談中" in g                                   # status=4 轉譯
        assert "目前非刊登中" not in g                          # 混軸紅線（物件在刊登清單中）
    finally:
        await _cleanup(pool, sid)


# ── 4.1 診斷中 how-to → switch 出（雙向互轉之二）（R5.3）──
@pytest.mark.req("estate-conversational-facets:5.3")
async def test_diag_switch_out_on_howto(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "物件現況診斷")
    brain = _Brain([
        {"action": "ask", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {}, "next_question": "請問是哪個物件？"},
        {"action": "ask", "converge_kind": "answer", "scope": "switch",
         "extracted_fields": {}, "next_question": ""},
    ])
    eng = _engine(pool, brain, _handler([]))
    sid = "it-estd2-" + os.urandom(3).hex()
    try:
        d1 = await eng.prepare(sid, "u1", 7, "有個物件狀態怪怪的", config=cfg, role_id="37305")
        assert d1["kind"] == "ask"
        d2 = await eng.prepare(sid, "u1", 7, "招租店舖要怎麼分享出去", config=None, role_id="37305")
        assert d2 is None                                      # switch → 關會話重路由
    finally:
        await _cleanup(pool, sid)


# ── 跨域 switch：操作引導中問特定物件現況（R5.3）──
@pytest.mark.req("estate-conversational-facets:5.3")
async def test_guide_switch_out_on_case_specific(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "物件操作引導")
    brain = _Brain([
        {"action": "ask", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {}, "next_question": "想了解哪類操作？"},
        {"action": "ask", "converge_kind": "answer", "scope": "switch",
         "extracted_fields": {}, "next_question": ""},
    ])
    eng = _engine(pool, brain, _handler([]))
    sid = "it-estw-" + os.urandom(3).hex()
    try:
        d1 = await eng.prepare(sid, "u1", 7, "物件怎麼管理", config=cfg, role_id="37305")
        assert d1["kind"] == "ask"
        d2 = await eng.prepare(sid, "u1", 7, "那B棟那間為什麼不能建約", config=None, role_id="37305")
        assert d2 is None                                      # switch → 關會話重路由
        n = await pool.fetchval(
            "SELECT count(*) FROM form_sessions WHERE session_id=$1 AND form_id='conversational' "
            "AND state='COLLECTING'", sid)
        assert n == 0
    finally:
        await _cleanup(pool, sid)
