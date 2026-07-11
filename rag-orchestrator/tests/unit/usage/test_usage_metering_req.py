"""unit：usage-metering 歸集器（tasks 1.2/1.3/1.4｜R1.3/1.4/2.3/2.4/2.5/3.1/3.2/7.1/8.2）。

契約：contextvar 承載本請求計量；begin 判內部流量與 user_type；add_llm_usage 累計
token；finalize 冪等（雙落點只寫一次）、成本以單價表估算（缺模型留空）、
fire-and-forget（寫入失敗僅 log）；開關關閉全鏈 no-op；不存問題原文（個資負斷言）。
"""
import asyncio
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
