"""unit：主題錨定極性詞表 `negation_status_pairs`（W6-b3／plan-verifier r3 #1）。

病灶（第二批回測）：事實段印「已逾期 8 天」，模型答「尚未逾期」——`negation_terms`
十項裡沒有「尚未／未／還沒」，極性檢查看不見這個翻轉。

**⛔ 不加裸「尚未」「未」**：整段引文比對會把「句子沒提到該主題、引文另一段落剛好有
否定」的**正確句**誤殺（`known_open.json` 的 `r4_edit_contract_requires_admin_role`：
句子「編輯合約需要管理者權限」、引文段落含「管理方尚未回簽」）。改成
`(否定詞, 狀態詞)` 配對——兩側必須談到**同一個狀態詞**才算數。

覆蓋：
- 載入正對照（規則檔筆數＝載入筆數＝7×8＝56，且兩個集合就是規則檔寫的那兩個）；
- 「尚未逾期」對「已逾期 8 天（以今日 2026/09/09 計）」⇒ `POLARITY_MISMATCH`；
- 正對照「已逾期 8 天」對同一段引文 ⇒ 放行；
- `known_open` 那個案的形狀（句子不含「回簽」、引文含「尚未回簽」）⇒ 放行；
- 三份自檢 fixture 經 `self_test` 全綠（詞表變更的驗收面）；
- `term_id` 與 `negation_terms` 的索引**不撞號**。
"""
import json
from pathlib import Path

import pytest

from services.agent.output_schema import AgentOutput, VerifierRules
from services.agent.provenance_units import resolve_refs
from services.agent.tools.registry import ToolResult
from services.agent.verifier import OutputVerifier

pytestmark = pytest.mark.unit

_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "agent"
_RULES_PATH = Path(__file__).resolve().parents[3] / "config" / "agent_verifier_rules.json"

NONCE = "POLARITY00000000"

#: 第二批走查抓到的真實引文（帳單事實段）。
OVERDUE_UNIT = "本期帳單已逾期 8 天（以今日 2026/09/09 計）。"
#: `known_open.json` 的 `r4_edit_contract_requires_admin_role` 的形狀：
#: 句子不談「回簽」，引文段落卻含「尚未回簽」。
CONTRACT_UNIT = "編輯合約需要管理者權限，且管理方尚未回簽時不得送出。"


@pytest.fixture(scope="module")
def rules() -> VerifierRules:
    return VerifierRules.load(_RULES_PATH)


@pytest.fixture(scope="module")
def verifier(rules: VerifierRules) -> OutputVerifier:
    return OutputVerifier(rules)


def _verify(verifier: OutputVerifier, sentence_text: str, unit_text: str):
    out = AgentOutput.model_validate({
        "kind": "answer",
        "sentences": [{
            "text": sentence_text,
            "kind": "fact",
            "refs": [f"[{NONCE}:t1:kb:7000§0]"],
        }],
        "fact_class": "feature",
        "handoff_reason": None,
    })
    tool_results = {"t1": ToolResult.model_validate({
        "ok": True,
        "provenance": [{"source": "kb:7000", "text": unit_text, "citable": True}],
        "text_for_model": "",
    })}
    resolved, resolve_errors = resolve_refs(out, tool_results, NONCE)
    return verifier.verify(out, tool_results, "帳單狀況？", None,
                           resolved=resolved, resolve_errors=resolve_errors)


# ---------------------------------------------------------------- 載入正對照


def test_pairs_are_loaded_from_the_shipped_rules_file(rules):
    """正對照（plan-verifier r1 #2 同型）：pydantic 白名單會**靜默忽略**未宣告的鍵——
    沒有這條，規則檔寫了 56 筆而程式一筆都沒讀到，測試照樣全綠。"""
    raw = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
    assert len(raw["negation_status_pairs"]) == 56
    assert len(rules.negation_status_pairs) == len(raw["negation_status_pairs"])
    assert rules.negation_status_pairs, "載入結果是空表＝這條規則等於沒開"


def test_pairs_are_the_cartesian_product_of_two_closed_sets(rules):
    """詞表以**兩個封閉集合的笛卡兒積**維護（⛔ 不是逐案加詞）。"""
    negs = ["尚未", "未", "還沒", "沒有", "不在", "並未", "待"]   # 「待」＝尚未（待發送／待繳費），2026-09-09 第四批回測誤殺後加入
    statuses = ["逾期", "繳費", "到帳", "發送", "回簽", "簽署", "指派", "完成"]
    got = {(p["neg"], p["status"]) for p in rules.negation_status_pairs}
    assert got == {(n, s) for n in negs for s in statuses}
    assert len(got) == len(negs) * len(statuses) == 56


def test_bare_negation_terms_are_untouched(rules):
    """⛔ 裸「尚未」「未」不得混進 `negation_terms`（那正是誤殺 `known_open` 的作法）。"""
    assert "尚未" not in rules.negation_terms
    assert "未" not in rules.negation_terms
    assert len(rules.negation_terms) == 10


# ---------------------------------------------------------------- 判定


def test_not_yet_overdue_against_already_overdue_is_a_polarity_mismatch(verifier):
    """病灶案：句「尚未逾期」對引文「已逾期 8 天」⇒ 擋。"""
    verdict = _verify(verifier, "您的這期帳單尚未逾期，可以再等等。", OVERDUE_UNIT)
    assert verdict.ok is False
    assert verdict.reason == "POLARITY_MISMATCH"


def test_already_overdue_against_the_same_unit_passes(verifier):
    """正對照：同一段引文、句子改成正確的「已逾期 8 天」⇒ 放行。
    沒有這條，上面那條只證明「這句被擋了」，不證明擋的是**極性**。"""
    verdict = _verify(verifier, "您的這期帳單已逾期 8 天，請儘快處理。", OVERDUE_UNIT)
    assert verdict.ok is True, verdict.model_dump()


def test_known_open_shape_is_not_a_false_positive(verifier):
    """r3 #1：句子**不含**該狀態詞（「回簽」）⇒ 引文側的「尚未回簽」不算數。
    這正是加裸「尚未」會翻紅 `known_open` 的那個形狀。"""
    verdict = _verify(verifier, "編輯合約需要管理者權限。", CONTRACT_UNIT)
    assert verdict.ok is True, verdict.model_dump()


def test_unit_side_negation_with_a_positive_sentence_is_blocked(verifier):
    """反向（引文側否定）：句子說「已回簽」、引文說「尚未回簽」⇒ 擋。"""
    verdict = _verify(verifier, "管理方已回簽這份合約，可以編輯。", CONTRACT_UNIT)
    assert verdict.ok is False
    assert verdict.reason == "POLARITY_MISMATCH"


def test_same_polarity_on_the_same_topic_passes(verifier):
    """正對照：兩側**同樣**否定同一個狀態詞 ⇒ 放行。"""
    verdict = _verify(verifier, "管理方尚未回簽這份合約，需要管理者權限。", CONTRACT_UNIT)
    assert verdict.ok is True, verdict.model_dump()


def test_pair_term_id_does_not_collide_with_bare_negation_terms(verifier, rules):
    """`term_id` 是 `(reason, 索引)` 的索引：兩張表撞號就對不回是哪一條規則。"""
    verdict = _verify(verifier, "您的這期帳單尚未逾期，可以再等等。", OVERDUE_UNIT)
    assert verdict.term_id is not None
    index = int(verdict.term_id.split("#")[1])
    assert index >= 1000 > len(rules.negation_terms)


# ---------------------------------------------------------------- 詞表變更的驗收面


def test_all_three_shipped_fixtures_stay_green(verifier):
    """詞表變更的驗收面＝三份自檢 fixture 全綠（`bootstrap.build_runtime` 起得來）。

    `known_open.json` 的 `r4_edit_contract_requires_admin_role` **維持在原檔**
    （⛔ 不搬檔）——它是正確句，被 `self_test` 以 `expect_ok=True` 守著。"""
    verifier.self_test(_FIXTURES_DIR)  # 不 raise 即通過
    ids = [c["id"] for c in json.loads(
        (_FIXTURES_DIR / "known_open.json").read_text(encoding="utf-8"))]
    assert "r4_edit_contract_requires_admin_role" in ids


def test_compound_word_anchor_is_not_a_false_positive(verifier):
    """2026-09-09 第四批回測誤殺：「繳費期限」裡的「繳費」不是狀態詞——句子「待繳費」對引文
    「• 繳費期限：2026/09/01」不得判成否定對肯定（錨定改成對面要有「已＋狀態詞」）。"""
    verdict = _verify(verifier, "帳單目前狀態為「待繳費」，繳費期限 2026/09/01。", "• 繳費期限：2026/09/01\n")
    assert verdict.ok is True, verdict.model_dump()


def test_pending_state_and_not_yet_are_the_same_polarity(verifier):
    """「待發送」與「尚未發送給租客」同為否定形（都不是「已發送」）⇒ 放行。"""
    verdict = _verify(verifier, "該帳單目前狀態為「待發送」，尚未發送給租客。", "• 狀態：待發送\n")
    assert verdict.reason != "POLARITY_MISMATCH", verdict.model_dump()   # 覆蓋率另計，這條只看極性


def test_pending_state_against_explicit_already_sent_is_blocked(verifier):
    """正對照：句子「待發送」對引文明寫「已發送」⇒ 擋（肯定形錨定看得見）。"""
    verdict = _verify(verifier, "該帳單目前狀態為「待發送」。", "此帳單已發送，租客端應可見。")
    assert verdict.ok is False
    assert verdict.reason == "POLARITY_MISMATCH"
