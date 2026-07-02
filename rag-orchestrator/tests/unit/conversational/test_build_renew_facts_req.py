"""unit:build_renew_facts 續約（contract-conversational-facets 任務 2.5 / R4.1, R4.3, R4.5, R10.3）。

決定性 facts（research.md §三）：
  - date_end 剩餘天數／已逾期天數。
  - 可否系統續約＝包裝既有 check_can_renew（雙簽完成＋未過期＋非點退/解約流程等）。
  - is_tenant_registered：免註冊 → 管理者單方確認生效不重簽；已註冊 → 雙方重簽（邀請效期 72 小時）。
  - G4 is_newest 存在且 =0 → 已有較新續約（列表僅顯示最新、原約分頁呈現增補文件，R4.5）；缺 → 略過。
  - father_id 鏈：father_id 非空且 ≠id ⇒ 本約即續約（isRenewContract 判斷式）。
含 G4／is_tenant_registered 有無欄位矩陣（存在性驅動，R10.3）。
"""
from datetime import datetime, timedelta

import pytest

from services.jgb.contracts import ContractBit, FACE_BUILDERS, build_renew_facts

pytestmark = pytest.mark.unit

_SIGNED = (ContractBit.READY | ContractBit.INVITING |
           ContractBit.INVITING_NEXT | ContractBit.SIGNED)


def _ymd(dt) -> int:
    return int(dt.strftime("%Y%m%d"))


def _contract(**over):
    c = {"id": 84800, "title": "台北信義-單人房", "status": 8, "bit_status": _SIGNED,
         "is_history": 0, "date_start": 20240101,
         "date_end": _ymd(datetime.now() + timedelta(days=45)),
         "rent": 20000, "to_user_connect": 1, "father_id": 84800}
    c.update(over)
    return c


# ── 剩餘天數（date_end 未到）／已逾期（R4.1）──
@pytest.mark.req("contract-conversational-facets:4.1")
def test_days_remaining_before_expiry():
    out = build_renew_facts(_contract(), "快到期了要續約")
    assert "45 天" in out and "到期" in out


@pytest.mark.req("contract-conversational-facets:4.1")
def test_expired_states_overdue():
    past = _ymd(datetime.now() - timedelta(days=10))
    out = build_renew_facts(_contract(date_end=past), "還能續嗎")
    assert "已於" in out and "到期" in out


# ── 可否系統續約：雙簽完成＋未過期 → 可；缺件忠實列出（R4.1）──
@pytest.mark.req("contract-conversational-facets:4.1")
def test_renewable_when_signed_and_not_expired():
    out = build_renew_facts(_contract(), "")
    assert "可" in out and "系統續約" in out
    assert "不可" not in out


@pytest.mark.req("contract-conversational-facets:4.1")
def test_not_renewable_lists_blockers():
    past = _ymd(datetime.now() - timedelta(days=10))
    out = build_renew_facts(_contract(date_end=past), "")
    assert "目前不可" in out and "系統續約" in out
    assert "重建新約" in out                       # 不可續 → 給替代出口


# ── 免註冊/已註冊重簽規則（R4.3）──
@pytest.mark.req("contract-conversational-facets:4.3")
def test_unregistered_tenant_single_side_confirm():
    out = build_renew_facts(_contract(is_tenant_registered=0), "")
    assert "免註冊" in out and "單方確認" in out
    assert "不需" in out and "重簽" in out


@pytest.mark.req("contract-conversational-facets:4.3")
def test_registered_tenant_needs_resign_72h():
    out = build_renew_facts(_contract(is_tenant_registered=1), "")
    assert "重新簽署" in out or "重簽" in out
    assert "72 小時" in out


@pytest.mark.req("contract-conversational-facets:10.3")
def test_registration_field_absent_skips_branch():
    out = build_renew_facts(_contract(), "")
    assert "免註冊" not in out and "72 小時" not in out   # 欄位缺 → 不虛構


# ── G4 is_newest：=0 已被續約；=1 無提示；缺 → 略過（R4.5, R10.3）──
@pytest.mark.req("contract-conversational-facets:4.5")
def test_g4_is_newest_zero_means_already_renewed():
    out = build_renew_facts(_contract(is_newest=0), "")
    assert "已有較新" in out
    assert "最新" in out and "分頁" in out          # 列表僅顯示最新＋原約分頁增補


@pytest.mark.req("contract-conversational-facets:10.3")
@pytest.mark.parametrize("over", [{}, {"is_newest": 1}])
def test_g4_newest_or_absent_no_renewed_hint(over):
    out = build_renew_facts(_contract(**over), "")
    assert "已有較新" not in out


# ── father_id 鏈 facts（isRenewContract：father_id 非空且 ≠id）──
@pytest.mark.req("contract-conversational-facets:4.5")
def test_father_chain_marks_renew_contract():
    out = build_renew_facts(_contract(id=85001, father_id=84800), "")
    assert "續約" in out and "84800" in out         # 鏈上父約 id 可對回

    out_first = build_renew_facts(_contract(), "")   # father_id == id → 首約
    assert "84800" not in out_first.replace("台北信義", "")  # 不冒出鏈 facts（title 內無 id）


# ── 已註冊進 FACE_BUILDERS ──
@pytest.mark.req("contract-conversational-facets:7.1")
def test_registered_in_face_builders():
    assert FACE_BUILDERS.get("續約") is build_renew_facts
