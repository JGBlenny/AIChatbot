"""integration:IoT 面向資料四件套整合驗證（iot-conversational-facets 任務 2.4 / R1, R2, R3, R6）。

真 DB＋真 get_system_context＋真 config_for_category＋真引擎＋真 get_meters adapter
（stub 到 jgb_api._request 層，wrapper 的 client 端 keyword 過濾真跑）；brain 腳本化。

驗證：兩面向進場；三層脈絡疊加（母薄層＋子；不含前三域層與售前）；
電表排障 identify→過濾→候選/直中→四分支 facts；設定引導 category 收斂
（target_user 明填生效；fixture 自插測試知識不依賴第 3 節）；面向互轉保留識別；
跨域 switch。fixture 冪等套用三支種子；無法連 DB → skip。
"""
import os

import pytest
from unittest.mock import AsyncMock


pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _force_mock_jgb(monkeypatch):
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")

_MIG = os.path.join(os.path.dirname(__file__), "..", "..", "..", "database", "migrations")
FACETS = ["電表排障", "IoT設定引導"]
_SEEDS = ["split_base_system_context_extract_presales.sql",
          "add_iot_facet_categories.sql",
          "seed_iot_facet_system_context.sql",
          "seed_iot_facet_configs.sql"]

_TEST_KB_SUMMARY = "IT測試-電表串接教學"   # fixture 自插（teardown 刪），供 category 收斂有資料


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
    # 設定引導收斂資料源（第 3 節知識未產前以測試列頂替；target_user 明填驗證用）
    await p.execute(
        "INSERT INTO knowledge_base (question_summary, answer, category, categories, target_user, is_active) "
        "SELECT $1, '串接教學測試內容：綁定台科電帳號後系統自動同步裝置清單。', '一般知識', "
        "ARRAY['IoT設定引導']::text[], ARRAY['property_manager']::text[], TRUE "
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


def _meter(**over):
    m = {"id": 501, "estate_id": 9001, "estate_name": "海大質感獨立套房",
         "name": "3F 分電表", "manufacturer": "DAE", "meter_type": "cloud",
         "is_online": True, "is_topup": True, "enable_topup": True,
         "balance": 0.0, "available_meter": 0.0, "current_reading": 1234.5,
         "is_poweron": False, "is_low_battery": False,
         "synced_at": "2026-07-04 10:35:00"}
    m.update(over)
    return m


def _handler(meter_rows):
    """真實 APICallHandler＋真 get_meters adapter：stub 到 _request 層，
    wrapper 的 client 端 keyword 過濾真跑（adapter 當受測物）。"""
    from services.api_call_handler import APICallHandler
    handler = APICallHandler(db_pool=None)
    handler.jgb_api.use_mock = False
    handler.jgb_api._request = AsyncMock(return_value={"success": True, "data": meter_rows})
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
@pytest.mark.req("iot-conversational-facets:1.2")
async def test_both_facets_enter_by_category(pool):
    from services import conversational_config as cc
    from services.conversational_rules import load_rules
    for facet in FACETS:
        cfg = await cc.config_for_category(pool, facet)
        assert cfg is not None and cfg.enabled, f"{facet} 進場 config 缺"
        assert cfg.persona_role.startswith("pm_iot_")
        rules = await load_rules(pool, cfg.persona_role)
        assert rules and "JGB" in rules
        assert "不代" in rules or "只指路" in rules or "不代執行" in rules   # 不代操作紅線


# ── 三層脈絡：base＋母智慧設備（薄）＋命中子；不含他域層（R1.3）──
@pytest.mark.req("iot-conversational-facets:1.3")
async def test_three_layer_context_isolated(pool):
    from services import system_context as sc
    markers = {"電表排障": "自動復電", "IoT設定引導": "單價"}
    for facet, marker in markers.items():
        sc.reset_cache()
        md = await sc.get_system_context(pool, facet)
        assert "手動抄表" in md, f"{facet} 缺母『智慧設備』層"       # 母薄層名詞對照
        assert marker in md, f"{facet} 缺自身子面向層"
        for pm in ("競品處理協定", "CTA 出口", "功能對照索引"):
            assert pm not in md                                   # 不含售前 append
        assert "12 里程碑" not in md, "混入合約領域層"
        assert "待對帳" not in md, "混入帳務領域層"
        assert "一人一個主帳號" not in md, "混入帳號領域層"


# ── 電表排障：identify→client 過濾→候選/直中→四分支 facts（R2.1/R2.2）──
@pytest.mark.req("iot-conversational-facets:2.2")
async def test_meter_flow_filter_then_exhausted_branch(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "電表排障")
    rows = [_meter()]                                             # 儲值耗盡態
    brain = _Brain([
        {"action": "ask", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {"symptom": "沒電"},
         "next_question": "請問是哪個物件或房號的電表？"},
        {"action": "converge", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {"meter_ref": "海大"}},
    ])
    eng = _engine(pool, brain, _handler(rows))
    sid = "it-iot-" + os.urandom(3).hex()
    try:
        d1 = await eng.prepare(sid, "u1", 7, "租客說房間沒電了", config=cfg, role_id="37305")
        assert d1["kind"] == "ask"                                # 追問識別
        d2 = await eng.prepare(sid, "u1", 7, "海大那間", config=None, role_id="37305")
        assert d2["kind"] == "converge"
        g = d2["grounding"]
        assert "自動復電" in g and "儲值" in g                     # 耗盡分支
        assert "0" in g                                           # 餘額存值原樣
    finally:
        await _cleanup(pool, sid)


@pytest.mark.req("iot-conversational-facets:2.1")
async def test_meter_flow_multiple_candidates(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "電表排障")
    rows = [_meter(id=501, name="3F 分電表"), _meter(id=502, name="1F 主電表")]
    brain = _Brain([{"action": "converge", "converge_kind": "answer", "scope": "stay",
                     "extracted_fields": {"meter_ref": "海大"}}])
    eng = _engine(pool, brain, _handler(rows))
    sid = "it-iotc-" + os.urandom(3).hex()
    try:
        d = await eng.prepare(sid, "u1", 7, "海大那間的電表怪怪的", config=cfg, role_id="37305")
        assert d["kind"] == "ask" and d.get("answer")             # 2 顆 → 列候選
        state = await eng.get_state(sid)
        labels = [c["label"] for c in (state.get("pending_candidates") or [])]
        assert len(labels) == 2
        assert any("3F 分電表" in lb for lb in labels)
        assert any("海大質感獨立套房" in lb for lb in labels)      # label 帶物件名
    finally:
        await _cleanup(pool, sid)


@pytest.mark.req("iot-conversational-facets:2.3")
async def test_meter_flow_offline_snapshot_wording(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "電表排障")
    rows = [_meter(is_online=False, is_poweron=True)]
    brain = _Brain([{"action": "converge", "converge_kind": "answer", "scope": "stay",
                     "extracted_fields": {"meter_ref": "海大"}}])
    eng = _engine(pool, brain, _handler(rows))
    sid = "it-iotoff-" + os.urandom(3).hex()
    try:
        d = await eng.prepare(sid, "u1", 7, "海大的電表離線了", config=cfg, role_id="37305")
        assert d["kind"] == "converge"
        g = d["grounding"]
        assert "離線" in g and "2026-07-04 10:35" in g            # 快照措辭
        assert "供電正常" not in g                                # 離線不下供電結論（J-I1）
        assert "帳號" in g                                        # DAE 帳密真因
    finally:
        await _cleanup(pool, sid)


# ── 設定引導：category 收斂（target_user 明填生效）＋面向互轉保留識別（R3.1/R6.1）──
@pytest.mark.req("iot-conversational-facets:3.1")
async def test_setup_guide_category_grounding_and_face_switch(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "IoT設定引導")
    brain = _Brain([
        {"action": "converge", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {"topic": "串接"}},
    ])
    eng = _engine(pool, brain, _handler([]))
    sid = "it-iotset-" + os.urandom(3).hex()
    try:
        d = await eng.prepare(sid, "u1", 7, "電表要怎麼串接進來", config=cfg, role_id="37305")
        assert d["kind"] == "converge"
        assert "串接教學測試內容" in d["grounding"]                # category 收斂吃到掛面向知識
    finally:
        await _cleanup(pool, sid)


# ── 跨域 switch：儲值金流話題 → 關會話重路由（→帳務）（R6.2）──
@pytest.mark.req("iot-conversational-facets:6.2")
async def test_cross_domain_switch_to_billing(pool):
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "電表排障")
    brain = _Brain([
        {"action": "ask", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {}, "next_question": "請問是哪個物件的電表？"},
        {"action": "converge", "converge_kind": "answer", "scope": "switch",
         "extracted_fields": {}},
    ])
    eng = _engine(pool, brain, _handler([]))
    sid = "it-iotxd-" + os.urandom(3).hex()
    try:
        d1 = await eng.prepare(sid, "u1", 7, "電表有點問題", config=cfg, role_id="37305")
        assert d1["kind"] == "ask"
        d2 = await eng.prepare(sid, "u1", 7, "租客儲值的錢到底入帳了沒", config=None, role_id="37305")
        assert d2 is None                                         # switch → 關會話重路由
        n = await pool.fetchval(
            "SELECT count(*) FROM form_sessions WHERE session_id=$1 AND form_id='conversational' "
            "AND state='COLLECTING'", sid)
        assert n == 0
    finally:
        await _cleanup(pool, sid)


# ════════ 任務 4.1 補全流程：四分支其餘兩案＋設定引導兩輪分流＋switch 第二向 ════════

@pytest.mark.req("iot-conversational-facets:2.2")
async def test_meter_flow_poweroff_switch_branch(pool):
    """online＋poweron=false＋餘額足 → 供電關閉分支（不臆測原因＋模式切換指路）。"""
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "電表排障")
    rows = [_meter(is_poweron=False, balance=350.0, available_meter=87.5)]
    brain = _Brain([{"action": "converge", "converge_kind": "answer", "scope": "stay",
                     "extracted_fields": {"meter_ref": "海大"}}])
    eng = _engine(pool, brain, _handler(rows))
    sid = "it-iotpo-" + os.urandom(3).hex()
    try:
        d = await eng.prepare(sid, "u1", 7, "海大的電表沒在供電", config=cfg, role_id="37305")
        assert d["kind"] == "converge"
        g = d["grounding"]
        assert "關閉" in g and "原因" in g                        # 無原因紀錄不臆測
        assert "供電模式" in g or "IoT 裝置" in g                 # 指路
        assert "排除儲值因素" in g                                # 餘額足註記
    finally:
        await _cleanup(pool, sid)


@pytest.mark.req("iot-conversational-facets:2.2")
async def test_meter_flow_normal_turns_hardware(pool):
    """online＋poweron=true → 供電正常轉硬體/確認問對表。"""
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "電表排障")
    rows = [_meter(is_poweron=True, balance=350.0, available_meter=87.5)]
    brain = _Brain([{"action": "converge", "converge_kind": "answer", "scope": "stay",
                     "extracted_fields": {"meter_ref": "海大"}}])
    eng = _engine(pool, brain, _handler(rows))
    sid = "it-iotok-" + os.urandom(3).hex()
    try:
        d = await eng.prepare(sid, "u1", 7, "海大那間說沒電 但我看電表好像正常", config=cfg, role_id="37305")
        assert d["kind"] == "converge"
        g = d["grounding"]
        assert "正常" in g
        assert "台科電" in g or "廠商" in g                       # 硬體轉向
    finally:
        await _cleanup(pool, sid)


@pytest.mark.req("iot-conversational-facets:3.1")
async def test_setup_guide_two_round_triage(pool):
    """設定引導兩輪分流：先問設定對象 → 回答後收斂（機制 facts 進底稿）。"""
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "IoT設定引導")
    brain = _Brain([
        {"action": "ask", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {}, "next_question": "請問要設定電表串接、儲值單價，還是門鎖密碼規則？"},
        {"action": "converge", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {"topic": "串接"}},
    ])
    eng = _engine(pool, brain, _handler([]))
    sid = "it-iot2r-" + os.urandom(3).hex()
    try:
        d1 = await eng.prepare(sid, "u1", 7, "IoT 要怎麼設定", config=cfg, role_id="37305")
        assert d1["kind"] == "ask"                                # 第一輪分流
        d2 = await eng.prepare(sid, "u1", 7, "電表串接", config=None, role_id="37305")
        assert d2["kind"] == "converge"
        assert "串接教學測試內容" in d2["grounding"]               # category 收斂
    finally:
        await _cleanup(pool, sid)


@pytest.mark.req("iot-conversational-facets:6.2")
async def test_cross_domain_switch_to_account(pool):
    """switch 第二向：租客登入視角話題 → 關會話重路由（→帳號域）。"""
    from services import conversational_config as cc
    cfg = await cc.config_for_category(pool, "電表排障")
    brain = _Brain([
        {"action": "ask", "converge_kind": "answer", "scope": "stay",
         "extracted_fields": {}, "next_question": "請問是哪個物件的電表？"},
        {"action": "converge", "converge_kind": "answer", "scope": "switch",
         "extracted_fields": {}},
    ])
    eng = _engine(pool, brain, _handler([]))
    sid = "it-iotxa-" + os.urandom(3).hex()
    try:
        d1 = await eng.prepare(sid, "u1", 7, "電表有問題", config=cfg, role_id="37305")
        assert d1["kind"] == "ask"
        d2 = await eng.prepare(sid, "u1", 7, "租客說他根本登不進去系統", config=None, role_id="37305")
        assert d2 is None
        n = await pool.fetchval(
            "SELECT count(*) FROM form_sessions WHERE session_id=$1 AND form_id='conversational' "
            "AND state='COLLECTING'", sid)
        assert n == 0
    finally:
        await _cleanup(pool, sid)
