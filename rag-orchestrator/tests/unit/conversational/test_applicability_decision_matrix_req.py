"""unit：P1c——**接契約，不接政策**。

completion criterion（業主定案 2026-08-29）五條：
```text
1. Knowledge／Face 兩個 contract reader 都是 tri-state
2. 交叉判定是純函數，六格 deterministic matrix 全過
3. UNKNOWN 在任何一側都不被降成 false／general
4. 3509 保持 census UNKNOWN，證明沒有 fallback inference
5. Gate 仍 OFF，P1c 前後 routing equivalence 成立
```

⚠️ 這一刀的目標是「讓系統能正確理解**已宣告**的 applicability」，
⛔ **不是**「讓 gate 開始替 873 筆知識做判斷」——後者還需要 population 與新的 authorization。
"""
import inspect
import io as _io
import tokenize
from pathlib import Path

import pytest

from services import instance_applicability as ia
from services.instance_reference_gate import (LEVEL_A_INSTANCE_GATE_SCOPE,
                                              is_instance_requiring_face)

pytestmark = pytest.mark.unit

APP = Path(__file__).resolve().parents[3]


def _executable_source(path: Path) -> str:
    """剝掉註解與字串常量（含 docstring），只留**可執行**的程式碼。

    ⚠️ 第一版用「行首是 # 或含三引號」剝，太弱——module docstring 裡提到
    `form_id`／`instance_applicability_decision` 都被誤判成違規。
    註解與文件**刻意**會提到這些名字（那正是它們的說明文），
    量尺必須分得出「說明」與「使用」。
    """
    out = []
    with tokenize.open(str(path)) as fh:
        for tok in tokenize.generate_tokens(fh.readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            out.append(tok.string)
    return " ".join(out)


class _Cfg:
    def __init__(self, scope):
        self.grounding_scope = scope


def _face(req):
    return _Cfg({} if req is None else {"requires_instance_reference": req})


def _row(applicability=None, **extra):
    meta = dict(extra.pop("generation_metadata", {}) or {})
    if applicability is not None:
        meta[ia.KNOWLEDGE_APPLICABILITY_KEY] = applicability
    return {"generation_metadata": meta or None, **extra}


# ════════════════════════════════════════════════════════════════════
# 六格 deterministic matrix
# ════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("knowledge,face_req,expected", [
    # 業主鎖定的四格
    ("instance", True,  ia.DECISION_ELIGIBLE),
    ("general",  True,  ia.DECISION_INELIGIBLE),
    (None,       True,  ia.DECISION_UNKNOWN),          # UNKNOWN ⛔ 不得取得正向 authorization
    ("instance", False, ia.DECISION_NOT_APPLICABLE),   # ⛔ 不得被 instance 規則誤傷
    # 補的兩格：**Face 契約缺失 ≠ 這個 Face 不要求 instance**
    ("instance", None,  ia.DECISION_UNKNOWN),
    ("general",  None,  ia.DECISION_UNKNOWN),
])
def test_six_cell_matrix(knowledge, face_req, expected):
    assert ia.instance_applicability_decision(_row(knowledge), _face(face_req)) == expected


@pytest.mark.parametrize("knowledge", ["instance", "general", None])
def test_face_not_required_is_never_hit_by_instance_rules(knowledge):
    """face=NOT_REQUIRED 時，knowledge 三態一律 NOT_APPLICABLE（不受此述詞誤傷）。"""
    assert ia.instance_applicability_decision(_row(knowledge), _face(False)) \
        == ia.DECISION_NOT_APPLICABLE


def test_decision_is_a_pure_function():
    """⛔ 交叉判定不得讀環境、不得打 DB、不得看 runtime 狀態。"""
    src = inspect.getsource(ia.instance_applicability_decision)
    for forbidden in ("os.getenv", "os.environ", "await", "requests", "psql", "db_pool"):
        assert forbidden not in src, f"純函式契約被破壞：出現 {forbidden}"


# ════════════════════════════════════════════════════════════════════
# UNKNOWN 在任何一側都不被降級
# ════════════════════════════════════════════════════════════════════

def test_unknown_never_collapses_into_general_or_false():
    assert ia.knowledge_instance_applicability(_row(None)) == ia.APPLICABILITY_UNKNOWN
    assert ia.knowledge_instance_applicability(_row(None)) != ia.APPLICABILITY_GENERAL
    assert ia.face_instance_requirement(_face(None)) == ia.FACE_UNKNOWN
    assert ia.face_instance_requirement(_face(None)) != ia.FACE_NOT_REQUIRED
    # 交叉後仍是 UNKNOWN，⛔ 不得變成 INELIGIBLE（那等於當成 general）
    assert ia.instance_applicability_decision(_row(None), _face(True)) == ia.DECISION_UNKNOWN


def test_unknown_and_ineligible_are_distinct_results():
    """⚠️ 兩者都「不放行」，但**理由不同**——壓成同一格就退回布林時代。"""
    assert ia.DECISION_UNKNOWN != ia.DECISION_INELIGIBLE


# ════════════════════════════════════════════════════════════════════
# 3509：census false-negative control —— ⛔ 不得從 runtime／歷史推導 metadata
# ════════════════════════════════════════════════════════════════════

def test_3509_shape_stays_unknown_despite_us_knowing_it_is_instance():
    """3509「訂閱扣款失敗導致功能異常」：**我們人知道**它需要查訂閱狀態，
    但它沒有宣告、沒有 form、是 direct_answer ⇒ 契約必須照實回 UNKNOWN。

    ⛔ 不得因為「本輪 smoke 證明過它是 instance」就在契約層偷偷補上——
    那會讓 metadata 變成從 runtime 反推，正是 P1a 明令禁止的 fallback。
    """
    row_3509 = _row(None, action_type="direct_answer", form_id=None,
                    question_summary="訂閱扣款失敗導致功能異常")
    assert ia.knowledge_instance_applicability(row_3509) == ia.APPLICABILITY_UNKNOWN
    assert ia.instance_applicability_decision(row_3509, _face(True)) == ia.DECISION_UNKNOWN


def test_contract_module_has_no_inference_surface():
    """契約模組**只讀宣告**：不得出現 form_id／action_type／api_config 等推導來源。"""
    code = _executable_source(APP / "services/instance_applicability.py")
    for field in ("form_id", "action_type", "api_config", "categories"):
        assert field not in code, f"契約模組出現推導來源 {field}"


# ════════════════════════════════════════════════════════════════════
# routing equivalence：P1c 前後行為必須逐位元相同，且 gate 仍 OFF
# ════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("scope,expected", [
    ({"requires_instance_reference": True}, True),
    ({"requires_instance_reference": False}, False),
    ({}, False),                                    # 缺欄位 → False（fail-closed by scope）
    ({"requires_instance_reference": "true"}, False),
    (None, False),
])
def test_live_predicate_truth_table_unchanged(scope, expected):
    """⚠️ `is_instance_requiring_face` 已改為委派新契約，**行為必須逐位元不變**。

    它現在是 compatibility wrapper，⛔ 不再是 authority truth source；
    降級（三態→布林）發生在單一可見處。
    """
    assert is_instance_requiring_face(_Cfg(scope)) is expected


def test_gate_scope_unchanged_and_still_paused():
    """⛔ P1c 不得順手擴大 gate 的 rollout scope。"""
    assert LEVEL_A_INSTANCE_GATE_SCOPE == frozenset({"bill_diagnosis"})


def test_no_consumer_reads_the_new_decision_yet():
    """⛔ P1c **不接政策**：routing 尚未依 `instance_applicability_decision` 改變行為。

    ⚠️ 這條是刻意的「尚未接線」斷言——它會在 P1d／authorization 時被有意改掉，
    改的時候必須同時提出新的授權證據，而不是悄悄接上。
    """
    for rel in ("routers/chat.py", "services/conversational_engine.py",
                "services/instance_reference_gate.py"):
        code = _executable_source(APP / rel)
        assert "instance_applicability_decision" not in code, \
            f"{rel} 已消費新判定 ⇒ P1c 的『不接政策』界線被跨越"
