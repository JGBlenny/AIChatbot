"""unit：`OutputVerifier`（spec agentic-mcp-orchestration 任務 2.3，design.md 元件 6）。

覆蓋：
- 11 個結構化拒因各自的正反例（`tests/fixtures/agent/known_fabrications.json` 逐筆核對 `expected_reason`，
  `known_good.json` 全部放行）
- design 元件 6 例句「支援批次匯入合約，請問您有幾間？」的降級判定（無引用拒、有引用放）
- `self_test()`：對兩份 fixture 全過；植入一筆漏網的捏造句（無引用的斷言）即 raise，
  證明自證機制真的會咬——而不是「兩份檔案存在」就算過。
- DSP-028 逐筆／逐片段：空陣列／空 text／cite 越界（含負索引）三種 SCHEMA、
  跨筆拆字與拆數字的規避、片段繼承 cite 但自己覆蓋不足、問候／導流筆尾巴夾斷言，
  以及四個正對照（同筆多問句、拆兩筆各自引用、同筆兩片段共用一筆引用、handoff 捏造文字）。

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
    # ⛔ 無原文：結構化欄位不得裝回答句子或 quote 內容（DSP-028：逐筆 text 一一比對）
    texts = [sentence["text"] for sentence in case["agent_output"]["sentences"]]
    assert verdict.term_id not in texts
    assert verdict.term_id not in {c["quote"] for c in case["agent_output"]["citations"]}


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
        ("schema_mismatch", "SCHEMA"),                        # DSP-028：cite 索引越界
        ("handoff_fact_class_missing", "SENSITIVE_TOPIC"),    # DSP-021：handoff 仍要合法 fact_class
        ("handoff_reason_free_text", "SCHEMA"),               # DSP-021：handoff_reason 值域外
        ("wrong_label_cannot_launder_non_citable", "SOURCE_NOT_CITABLE"),  # DSP-021：標籤錯洗不掉 citable=false
    ],
)
def test_specific_named_scenarios(verifier, case_id, expected_reason):
    case = next(c for c in _FABRICATIONS if c["id"] == case_id)
    verdict = _run(verifier, case)
    assert verdict.ok is False
    assert verdict.reason == expected_reason


# ---------------------------------------------------------------- DSP-028 逐筆／逐片段

@pytest.mark.parametrize(
    "case_id,expected_reason,expected_sent",
    [
        # r2 #10 多句變體：同一筆「斷言句＋問句」標 question ⇒ 斷言片段降級 fact
        ("question_with_assertion_in_same_entry", "UNCITED_ASSERTION", 0),
        # (a) 非 handoff 的空陣列
        ("empty_sentences_non_handoff", "SCHEMA", None),
        # (b) 空白 text
        ("empty_text_sentence", "SCHEMA", 0),
        # (c)/F-5 負索引（python 的 citations[-1] 會靜靜取到合法引用）
        ("cite_negative_index", "SCHEMA", 0),
        # F-a 跨筆拆字規避 assertion_terms ⇒ 結構複核仍降級 fact
        ("split_assertion_across_entries", "UNCITED_ASSERTION", 0),
        # F-b 跨筆拆數字 ⇒ 靠①掃拼接全文的反向護欄
        ("split_number_across_entries", "SENSITIVE_TOPIC", None),
        # F-1／F-c 片段只繼承 cite 標籤、不繼承驗證結果；sent = 筆索引
        ("fragment_inherits_cite_but_not_covering", "QUOTE_NOT_COVERING", 0),
        # F-d 問候／導流筆尾巴夾斷言
        ("greeting_tail_assertion", "UNCITED_ASSERTION", 0),
        ("routing_tail_assertion", "UNCITED_ASSERTION", 0),
    ],
)
def test_dsp028_per_entry_and_per_fragment_scenarios(verifier, case_id, expected_reason, expected_sent):
    case = next(c for c in _FABRICATIONS if c["id"] == case_id)
    verdict = _run(verifier, case)
    assert verdict.ok is False
    assert verdict.reason == expected_reason
    assert verdict.sent == expected_sent, "sent 是**筆索引**（片段不另編號）"


@pytest.mark.parametrize(
    "case_id",
    [
        # 正對照：同一筆放兩個純問句片段 ⇒ 放行（逐片段複核不是「一筆多句一律拒」）
        "good_question_only_multi_entry_fragments",
        # F-c 正對照(1/2)：拆成兩筆、各自帶引用
        "good_fragments_split_into_two_entries_each_cited",
        # F-c 正對照(2/2)：同一筆兩個片段各自通過同一筆引用
        "good_two_fragments_one_entry_same_citation_covers_both",
        # F-f：handoff 帶捏造 sentences ⇒ Verifier 放行（文字由 Runtime 換固定句）
        "good_handoff_with_fabricated_sentences",
    ],
)
def test_dsp028_positive_controls_pass(verifier, case_id):
    case = next(c for c in _GOOD if c["id"] == case_id)
    verdict = _run(verifier, case)
    assert verdict.ok is True, f"{case_id} 預期放行，實得 {verdict.model_dump()}"


def test_answer_is_the_join_of_sentence_texts_and_is_what_gets_scanned():
    """DSP-028：①⑤⑥⑦掃的字串＝送出的字串。用 F-b（跨筆拆數字）當正對照——
    兩筆單看都不像價格，拼接後才命中敏感樣式。"""
    case = next(c for c in _FABRICATIONS if c["id"] == "split_number_across_entries")
    out = AgentOutput.model_validate(case["agent_output"])
    assert out.answer == "月費 3000 元起。"
    assert all("3000" not in s.text for s in out.sentences)     # 單筆都看不出來


def test_uncited_fragment_needs_a_citation_that_passes_on_its_own(verifier):
    """r11 安全審 F-1（量詞）：降級為 fact 的片段，必須在**該筆 cite** 中至少一筆
    citation 完整通過③④；⛔ 不得以「同筆的別的片段已經通過」代替。

    反證：把 F-c 那筆的第二個片段刪掉（只留通得過的片段）就會放行——
    證明拒因確實來自第二個片段自己，不是整筆一律拒。"""
    case = next(c for c in _FABRICATIONS if c["id"] == "fragment_inherits_cite_but_not_covering")
    assert _run(verifier, case).reason == "QUOTE_NOT_COVERING"

    trimmed = json.loads(json.dumps(case))          # 深拷貝，⛔ 不改到原 fixture 物件
    entry = trimmed["agent_output"]["sentences"][0]
    entry["text"] = "物件資料可以透過範本檔案批次匯入。"
    assert _run(verifier, trimmed).ok is True


def test_self_test_raises_when_expected_reason_drifts(verifier, tmp_path):
    """r11 安全審 F-3：`self_test` 只比 `ok` 會假綠——轉換若把違規性質改掉
    （本來測 QUOTE_NOT_COVERING、變成 SCHEMA），`ok=False` 照樣成立。

    正對照：先確認原封不動的兩份 fixture 會通過；再只改 `expected_reason` 一個鍵，
    必須 raise。若第一段就 raise，代表是別的東西壞了，不是這條在咬。"""
    (tmp_path / "known_fabrications.json").write_text(
        json.dumps(_FABRICATIONS, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "known_good.json").write_text(
        json.dumps(_GOOD, ensure_ascii=False), encoding="utf-8")
    verifier.self_test(tmp_path)                     # 正對照：不 raise

    drifted = json.loads(json.dumps(_FABRICATIONS))
    target = next(c for c in drifted if c["id"] == "quote_not_covering")
    target["expected_reason"] = "SCHEMA"             # ok 仍是 False，只有 reason 對不上
    (tmp_path / "known_fabrications.json").write_text(
        json.dumps(drifted, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(RuntimeError):
        verifier.self_test(tmp_path)


def test_assertion_terms_cover_the_product_capability_verbs_and_not_the_over_broad_ones():
    """r11 安全審 F-2：補的是**產品能力動詞**這個封閉子集；
    「有／是／已／將」刻意 OPEN（會把「您有幾間？」降成 fact，推高誤殺）。"""
    rules = VerifierRules.load(_RULES_PATH)
    assert {"支持", "包含", "內建", "整合", "自動"} <= set(rules.assertion_terms)
    assert {"有", "是", "已", "將"}.isdisjoint(set(rules.assertion_terms))
    assert rules.version == "1.2.0"


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
            "sentences": [{"text": "這是一句沒有引用的斷言。", "kind": "fact", "cite": []}],
            "citations": [],
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
