"""unit：T4-A responsibility session carrier ＋ resume integrity（業主凍結 2026-08-30）。

```text
A-G1 authority survives round-trip   form 任何輸入都不得改四個 authority 欄位
A-G2 no authority recovery from row  responsibility mode 帶 non-null knowledge_id → **hard fail**
                                     （⚠️ 比「默默 ignore」更可稽核）
A-G3 wrong completion action         responsibility＋show_knowledge → 紅；
                                     反向正控制：legacy＋show_knowledge → **行為不變**
A-G4 mode exactness                  mode 缺／未知／欄位缺／legacy 用 responsibility-only action → 紅
                                     ⛔ 不得「欄位有哪個就猜 mode」
A-G5 binding immutability            payload 塞 responsibility_id／binding_id → 無權覆寫
```
⚠️ 本刀 ⛔ 不執行 capability——resume 只恢復計畫。
"""
import pytest

from services import responsibility_session as rsess
from services.responsibility_session import (SessionAuthorityConflict, SessionAuthorityError,
                                             build_responsibility_session, resume_fulfillment,
                                             validate_session)

pytestmark = pytest.mark.unit

R29 = dict(responsibility_id="R-29", fulfillment_binding_id="receipt.actual_amount.v1",
           fulfillment_strategy="CAPABILITY", input_contract_id="bill.by_ref.v1")


def _legacy(action=rsess.ACTION_SHOW_KNOWLEDGE, **over):
    s = {"session_authority_mode": rsess.MODE_LEGACY, "knowledge_id": 3496,
         "on_complete_action": action}
    s.update(over)
    return s


# ───────────────────────── A-G1 ─────────────────────────
@pytest.mark.req("T4A_G1:1")
def test_a_g1_authority_survives_round_trip():
    sess = build_responsibility_session(**R29)
    plan = resume_fulfillment(sess, {"bill_ref": "B-12345", "note": "使用者亂填的東西"})
    for f in rsess.AUTHORITY_FIELDS:
        assert plan[f] == R29[f], f"{f} 在 round-trip 後改變了"
    assert plan["resolved_inputs"] == {"bill_ref": "B-12345", "note": "使用者亂填的東西"}
    assert plan["kind"] == "resumed_fulfillment_plan"


@pytest.mark.req("T4A_G1:2")
def test_a_g1_resume_does_not_execute_capability():
    """⚠️ T4-A ⛔ 不執行 capability——輸出只有計畫，沒有答案。"""
    plan = resume_fulfillment(build_responsibility_session(**R29), {"bill_ref": "B-1"})
    assert "answer" not in plan and "similarity" not in plan and "grounding" not in plan
    assert "_not_executed" in plan


# ───────────────────────── A-G2 ─────────────────────────
@pytest.mark.req("T4A_G2:1")
def test_a_g2_build_rejects_knowledge_id():
    with pytest.raises(SessionAuthorityConflict, match="不得攜帶 non-null knowledge_id"):
        build_responsibility_session(**R29, knowledge_id=3496)


@pytest.mark.req("T4A_G2:2")
def test_a_g2_legacy_field_residue_is_hard_fail():
    """mutation：模擬舊欄位殘留（⛔ 不得默默 ignore）。"""
    sess = build_responsibility_session(**R29)
    sess["knowledge_id"] = 3496
    with pytest.raises(SessionAuthorityConflict, match="不得從 knowledge_id 回收 authority"):
        validate_session(sess)
    with pytest.raises(SessionAuthorityConflict):
        resume_fulfillment(sess, {"bill_ref": "B-1"})


# ───────────────────────── A-G3 ─────────────────────────
@pytest.mark.req("T4A_G3:1")
def test_a_g3_responsibility_with_show_knowledge_rejected():
    sess = build_responsibility_session(**R29)
    sess["on_complete_action"] = rsess.ACTION_SHOW_KNOWLEDGE
    with pytest.raises(SessionAuthorityError, match="不得使用 show_knowledge"):
        validate_session(sess)


@pytest.mark.req("T4A_G3:2")
def test_a_g3_legacy_show_knowledge_unchanged():
    """反向正控制：⛔ 沒有順手殺掉 legacy。"""
    assert validate_session(_legacy()) == rsess.MODE_LEGACY


# ───────────────────────── A-G4 ─────────────────────────
@pytest.mark.req("T4A_G4:1")
@pytest.mark.parametrize("mutate,match", [
    (lambda s: s.pop("session_authority_mode"), "不得由欄位存在與否猜測 mode"),
    (lambda s: s.update({"session_authority_mode": "auto"}), "未知的 session_authority_mode"),
    (lambda s: s.update({"responsibility_id": None}), "缺少 authority 欄位"),
    (lambda s: s.update({"fulfillment_binding_id": None}), "缺少 authority 欄位"),
    (lambda s: s.update({"input_contract_id": None}), "缺少 authority 欄位"),
])
def test_a_g4_mode_exactness(mutate, match):
    sess = build_responsibility_session(**R29)
    mutate(sess)
    with pytest.raises(SessionAuthorityError, match=match):
        validate_session(sess)


@pytest.mark.req("T4A_G4:2")
def test_a_g4_legacy_cannot_use_responsibility_action():
    with pytest.raises(SessionAuthorityError, match="不得使用 responsibility-only"):
        validate_session(_legacy(action=rsess.ACTION_RESUME_FULFILLMENT))


@pytest.mark.req("T4A_G4:3")
def test_a_g4_no_mixed_session():
    """⛔ 不做讓 runtime 猜誰優先的混合 session。"""
    with pytest.raises(SessionAuthorityError, match="不得攜帶 responsibility authority 欄位"):
        validate_session(_legacy(responsibility_id="R-29"))


@pytest.mark.req("T4A_G4:4")
def test_a_g4_legacy_session_cannot_resume():
    with pytest.raises(SessionAuthorityError, match="不得走 resume_fulfillment"):
        resume_fulfillment(_legacy(), {})


# ───────────────────────── A-G5 ─────────────────────────
@pytest.mark.req("T4A_G5:1")
@pytest.mark.parametrize("field", list(rsess.AUTHORITY_FIELDS))
def test_a_g5_payload_cannot_override_authority(field):
    sess = build_responsibility_session(**R29)
    with pytest.raises(SessionAuthorityError, match="嘗試覆寫 execution authority"):
        resume_fulfillment(sess, {field: "attacker-value", "bill_ref": "B-1"})


@pytest.mark.req("T4A_G5:2")
def test_a_g5_payload_cannot_change_mode_or_action():
    sess = build_responsibility_session(**R29)
    for bad in ({"session_authority_mode": rsess.MODE_LEGACY},
                {"on_complete_action": rsess.ACTION_SHOW_KNOWLEDGE}):
        with pytest.raises(SessionAuthorityError, match="不得改寫 session mode"):
            resume_fulfillment(sess, bad)


@pytest.mark.req("T4A_G5:3")
def test_a_g5_binding_id_is_opaque_not_callable():
    """⚠️ session 存**穩定 ID**，⛔ 不存 callable／function path。"""
    sess = build_responsibility_session(**R29)
    b = sess["fulfillment_binding_id"]
    assert isinstance(b, str) and "::" not in b and ".py" not in b and not callable(b)
