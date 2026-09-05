"""unit：`OutputVerifier`（spec agentic-mcp-orchestration 任務 2.3，design.md 元件 6）。

覆蓋：
- 11 個結構化拒因各自的正反例（`tests/fixtures/agent/known_fabrications.json` 逐筆核對 `expected_reason`，
  `known_good.json` 全部放行）
- design 元件 6 例句「支援批次匯入合約，請問您有幾間？」的降級判定（無引用拒、有引用放）
- `self_test()`：對兩份 fixture 全過；植入一筆漏網的捏造句（無引用的斷言）即 raise，
  證明自證機制真的會咬——而不是「兩份檔案存在」就算過。
- DSP-028 逐筆／逐片段：空陣列／空 text 兩種結構 SCHEMA、
  跨筆拆字與拆數字的規避、片段繼承 refs 但自己覆蓋不足、問候／導流筆尾巴夾斷言，
  以及四個正對照（同筆多問句、拆兩筆各自引用、同筆兩片段共用一筆引用、handoff 捏造文字）。

離線、不接觸真 DB／真 LLM。`SENSITIVE`／`HANDOFF_WORDS` 只 import `services.presales_gate`，
本檔不重造這些封閉集合。
"""
import json
from pathlib import Path

import pytest

from services.agent.output_schema import AgentOutput, VerifierRules
from services.agent.provenance_units import provenance_units, resolve_refs
from services.agent.tools.registry import ToolResult
from services.agent.verifier import _FIXTURE_NONCE, OutputVerifier, split_sentences

pytestmark = pytest.mark.unit

_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "agent"
_RULES_PATH = Path(__file__).resolve().parents[3] / "config" / "agent_verifier_rules.json"


def _load_cases(name: str) -> list[dict]:
    return json.loads((_FIXTURES_DIR / name).read_text(encoding="utf-8"))


def _run(verifier: OutputVerifier, case: dict):
    """與產線同一個順序：解析 → 驗證（DSP-029a；正規化那一步已隨
    `_canonicalize_outline_sources` 一併退役）。

    ⚠️ `resolved`／`resolve_errors` ⛔ 不在這裡另寫一套算法——那樣測到的就是本檔
    自己的解析，不是系統的解析。nonce 取案內的值（缺省與 `self_test` 同一個），
    測「nonce 不符」的案例靠案內 nonce 與標記裡的 nonce 不同來造。"""
    out = AgentOutput.model_validate(case["agent_output"])
    tool_results = {
        tid: ToolResult.model_validate(tr) for tid, tr in case.get("tool_results", {}).items()
    }
    resolved, resolve_errors = resolve_refs(
        out, tool_results, case.get("nonce") or _FIXTURE_NONCE)
    return verifier.verify(
        out, tool_results, case.get("user_message", ""), case.get("handoff"),
        resolved=resolved, resolve_errors=resolve_errors)


@pytest.fixture(scope="module")
def rules() -> VerifierRules:
    return VerifierRules.load(_RULES_PATH)


@pytest.fixture(scope="module")
def verifier(rules: VerifierRules) -> OutputVerifier:
    return OutputVerifier(rules)


# ---------------------------------------------------------------- 11 拒因正反例

_FABRICATIONS = _load_cases("known_fabrications.json")
_GOOD = _load_cases("known_good.json")
#: DSP-029 r13 #1：**已知擋不住**的捏造句（`expect_ok=True`）。⛔ 它們不是通過的
#: 證據，是「還沒擋住」這件事的可執行紀錄；DSP-030 擋住之後整案搬去 known_fabrications。
_KNOWN_OPEN = _load_cases("known_open.json")


def test_fabrications_cover_all_eleven_reasons():
    """正對照組：先確認 fixture 真的覆蓋 design 元件 6 列的全部 11 個拒因，
    否則下面的逐筆核對就算全過也不構成「11 拒因都測到了」的證據。

    ⚠️ **DSP-029 調整**：`QUOTE_NOT_VERBATIM` 在模型端已**不可達**——引文不再由模型
    抄寫，而是系統依 `(tool_call_id, source, unit)` 從 `Provenance.text` 切出來的，
    「不逐字」這件事在資料上不成立，⛔ 造不出誠實的 fixture。該拒因改由本檔的
    **程式層**測試 `test_resolved_unit_is_always_a_substring_of_provenance` 覆蓋
    （直接驗那個不變量本身），故從 fixture 應覆蓋集合中扣除；11 拒因的覆蓋沒有變少，
    只是其中一個換了證據形式。"""
    expected_reasons = {
        "SENSITIVE_TOPIC", "UNCITED_ASSERTION", "QUOTE_TOO_SHORT",
        "QUOTE_NOT_COVERING", "POLARITY_MISMATCH", "SOURCE_NOT_CITABLE", "ROUTE_NOT_ALLOWED",
        "FORBIDDEN_TERM", "HANDOFF_WORD_NO_HANDOFF", "SCHEMA",
    }
    got = {c["expected_reason"] for c in _FABRICATIONS}
    assert got == expected_reasons
    # 正對照：被扣掉的那個拒因**仍在拒因列舉裡**（trace 相容），⛔ 不是被刪掉了。
    from services.agent.output_schema import VerdictReason
    import typing

    assert "QUOTE_NOT_VERBATIM" in typing.get_args(VerdictReason)


@pytest.mark.parametrize("case", _FABRICATIONS, ids=[c["id"] for c in _FABRICATIONS])
def test_known_fabrication_rejected_with_expected_reason(verifier, case):
    verdict = _run(verifier, case)
    assert verdict.ok is False
    assert verdict.reason == case["expected_reason"]
    # 標了 `expected_schema_cause` 的案（DSP-029 的七種 SCHEMA 子成因）必須對得上——
    # 只比 reason 會假綠：七種結構性失敗全是 `SCHEMA`。
    if "expected_schema_cause" in case:
        assert verdict.schema_cause == case["expected_schema_cause"]
    # ⛔ 無原文：結構化欄位不得裝回答句子（DSP-028：逐筆 text 一一比對）。
    # DSP-029a 後模型端連引文欄位都不存在——`refs` 只放標記字串，
    # 正對照：先確認 fixture 真的沒有 `citations`／`cite` 這兩個已退役的鍵。
    texts = [sentence["text"] for sentence in case["agent_output"]["sentences"]]
    assert verdict.term_id not in texts
    assert "citations" not in case["agent_output"]
    for sentence in case["agent_output"]["sentences"]:
        assert "cite" not in sentence
        assert all(isinstance(r, str) for r in sentence.get("refs", []))


@pytest.mark.parametrize("case", _GOOD, ids=[c["id"] for c in _GOOD])
def test_known_good_passes(verifier, case):
    verdict = _run(verifier, case)
    assert verdict.ok is True, f"{case['id']} 預期放行，實得 {verdict.model_dump()}"


# ---------------------------------------------------------------- design 元件 6 例句

def test_impure_question_without_citation_is_rejected(verifier):
    """「支援批次匯入合約，請問您有幾間？」子句命中 assertion_terms（支援）⇒ 降級 fact ⇒ 需 refs。"""
    case = next(c for c in _FABRICATIONS if c["id"] == "impure_question_uncited")
    verdict = _run(verifier, case)
    assert verdict.ok is False
    assert verdict.reason == "UNCITED_ASSERTION"


def test_impure_question_with_valid_citation_passes(verifier):
    """同一句型，補上有效引用後應放行——證明降級只影響「要不要引用」，不是整句一律拒。"""
    case = next(c for c in _GOOD if c["id"] == "good_impure_question_with_citation")
    verdict = _run(verifier, case)
    assert verdict.ok is True


# ---------------------------------------------------------------- 針對性場景（brief 列點逐條對應 fixture id）

@pytest.mark.parametrize(
    "case_id,expected_reason",
    [
        ("polarity_mismatch", "POLARITY_MISMATCH"),          # 否定翻轉（來源片段講「可以」，句子講「無法」）
        ("quote_not_covering", "QUOTE_NOT_COVERING"),         # 通用引用不覆蓋句子內容
        ("source_not_citable", "SOURCE_NOT_CITABLE"),         # citable=false
        ("route_url_fullwidth", "ROUTE_NOT_ALLOWED"),         # URL 全形變形
        ("route_url_spaced", "ROUTE_NOT_ALLOWED"),            # URL 被空格拆開
        ("sensitive_customer_reference", "SENSITIVE_TOPIC"),  # 敏感題「有料」（有引用）仍拒
        ("fact_class_missing", "SENSITIVE_TOPIC"),            # fact_class 缺
        ("empty_text_sentence", "SCHEMA"),                    # DSP-028：某筆 text 全空白
        ("handoff_fact_class_missing", "SENSITIVE_TOPIC"),    # DSP-021：handoff 仍要合法 fact_class
        ("handoff_reason_free_text", "SCHEMA"),               # DSP-021：handoff_reason 值域外
        # DSP-029：`source` 就是定址 ⇒ 洗白手法在結構上消失，拒因改為覆蓋不過
        ("wrong_label_cannot_launder_non_citable", "QUOTE_NOT_COVERING"),
        ("unit_out_of_range", "SCHEMA"),                     # DSP-029：編號越界
        ("ref_negative_unit_is_malformed", "SCHEMA"),        # DSP-029a：負數編號連格式都不合
        ("source_not_found", "SCHEMA"),                      # DSP-029：來源不存在
        ("marker_copied_into_text", "SCHEMA"),               # r13 #2：標記抄進 text
        ("unit_points_to_unrelated_sentence", "QUOTE_NOT_COVERING"),  # 指到同來源無關句
        # DSP-029a 新增的四種 refs 病灶
        ("ref_nonce_from_another_turn", "SCHEMA"),
        ("ref_ambiguous_same_source_two_texts_in_one_tool_result", "SCHEMA"),
        ("fact_entry_with_empty_refs_while_another_entry_is_cited", "UNCITED_ASSERTION"),
        ("ref_points_to_kb_search_snippet_not_citable", "SOURCE_NOT_CITABLE"),
        # DSP-029a：`_canonicalize_outline_sources` 退役後改判的 DSP-021 兩案
        ("outline_source_with_title_suffix_no_longer_canonicalized", "SCHEMA"),
        ("outline_source_missing_prefix_no_longer_canonicalized", "SCHEMA"),
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
        # F-a 跨筆拆字規避 assertion_terms ⇒ 結構複核仍降級 fact
        ("split_assertion_across_entries", "UNCITED_ASSERTION", 0),
        # F-b 跨筆拆數字 ⇒ 靠①掃拼接全文的反向護欄
        ("split_number_across_entries", "SENSITIVE_TOPIC", None),
        # F-1／F-c 片段只繼承 refs 標籤、不繼承驗證結果；sent = 筆索引
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
        # DSP-029a r15 #4：非 fact 筆的 refs 解析失敗 ⛔ 不影響 verdict
        "good_greeting_entry_with_broken_ref_and_cited_fact",
        # DSP-029a 主流程：search→get 同一個 `kb:id` 兩個 tool_call，引 get 的片段
        "good_search_then_get_same_source_two_tool_calls",
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
    """r11 安全審 F-1（量詞）：降級為 fact 的片段，必須在**該筆 refs** 中至少一個
    解析結果完整通過③④；⛔ 不得以「同筆的別的片段已經通過」代替。

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
    (tmp_path / "known_open.json").write_text(
        json.dumps(_KNOWN_OPEN, ensure_ascii=False), encoding="utf-8")
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
    assert rules.version == "1.3.0"
    # DSP-029：相對覆蓋率進規則集（版本化，才跟得上 `rules_sha`）。
    assert rules.min_coverage_ratio == 0.5


# ---------------------------------------------------------------- self_test 自證

def test_self_test_passes_on_shipped_fixtures(verifier):
    verifier.self_test(_FIXTURES_DIR)  # 不 raise 即通過


def test_shipped_fixtures_include_known_open(verifier):
    """正對照：出貨那份 fixture 目錄**必須**有 `known_open.json`。

    `self_test` 對「檔案不存在」是回 0（讓 `test_bootstrap_req.py` 的臨時目錄能跑），
    沒有這條就會出現最糟的那種假綠——檔案被刪掉、自證照樣全綠、而「已知未擋的捏造句」
    這件事就這樣從紀錄裡消失。"""
    assert (_FIXTURES_DIR / "known_open.json").exists()
    n = verifier.self_test(_FIXTURES_DIR)
    assert n == len(_KNOWN_OPEN) == 4, "R4 三個真捏造句＋DSP-034 移入的一案"


@pytest.mark.parametrize("case", _KNOWN_OPEN, ids=[c["id"] for c in _KNOWN_OPEN])
def test_known_open_cases_are_still_passing(verifier, case):
    """r13 #1：這幾句**現在確實會被放行**，本測試把「還沒擋住」寫成事實。

    ⚠️ 它 ⛔ 不是「系統正確」的證據。哪天 DSP-030 的新資訊規則上線讓它們被拒，
    這條會紅——那時的正確處置是把案例搬去 `known_fabrications.json` 並改斷言，
    ⛔ 不是放寬新規則來讓這條繼續綠。"""
    assert case["known_open"] is True
    assert case["open_since"] and case["closed_by"]
    verdict = _run(verifier, case)
    assert verdict.ok is True, (
        f"{case['id']} 由未擋轉為已擋——請把它搬去 known_fabrications.json，"
        f"⛔ 不要放寬規則。實得 {verdict.model_dump()}"
    )


# ---------------------------------------------------------------- DSP-029 程式層不變量

def test_resolved_unit_is_always_a_substring_of_provenance():
    """取代 `quote_not_verbatim` fixture 的**程式層**測試：解析出來的引文，
    必然是對應 `Provenance.text` 的子字串——「引文不逐字」在模型端不可達。

    正對照：先確認同一組資料裡真的解析出東西（`resolved` 非空），
    否則這個 for 迴圈跑 0 圈也會「通過」，什麼都沒證明。"""
    checked = 0
    for case in _GOOD + _FABRICATIONS + _KNOWN_OPEN:
        out = AgentOutput.model_validate(case["agent_output"])
        tool_results = {
            tid: ToolResult.model_validate(tr)
            for tid, tr in case.get("tool_results", {}).items()
        }
        resolved, _errors = resolve_refs(
            out, tool_results, case.get("nonce") or _FIXTURE_NONCE)
        for (sent_idx, ref_idx), ref in resolved.items():
            # 解析結果一定出自某一筆 provenance 的原文；`ResolvedRef.source` 記的是
            # 標記裡那一段，拿它回頭找那筆 provenance 就能驗子字串關係。
            prov_texts = [
                p.text
                for tr in tool_results.values()
                for p in (tr.provenance or [])
                if p.source == ref.source
            ]
            assert any(ref.quote in t for t in prov_texts), (case["id"], sent_idx, ref_idx)
            checked += 1
    assert checked > 0, "沒有任何 ref 解析成功——這條斷言什麼都沒證明"


def test_provenance_units_drops_blank_pieces_and_keeps_order():
    """`provenance_units` ＝ `split_sentences` 去掉空片段；順序即編號。

    正對照：先確認 `split_sentences` 真的切出了那個空片段（換行），
    否則「去掉空片段」這件事根本沒被驗到。"""
    text = "第一句。\n第二句。\n"
    raw = split_sentences(text)
    assert any(p.strip() == "" for p in raw), "切句沒有產生空片段——正對照失敗"
    assert provenance_units(text) == ["第一句。", "第二句。"]


def test_relative_coverage_threshold_is_stricter_than_the_absolute_floor(verifier):
    """DSP-029 ③：覆蓋改片段側相對值。長句只共用四個字不再夠。

    正對照：同一筆引用配一個**忠實**的短句要放行——否則就只是「全部拒掉」。"""
    def _case(sentence_text):
        return {
            "id": "inline",
            "user_message": "q",
            "agent_output": {
                "kind": "answer",
                "sentences": [{"text": sentence_text, "kind": "fact",
                               "refs": [f"[{_FIXTURE_NONCE}:t1:kb:1§0]"]}],
                "fact_class": "feature",
                "handoff_reason": None,
            },
            "tool_results": {
                "t1": {
                    "ok": True,
                    "provenance": [
                        {"source": "kb:1", "text": "物件資料可以透過範本檔案批次匯入。",
                         "citable": True}
                    ],
                    "text_for_model": "",
                }
            },
            "handoff": None,
        }

    faithful = _run(verifier, _case("物件資料可以透過範本檔案批次匯入。"))
    assert faithful.ok is True, faithful.model_dump()
    # 只共用「物件／資料／匯入」等少數字，其餘全是原文沒有的內容
    padded = _run(verifier, _case("物件資料的匯入流程需要先申請開通白名單並由專人排程。"))
    assert padded.ok is False and padded.reason == "QUOTE_NOT_COVERING", padded.model_dump()


def test_self_test_raises_when_a_fabrication_slips_through(verifier, tmp_path):
    """植入一筆會被誤放行的捏造句（無引用斷言，但塞進 known_fabrications.json）⇒ self_test 必須 raise。
    這條防的是「自證機制形同虛設」——兩個 json 檔存在、`self_test()` 被呼叫，但根本沒人真的比對結果。"""
    leaking_case = {
        "id": "planted_leak_uncited_but_marked_pass_expected",
        "expected_reason": "UNCITED_ASSERTION",
        "user_message": "test",
        "agent_output": {
            "kind": "answer",
            "sentences": [{"text": "這是一句沒有引用的斷言。", "kind": "fact", "refs": []}],
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
