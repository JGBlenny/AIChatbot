"""unit：P1e-2——Face requirement 已 population，但 **routing 必須不變**。

⚠️ 寫入 `requires_instance_reference` 是補上**授權輸入**，⛔ 不是授權本身。
`gate_active()` 是最外層守衛（`INSTANCE_REFERENCE_GATE` 未設 ⇒ false），
`_instance_gate_decision` 直接回 `None` ⇒ `_instance_hint_suppressed` 恆 False。
⇒ 宣告寫入前後 routing 逐位元相同。
"""
import os

import pytest

from services import instance_applicability as ia
from services.instance_reference_gate import (gate_active, gate_applies_to,
                                              gate_requested,
                                              is_instance_requiring_face)

pytestmark = pytest.mark.unit


class _Cfg:
    def __init__(self, key, scope):
        self.key = key
        self.grounding_scope = scope


def _row(applicability):
    return {"generation_metadata": {ia.KNOWLEDGE_APPLICABILITY_KEY: applicability}}


# ════════════════════════════════════════════════════════════════════
# routing equivalence：宣告存在，但 gate 仍不作用
# ════════════════════════════════════════════════════════════════════

def test_gate_still_inactive_after_population(monkeypatch):
    """⛔ population 不得使 gate 生效——旗標未設時 `gate_active()` 必為 False。"""
    monkeypatch.delenv("INSTANCE_REFERENCE_GATE", raising=False)
    assert gate_requested() is False
    assert gate_active() is False


def test_declared_face_becomes_gate_applicable_only_within_rollout_scope():
    """⚠️ C∧D：即使 16 個 Face 都宣告了 true，D（rollout scope）仍只含 bill_diagnosis。

    ⇒ 宣告本身**不會**讓其他面向進入納管；擴大納管需要另外的授權決定。
    """
    declared = _Cfg("contract_diag", {"requires_instance_reference": True})
    assert is_instance_requiring_face(declared) is True
    assert gate_applies_to(declared) is False, "宣告 true 就被納管 ⇒ C∧D 兩層被摺疊"
    bill = _Cfg("bill_diagnosis", {"requires_instance_reference": True})
    assert gate_applies_to(bill) is True     # C∧D 成立，但仍受 gate_active() 外層守衛


def test_suppression_requires_gate_active_not_just_declaration(monkeypatch):
    """⚠️ 最重要的一條：C∧D 成立 **不等於** 會抑制——外層還有 `gate_active()`。"""
    monkeypatch.delenv("INSTANCE_REFERENCE_GATE", raising=False)
    from routers.chat import _instance_gate_decision, _instance_hint_suppressed
    decision = _instance_gate_decision("這筆帳單為什麼發不出去")
    assert decision is None, "旗標未設卻產生判定 ⇒ gate 已被意外開啟"
    bill = _Cfg("bill_diagnosis", {"requires_instance_reference": True})
    assert _instance_hint_suppressed(decision, bill) is False


# ════════════════════════════════════════════════════════════════════
# 兩軸交叉首次真正成立
# ════════════════════════════════════════════════════════════════════

def test_cross_product_now_resolves_for_declared_pairs():
    """知識 3503（已宣告 instance）× billing_invoice（已宣告 required）→ ELIGIBLE。"""
    face_required = _Cfg("billing_invoice", {"requires_instance_reference": True})
    face_not_required = _Cfg("estate_guide", {"requires_instance_reference": False})
    face_unknown = _Cfg("account_binding", {})

    assert ia.instance_applicability_decision(_row("instance"), face_required) \
        == ia.DECISION_ELIGIBLE
    assert ia.instance_applicability_decision(_row("general"), face_required) \
        == ia.DECISION_INELIGIBLE
    # NOT_REQUIRED 的面向不受 instance 規則誤傷
    assert ia.instance_applicability_decision(_row("instance"), face_not_required) \
        == ia.DECISION_NOT_APPLICABLE
    # ⚠️ account_binding 刻意維持 UNKNOWN → 交叉結果亦為 UNKNOWN，不得取得正向授權
    assert ia.instance_applicability_decision(_row("instance"), face_unknown) \
        == ia.DECISION_UNKNOWN


# ════════════════════════════════════════════════════════════════════
# 反例矩陣：⛔ 不得把 execution shape 當 responsibility
# ════════════════════════════════════════════════════════════════════

def test_counter_matrix_execution_shape_is_not_responsibility():
    """本批實際出現的兩個反例——防止 reviewer 用 endpoint／名字推導。

    ```text
    名字像 diagnosis／責任是排障，但 NOT_REQUIRED
      account_register —— 責任明文「**當事人（租客）不在系統內**」
                          ⇒ 根本沒有可讀的個體資料
    無查詢 API（只有 execute_endpoint），但 REQUIRED
      repair_create    —— 責任明文「**物件由租約帶入**」⇒ 須讀該租客租約
    ```
    ⚠️ 「有 API 但責任是 general」這一格本批**沒有**實例，
       ⛔ 該格為空不代表不可能——⛔ 不得反推成「有 API 就是 REQUIRED」。
    """
    register = _Cfg("account_register", {"requires_instance_reference": False})
    repair = _Cfg("repair_create", {"requires_instance_reference": True})
    assert is_instance_requiring_face(register) is False
    assert is_instance_requiring_face(repair) is True
