"""integration（真 PG）：A+ 片 AP-3——`tools/confirm.pending_token_state` 的唯讀查詢對真表的判定。

凍結驗收清單 `.kiro/specs/agentic-mcp-orchestration/acceptance-card-program-only-aplus-20261019.md`
V4（單元＋DB）、V8 (2)（9q 型）的 DB 證據：單元測試的 `FakeTokenDB` 只認 SQL 常數，這裡讓
`_PENDING_TOKEN_STATE_SQL` 真的在 PG 上跑——剩餘秒數以 DB `now()` 計、`redeemed` 優先於過期、
雙鍵（`pending_id`＋`session_id`）過濾、查詢不改任何列。

出卡走正式碼 `confirm_request`（同 `test_step3_unique_card_pg_req.py` 的 `_issue`）；調整到期時間／
兌現狀態只對本檔 `session_id` 前綴的列下 `UPDATE`，finally 由共用 `pool` fixture 清掉。
DB 安全：`tests/conftest.py` 的守門（`DB_ENV` 已設且非 production、`DB_NAME` 非產線預設、
`RUN_INTEGRATION=1`）。
"""
from __future__ import annotations

import uuid

import pytest

from services.agent.tools import confirm as C

from tests.integration.agent.test_step3_unique_card_pg_req import (  # noqa: F401 — fixture 匯入
    _SESSION_PREFIX, _freeze_today, _issue, pool,
)

pytestmark = pytest.mark.integration


async def _row(pool, pid: str, sid: str) -> dict:
    r = await pool.fetchrow(
        "SELECT token, session_id, payload_sha256, summary_sha256, expires_at, redeemed, pending_id "
        "FROM agent_confirmation_tokens WHERE pending_id = $1 AND session_id = $2", pid, sid)
    assert r is not None, "前提不成立：出卡沒有寫進 token 表"
    return dict(r)


async def _card(pool, monkeypatch):
    monkeypatch.setenv("AGENT_WRITE_LIFECYCLE", "off")             # 預檢會讀 JGB；本檔只驗 token 表
    sid = _SESSION_PREFIX + "aplus_" + uuid.uuid4().hex[:12]
    res = await _issue(pool, sid, 3)
    assert res.ok, res
    pid = res.data["pending_id"]
    return sid, pid, await _row(pool, pid, sid)


async def test_live_card_is_live_with_both_hashes_matching_and_row_unchanged(pool, monkeypatch):
    """剛出的卡 ⇒ `live`、兩把雜湊比對成立；查詢前後該列逐欄不變（純 SELECT）。"""
    sid, pid, before = await _card(pool, monkeypatch)
    st = await C.pending_token_state(pool, sid, pid, card_sha256=before["summary_sha256"],
                                     payload_sha256=before["payload_sha256"])
    assert (st.state, st.summary_match, st.payload_match) == (C.PENDING_STATE_LIVE, True, True)
    wrong = await C.pending_token_state(pool, sid, pid, card_sha256="0" * 64,
                                        payload_sha256=before["payload_sha256"])
    assert (wrong.state, wrong.summary_match) == (C.PENDING_STATE_LIVE, False)
    assert await _row(pool, pid, sid) == before


async def test_other_session_with_the_same_pending_id_is_missing(pool, monkeypatch):
    """V8 (2) 9q 型：同一個 `pending_id`、別的 `session_id` ⇒ `missing`；該列不變。
    正對照：本 session 查得到 `live`。"""
    sid, pid, before = await _card(pool, monkeypatch)
    other = _SESSION_PREFIX + "aplus_other_" + uuid.uuid4().hex[:8]
    assert (await C.pending_token_state(pool, other, pid)).state == C.PENDING_STATE_MISSING
    assert (await C.pending_token_state(pool, sid, pid)).state == C.PENDING_STATE_LIVE
    assert await _row(pool, pid, sid) == before


async def test_less_than_60_seconds_left_is_expired_by_db_now(pool, monkeypatch):
    """剩餘 30 秒（以 DB `now()` 設定）⇒ `expired` 但未 `lapsed`；已過期 ⇒ `expired` 且 `lapsed`。"""
    sid, pid, _before = await _card(pool, monkeypatch)
    await pool.execute("UPDATE agent_confirmation_tokens SET expires_at = now() + interval '30 seconds' "
                       "WHERE pending_id = $1 AND session_id = $2", pid, sid)
    st = await C.pending_token_state(pool, sid, pid)
    assert (st.state, st.lapsed) == (C.PENDING_STATE_EXPIRED, False)
    await pool.execute("UPDATE agent_confirmation_tokens SET expires_at = now() - interval '5 seconds' "
                       "WHERE pending_id = $1 AND session_id = $2", pid, sid)
    st = await C.pending_token_state(pool, sid, pid)
    assert (st.state, st.lapsed) == (C.PENDING_STATE_EXPIRED, True)


async def test_redeemed_wins_over_expired(pool, monkeypatch):
    """安全審查 3-1：`redeem_pending` 兌現後再過期 ⇒ 仍判 `redeemed`（已兌現優先）。"""
    sid, pid, _before = await _card(pool, monkeypatch)
    assert await C.redeem_pending(pool, sid, pid) is not None
    assert (await C.pending_token_state(pool, sid, pid)).state == C.PENDING_STATE_REDEEMED
    await pool.execute("UPDATE agent_confirmation_tokens SET expires_at = now() - interval '5 seconds' "
                       "WHERE pending_id = $1 AND session_id = $2", pid, sid)
    assert (await C.pending_token_state(pool, sid, pid)).state == C.PENDING_STATE_REDEEMED
