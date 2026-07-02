"""unit:build_sign_facts 簽署排障（contract-conversational-facets 任務 2.4 / R6.1–6.4, R7.4, R10.3）。

決定性排查（research.md §一）：
  - 還差誰簽：bit 2 已發送、bit 4 租客已簽、bit 8 管理者回簽完成（無 per-signer 表，位元即真相）。
  - 發送通道 to_user_email/phone；綁定 to_user_connect。
  - G1（contract_inviting_expire_at）存在 → 效期判斷＋過期自動退回並清租客資料說明（R6.4）。
  - G2（to_user_login_email）存在 → 發送信箱 vs 登入信箱錯配比對，登入信箱遮罩輸出（R6.3）。
  - G 欄位缺 → 略過分支不虛構（存在性驅動，R7.4/R10.3）。含 G1/G2 有無欄位矩陣。
"""
from datetime import datetime, timedelta

import pytest

from services.jgb.contracts import ContractBit, FACE_BUILDERS, build_sign_facts

pytestmark = pytest.mark.unit


def _contract(bits, **over):
    c = {"id": 83315, "title": "基隆物件", "status": 2, "bit_status": bits,
         "is_history": 0, "date_start": 20260701, "date_end": 99991231,
         "rent": 20000, "to_user_connect": 1,
         "to_user_email": "gg123@gmail.com", "to_user_phone": ""}
    c.update(over)
    return c


_INVITING = ContractBit.READY | ContractBit.INVITING
_TENANT_SIGNED = _INVITING | ContractBit.INVITING_NEXT
_BOTH_SIGNED = _TENANT_SIGNED | ContractBit.SIGNED


# ── 還差誰簽：位元決定性判斷（R6.1）──
@pytest.mark.req("contract-conversational-facets:6.1")
def test_not_sent_yet():
    out = build_sign_facts(_contract(ContractBit.READY), "租客說看不到合約")
    assert "尚未發送" in out


@pytest.mark.req("contract-conversational-facets:6.1")
def test_waiting_tenant_signature():
    out = build_sign_facts(_contract(_INVITING), "卡在哪")
    assert "還差租客簽名" in out


@pytest.mark.req("contract-conversational-facets:6.1")
def test_waiting_manager_countersign():
    out = build_sign_facts(_contract(_TENANT_SIGNED), "租客簽了嗎")
    assert "租客已簽名" in out and "回簽" in out


@pytest.mark.req("contract-conversational-facets:6.1")
def test_both_signed_complete():
    out = build_sign_facts(_contract(_BOTH_SIGNED, status=8), "簽好了嗎")
    assert "雙方簽名" in out and "完成" in out


# ── 發送通道與綁定狀態（R6.2）──
@pytest.mark.req("contract-conversational-facets:6.2")
def test_channel_email_and_connect_state():
    out = build_sign_facts(_contract(_INVITING), "")
    assert "gg123@gmail.com" in out            # 發送通道（管理者自填欄位，不遮罩）
    assert "已綁定" in out

    out2 = build_sign_facts(_contract(_INVITING, to_user_connect=0,
                                      to_user_email="", to_user_phone="0912345678"), "")
    assert "0912345678" in out2                # 電話通道
    assert "尚未綁定" in out2


@pytest.mark.req("contract-conversational-facets:6.2")
def test_no_channel_at_all_is_stated():
    out = build_sign_facts(_contract(_INVITING, to_user_email="", to_user_phone=""), "")
    assert "未設定" in out and "聯絡方式" in out


# ── G1 存在：效期判斷（未過期/已過期＋自動退回清資料說明，R6.4）──
@pytest.mark.req("contract-conversational-facets:6.4")
def test_g1_present_not_expired():
    future = (datetime.now() + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    out = build_sign_facts(_contract(_INVITING, contract_inviting_expire_at=future), "")
    assert "效期" in out and "有效" in out
    assert "清空" not in out                    # 未過期不講過期後果


@pytest.mark.req("contract-conversational-facets:6.4")
def test_g1_present_expired_explains_reset_and_data_wipe():
    past = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    out = build_sign_facts(_contract(_INVITING, contract_inviting_expire_at=past), "")
    assert "過" in out and "效期" in out
    assert "待發送" in out and "清空" in out     # 自動退回＋清租客資料
    assert "重新發送" in out


@pytest.mark.req("contract-conversational-facets:10.3")
def test_g1_absent_skips_expiry_branch():
    out = build_sign_facts(_contract(_INVITING), "")
    assert "效期" not in out                    # 欄位缺 → 不虛構效期判斷


# ── G2 存在：登入信箱錯配比對，登入信箱遮罩（R6.3）──
@pytest.mark.req("contract-conversational-facets:6.3")
def test_g2_present_mismatch_masked():
    out = build_sign_facts(
        _contract(_INVITING, to_user_login_email="sso.user99@yahoo.com"), "租客登入看不到")
    assert "不一致" in out
    assert "sso.user99@yahoo.com" not in out    # 登入信箱屬個資，不完整揭露
    assert "s***@yahoo.com" in out              # 遮罩形式
    assert "重新發送" in out                     # 解法：改用登入信箱重發


@pytest.mark.req("contract-conversational-facets:6.3")
def test_g2_present_match_states_consistent():
    out = build_sign_facts(
        _contract(_INVITING, to_user_login_email="GG123@gmail.com"), "")   # 大小寫不敏感
    assert "一致" in out and "不一致" not in out


@pytest.mark.req("contract-conversational-facets:10.3")
def test_g2_absent_skips_mismatch_branch():
    out = build_sign_facts(_contract(_INVITING), "")
    assert "登入" not in out                    # 欄位缺 → 略過比對分支


# ── G2 值非明文信箱（jgb2 實測回加密密文，如 'IAiPNxhp3ug…='）→ 視同欄位不可用，
#    略過比對不虛構——拿密文比明文會永遠「不一致」變假錯配（preview 實盤揪出）──
@pytest.mark.req("contract-conversational-facets:10.3")
def test_g2_ciphertext_value_skips_comparison():
    out = build_sign_facts(
        _contract(_INVITING, to_user_login_email="IAiPNxhp3ug8Uhkf4ySCbGgwtvs="), "")
    assert "不一致" not in out and "登入" not in out   # 不產生假錯配
    assert "IAiPNxhp" not in out                       # 密文不外洩


# ── 已註冊進 FACE_BUILDERS ──
@pytest.mark.req("contract-conversational-facets:7.1")
def test_registered_in_face_builders():
    assert FACE_BUILDERS.get("簽署排障") is build_sign_facts
