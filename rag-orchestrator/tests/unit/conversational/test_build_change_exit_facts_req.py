"""unit:build_change_exit_facts 合約異動三出口（contract-conversational-facets 任務 2.2 / R2.2, R2.6, R7.1）。

status 決定性分流（research.md §二 ground truth，file:line 皆已盤）：
  - status==1（待發送）→ 可直接編輯＋操作路徑（編輯僅 READY，ContractController:12636）
  - status∈{2,4}（待簽）→ 取消退回待發送再改；主取消路徑保留租客資料（reset(true)，:18489），
    租客按不同意/邀請過期路徑仍清空（:15246/:15413/:18587）
  - status>=8（執行中）→ 不可直改；出口＝複製重建 或 資料異動申請書（使用者端無異動模組）
  - 已簽分支附「藍字（簽後印上 PDF）不可改 vs DB 可調＋不一致風險」事實（R2.6）
  - 歷史合約 → 異動申請書共用出口
全 status 矩陣覆蓋；facts 由程式決定性產出、LLM 只轉述（R7.1）。
"""
import pytest

from services.jgb.contracts import (ContractBit, FACE_BUILDERS,
                                    build_change_exit_facts)

pytestmark = pytest.mark.unit

_ORDER = [ContractBit.READY, ContractBit.INVITING, ContractBit.INVITING_NEXT,
          ContractBit.SIGNED, ContractBit.MOVE_IN, ContractBit.MOVE_IN_DONE,
          ContractBit.MOVE_OUT, ContractBit.MOVE_OUT_DONE,
          ContractBit.EARLY_TERMINATION, ContractBit.EARLY_TERMINATION_DONE]


def _bits_upto(status):
    bits = 0
    for b in _ORDER:
        if b <= status:
            bits |= b
    return bits


def _contract(status, **over):
    c = {"id": 83315, "title": "基隆物件", "status": status,
         "bit_status": _bits_upto(status), "is_history": 0, "is_history_done": 0,
         "date_start": 20260701, "date_end": 99991231, "rent": 20000,
         "to_user_connect": 1}
    c.update(over)
    return c


# ── 出口一：status==1 → 可直接編輯＋操作路徑（R2.2）──
@pytest.mark.req("contract-conversational-facets:2.2")
def test_status_ready_can_edit_directly():
    out = build_change_exit_facts(_contract(1), "我想改租期")
    assert "可直接編輯" in out
    assert "編輯" in out and "刪除" in out          # READY 也可刪（共用出口素材）
    assert "取消" not in out                        # 不混入待簽出口
    assert "申請書" not in out                      # 不混入已簽出口


# ── 出口二：status∈{2,4} → 取消退回再改＋保留租客資料語意（R2.2）──
@pytest.mark.req("contract-conversational-facets:2.2")
@pytest.mark.parametrize("status", [2, 4])
def test_status_inviting_cancel_and_redo(status):
    out = build_change_exit_facts(_contract(status), "內容打錯了要改")
    assert "不可直接編輯" in out
    assert "取消" in out and "待發送" in out         # 取消退回待發送再改
    assert "保留" in out and "租客資料" in out       # 主取消路徑保留租客資料
    assert "清空" in out                            # 不同意/逾期路徑會清空（講全，不誤導）
    assert "藍字" not in out                        # 藍字區分屬已簽分支


# ── 出口三：status>=8 → 不可直改；複製重建 或 異動申請書＋藍字區分（R2.2, R2.6）──
@pytest.mark.req("contract-conversational-facets:2.6")
@pytest.mark.parametrize("status", [8, 16, 32, 64, 128, 256, 512])
def test_status_signed_two_exits_with_blue_letter_facts(status):
    out = build_change_exit_facts(_contract(status), "想改租金")
    assert "不可直接修改" in out
    assert "複製" in out and "異動申請書" in out     # 兩條出口都在
    # 藍字 vs DB 可調＋不一致風險（R2.6 三要素）
    assert "藍字" in out and "不可改" in out
    assert "資料庫" in out or "DB" in out
    assert "不一致" in out


# ── 歷史合約 → 異動申請書共用出口（R2.7 素材）──
@pytest.mark.req("contract-conversational-facets:2.2")
def test_history_contract_routes_to_application_form():
    out = build_change_exit_facts(_contract(128, is_history=1), "歷史合約要改資料")
    assert "歷史合約" in out
    assert "異動申請書" in out
    assert "可直接編輯" not in out


# ── 每個分支都帶當前狀態 facts（LLM 有據可述，R7.1）──
@pytest.mark.req("contract-conversational-facets:7.1")
@pytest.mark.parametrize("status", [1, 2, 8])
def test_facts_carry_current_stage(status):
    out = build_change_exit_facts(_contract(status), "")
    assert "基隆物件" in out
    assert "目前狀態" in out


# ── 已註冊進 FACE_BUILDERS（face=合約異動 命中即分發）──
@pytest.mark.req("contract-conversational-facets:7.1")
def test_registered_in_face_builders():
    assert FACE_BUILDERS.get("合約異動") is build_change_exit_facts


# ════════ G5 grounded：requester_permissions 附掛——權限擋 vs 狀態擋分流（7.4）════════
#
# secondary_call（jgb_member_permissions，user_id={session.user_id}）掛 requester_permissions；
# 存在性驅動：未掛/查無 → 現行輸出恆等（G5 未啟用常態）。自訂角色靠 edit_contract 旗標。

def _perm(edit_contract, name="自訂角色"):
    return [{"character_name": name, "abilities": {"edit_contract": edit_contract}}]


@pytest.mark.req("contract-conversational-facets:7.4")
def test_g5_no_edit_permission_flags_permission_block():
    """狀態可編輯（READY）但角色無 edit_contract → 權限擋明示。"""
    out = build_change_exit_facts(
        _contract(1, requester_permissions=_perm(False, "業務")), "我編輯不了合約")
    assert "可直接編輯" in out                              # 狀態層不變
    assert "權限" in out and ("沒有" in out or "未開" in out)  # 權限擋
    assert "業務" in out                                    # 角色名（顯示用）
    assert "變更角色" in out or "調整" in out                # 解法指路


@pytest.mark.req("contract-conversational-facets:7.4")
def test_g5_has_edit_permission_ready_confirms_not_permission():
    out = build_change_exit_facts(
        _contract(1, requester_permissions=_perm(True)), "編輯不了")
    assert "可直接編輯" in out
    assert "具備" in out or "有合約編輯權限" in out           # 確認非權限問題


@pytest.mark.req("contract-conversational-facets:7.4")
def test_g5_signed_with_permission_disambiguates_status_block():
    """已簽署＋有權限 → 明示擋的是狀態非權限（分流核心）。"""
    out = build_change_exit_facts(
        _contract(8, requester_permissions=_perm(True)), "為什麼不能改")
    assert "不可直接修改" in out                            # 狀態擋不變
    assert "非權限" in out or "不是權限" in out              # 分流明示


@pytest.mark.req("contract-conversational-facets:7.4")
def test_g5_absent_identity_with_current_output():
    """未附掛（G5 未啟用/user_id 非成員）→ 與現行輸出逐字恆等（零回歸）。"""
    for status in (1, 2, 8):
        assert build_change_exit_facts(_contract(status), "改合約") == \
            build_change_exit_facts(_contract(status), "改合約")
        base = build_change_exit_facts(_contract(status), "改合約")
        assert "權限" not in base.split("出口判定")[0]        # 未啟用不憑空談權限
