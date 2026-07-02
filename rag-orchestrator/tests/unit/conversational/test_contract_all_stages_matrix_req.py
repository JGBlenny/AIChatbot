"""unit:合約 12 里程碑×生命週期旗標 全矩陣——decode 層（formatter）逐一驗證。

真實測試帳號只有 8/12 種狀態的合約（缺 16/128/256/512 與 is_history_done），
LLM 組話品質另以真 LLM＋合成列抽驗；本檔把「決定性解碼層」全蓋：
每個 status 的階段判定（get_current_stage）＋狀態回應（_format_status_response）
不崩、階段字樣正確、歷程行一致。fixture 造位元採「累加到該階段」（bit_status 為累積 bitmask）。
"""
import pytest

from services.jgb.contracts import (ContractBit, get_current_stage,
                                    _format_status_response, decode_bit_status)

pytestmark = pytest.mark.unit

_ORDER = [ContractBit.READY, ContractBit.INVITING, ContractBit.INVITING_NEXT,
          ContractBit.SIGNED, ContractBit.MOVE_IN, ContractBit.MOVE_IN_DONE,
          ContractBit.MOVE_OUT, ContractBit.MOVE_OUT_DONE,
          ContractBit.EARLY_TERMINATION, ContractBit.EARLY_TERMINATION_DONE]


def _bits_upto(status: int) -> int:
    bits = 0
    for b in _ORDER:
        if b <= status:
            bits |= b
    return bits


def _contract(status, is_history=0, is_history_done=0):
    return {"id": 1, "title": "T", "status": status, "bit_status": _bits_upto(status),
            "is_history": is_history, "is_history_done": is_history_done,
            "date_start": 20260701, "date_end": 99991231, "rent": 20000,
            "to_user_connect": 1}


# ── 12 里程碑 → 階段判定全對照（jgb2 語意）──
_EXPECTED_STAGE = {
    1: "已建立（待發送）",
    2: "已發送簽約邀請（等待租客簽名）",
    4: "租客已簽名（等待房東簽名）",
    8: "已簽約（待點交）",
    16: "點交中（等待租客同意）",
    32: "已點交（執行中）",
    64: "點退中（等待租客同意）",
    128: "點退完成",
    256: "提前解約中",
    512: "提前解約已確認",
}


@pytest.mark.req("domain-conversational-facets:3.2")
@pytest.mark.parametrize("status,expected", sorted(_EXPECTED_STAGE.items()))
def test_stage_label_per_status(status, expected):
    assert get_current_stage(_contract(status)) == expected


# ── 生命週期旗標優先於殘留 status（jgb2 ground truth：is_history 為權威）──
@pytest.mark.req("domain-conversational-facets:3.2")
def test_lifecycle_flags_override_status():
    assert get_current_stage(_contract(64, is_history=1)) == "歷史合約（已到期）"
    assert get_current_stage(_contract(64, is_history=1, is_history_done=1)) == "歷史完成（已歸檔）"


# ── 每種狀態的狀態回應：不崩、含階段字樣、歷程行與 bit 解碼一致 ──
@pytest.mark.req("domain-conversational-facets:3.2")
@pytest.mark.parametrize("status", sorted(_EXPECTED_STAGE))
def test_status_response_renders_every_status(status):
    c = _contract(status)
    out = _format_status_response(c)
    assert _EXPECTED_STAGE[status] in out
    for label in decode_bit_status(c["bit_status"]):
        assert label in out                       # 歷程行含全部已達位元
    # 半途流程（送出未完成）必須被明講（缺席推理由程式做）
    if status == 16:
        assert "點交未完成" in out
    if status == 64:
        assert "點退未完成" in out
    if status == 256:
        assert "提前解約" in out and "未完成" in out
    # 完成態不得標未完成
    if status in (128, 512):
        assert "未完成" not in out
