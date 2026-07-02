"""unit:build_closeout_facts 退租收尾步驟鏈（contract-conversational-facets 任務 2.3 / R3.1–3.5, R7.4）。

以 bit_status 旗標決定性判定「卡在哪一步、下一步做什麼」（research.md §二）：
  提前解約(256/512)／點退(64/128) → 帳單封存（G3 前輸出通用指引＝常態降級，R3.3/R7.4）
  → 轉歷史時點（過終止/到期日後每日排程自動轉；逾期未轉 → 導客服，R3.4）。
  未發起 → 重用 check_can_move_out（點交點退互不相依，R3.2）＋提前解約發起路徑
  ＋回簽效期 30 天＋提前產出帳單封存提醒（R3.5）。旗標組合矩陣覆蓋。
"""
from datetime import datetime, timedelta

import pytest

from services.jgb.contracts import (ContractBit, FACE_BUILDERS,
                                    build_closeout_facts)

pytestmark = pytest.mark.unit

_SIGNED_BASE = (ContractBit.READY | ContractBit.INVITING |
                ContractBit.INVITING_NEXT | ContractBit.SIGNED)


def _ymd(dt) -> int:
    return int(dt.strftime("%Y%m%d"))


def _contract(extra_bits=0, date_end=99991231, **over):
    c = {"id": 84908, "title": "基隆物件", "status": 8,
         "bit_status": _SIGNED_BASE | extra_bits, "is_history": 0,
         "is_history_done": 0, "date_start": 20240101, "date_end": date_end,
         "rent": 20000, "to_user_connect": 1}
    c.update(over)
    return c


# ── 提前解約中（256 無 512）→ 等待租客回簽＋效期 30 天（R3.1）──
@pytest.mark.req("contract-conversational-facets:3.1")
def test_early_termination_pending_waits_countersign():
    out = build_closeout_facts(_contract(ContractBit.EARLY_TERMINATION), "退租進度")
    assert "提前解約" in out and "等待租客" in out
    assert "30 天" in out                                # 回簽效期


# ── 點退中（64 無 128）→ 等待租客同意（R3.1）──
@pytest.mark.req("contract-conversational-facets:3.1")
def test_move_out_pending_waits_tenant():
    out = build_closeout_facts(_contract(ContractBit.MOVE_OUT), "點退到哪了")
    assert "點退" in out and "等待租客同意" in out


# ── 點退完成（128）→ 下一步封存（通用指引）＋轉歷史時點（R3.1, R3.3, R3.4）──
@pytest.mark.req("contract-conversational-facets:3.3")
@pytest.mark.parametrize("bits,what", [
    (ContractBit.MOVE_OUT | ContractBit.MOVE_OUT_DONE, "點退"),
    (ContractBit.EARLY_TERMINATION | ContractBit.EARLY_TERMINATION_DONE, "提前解約"),
])
def test_closeout_done_next_is_archive_then_history(bits, what):
    out = build_closeout_facts(_contract(bits), "接下來要做什麼")
    assert f"{what}已完成" in out
    assert "封存" in out and "帳單總表" in out           # G3 前通用指引（常態降級）
    assert "每日" in out and "自動轉" in out             # 轉歷史時點（排程）
    assert "客服" not in out                             # 未逾期不導客服


# ── 已逾到期日仍未轉歷史 → 導客服盤查（R3.4）──
@pytest.mark.req("contract-conversational-facets:3.4")
def test_overdue_not_history_escalates_to_support():
    past = _ymd(datetime.now() - timedelta(days=10))
    out = build_closeout_facts(
        _contract(ContractBit.MOVE_OUT | ContractBit.MOVE_OUT_DONE, date_end=past),
        "怎麼還是執行中")
    assert "尚未轉" in out and "客服" in out


# ── 已轉歷史 → 收尾完成（R3.4）──
@pytest.mark.req("contract-conversational-facets:3.4")
def test_history_means_closeout_complete():
    out = build_closeout_facts(
        _contract(ContractBit.MOVE_OUT | ContractBit.MOVE_OUT_DONE, is_history=1), "")
    assert "歷史合約" in out and "完成" in out
    assert "客服" not in out


# ── 未發起＋點退窗內可點退 → 可略過點交直接點退（互不相依，R3.2）──
@pytest.mark.req("contract-conversational-facets:3.2")
def test_not_started_movable_states_pair_independence():
    near_end = _ymd(datetime.now() + timedelta(days=15))   # 30 天窗內
    out = build_closeout_facts(_contract(date_end=near_end), "要退租了怎麼做")
    assert "可" in out and "點退" in out
    assert "可略過點交直接點退" in out                     # 點交點退互不相依


# ── 未發起＋不可點退 → 忠實列缺件（重用 check_can_move_out，R3.2）──
@pytest.mark.req("contract-conversational-facets:3.2")
def test_not_started_blocked_lists_blockers():
    out = build_closeout_facts(_contract(date_end=99991231), "想退租")   # 遠期：30 天窗未到
    assert "尚不可點退" in out
    assert "30 天" in out                                  # 窗口缺件原文含「到期前 30 天」


# ── 未發起 → 提前解約發起路徑＋回簽效期 30 天＋帳單封存提醒（R3.5）──
@pytest.mark.req("contract-conversational-facets:3.5")
def test_not_started_gives_early_termination_path():
    out = build_closeout_facts(_contract(), "想提前解約")
    assert "提前解約" in out and "尚未發起" in out
    assert "30 天" in out                                  # 回簽效期
    assert "封存" in out                                   # 提前產出帳單封存提醒


# ── 已註冊進 FACE_BUILDERS ──
@pytest.mark.req("contract-conversational-facets:7.1")
def test_registered_in_face_builders():
    assert FACE_BUILDERS.get("退租收尾") is build_closeout_facts
