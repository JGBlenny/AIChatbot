"""unit:合約 formatter 事實強化——操作清單效力聲明＋bit 歷程行（決定性，治 LLM 先驗蓋台）。

真環境揪出（gpt-4o temp0.2 仍 3/3 錯）：
  ①「待點交可直接點退嗎」——底稿明列可點退，LLM 仍用常識掰「要先點交」；
  ②「點退算完成了嗎」——底稿只說歷史，LLM 斷言「算完成」。
prompt 迭代到頂 → 回歸架構原則（機械判斷用程式）：formatter 把事實講白——
  ① 操作行加效力聲明（各 check_can_* 本就獨立判定，忠實陳述「皆可立即進行/未列出者不可」）；
  ② 加「已完成的歷程」行（既有 decode_bit_status 逐位元解碼）→ 點退送出/完成有據可答。
"""
import pytest

from services.jgb.contracts import ContractBit, _format_status_response

pytestmark = pytest.mark.unit


def _contract(bit_status, status, is_history=0, date_end=99991231):
    # to_user_connect：check_can_*（jgb2 真規則）要求租客已綁定帳號才可操作。
    # date_end 遠期：不依賴牆鐘（點退 30 天窗依「今天」計）；驗聲明只需至少一操作可用（點交）。
    return {"id": 1, "title": "T", "bit_status": bit_status, "status": status,
            "is_history": is_history, "date_start": 20260701, "date_end": date_end,
            "rent": 20000, "to_user_connect": 1}


# ── 有可用操作 → 帶效力聲明（獨立/立即/未列不可），LLM 無從自加前置條件 ──
@pytest.mark.req("domain-conversational-facets:3.2")
def test_ops_line_carries_effectiveness_statement():
    # 雙方簽名完成（待點交）＋近到期 → 點交/點退/續約 皆可（jgb2 check_can_* 各自獨立判定）
    bits = ContractBit.READY | ContractBit.INVITING | ContractBit.INVITING_NEXT | ContractBit.SIGNED
    out = _format_status_response(_contract(bits, ContractBit.SIGNED))
    assert "目前可進行的操作：" in out
    assert "皆可立即進行" in out and "彼此獨立" in out     # 清單內操作無先後依賴
    assert "未列出的操作目前不可進行" in out               # 清單外＝不可


# ── 無可用操作 → 原樣「沒有可進行的操作」（不加聲明）──
@pytest.mark.req("domain-conversational-facets:3.2")
def test_no_ops_line_unchanged():
    out = _format_status_response(_contract(ContractBit.READY, ContractBit.READY, date_end=20200101))
    assert "目前沒有可進行的操作" in out
    assert "皆可立即進行" not in out


# ── 歷程行：bit_status 逐位元解碼（機械、用程式非 LLM）──
@pytest.mark.req("domain-conversational-facets:3.2")
def test_milestones_line_from_bit_status():
    # 送過點退但未完成（如 84908 型）：歷程含「已發送點退」、不含「租客同意點退」
    bits = (ContractBit.READY | ContractBit.INVITING | ContractBit.INVITING_NEXT
            | ContractBit.SIGNED | ContractBit.MOVE_OUT)
    out = _format_status_response(_contract(bits, ContractBit.MOVE_OUT, is_history=1))
    assert "已完成的歷程：" in out
    assert "已發送點退" in out
    assert "租客同意點退" not in out          # bit 128 未設 → 不得出現（點退未完成有據可查）
    # 缺席推理由程式做：送出有、完成無 → 明講「未完成」（LLM 會把「已發送」腦補成「已完成」）
    assert "點退已送出但租客尚未同意（點退未完成）" in out
    # 點退完成型：同意在列、不再標未完成
    out2 = _format_status_response(_contract(bits | ContractBit.MOVE_OUT_DONE,
                                             ContractBit.MOVE_OUT_DONE, is_history=1))
    assert "租客同意點退" in out2
    assert "點退未完成" not in out2
