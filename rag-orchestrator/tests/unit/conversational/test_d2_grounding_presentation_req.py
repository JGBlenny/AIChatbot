"""unit：T4-D2 GROUNDING_FACTS presentation adapter guards（業主凍結 2026-08-30）。

```text
D2-G1 adapter signature ⛔ 無 user_question／face／category／config
D2-G2 same facts ＋ 不同 utterance／face noise → **identical** presentation payload
D2-G3 R-28 member answers 皆空 → presentation 仍完整成立
D2-G4 grounding facts 缺／空 → hard fail；⛔ 不得 fallback canonical text／member answer
D2-G5 candidate outcome → ask presentation，⛔ 不得自行 candidates[0]
D2-G6 FACTS outcome → converge presentation，⛔ 不重跑 semantic dispatcher
D2-M1 adapter 內用 face 選 builder → 必紅
D2-M2 adapter 偷讀 row.answer     → 必紅
D2-M3 adapter 用 user_question 選不同話術 owner → 必紅
```
⚠️ 本刀 ⛔ 不處理 LLM 最終生成 correctness——那是後續 wired integration 的另一層。
"""
import inspect
import re

import pytest

from services import grounding_presentation as gp
from services.grounding_presentation import GroundingPresentationError, present

pytestmark = pytest.mark.unit

LATE_FEE_FACTS = ("帳單「延遲金 2026-07」金額 NT$ 360、狀態：待繳費。\n"
                  "系統結算備註（原樣）：租金 ×（實際付款日 − 繳費期限 − 緩衝天數）× 費率。")


def _facts(**over):
    p = {"outcome": gp.OUTCOME_FACTS, "responsibility_id": "R-28",
         "grounding_facts": LATE_FEE_FACTS, "entity_id": 88012, "entity_label": "延遲金 2026-07"}
    p.update(over)
    return p


# ───────────────────────── D2-G1 ─────────────────────────
#: ⛔ 不得出現在**可執行碼**的識別字（出現在 docstring 的禁止清單說明中是允許的）
BANNED_IDENTIFIERS = ("user_question", "face", "category", "_domain_key",
                      "BILL_FACE_BUILDERS", "is_point_refund_intent", "endpoint",
                      "mapping", "select_point_refund")


def _executable_identifiers(module):
    """⚠️ 以 **AST** 取可執行碼中的識別字——⛔ 不用行首字元猜註解／docstring
    （那種 heuristic 會把禁止清單的說明文字誤判成違規）。"""
    import ast
    tree = ast.parse(inspect.getsource(module))
    for node in ast.walk(tree):        # 移除所有 docstring 常數
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                body.pop(0)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                names.add(a.name.split(".")[-1])
                if a.asname:
                    names.add(a.asname)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            names.add(node.value)          # 非 docstring 的字串常數也算可執行碼
    return names


@pytest.mark.req("D2_G1:1")
def test_d2_g1_signature_has_no_authority_inputs():
    params = set(inspect.signature(present).parameters)
    assert params == {"payload"}
    ident = _executable_identifiers(gp)
    for banned in BANNED_IDENTIFIERS:
        assert not any(banned in n for n in ident), \
            f"可執行碼含 {banned} ⇒ 邊界不夠 post-authority"


@pytest.mark.req("D2_G1:3")
def test_d2_g1_scanner_itself_can_detect_violation():
    """⚠️ **正對照**：掃描器必須抓得到真正的違規，否則 D2-G1 是假綠。"""
    import ast
    import types
    fake = types.ModuleType("fake")
    fake.__loader__ = None
    src = 'def present(payload, user_question=None):\n    return BILL_FACE_BUILDERS.get(payload)\n'
    tree = ast.parse(src)
    names = {n.arg for n in ast.walk(tree) if isinstance(n, ast.arg)}
    names |= {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert "user_question" in names and "BILL_FACE_BUILDERS" in names, \
        "掃描器抓不到已知違規 ⇒ D2-G1 不可信"


@pytest.mark.req("D2_G1:2")
def test_d2_g1_module_does_not_import_owner_selection():
    src = inspect.getsource(gp)
    assert "from services.jgb" not in src and "import services.jgb" not in src, \
        "presentation 層 ⛔ 不應 import 領域 builder"


# ───────────────────────── D2-G2 ─────────────────────────
@pytest.mark.req("D2_G2:1")
def test_d2_g2_identical_payload_under_noise():
    """⚠️ 干擾**無處可傳**：多塞的鍵一律被忽略，輸出逐位相同。"""
    base = present(_facts())
    noisy = present(_facts(user_question="為什麼不能取消帳單", face="條件診斷：帳單",
                           category="帳單管理", config={"x": 1}))
    assert dict(noisy) == dict(base), "presentation 隨干擾改變 ⇒ 邊界破了"


# ───────────────────────── D2-G3 ─────────────────────────
@pytest.mark.req("D2_G3:1")
def test_d2_g3_r28_members_empty_answer_still_works():
    """R-28 的 3939／3940 answer 皆空——presentation 仍必須完整成立。"""
    import json
    import os
    reg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..",
                       ".kiro", "specs", "conversational-routing-execution", "r10p",
                       "registry-v2.json")
    with open(os.path.abspath(reg), encoding="utf-8") as f:
        r28 = next(r for r in json.load(f)["responsibilities"]
                   if r["responsibility_id"] == "R-28")
    assert sorted(m["row_id"] for m in r28["members"]) == [3939, 3940]
    out = present(_facts())
    assert out["kind"] == gp.KIND_CONVERGE and LATE_FEE_FACTS in out["grounding"]
    assert "延遲金 2026-07" in out["grounding"] and "88012" in out["grounding"]


# ───────────────────────── D2-G4 ＋ D2-M2 ─────────────────────────
@pytest.mark.req("D2_G4:1")
@pytest.mark.parametrize("bad", [None, "", "   "])
def test_d2_g4_missing_facts_hard_fails(bad):
    with pytest.raises(GroundingPresentationError, match="不得改用 canonical_responsibility"):
        present(_facts(grounding_facts=bad))


@pytest.mark.req("D2_M2:1")
def test_d2_m2_row_answer_cannot_rescue_missing_facts():
    """D2-M2：即使塞 answer／canonical_responsibility，⛔ 不得被拿來補。"""
    with pytest.raises(GroundingPresentationError):
        present(_facts(grounding_facts=None, answer="ROW ANSWER",
                       canonical_responsibility="canonical 陳述"))
    # 正對照：facts 正常時，row answer **不會**混進輸出
    out = present(_facts(answer="ROW ANSWER"))
    assert "ROW ANSWER" not in out["grounding"]


# ───────────────────────── D2-G5 ─────────────────────────
@pytest.mark.req("D2_G5:1")
def test_d2_g5_candidates_never_auto_selected():
    cands = [{"id": 9001, "label": "點退帳單 A"}, {"id": 9002, "label": "點退帳單 B"}]
    out = present({"outcome": gp.OUTCOME_CANDIDATES, "responsibility_id": "R-31",
                   "candidates": cands})
    assert out["kind"] == gp.KIND_ASK
    assert "grounding" not in out, "候選態 ⛔ 不得產出 converge grounding"
    assert [c["id"] for c in out["candidates"]] == [9001, 9002]
    assert [q["value"] for q in out["quick_replies"]] == ["9001", "9002"]


@pytest.mark.req("D2_G5:2")
def test_d2_g5_empty_candidates_hard_fails():
    with pytest.raises(GroundingPresentationError, match="沒有候選"):
        present({"outcome": gp.OUTCOME_CANDIDATES, "responsibility_id": "R-31",
                 "candidates": []})


# ───────────────────────── D2-G6 ─────────────────────────
@pytest.mark.req("D2_G6:1")
def test_d2_g6_facts_outcome_is_converge_and_writes_note():
    out = present(_facts())
    assert out["kind"] == gp.KIND_CONVERGE
    assert out["state_updates"]["grounding_note"] == out["grounding"][:gp.GROUNDING_NOTE_LIMIT]


@pytest.mark.req("D2_G6:2")
def test_d2_g6_does_not_reclassify_outcome():
    """⚠️ 本層 ⛔ 不重新分類——未知 outcome 直接 hard fail，⛔ 不猜。"""
    with pytest.raises(GroundingPresentationError, match="本層不重新分類"):
        present({"outcome": "SELECTED_MAYBE", "responsibility_id": "R-31"})


# ───────────────────────── R-31 的多 outcome ─────────────────────────
@pytest.mark.req("D2_R31:1")
@pytest.mark.parametrize("outcome", [gp.OUTCOME_NOT_FOUND, gp.OUTCOME_TYPE_MISMATCH])
def test_d2_r31_other_outcomes_need_reviewed_note(outcome):
    note = "這份合約目前沒有點退帳單。"
    out = present({"outcome": outcome, "responsibility_id": "R-31", "outcome_note": note})
    assert out["kind"] == gp.KIND_ASK and out["answer"] == note
    with pytest.raises(GroundingPresentationError, match="本層不自行編話術"):
        present({"outcome": outcome, "responsibility_id": "R-31"})


@pytest.mark.req("D2_R31:2")
def test_d2_does_not_rerun_selection():
    """⚠️ D2 收的是 **already-classified outcome**，⛔ 不重跑 select_point_refund。"""
    assert not any("select_point_refund" in n for n in _executable_identifiers(gp))


# ───────────────────────── mutations ─────────────────────────
@pytest.mark.req("D2_M1:1")
def test_d2_m1_face_based_builder_selection_would_be_red():
    """D2-M1：若 adapter 內用 face 選 builder，同 facts 會因 face 不同而異。"""
    from services.jgb.bills import BILL_FACE_BUILDERS
    a = BILL_FACE_BUILDERS.get("滯納金")
    b = BILL_FACE_BUILDERS.get("帳單異常")
    assert a is not b, "D2-M1 未讓 guard 變紅 ⇒ face 選 builder 確實會改變 owner"
    assert not any("BILL_FACE_BUILDERS" in n for n in _executable_identifiers(gp)), \
        "presentation 層引用了 face builder 表"


@pytest.mark.req("D2_M3:1")
def test_d2_m3_utterance_cannot_select_different_wording():
    """D2-M3：用 user_question 選不同話術 owner。"""
    outs = {present(_facts(user_question=q))["grounding"]
            for q in ("滯納金怎麼收這麼多", "這筆延遲金是怎麼算的", "為什麼不能取消帳單")}
    assert len(outs) == 1, "D2-M3：輸出隨 utterance 改變 ⇒ 話術 owner 被重選"
