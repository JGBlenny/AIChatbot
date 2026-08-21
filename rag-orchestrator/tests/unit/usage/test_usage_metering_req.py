"""unit：usage-metering 歸集器（tasks 1.2/1.3/1.4｜R1.3/1.4/2.3/2.4/2.5/3.1/3.2/7.1/8.2）。

契約：contextvar 承載本請求計量；begin 判內部流量與 user_type；add_llm_usage 累計
token；finalize 冪等（雙落點只寫一次）、成本以單價表估算（缺模型留空）、
fire-and-forget（寫入失敗僅 log）；開關關閉全鏈 no-op；不存問題原文（個資負斷言）。
"""
import asyncio
import json
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from services import usage_metering as um

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clean_ctx(monkeypatch):
    """每案重置 contextvar 與開關。"""
    monkeypatch.setenv("USAGE_METERING_ENABLED", "true")
    um._ctx.set(None)
    yield
    um._ctx.set(None)


def _fields(**kw):
    base = {"message": "帳單為什麼發不出去", "vendor_id": 2, "mode": "b2b",
            "target_user": "property_manager", "role_id": "37305",
            "user_id": "u1", "session_id": "web_abc"}
    base.update(kw)
    return base


# ── R2.5：token 合計＝各呼叫 usage 總和 ──
def test_token_accumulation_equals_sum_of_calls():
    um.begin(_fields())
    um.add_llm_usage("gpt-4o-mini", {"prompt_tokens": 100, "completion_tokens": 20})
    um.add_llm_usage("gpt-4o-mini", {"prompt_tokens": 300, "completion_tokens": 50})
    um.add_llm_usage("gpt-3.5-turbo", {"prompt_tokens": 10, "completion_tokens": 5})
    ctx = um._ctx.get()
    assert ctx.llm_calls == 3
    assert ctx.prompt_tokens == 410 and ctx.completion_tokens == 75
    assert ctx.model_breakdown["gpt-4o-mini"]["calls"] == 2


# ── R3.1/3.2：內部流量判定表 ──
@pytest.mark.parametrize("fields,kind", [
    (dict(session_id="backtest_abc_1"), "backtest"),
    (dict(disable_answer_synthesis=True), "backtest"),
    (dict(skip_sop=True), "backtest"),
    (dict(session_id="loop_x"), "loop"),
    (dict(session_id="smoke_x"), "smoke"),
    (dict(session_id="verify_add1"), "smoke"),
])
def test_internal_traffic_rules(fields, kind):
    um.begin(_fields(**fields))
    ctx = um._ctx.get()
    assert ctx.is_internal is True and ctx.internal_kind == kind


def test_normal_traffic_not_internal():
    um.begin(_fields())
    assert um._ctx.get().is_internal is False


# ── user_type 推導矩陣 ──
@pytest.mark.parametrize("fields,expected", [
    (dict(target_user="tenant"), "tenant"),
    (dict(target_user="property_manager"), "property_manager"),
    (dict(target_user=None, mode="b2b", role_id=None), "prospect"),          # b2b 無 role
    (dict(target_user=None, mode="b2b", role_id="37305"), "unknown"),
    (dict(target_user=None, mode="b2c", role_id=None), "tenant"),   # 與 chat 路由推導一致（租客端漏帶防呆）
    (dict(target_user=None, mode="b2b", role_id=None,
          session_id="backtest_x"), "internal"),                             # 內部且無形狀
])
def test_user_type_derivation(fields, expected):
    um.begin(_fields(**fields))
    assert um._ctx.get().user_type == expected


# ── R1.4/R7.1：不存原文，只存長度 ──
def test_no_raw_message_stored():
    um.begin(_fields(message="這是一句包含個資的問題內容"))
    ctx = um._ctx.get()
    assert ctx.message_len == len("這是一句包含個資的問題內容")
    row = um._to_row(ctx)
    assert "這是一句包含個資的問題內容" not in str(row)


# ── finalize 冪等（雙落點防重）＋fire-and-forget ──
async def test_finalize_idempotent_single_write():
    um.begin(_fields())
    writes = []
    async def fake_write(pool, row):
        writes.append(row)
    with patch.object(um, "_write_event", fake_write):
        um.finalize("success", 200, db_pool=object())
        um.finalize("success", 200, db_pool=object())     # 第二落點
        await asyncio.sleep(0)                             # 讓 task 跑
    assert len(writes) == 1
    assert writes[0]["status"] == "success"


async def test_write_failure_does_not_raise():
    um.begin(_fields())
    async def boom(pool, row):
        raise RuntimeError("db down")
    with patch.object(um, "_write_event", boom):
        um.finalize("success", 200, db_pool=object())      # 不得拋出
        await asyncio.sleep(0)


# ── R2.4：成本估算與缺模型留空 ──
def test_cost_known_model():
    um.begin(_fields())
    um.add_llm_usage("gpt-4o-mini", {"prompt_tokens": 1_000_000, "completion_tokens": 0})
    ctx = um._ctx.get()
    um._compute_cost(ctx)
    assert ctx.est_cost_usd == Decimal("0.150000")


def test_cost_unknown_model_left_null():
    um.begin(_fields())
    um.add_llm_usage("some-future-model", {"prompt_tokens": 999, "completion_tokens": 1})
    ctx = um._ctx.get()
    um._compute_cost(ctx)
    assert ctx.est_cost_usd is None
    assert ctx.prompt_tokens == 999                        # token 照記


# ── R8.2：開關關閉全鏈 no-op ──
def test_disabled_noop(monkeypatch):
    monkeypatch.setenv("USAGE_METERING_ENABLED", "false")
    um.begin(_fields())
    assert um._ctx.get() is None
    um.add_llm_usage("gpt-4o-mini", {"prompt_tokens": 1, "completion_tokens": 1})  # 不炸
    um.set_path("knowledge")                                                        # 不炸
    um.finalize("success", 200, db_pool=object())                                   # 不炸


# ── 邊界：無 context 時 add/set 靜默略過 ──
def test_no_context_silent():
    um.add_llm_usage("gpt-4o-mini", {"prompt_tokens": 1, "completion_tokens": 1})
    um.set_path("knowledge")


# ── 日界：date_tpe 以台北時區計 ──
def test_date_tpe_taipei_boundary():
    um.begin(_fields())
    ctx = um._ctx.get()
    from datetime import datetime, timezone
    ctx.ts = datetime(2026, 7, 5, 17, 30, tzinfo=timezone.utc)   # UTC 17:30 = 台北 7/6 01:30
    row = um._to_row(ctx)
    assert str(row["date_tpe"]) == "2026-07-06"


# ════════════════════════════════════════════════════════════
# task 3.2：set_comparison hook＋欄位偵測降級（R3.1/3.3/3.5）
# ════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def _reset_score_cols_cache():
    """每案重置分數欄位偵測快取（模組層狀態）。"""
    orig = um._score_cols_present
    um._score_cols_present = None
    yield
    um._score_cols_present = orig


# ── 矩陣①：ctx None 呼叫不爆 ──
def test_set_comparison_no_context_silent():
    assert um._ctx.get() is None
    um.set_comparison(knowledge_score=0.7, sop_score=0.5, decision_case="knowledge_wins")


# ── 矩陣②：decision_case 截斷 [:60] ──
def test_set_comparison_decision_case_truncated():
    um.begin(_fields())
    long_case = "c" * 200
    um.set_comparison(knowledge_score=0.61, sop_score=0.4, decision_case=long_case)
    ctx = um._ctx.get()
    assert ctx.knowledge_score == 0.61
    assert ctx.sop_score == 0.4
    assert ctx.decision_case == "c" * 60


# ── 矩陣③：finalized 後呼叫不改值 ──
def test_set_comparison_after_finalized_noop():
    um.begin(_fields())
    ctx = um._ctx.get()
    ctx._finalized = True
    um.set_comparison(knowledge_score=0.9, sop_score=0.9, decision_case="late")
    assert ctx.knowledge_score is None
    assert ctx.sop_score is None
    assert ctx.decision_case is None


# ── 矩陣④：偵測為 False（欄位未建）→ _to_row 不含三 key、其餘欄位齊全 ──
def test_to_row_without_score_cols():
    um.begin(_fields())
    ctx = um._ctx.get()
    um.set_comparison(knowledge_score=0.7, sop_score=0.5, decision_case="knowledge_wins")
    um._score_cols_present = False
    row = um._to_row(ctx)
    for k in ("knowledge_score", "sop_score", "decision_case"):
        assert k not in row
    # 其餘既有欄位齊全
    for k in ("request_id", "ts", "date_tpe", "vendor_id", "user_type",
              "message_len", "processing_path", "status", "prompt_tokens",
              "model_breakdown"):
        assert k in row


# ── 矩陣④'：未偵測（None）視同不存在 → _to_row 不含三 key ──
def test_to_row_undetected_omits_score_cols():
    um.begin(_fields())
    ctx = um._ctx.get()
    um.set_comparison(knowledge_score=0.7)
    assert um._score_cols_present is None
    row = um._to_row(ctx)
    for k in ("knowledge_score", "sop_score", "decision_case"):
        assert k not in row


# ── 矩陣⑤：偵測為 True → _to_row 含三 key（含分數值透傳） ──
def test_to_row_with_score_cols():
    um.begin(_fields())
    ctx = um._ctx.get()
    um.set_comparison(knowledge_score=0.72, sop_score=0.33, decision_case="knowledge_wins")
    um._score_cols_present = True
    row = um._to_row(ctx)
    assert row["knowledge_score"] == 0.72
    assert row["sop_score"] == 0.33
    assert row["decision_case"] == "knowledge_wins"


# ── 偵測為 True 但未設分數 → 三 key 存在且為 None（NULL 落地） ──
def test_to_row_score_cols_present_but_none():
    um.begin(_fields())
    ctx = um._ctx.get()
    um._score_cols_present = True
    row = um._to_row(ctx)
    assert row["knowledge_score"] is None
    assert row["sop_score"] is None
    assert row["decision_case"] is None


# ── 降級偵測：欄位齊全 → 快取 True ──
async def test_detect_score_cols_present(mock_db_pool):
    mock_db_pool._conn.fetch = AsyncMock(
        return_value=[{"column_name": c} for c in um._SCORE_COLS])
    await um._detect_score_cols(mock_db_pool)
    assert um._score_cols_present is True


# ── 降級偵測：欄位缺 → 快取 False ──
async def test_detect_score_cols_absent(mock_db_pool):
    mock_db_pool._conn.fetch = AsyncMock(
        return_value=[{"column_name": "knowledge_score"}])   # 缺兩欄
    await um._detect_score_cols(mock_db_pool)
    assert um._score_cols_present is False


# ── 降級偵測：查詢失敗 → 保持 None（下次重試），不外拋 ──
async def test_detect_score_cols_failure_retryable(mock_db_pool):
    mock_db_pool._conn.fetch = AsyncMock(side_effect=RuntimeError("db down"))
    await um._detect_score_cols(mock_db_pool)
    assert um._score_cols_present is None


# ── 降級偵測：已偵測（非 None）則不再查 ──
async def test_detect_score_cols_cached_skips_query(mock_db_pool):
    um._score_cols_present = True
    mock_db_pool._conn.fetch = AsyncMock(side_effect=AssertionError("不應再查"))
    await um._detect_score_cols(mock_db_pool)
    assert um._score_cols_present is True


# ════════════════════════════════════════════════════════════
# task 1.2：set_facet hook＋面向欄位偵測降級（conversational-repair R7.1）
# 契約：完全比照 set_comparison／_detect_score_cols 房式——contextvar 承載、
# ctx None／finalized 靜默、facet_key 截斷 [:60]；欄位未建時事件本體照寫、
# facet_key/turn_number 兩欄略過（欄位未建不能弄壞既有計量）。
# ════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def _reset_facet_cols_cache():
    """每案重置面向欄位偵測快取（模組層狀態）。"""
    orig = um._facet_cols_present
    um._facet_cols_present = None
    yield
    um._facet_cols_present = orig


# ── 矩陣①：ctx 存在時 set_facet 寫入 ctx（turn_number 正常傳遞）──
@pytest.mark.req("conversational-repair:7.1")
def test_set_facet_writes_to_ctx():
    um.begin(_fields())
    um.set_facet(facet_key="contract", turn_number=3)
    ctx = um._ctx.get()
    assert ctx.facet_key == "contract"
    assert ctx.turn_number == 3


# ── 矩陣②：ctx None → 靜默不拋 ──
@pytest.mark.req("conversational-repair:7.1")
def test_set_facet_no_context_silent():
    assert um._ctx.get() is None
    um.set_facet(facet_key="billing", turn_number=1)


# ── 矩陣③：finalized 後呼叫不改值 ──
@pytest.mark.req("conversational-repair:7.1")
def test_set_facet_after_finalized_noop():
    um.begin(_fields())
    ctx = um._ctx.get()
    ctx._finalized = True
    um.set_facet(facet_key="account", turn_number=9)
    assert ctx.facet_key is None
    assert ctx.turn_number is None


# ── 矩陣④：facet_key 超長截斷 [:60] ──
@pytest.mark.req("conversational-repair:7.1")
def test_set_facet_key_truncated():
    um.begin(_fields())
    um.set_facet(facet_key="f" * 200, turn_number=2)
    ctx = um._ctx.get()
    assert ctx.facet_key == "f" * 60
    assert ctx.turn_number == 2


# ── 矩陣⑤：偵測為 False（欄位未建）→ _to_row 不含兩 key、其餘欄位齊全、不拋 ──
@pytest.mark.req("conversational-repair:7.1")
def test_to_row_without_facet_cols():
    um.begin(_fields())
    ctx = um._ctx.get()
    um.set_facet(facet_key="iot", turn_number=4)
    um._facet_cols_present = False
    row = um._to_row(ctx)
    for k in ("facet_key", "turn_number"):
        assert k not in row
    # 既有欄位不受影響
    for k in ("request_id", "ts", "vendor_id", "user_type", "message_len",
              "processing_path", "status", "prompt_tokens", "model_breakdown"):
        assert k in row


# ── 矩陣⑤'：未偵測（None）視同不存在 → _to_row 不含兩 key ──
@pytest.mark.req("conversational-repair:7.1")
def test_to_row_undetected_omits_facet_cols():
    um.begin(_fields())
    ctx = um._ctx.get()
    um.set_facet(facet_key="estate", turn_number=1)
    assert um._facet_cols_present is None
    row = um._to_row(ctx)
    for k in ("facet_key", "turn_number"):
        assert k not in row


# ── 矩陣⑥：偵測為 True → _to_row 含兩 key（值透傳）──
@pytest.mark.req("conversational-repair:7.1")
def test_to_row_with_facet_cols():
    um.begin(_fields())
    ctx = um._ctx.get()
    um.set_facet(facet_key="repair", turn_number=7)
    um._facet_cols_present = True
    row = um._to_row(ctx)
    assert row["facet_key"] == "repair"
    assert row["turn_number"] == 7


# ── 偵測為 True 但未設面向 → 兩 key 存在且為 None（NULL 落地）──
@pytest.mark.req("conversational-repair:7.1")
def test_to_row_facet_cols_present_but_none():
    um.begin(_fields())
    ctx = um._ctx.get()
    um._facet_cols_present = True
    row = um._to_row(ctx)
    assert row["facet_key"] is None
    assert row["turn_number"] is None


# ── 降級偵測：欄位齊全 → 快取 True ──
@pytest.mark.req("conversational-repair:7.1")
async def test_detect_facet_cols_present(mock_db_pool):
    mock_db_pool._conn.fetch = AsyncMock(
        return_value=[{"column_name": c} for c in um._FACET_COLS])
    await um._detect_facet_cols(mock_db_pool)
    assert um._facet_cols_present is True


# ── 降級偵測：欄位缺 → 快取 False ──
@pytest.mark.req("conversational-repair:7.1")
async def test_detect_facet_cols_absent(mock_db_pool):
    mock_db_pool._conn.fetch = AsyncMock(
        return_value=[{"column_name": "facet_key"}])   # 缺 turn_number
    await um._detect_facet_cols(mock_db_pool)
    assert um._facet_cols_present is False


# ── 降級偵測：查詢失敗 → 保持 None（下次重試），不外拋 ──
@pytest.mark.req("conversational-repair:7.1")
async def test_detect_facet_cols_failure_retryable(mock_db_pool):
    mock_db_pool._conn.fetch = AsyncMock(side_effect=RuntimeError("db down"))
    await um._detect_facet_cols(mock_db_pool)
    assert um._facet_cols_present is None


# ── 降級偵測：已偵測（非 None）則不再查 ──
@pytest.mark.req("conversational-repair:7.1")
async def test_detect_facet_cols_cached_skips_query(mock_db_pool):
    um._facet_cols_present = True
    mock_db_pool._conn.fetch = AsyncMock(side_effect=AssertionError("不應再查"))
    await um._detect_facet_cols(mock_db_pool)
    assert um._facet_cols_present is True


# ════════════════════════════════════════════════════════════
# task 1.1：set_search_kb_status hook＋search_kb_status 欄位偵測降級
# （brain-kb-grounding R5.2）
# 契約：完全比照 set_facet／_detect_facet_cols 房式——contextvar 承載、
# ctx None／finalized 靜默、只接受 'hit'/'miss'（越界忽略）；欄位未建時事件本體
# 照寫、search_kb_status 略過（欄位未建不能弄壞既有計量）。
# ════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def _reset_search_kb_col_cache():
    """每案重置 search_kb 欄位偵測快取（模組層狀態）。"""
    orig = um._search_kb_col_present
    um._search_kb_col_present = None
    yield
    um._search_kb_col_present = orig


# ── ①：ctx 存在時 set_search_kb_status 寫入 ctx（hit/miss 正常）──
@pytest.mark.req("brain-kb-grounding:5.2")
@pytest.mark.parametrize("status", ["hit", "miss"])
def test_set_search_kb_status_writes_to_ctx(status):
    um.begin(_fields())
    um.set_search_kb_status(status)
    assert um._ctx.get().search_kb_status == status


# ── ②：ctx None → 靜默不拋 ──
@pytest.mark.req("brain-kb-grounding:5.2")
def test_set_search_kb_status_no_context_silent():
    assert um._ctx.get() is None
    um.set_search_kb_status("hit")


# ── ③：finalized 後呼叫不改值 ──
@pytest.mark.req("brain-kb-grounding:5.2")
def test_set_search_kb_status_after_finalized_noop():
    um.begin(_fields())
    ctx = um._ctx.get()
    ctx._finalized = True
    um.set_search_kb_status("hit")
    assert ctx.search_kb_status is None


# ── ④：越界值忽略（防污染）──
@pytest.mark.req("brain-kb-grounding:5.2")
@pytest.mark.parametrize("bad", ["HIT", "found", "", "true", "1"])
def test_set_search_kb_status_rejects_out_of_domain(bad):
    um.begin(_fields())
    um.set_search_kb_status(bad)
    assert um._ctx.get().search_kb_status is None


# ── ⑤：偵測為 False（欄位未建）→ _to_row 不含 key、其餘欄位齊全、不拋 ──
@pytest.mark.req("brain-kb-grounding:5.2")
def test_to_row_without_search_kb_col():
    um.begin(_fields())
    ctx = um._ctx.get()
    um.set_search_kb_status("hit")
    um._search_kb_col_present = False
    row = um._to_row(ctx)
    assert "search_kb_status" not in row
    for k in ("request_id", "ts", "vendor_id", "user_type", "message_len",
              "processing_path", "status", "prompt_tokens", "model_breakdown"):
        assert k in row


# ── ⑤'：未偵測（None）視同不存在 → _to_row 不含 key ──
@pytest.mark.req("brain-kb-grounding:5.2")
def test_to_row_undetected_omits_search_kb_col():
    um.begin(_fields())
    ctx = um._ctx.get()
    um.set_search_kb_status("miss")
    assert um._search_kb_col_present is None
    row = um._to_row(ctx)
    assert "search_kb_status" not in row


# ── ⑥：偵測為 True → _to_row 含 key（值透傳）──
@pytest.mark.req("brain-kb-grounding:5.2")
def test_to_row_with_search_kb_col():
    um.begin(_fields())
    ctx = um._ctx.get()
    um.set_search_kb_status("hit")
    um._search_kb_col_present = True
    row = um._to_row(ctx)
    assert row["search_kb_status"] == "hit"


# ── ⑥'：偵測為 True 但未呼叫工具 → key 存在且為 None（一般輪 NULL 落地）──
@pytest.mark.req("brain-kb-grounding:5.2")
def test_to_row_search_kb_col_present_but_none():
    um.begin(_fields())
    ctx = um._ctx.get()
    um._search_kb_col_present = True
    row = um._to_row(ctx)
    assert row["search_kb_status"] is None


# ── 降級偵測：欄位存在 → 快取 True ──
@pytest.mark.req("brain-kb-grounding:5.2")
async def test_detect_search_kb_col_present(mock_db_pool):
    mock_db_pool._conn.fetch = AsyncMock(
        return_value=[{"column_name": c} for c in um._SEARCH_KB_COLS])
    await um._detect_search_kb_col(mock_db_pool)
    assert um._search_kb_col_present is True


# ── 降級偵測：欄位缺 → 快取 False ──
@pytest.mark.req("brain-kb-grounding:5.2")
async def test_detect_search_kb_col_absent(mock_db_pool):
    mock_db_pool._conn.fetch = AsyncMock(return_value=[])
    await um._detect_search_kb_col(mock_db_pool)
    assert um._search_kb_col_present is False


# ── 降級偵測：查詢失敗 → 保持 None（下次重試），不外拋 ──
@pytest.mark.req("brain-kb-grounding:5.2")
async def test_detect_search_kb_col_failure_retryable(mock_db_pool):
    mock_db_pool._conn.fetch = AsyncMock(side_effect=RuntimeError("db down"))
    await um._detect_search_kb_col(mock_db_pool)
    assert um._search_kb_col_present is None


# ── 降級偵測：已偵測（非 None）則不再查 ──
@pytest.mark.req("brain-kb-grounding:5.2")
async def test_detect_search_kb_col_cached_skips_query(mock_db_pool):
    um._search_kb_col_present = True
    mock_db_pool._conn.fetch = AsyncMock(side_effect=AssertionError("不應再查"))
    await um._detect_search_kb_col(mock_db_pool)
    assert um._search_kb_col_present is True


# ════════════════════════════════════════════════════════════
# retrieval-decision-layer 任務 1.2：set_decision hook＋決策快照欄位偵測降級
# （R8.3：每輪落決策快照，使任何路由不一致可事後歸因）
# 契約：比照 set_facet／_detect_facet_cols 房式——contextvar 承載、ctx None／
# finalized 靜默、facet_event 截斷 [:30]；欄位未建時事件本體照寫、兩欄略過。
# 額外契約（本 hook 特有）：同輪多次 set_decision 的快照**不得靜默覆蓋**——
# 同 key 值衝突時舊快照整份進 prior（E-5 歸因要看得見同輪擺盪）。
# ════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def _reset_decision_cols_cache():
    """每案重置決策快照欄位偵測快取（模組層狀態）。"""
    orig = um._decision_cols_present
    um._decision_cols_present = None
    yield
    um._decision_cols_present = orig


# ── 矩陣①：ctx 存在時 set_decision 寫入 ctx ──
@pytest.mark.req("retrieval-decision-layer:8.3")
def test_set_decision_writes_to_ctx():
    um.begin(_fields())
    um.set_decision(snapshot={"verdict": "direct_answer", "kb_top1_final": 0.61},
                    facet_event="none")
    ctx = um._ctx.get()
    assert ctx.decision_snapshot == {"verdict": "direct_answer", "kb_top1_final": 0.61}
    assert ctx.facet_event == "none"


# ── 矩陣②：ctx None → 靜默不拋 ──
@pytest.mark.req("retrieval-decision-layer:8.3")
def test_set_decision_no_context_silent():
    assert um._ctx.get() is None
    um.set_decision(snapshot={"verdict": "fallback"}, facet_event="exit_requery")


# ── 矩陣③：finalized 後呼叫不改值 ──
@pytest.mark.req("retrieval-decision-layer:8.3")
def test_set_decision_after_finalized_noop():
    um.begin(_fields())
    ctx = um._ctx.get()
    ctx._finalized = True
    um.set_decision(snapshot={"verdict": "enter_facet"}, facet_event="enter")
    assert ctx.decision_snapshot is None
    assert ctx.facet_event is None


# ── 矩陣④：facet_event 超長截斷 [:30]（欄位 VARCHAR(30)）──
@pytest.mark.req("retrieval-decision-layer:8.3")
def test_set_decision_facet_event_truncated():
    um.begin(_fields())
    um.set_decision(facet_event="e" * 90)
    assert um._ctx.get().facet_event == "e" * 30


# ── 矩陣④'：只給 facet_event 不給 snapshot（兩參數各自獨立）──
@pytest.mark.req("retrieval-decision-layer:8.3")
def test_set_decision_partial_args_independent():
    um.begin(_fields())
    um.set_decision(snapshot={"verdict": "enter_facet"})
    um.set_decision(facet_event="degrade_knowledge")
    ctx = um._ctx.get()
    assert ctx.decision_snapshot == {"verdict": "enter_facet"}
    assert ctx.facet_event == "degrade_knowledge"


# ── 矩陣⑤：同輪二次呼叫、key 不衝突 → 淺層合併（不產生 prior）──
@pytest.mark.req("retrieval-decision-layer:8.3")
def test_set_decision_merges_disjoint_keys():
    um.begin(_fields())
    um.set_decision(snapshot={"verdict": "enter_facet", "gray_zone": True})
    um.set_decision(snapshot={"rule_version": "v1"})
    ctx = um._ctx.get()
    assert ctx.decision_snapshot == {"verdict": "enter_facet", "gray_zone": True,
                                     "rule_version": "v1"}
    assert "prior" not in ctx.decision_snapshot


# ── 矩陣⑥：同輪二次決策且值衝突 → 舊快照整份進 prior，不得靜默消失 ──
@pytest.mark.req("retrieval-decision-layer:8.3")
def test_set_decision_conflicting_write_keeps_prior():
    um.begin(_fields())
    um.set_decision(snapshot={"verdict": "enter_facet", "facet_key": "billing"})
    um.set_decision(snapshot={"verdict": "direct_answer"})   # exit_requery 後重判
    snap = um._ctx.get().decision_snapshot
    assert snap["verdict"] == "direct_answer"
    assert snap["facet_key"] == "billing"                    # 未衝突的 key 保留
    assert snap["prior"] == [{"verdict": "enter_facet", "facet_key": "billing"}]


# ── 矩陣⑥'：prior 有上限，不得無限膨脹（事件列大小可控）──
@pytest.mark.req("retrieval-decision-layer:8.3")
def test_set_decision_prior_capped():
    um.begin(_fields())
    for i in range(um._DECISION_PRIOR_MAX + 3):
        um.set_decision(snapshot={"verdict": "v%d" % i})
    snap = um._ctx.get().decision_snapshot
    assert len(snap["prior"]) == um._DECISION_PRIOR_MAX
    assert snap["verdict"] == "v%d" % (um._DECISION_PRIOR_MAX + 2)   # 最後一筆為現值
    assert snap["prior"][-1]["verdict"] == "v%d" % (um._DECISION_PRIOR_MAX + 1)


# ── 矩陣⑦：偵測為 False（欄位未建）→ _to_row 不含兩 key、其餘欄位齊全、不拋 ──
@pytest.mark.req("retrieval-decision-layer:8.3")
def test_to_row_without_decision_cols():
    um.begin(_fields())
    ctx = um._ctx.get()
    um.set_decision(snapshot={"verdict": "fallback"}, facet_event="none")
    um._decision_cols_present = False
    row = um._to_row(ctx)
    for k in ("decision_snapshot", "facet_event"):
        assert k not in row
    for k in ("request_id", "ts", "vendor_id", "user_type", "message_len",
              "processing_path", "status", "prompt_tokens", "model_breakdown"):
        assert k in row


# ── 矩陣⑦'：未偵測（None）視同不存在 → _to_row 不含兩 key ──
@pytest.mark.req("retrieval-decision-layer:8.3")
def test_to_row_undetected_omits_decision_cols():
    um.begin(_fields())
    ctx = um._ctx.get()
    um.set_decision(snapshot={"verdict": "form"})
    assert um._decision_cols_present is None
    row = um._to_row(ctx)
    for k in ("decision_snapshot", "facet_event"):
        assert k not in row


# ── 矩陣⑧：偵測為 True → decision_snapshot 以 JSON 字串落地（jsonb 需 str）──
@pytest.mark.req("retrieval-decision-layer:8.3")
def test_to_row_with_decision_cols_serialized():
    um.begin(_fields())
    ctx = um._ctx.get()
    um.set_decision(snapshot={"verdict": "enter_facet", "facet_key": "合約"},
                    facet_event="enter")
    um._decision_cols_present = True
    row = um._to_row(ctx)
    assert isinstance(row["decision_snapshot"], str)         # 比照 model_breakdown
    assert json.loads(row["decision_snapshot"]) == {"verdict": "enter_facet",
                                                    "facet_key": "合約"}
    assert "\\u" not in row["decision_snapshot"]             # ensure_ascii=False
    assert row["facet_event"] == "enter"


# ── 矩陣⑧'：偵測為 True 但未設決策 → 兩 key 存在且為 None（NULL 落地，非 "null"）──
@pytest.mark.req("retrieval-decision-layer:8.3")
def test_to_row_decision_cols_present_but_none():
    um.begin(_fields())
    ctx = um._ctx.get()
    um._decision_cols_present = True
    row = um._to_row(ctx)
    assert row["decision_snapshot"] is None
    assert row["facet_event"] is None


# ── 矩陣⑨：非 JSON 原生型別（Decimal/datetime 等）以 str 收編，快照不因此整欄丟失 ──
@pytest.mark.req("retrieval-decision-layer:8.3")
def test_to_row_non_json_native_values_coerced():
    um.begin(_fields())
    ctx = um._ctx.get()
    um.set_decision(snapshot={"verdict": "direct_answer", "score": Decimal("0.61")})
    um._decision_cols_present = True
    row = um._to_row(ctx)
    snap = json.loads(row["decision_snapshot"])
    assert snap["verdict"] == "direct_answer"
    assert snap["score"] == "0.61"                           # default=str 收編


# ── 矩陣⑨'：真的序列化不了（循環參照）→ 只丟這一欄，事件本體照寫（寧漏勿堵 R1.3）──
@pytest.mark.req("retrieval-decision-layer:8.3")
def test_to_row_unserializable_snapshot_degrades():
    um.begin(_fields())
    ctx = um._ctx.get()
    cyclic = {"verdict": "direct_answer"}
    cyclic["self"] = cyclic
    um.set_decision(snapshot=cyclic)
    um._decision_cols_present = True
    row = um._to_row(ctx)
    assert row["decision_snapshot"] is None
    for k in ("request_id", "status", "model_breakdown"):
        assert k in row


# ── 降級偵測：欄位齊全 → 快取 True ──
@pytest.mark.req("retrieval-decision-layer:8.3")
async def test_detect_decision_cols_present(mock_db_pool):
    mock_db_pool._conn.fetch = AsyncMock(
        return_value=[{"column_name": c} for c in um._DECISION_COLS])
    await um._detect_decision_cols(mock_db_pool)
    assert um._decision_cols_present is True


# ── 降級偵測：欄位缺 → 快取 False ──
@pytest.mark.req("retrieval-decision-layer:8.3")
async def test_detect_decision_cols_absent(mock_db_pool):
    mock_db_pool._conn.fetch = AsyncMock(
        return_value=[{"column_name": "facet_event"}])       # 缺 decision_snapshot
    await um._detect_decision_cols(mock_db_pool)
    assert um._decision_cols_present is False


# ── 降級偵測：查詢失敗 → 保持 None（下次重試），不外拋 ──
@pytest.mark.req("retrieval-decision-layer:8.3")
async def test_detect_decision_cols_failure_retryable(mock_db_pool):
    mock_db_pool._conn.fetch = AsyncMock(side_effect=RuntimeError("db down"))
    await um._detect_decision_cols(mock_db_pool)
    assert um._decision_cols_present is None


# ── 降級偵測：已偵測（非 None）則不再查 ──
@pytest.mark.req("retrieval-decision-layer:8.3")
async def test_detect_decision_cols_cached_skips_query(mock_db_pool):
    um._decision_cols_present = True
    mock_db_pool._conn.fetch = AsyncMock(side_effect=AssertionError("不應再查"))
    await um._detect_decision_cols(mock_db_pool)
    assert um._decision_cols_present is True


# ── finalize 串接：三組既有偵測之外，決策欄偵測亦須在 fire-and-forget 內執行 ──
@pytest.mark.req("retrieval-decision-layer:8.3")
async def test_finalize_detects_decision_cols(mock_db_pool):
    um.begin(_fields())
    um.set_decision(snapshot={"verdict": "direct_answer"}, facet_event="none")
    mock_db_pool._conn.fetch = AsyncMock(
        return_value=[{"column_name": c} for c in um._DECISION_COLS])
    um.finalize(db_pool=mock_db_pool)
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert um._decision_cols_present is True
