"""unit：quota-management 檢查器與文案（任務 1｜R1.2/2.1-2.5/3.1-3.3/4.2-4.4/5.2）。

狀態機：none（未設/停用/內部/計量關）→ ok → warn（≥閾值）→ blocked（≥額度且攔截開；
寬限模式維持 warn）。文案受眾分流（pm 加值引導/其餘中性）。body 改寫 append-only。
fail-open：任何例外回 none。
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from services import usage_metering as um

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.setenv("USAGE_METERING_ENABLED", "true")
    um._quota_cache.clear()
    yield
    um._quota_cache.clear()


def _pool(quota_row, used):
    """mock asyncpg pool：fetchrow 回設定列、fetchval 回本月 count。"""
    conn = MagicMock()
    conn.fetchrow = AsyncMock(return_value=quota_row)
    conn.fetchval = AsyncMock(return_value=used)
    acq = MagicMock()
    acq.__aenter__ = AsyncMock(return_value=conn)
    acq.__aexit__ = AsyncMock(return_value=False)
    pool = MagicMock()
    pool.acquire = MagicMock(return_value=acq)
    return pool


def _row(quota=5000, warn=80, block=True, active=True):
    return {"monthly_message_quota": quota, "warn_threshold_pct": warn,
            "block_on_exceed": block, "is_active": active}


# ── 狀態機矩陣 ──
async def test_no_quota_row_none():
    qs = await um.quota_check(_pool(None, 0), vendor_id=2, is_internal=False)
    assert qs.state == "none"


async def test_inactive_row_none():
    qs = await um.quota_check(_pool(_row(active=False), 100), 2, False)
    assert qs.state == "none"


async def test_internal_traffic_none():
    qs = await um.quota_check(_pool(_row(), 4999), 2, is_internal=True)
    assert qs.state == "none"                      # 內部不計不攔（R2.2）


async def test_metering_disabled_none(monkeypatch):
    monkeypatch.setenv("USAGE_METERING_ENABLED", "false")
    qs = await um.quota_check(_pool(_row(), 100), 2, False)
    assert qs.state == "none"                      # R2.5


@pytest.mark.parametrize("used,expected", [
    (0, "ok"), (3999, "ok"),
    (4000, "warn"),          # 80% 邊界（≥閾值進警示）
    (4999, "warn"),
    (5000, "blocked"),       # ≥額度
    (6000, "blocked"),
])
async def test_state_machine_boundaries(used, expected):
    qs = await um.quota_check(_pool(_row(), used), 2, False)
    assert qs.state == expected
    assert qs.used == used and qs.quota == 5000


async def test_grace_mode_stays_warn():
    qs = await um.quota_check(_pool(_row(block=False), 9999), 2, False)
    assert qs.state == "warn"                      # 寬限模式不攔（R4.4）


async def test_fail_open_on_db_error():
    pool = MagicMock()
    pool.acquire = MagicMock(side_effect=RuntimeError("db down"))
    qs = await um.quota_check(pool, 2, False)
    assert qs.state == "none"                      # R5.2


async def test_cache_hit_within_ttl():
    pool = _pool(_row(), 100)
    await um.quota_check(pool, 2, False)
    await um.quota_check(pool, 2, False)
    conn = pool.acquire.return_value.__aenter__.return_value
    assert conn.fetchrow.await_count == 1          # 第二次走快取


# ── 文案分流（R4.2/R4.3）──
def test_blocked_body_pm_has_topup_guidance():
    body = um.quota_blocked_body("property_manager", um.QuotaState("blocked", 5000, 5000, 100),
                                 {"mode": "b2b", "session_id": "s1"})
    assert "加值" in body["answer"] and "5,000" in body["answer"]
    assert body["action_type"] == "quota_blocked" and body["source_count"] == 0


@pytest.mark.parametrize("ut", ["tenant", "prospect", "unknown"])
def test_blocked_body_non_pm_neutral(ut):
    body = um.quota_blocked_body(ut, um.QuotaState("blocked", 5000, 5000, 100),
                                 {"mode": "b2c", "session_id": "s1"})
    assert "加值" not in body["answer"] and "額度" not in body["answer"]   # 無商業字眼（R4.3）
    assert "客服" in body["answer"] or "管理公司" in body["answer"]


# ── 警示改寫（R3.1–3.3）──
def test_append_hint_pm_json():
    raw = json.dumps({"answer": "正常回答", "mode": "b2b"}).encode()
    out = um.append_quota_hint(raw, "property_manager",
                               um.QuotaState("warn", 4100, 5000, 82))
    d = json.loads(out)
    assert d["answer"].startswith("正常回答")          # append-only
    assert "82%" in d["answer"] and "4,100/5,000" in d["answer"]
    assert d["mode"] == "b2b"                          # 其他欄位不動


@pytest.mark.parametrize("ut", ["tenant", "prospect"])
def test_append_hint_skipped_for_non_pm(ut):
    raw = json.dumps({"answer": "正常回答"}).encode()
    assert um.append_quota_hint(raw, ut, um.QuotaState("warn", 4100, 5000, 82)) is None


def test_append_hint_non_json_safe():
    assert um.append_quota_hint(b"not-json", "property_manager",
                                um.QuotaState("warn", 1, 5000, 1)) is None   # 改寫失敗回 None 走原回應


# ── 2026-07-06 改判：警示不進對話改寄信（每月首次跨閾值一次）──
async def test_warn_email_claim_once_per_month():
    """UPDATE 標記當裁判：首次 claim 成功觸發寄信路徑，同月第二次不寄。"""
    sent = []
    conn = MagicMock()
    conn.execute = AsyncMock(side_effect=["UPDATE 1", "UPDATE 0"])
    conn.fetchrow = AsyncMock(return_value={"name": "測試業者", "contact_email": None})
    acq = MagicMock(); acq.__aenter__ = AsyncMock(return_value=conn); acq.__aexit__ = AsyncMock(return_value=False)
    pool = MagicMock(); pool.acquire = MagicMock(return_value=acq)
    import services.usage_metering as m
    orig = m._smtp_configured
    m._smtp_configured = lambda: False          # SMTP 未設 → 走 log 分支（不炸）
    try:
        await um._maybe_send_warn_email(pool, 2, um.QuotaState("warn", 4100, 5000, 82))
        await um._maybe_send_warn_email(pool, 2, um.QuotaState("warn", 4200, 5000, 84))
        assert conn.fetchrow.await_count == 1   # 第二次 claim 失敗提前返回，不再查 vendor
    finally:
        m._smtp_configured = orig


async def test_warn_email_failure_never_raises():
    pool = MagicMock()
    pool.acquire = MagicMock(side_effect=RuntimeError("db down"))
    await um._maybe_send_warn_email(pool, 2, um.QuotaState("warn", 1, 5, 20))  # 不得拋
