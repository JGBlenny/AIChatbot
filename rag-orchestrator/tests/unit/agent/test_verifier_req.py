"""unit：`OutputVerifier`（spec agentic-mcp-orchestration 任務 2.3，design.md 元件 6）。

覆蓋：
- 11 個結構化拒因各自的正反例（`tests/fixtures/agent/known_fabrications.json` 逐筆核對 `expected_reason`，
  `known_good.json` 全部放行）
- design 元件 6 例句「支援批次匯入合約，請問您有幾間？」的降級判定（無引用拒、有引用放）
- `self_test()`：對兩份 fixture 全過；植入一筆漏網的捏造句（無引用的斷言）即 raise，
  證明自證機制真的會咬——而不是「兩份檔案存在」就算過。

離線、不接觸真 DB／真 LLM。`SENSITIVE`／`HANDOFF_WORDS` 只 import `services.presales_gate`，
本檔不重造這些封閉集合。
"""
import json
from pathlib import Path

import pytest

from services.agent.output_schema import AgentOutput, VerifierRules
from services.agent.tools.registry import ToolResult
from services.agent.verifier import OutputVerifier

pytestmark = pytest.mark.unit

_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "agent"
_RULES_PATH = Path(__file__).resolve().parents[3] / "config" / "agent_verifier_rules.json"


def _load_cases(name: str) -> list[dict]:
    return json.loads((_FIXTURES_DIR / name).read_text(encoding="utf-8"))


def _run(verifier: OutputVerifier, case: dict):
    out = AgentOutput.model_validate(case["agent_output"])
    tool_results = {
        tid: ToolResult.model_validate(tr) for tid, tr in case.get("tool_results", {}).items()
    }
    return verifier.verify(out, tool_results, case.get("user_message", ""), case.get("handoff"))


@pytest.fixture(scope="module")
def rules() -> VerifierRules:
    return VerifierRules.load(_RULES_PATH)


@pytest.fixture(scope="module")
def verifier(rules: VerifierRules) -> OutputVerifier:
    return OutputVerifier(rules)


# ---------------------------------------------------------------- 11 拒因正反例

_FABRICATIONS = _load_cases("known_fabrications.json")
_GOOD = _load_cases("known_good.json")


def test_fabrications_cover_all_eleven_reasons():
    """正對照組：先確認 fixture 真的覆蓋 design 元件 6 列的全部 11 個拒因，
    否則下面的逐筆核對就算全過也不構成「11 拒因都測到了」的證據。"""
    expected_reasons = {
        "SENSITIVE_TOPIC", "UNCITED_ASSERTION", "QUOTE_NOT_VERBATIM", "QUOTE_TOO_SHORT",
        "QUOTE_NOT_COVERING", "POLARITY_MISMATCH", "SOURCE_NOT_CITABLE", "ROUTE_NOT_ALLOWED",
        "FORBIDDEN_TERM", "HANDOFF_WORD_NO_HANDOFF", "SCHEMA",
    }
    got = {c["expected_reason"] for c in _FABRICATIONS}
    assert got == expected_reasons


@pytest.mark.parametrize("case", _FABRICATIONS, ids=[c["id"] for c in _FABRICATIONS])
def test_known_fabrication_rejected_with_expected_reason(verifier, case):
    verdict = _run(verifier, case)
    assert verdict.ok is False
    assert verdict.reason == case["expected_reason"]
    # ⛔ 無原文：結構化欄位不得裝回答句子或 quote 內容
    assert verdict.term_id != case["agent_output"]["answer"]


@pytest.mark.parametrize("case", _GOOD, ids=[c["id"] for c in _GOOD])
def test_known_good_passes(verifier, case):
    verdict = _run(verifier, case)
    assert verdict.ok is True, f"{case['id']} 預期放行，實得 {verdict.model_dump()}"


# ---------------------------------------------------------------- design 元件 6 例句

def test_impure_question_without_citation_is_rejected(verifier):
    """「支援批次匯入合約，請問您有幾間？」子句命中 assertion_terms（支援）⇒ 降級 fact ⇒ 需 cite。"""
    case = next(c for c in _FABRICATIONS if c["id"] == "impure_question_uncited")
    verdict = _run(verifier, case)
    assert verdict.ok is False
    assert verdict.reason == "UNCITED_ASSERTION"


def test_impure_question_with_valid_citation_passes(verifier):
    """同一句型，補上有效引用後應放行——證明降級只影響「要不要 cite」，不是整句一律拒。"""
    case = next(c for c in _GOOD if c["id"] == "good_impure_question_with_citation")
    verdict = _run(verifier, case)
    assert verdict.ok is True


# ---------------------------------------------------------------- 針對性場景（brief 列點逐條對應 fixture id）

@pytest.mark.parametrize(
    "case_id,expected_reason",
    [
        ("polarity_mismatch", "POLARITY_MISMATCH"),          # 否定翻轉（quote 引「支援」，句子講「無法／不支援」）
        ("quote_not_covering", "QUOTE_NOT_COVERING"),         # 通用引用不覆蓋句子內容
        ("source_not_citable", "SOURCE_NOT_CITABLE"),         # citable=false
        ("route_url_fullwidth", "ROUTE_NOT_ALLOWED"),         # URL 全形變形
        ("route_url_spaced", "ROUTE_NOT_ALLOWED"),            # URL 被空格拆開
        ("sensitive_customer_reference", "SENSITIVE_TOPIC"),  # 敏感題「有料」（有引用）仍拒
        ("fact_class_missing", "SENSITIVE_TOPIC"),            # fact_class 缺
        ("schema_mismatch", "SCHEMA"),                        # sentence_map 未覆蓋全文
    ],
)
def test_specific_named_scenarios(verifier, case_id, expected_reason):
    case = next(c for c in _FABRICATIONS if c["id"] == case_id)
    verdict = _run(verifier, case)
    assert verdict.ok is False
    assert verdict.reason == expected_reason


# ---------------------------------------------------------------- self_test 自證

def test_self_test_passes_on_shipped_fixtures(verifier):
    verifier.self_test(_FIXTURES_DIR)  # 不 raise 即通過


def test_self_test_raises_when_a_fabrication_slips_through(verifier, tmp_path):
    """植入一筆會被誤放行的捏造句（無引用斷言，但塞進 known_fabrications.json）⇒ self_test 必須 raise。
    這條防的是「自證機制形同虛設」——兩個 json 檔存在、`self_test()` 被呼叫，但根本沒人真的比對結果。"""
    leaking_case = {
        "id": "planted_leak_uncited_but_marked_pass_expected",
        "expected_reason": "UNCITED_ASSERTION",
        "user_message": "test",
        "agent_output": {
            "kind": "answer",
            "answer": "這是一句沒有引用的斷言。",
            "citations": [],
            "sentence_map": [{"sent": 0, "kind": "fact", "cite": []}],
            "fact_class": "feature",
            "handoff_reason": None,
        },
        "tool_results": {},
        "handoff": None,
    }
    good_dir = tmp_path
    (good_dir / "known_fabrications.json").write_text(
        json.dumps(_FABRICATIONS + [leaking_case], ensure_ascii=False), encoding="utf-8"
    )
    (good_dir / "known_good.json").write_text(json.dumps(_GOOD, ensure_ascii=False), encoding="utf-8")
    # 這筆會被 verifier 正確拒絕（UNCITED_ASSERTION），self_test 應該正常通過——
    # 用來反證「self_test 沒有假綠」：先確定同一份規則集真的會擋這筆已知捏造句。
    verifier.self_test(good_dir)

    # 再植入一筆會被誤放行的：把它錯放進 known_good.json（宣稱該放行，但其實是無引用斷言）
    (good_dir / "known_good.json").write_text(
        json.dumps(_GOOD + [leaking_case], ensure_ascii=False), encoding="utf-8"
    )
    with pytest.raises(RuntimeError):
        verifier.self_test(good_dir)


def test_rules_load_computes_sha_from_file_bytes(tmp_path):
    """`VerifierRules.sha256` 一律由載入時的檔案位元組計算，⛔ 信任 json 內欄位——
    塞一個假的 `sha256` 進檔案，載入結果不能是那個假值，必須是實際位元組算出來的雜湊。"""
    import hashlib

    raw = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
    raw["sha256"] = "deadbeef"  # 刻意塞一個錯的值，且它不影響位元組計算之外的欄位
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    loaded = VerifierRules.load(tampered)
    assert loaded.sha256 != "deadbeef"
    assert loaded.sha256 == hashlib.sha256(tampered.read_bytes()).hexdigest()
