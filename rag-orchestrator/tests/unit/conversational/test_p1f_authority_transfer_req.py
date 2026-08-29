"""unit：P1f——Level-A suppression authority 從 lexical query evidence 換手到
Knowledge applicability × Face requirement 的 cross-product。

業主授權（2026-08-29）：
> 不得 lexical fallback，不擴 Level-A scope，gate 保持 OFF。
> UNKNOWN 不等於 general，但對 REQUIRED Level-A Face 同樣不得取得進場 authorization。

⚠️ 這一刀最重要的不是「接了」，是 **authority 真的換手**——
   下方 death controls 若不能翻轉 lexical 的結果，就代表沒換成。
"""
import pytest

import services.instance_reference_gate as gate_mod
from routers.chat import (SUPPRESS_REASON_INELIGIBLE, SUPPRESS_REASON_UNKNOWN,
                          _applicability_suppressed)
from services import instance_applicability as ia

pytestmark = pytest.mark.unit


class _Cfg:
    def __init__(self, key, req):
        self.key = key
        self.grounding_scope = {} if req is None else {"requires_instance_reference": req}


def _row(applicability):
    meta = {} if applicability is None else {ia.KNOWLEDGE_APPLICABILITY_KEY: applicability}
    return {"generation_metadata": meta}


@pytest.fixture
def gate_on(monkeypatch):
    monkeypatch.setattr(gate_mod, "gate_active", lambda: True)


LEVEL_A = "bill_diagnosis"          # 唯一在 LEVEL_A_INSTANCE_GATE_SCOPE 內者
NON_LEVEL_A = "contract_diag"       # REQUIRED 但不在 Level-A


# ════════════════════════════════════════════════════════════════════
# deterministic matrix（7 形狀）
# ════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("applicability,face_key,face_req,expect_suppressed,expect_reason", [
    ("instance", LEVEL_A,     True,  False, None),                        # 保留
    ("general",  LEVEL_A,     True,  True,  SUPPRESS_REASON_INELIGIBLE),  # 抑制
    (None,       LEVEL_A,     True,  True,  SUPPRESS_REASON_UNKNOWN),     # 抑制，理由須為 unknown
    ("instance", LEVEL_A,     False, False, None),                        # NOT_REQUIRED → 不介入
    ("general",  LEVEL_A,     False, False, None),                        # NOT_REQUIRED → 不介入
    ("general",  NON_LEVEL_A, True,  False, None),                        # 非 Level-A → 不介入
    ("instance", NON_LEVEL_A, True,  False, None),                        # 非 Level-A → 不介入
])
def test_matrix(gate_on, applicability, face_key, face_req, expect_suppressed, expect_reason):
    got, reason = _applicability_suppressed(_row(applicability), _Cfg(face_key, face_req))
    assert got is expect_suppressed
    assert reason == expect_reason


def test_unknown_reason_is_not_disguised_as_general():
    """⚠️ UNKNOWN 與 general 的 rollout 動作相同，但**語義不同**——理由必須分得開。

    general → 已知不適格｜UNKNOWN → 未證明適格
    ⛔ 把 UNKNOWN 記成 general 會讓半年後的報表無法分辨「已裁定」與「還沒裁」。
    """
    assert SUPPRESS_REASON_UNKNOWN != SUPPRESS_REASON_INELIGIBLE
    assert "unknown" in SUPPRESS_REASON_UNKNOWN
    assert "general" in SUPPRESS_REASON_INELIGIBLE


# ════════════════════════════════════════════════════════════════════
# gate OFF ＋ 非 Level-A：逐位元等價
# ════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("applicability", ["instance", "general", None])
@pytest.mark.parametrize("face_key", [LEVEL_A, NON_LEVEL_A])
def test_gate_off_never_suppresses(monkeypatch, applicability, face_key):
    """⛔ gate 未啟用時，任何組合都不得抑制——P1f 前後 routing 逐位元相同。"""
    monkeypatch.setattr(gate_mod, "gate_active", lambda: False)
    assert _applicability_suppressed(_row(applicability), _Cfg(face_key, True)) == (False, None)


@pytest.mark.parametrize("applicability", ["instance", "general", None])
def test_non_level_a_faces_unchanged(gate_on, applicability):
    """16 個 REQUIRED Face 中只有 bill_diagnosis 在 Level-A
    ⇒ 其餘 15 個⛔ 不得因 P1f 順手開始受控。"""
    assert _applicability_suppressed(_row(applicability), _Cfg(NON_LEVEL_A, True)) == (False, None)


# ════════════════════════════════════════════════════════════════════
# mutation controls：證明 routing 真的在讀新的 truth contract
# ════════════════════════════════════════════════════════════════════

def test_mutation_general_to_instance_flips_to_retained(gate_on):
    face = _Cfg(LEVEL_A, True)
    assert _applicability_suppressed(_row("general"), face)[0] is True
    assert _applicability_suppressed(_row("instance"), face)[0] is False, \
        "改宣告卻不改結果 ⇒ routing 仍被別的東西控制（lexical／category shortcut）"


def test_mutation_instance_to_general_flips_to_suppressed(gate_on):
    face = _Cfg(LEVEL_A, True)
    assert _applicability_suppressed(_row("instance"), face)[0] is False
    assert _applicability_suppressed(_row("general"), face)[0] is True


def test_mutation_face_requirement_flip(gate_on):
    """Face 端宣告翻轉亦須改變結果（證明兩軸都真的被讀）。"""
    assert _applicability_suppressed(_row("general"), _Cfg(LEVEL_A, True))[0] is True
    assert _applicability_suppressed(_row("general"), _Cfg(LEVEL_A, False))[0] is False


# ════════════════════════════════════════════════════════════════════
# ⚠️ 舊 lexical gate 的「死亡證明」——這一刀最重要的因果證據
# ════════════════════════════════════════════════════════════════════

def test_lexical_block_cannot_suppress_a_declared_instance_row(gate_on, monkeypatch):
    """lexical 判 block（＝舊制會抑制），但 top1 truth = instance ⇒ **必須保留**。"""
    import routers.chat as chat

    class _Blocking:
        verdict = "block"
        reason = "lexical 認為是 rule 型問句"
    monkeypatch.setattr(chat, "_instance_gate_decision", lambda _m: _Blocking())
    suppressed, _ = _applicability_suppressed(_row("instance"), _Cfg(LEVEL_A, True))
    assert suppressed is False, "lexical block 仍能抑制 ⇒ authority 沒有換手"


def test_lexical_allow_cannot_rescue_a_declared_general_row(gate_on, monkeypatch):
    """lexical 看不出 rule 型（＝舊制會放行），但 top1 truth = general ⇒ **必須抑制**。"""
    import routers.chat as chat
    monkeypatch.setattr(chat, "_instance_gate_decision", lambda _m: None)
    suppressed, reason = _applicability_suppressed(_row("general"), _Cfg(LEVEL_A, True))
    assert suppressed is True and reason == SUPPRESS_REASON_INELIGIBLE, \
        "lexical 放行就能救回 ⇒ authority 沒有換手"


def test_suppression_seam_does_not_consult_lexical_evidence():
    """結構鎖：抑制述詞的原始碼**不得**出現 lexical 抽取器或其判定。"""
    import ast
    import inspect
    import textwrap
    # ⚠️ 只看**可執行語句**：docstring 裡本來就寫著「不再使用 lexical」，
    #    連說明一起比對會把文件誤判成違規（本檔第一版就是這樣紅的，同 P1c 的教訓）。
    tree = ast.parse(textwrap.dedent(inspect.getsource(_applicability_suppressed)))
    docstrings = {id(n.body[0].value) for n in ast.walk(tree)
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module))
                  and getattr(n, "body", None) and isinstance(n.body[0], ast.Expr)
                  and isinstance(n.body[0].value, ast.Constant)
                  and isinstance(n.body[0].value.value, str)}
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            names.add(n.id)
        elif isinstance(n, ast.Attribute):
            names.add(n.attr)
        elif isinstance(n, ast.arg):
            names.add(n.arg)
        elif isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings:
            names.add(n.value)
    for forbidden in ("InstanceEvidenceExtractor", "_instance_gate_decision", "user_message"):
        assert forbidden not in names, f"抑制述詞引用了 {forbidden} ⇒ 存在 lexical fallback"
    # 正對照：真正使用的名稱必須看得見，否則這把尺是空的
    assert "instance_applicability_decision" in names
    assert "gate_active" in names
