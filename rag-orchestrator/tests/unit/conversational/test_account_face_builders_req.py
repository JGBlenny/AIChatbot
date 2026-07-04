"""unit:帳號領域檔底座（account-conversational-facets 任務 1.1/1.2 / R3.3, R6, R10.1）。

build_login_trouble_facts 全分支矩陣（未註冊/錯配/一致/欄位缺失/密文）＋
face=None 恆等（既有 contracts 面向路由不變，mutation 證明）＋遮罩＋驗證碼紅線。
機制口徑以 research.md 主題 1/2 為準（快速驗證信 72 小時、「確切寫法」）。
"""
import re

import pytest

from services.jgb.accounts import ACCOUNT_FACE_BUILDERS, build_login_trouble_facts
from services.jgb.contracts import format_contract_response

pytestmark = pytest.mark.unit


def _contract(**over):
    c = {"id": 84927, "title": "海大質感獨立套房", "status": 2, "bit_status": 3,
         "to_user_email": "tenant@example.com", "to_user_phone": "0912345678",
         "to_user_connect": 1, "is_tenant_registered": True,
         "to_user_login_email": "tenant@example.com"}
    c.update(over)
    return c


# ════════ 三分支矩陣（R3.3）════════

def test_unregistered_gives_registration_guidance():
    out = build_login_trouble_facts(
        _contract(is_tenant_registered=False, to_user_login_email=None), "租客說登不進去")
    assert "尚未註冊" in out or "未註冊" in out
    assert "72 小時" in out                                    # 快速驗證信效期（research 主題 1）
    assert "tenant@example.com" in out                          # 邀請信箱（業者自填，原樣）
    assert "登錯" not in out                                    # 未註冊不談錯配


def test_registered_with_mismatched_login_email_suggests_wrong_account():
    out = build_login_trouble_facts(
        _contract(to_user_login_email="other.person@gmail.com"), "租客登入後看不到合約")
    assert "已註冊" in out
    assert "o***@gmail.com" in out                              # 登入信箱遮罩輸出
    assert "other.person@gmail.com" not in out                  # 不完整揭露
    assert "登錯" in out or "另一個帳號" in out                  # 疑似多帳號/登錯
    assert "tenant@example.com" in out                          # 對照邀請信箱


def test_registered_and_matched_turns_to_role_view_and_password():
    out = build_login_trouble_facts(_contract(), "租客說看不到資料")
    assert "一致" in out
    assert "身分" in out or "角色" in out                        # 角色視角切換
    assert "忘記密碼" in out                                     # 自助重設路徑
    assert "登錯" not in out


# ════════ 降級與防護（R6.4/R6.5）════════

def test_missing_registration_field_degrades_honestly():
    c = _contract()
    del c["is_tenant_registered"]
    del c["to_user_login_email"]
    out = build_login_trouble_facts(c, "登不進去")
    assert out.strip()
    assert "無法" in out and "註冊狀態" in out                   # 誠實說明查不到
    assert "確切寫法" in out                                     # 仍給一般排查
    assert "不一致" not in out                                   # 不虛構比對結果


def test_ciphertext_login_email_treated_unavailable():
    out = build_login_trouble_facts(
        _contract(to_user_login_email="A8f3kQ9zX2encrypted"), "登不進去")
    assert "不一致" not in out and "登錯" not in out             # 密文不得產生假錯配
    assert "已註冊" in out
    assert "A8f3kQ9zX2encrypted" not in out                     # 密文不外洩


def test_no_verification_code_value_ever(monkeypatch):
    for c in (_contract(), _contract(is_tenant_registered=False)):
        out = build_login_trouble_facts(c, "驗證碼多少")
        assert not re.search(r"驗證碼[^\n]{0,6}\d{4}", out)      # 不得出現驗證碼值樣式


# ════════ face 分發與恆等（R10.1）════════

def test_face_none_and_unknown_face_identity():
    c = _contract()
    legacy = format_contract_response([c], user_question="登不進去")
    assert format_contract_response([c], user_question="登不進去", face=None) == legacy
    assert format_contract_response([c], user_question="登不進去", face="不存在面向") == legacy


def test_login_face_routes_to_accounts_builder():
    c = _contract(to_user_login_email="other@gmail.com")
    legacy = format_contract_response([c], user_question="登不進去")
    faced = format_contract_response([c], user_question="登不進去", face="登入排障")
    assert faced != legacy                                       # mutation：分發真的生效
    assert faced == build_login_trouble_facts(c, "登不進去")


def test_contract_faces_still_route_to_contract_builders():
    from services.jgb.contracts import FACE_BUILDERS
    c = _contract()
    faced = format_contract_response([c], user_question="想改合約", face="合約異動")
    assert faced == FACE_BUILDERS["合約異動"](c, "想改合約")      # 既有面向不受影響


def test_registry_shape():
    assert set(ACCOUNT_FACE_BUILDERS.keys()) == {"登入排障"}
    assert all(callable(b) for b in ACCOUNT_FACE_BUILDERS.values())


# ════════ G-A1 註冊狀態附掛：三態排查（account 6.2* / R9.2）════════
#
# secondary_call 把 tenants/registration-status 結果掛在合約列 registration 鍵（單元素 list）；
# builder 以 found 當歸屬閘門、is_registered＋email_verify 驅動 found:true 三態排查。
# 嚴格遮罩：registration 帶 lessee_name/lessee_user_id，回話絕不輸出。

def _reg(**over):
    r = {"found": True, "lessee_user_id": 12291, "is_bound": True,
         "is_registered": True, "lessee_email_verify_status": 1, "lessee_name": "私密姓名"}
    r.update(over)
    return r


def test_ga1_found_false_routes_to_support():
    """found:false（查無此人為名下租客）→ 導客服，不揭露任何帳號細節。"""
    out = build_login_trouble_facts(_contract(registration=[_reg(found=False)]), "租客登不進去")
    assert "客服" in out
    assert "私密姓名" not in out and "12291" not in out


def test_ga1_not_registered_gives_invite_link():
    out = build_login_trouble_facts(
        _contract(registration=[_reg(is_registered=False, lessee_email_verify_status=0)]), "登不進去")
    assert ("尚未" in out or "未完成註冊" in out or "還沒" in out)
    assert "邀請連結" in out
    assert "私密姓名" not in out and "12291" not in out


def test_ga1_registered_but_email_unverified():
    out = build_login_trouble_facts(
        _contract(registration=[_reg(is_registered=True, lessee_email_verify_status=0)]), "登不進去")
    assert "驗證" in out and ("信箱" in out or "email" in out.lower() or "Email" in out)
    assert "私密姓名" not in out and "12291" not in out


def test_ga1_registered_verified_turns_to_login_ops():
    out = build_login_trouble_facts(
        _contract(registration=[_reg(is_registered=True, lessee_email_verify_status=1)]), "登不進去")
    assert "確切寫法" in out
    assert "角色" in out or "身分" in out
    assert "私密姓名" not in out and "12291" not in out


def test_ga1_no_pii_ever_across_states():
    for r in (_reg(found=False), _reg(is_registered=False), _reg(lessee_email_verify_status=0),
              _reg()):
        out = build_login_trouble_facts(_contract(registration=[r]), "登不進去")
        assert "私密姓名" not in out and "12291" not in out
        assert not re.search(r"驗證碼[^\n]{0,6}\d{4}", out)


def test_ga1_absent_falls_back_to_contract_logic():
    """未掛 registration（G-A1 未上線/降級）→ 沿用合約層三分支，零回歸。"""
    c = _contract(is_tenant_registered=False, to_user_login_email=None)
    assert build_login_trouble_facts(c, "登不進去") == \
        build_login_trouble_facts(_contract(is_tenant_registered=False, to_user_login_email=None), "登不進去")
    assert "尚未註冊" in build_login_trouble_facts(c, "登不進去")
