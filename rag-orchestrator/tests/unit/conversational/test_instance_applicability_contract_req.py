"""unit：P1a——instance applicability 成為獨立、machine-readable、三態可辨的資料契約。

completion criterion（業主定案 2026-08-29）：

> Instance applicability 已成為獨立、machine-readable、三態可辨的資料契約；
> candidate identity 仍由 nomination metadata 提供。
> **缺失宣告不得默認為 general**，且 routing 在重新授權前維持既有行為。
"""
import pytest

from services import instance_applicability as ia

pytestmark = pytest.mark.unit


# ════════════════════════════════════════════════════════════════════
# 三態
# ════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("declared,expected", [
    ("instance", ia.APPLICABILITY_INSTANCE),
    ("general", ia.APPLICABILITY_GENERAL),
])
def test_declared_values_are_read_verbatim(declared, expected):
    assert ia.knowledge_instance_applicability({"generation_metadata": {ia.KNOWLEDGE_APPLICABILITY_KEY: declared}}) == expected


@pytest.mark.parametrize("meta", [
    None, {}, {"iteration": 3}, {"instance_applicability": None},
    {"instance_applicability": True},          # 型別不對
    {"instance_applicability": "Instance"},    # 大小寫變體
    {"instance_applicability": "是"},          # 中文變體
    {"instance_applicability": "true"},        # 布林字面
])
def test_missing_or_malformed_is_unknown_never_general(meta):
    """⚠️ **缺宣告 ≠ general**，值寫錯也**不猜**——容忍變體＝讓資料品質問題靜默通過。"""
    got = ia.knowledge_instance_applicability({"generation_metadata": meta})
    assert got == ia.APPLICABILITY_UNKNOWN
    assert got != ia.APPLICABILITY_GENERAL, "「不知道」被讀成「不需要」——正是本輪要修的病灶"


# ════════════════════════════════════════════════════════════════════
# ⛔ 不得從執行能力推導（3509 是反證）
# ════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("row", [
    {"form_id": "jgb_subscription_diagnosis", "action_type": "form_fill"},
    {"action_type": "api_call", "api_config": {"endpoint": "jgb_bills"}},
    {"action_type": "direct_answer"},
])
def test_execution_capability_never_derives_applicability(row):
    """`form_id`／`action_type` 編碼的是**執行**，不是**實值依賴**。

    ⚠️ 反證：3509「訂閱扣款失敗導致功能異常」是 direct_answer、無 form_id，
    卻必須查該帳號訂閱狀態 ⇒ 用執行能力當代理會**系統性漏掉**這一類。
    """
    assert ia.knowledge_instance_applicability(row) == ia.APPLICABILITY_UNKNOWN


# ════════════════════════════════════════════════════════════════════
# UNKNOWN 不得取得正向授權
# ════════════════════════════════════════════════════════════════════

def test_unknown_grants_no_positive_authorization():
    assert ia.grants_positive_authorization(ia.APPLICABILITY_INSTANCE) is True
    assert ia.grants_positive_authorization(ia.APPLICABILITY_GENERAL) is False
    assert ia.grants_positive_authorization(ia.APPLICABILITY_UNKNOWN) is False


# ════════════════════════════════════════════════════════════════════
# Face 層三態，且 ⛔ P1a 不改現役 routing 行為
# ════════════════════════════════════════════════════════════════════

class _Cfg:
    def __init__(self, scope):
        self.grounding_scope = scope


@pytest.mark.parametrize("scope,expected", [
    ({"requires_instance_reference": True}, "required"),
    ({"requires_instance_reference": False}, "not_required"),
    ({}, "unknown"),
    ({"requires_instance_reference": "true"}, "unknown"),   # 型別不對＝未宣告
    (None, "unknown"),
])
def test_face_requirement_is_tri_state(scope, expected):
    """⚠️ 回字串不回 Optional[bool]：`None` 一個 `is True` 就被悄悄降成 False。"""
    assert ia.face_instance_requirement(_Cfg(scope)) == expected


def test_p1a_does_not_change_live_routing_predicate():
    """⛔ P1a 只建立**分辨能力**，現役述詞行為必須原樣（改它是 P1c）。

    `is_instance_requiring_face()` 缺欄位仍回 False（fail-closed by scope）；
    新的 `face_instance_requirement()` 才回 None。兩者**刻意**不同。
    """
    from services.instance_reference_gate import is_instance_requiring_face
    cfg = _Cfg({})
    assert is_instance_requiring_face(cfg) is False              # 現役：缺欄位→False
    assert ia.face_instance_requirement(cfg) == ia.FACE_UNKNOWN  # 新契約：缺欄位→未宣告
