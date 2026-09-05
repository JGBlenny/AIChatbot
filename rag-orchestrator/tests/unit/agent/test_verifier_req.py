"""unit：`OutputVerifier`（spec agentic-mcp-orchestration 任務 2.3，design.md 元件 6）。

覆蓋：
- 11＋1 個結構化拒因各自的正反例（`tests/fixtures/agent/known_fabrications.json` 逐筆核對
  `expected_reason`，`known_good.json` 全部放行）
- **DSP-033 兩把尺**：NLI 模式（floor ∧ 窄化極性 ∧ `NOT_ENTAILED`）與降級模式
  （DSP-029 ratio ∧ 全極性）各跑一遍全部 fixture，⛔ 不得只驗一種
- design 元件 6 例句「支援批次匯入合約，請問您有幾間？」的降級判定（無引用拒、有引用放）
- `self_test()`：對三份 fixture 全過；植入一筆漏網的捏造句（無引用的斷言）即 raise，
  證明自證機制真的會咬——而不是「兩份檔案存在」就算過。
- DSP-028 逐筆／逐片段：空陣列／空 text 兩種結構 SCHEMA、
  跨筆拆字與拆數字的規避、片段繼承 refs 但自己覆蓋不足、問候／導流筆尾巴夾斷言，
  以及四個正對照（同筆多問句、拆兩筆各自引用、同筆兩片段共用一筆引用、handoff 捏造文字）。

⛔ **離線、不觸網、不載模型**：NLI 一律用 `FakeNliClient`（DSP-033 P1-2）。
`SENSITIVE`／`HANDOFF_WORDS` 只 import `services.presales_gate`，本檔不重造這些封閉集合。
"""
import json
from pathlib import Path

import pytest

from services.agent.nli_client import FakeNliClient, NliPairsCapped, NliUnavailable
from services.agent.output_schema import AgentOutput, VerifierRules
from services.agent.provenance_units import provenance_units, resolve_refs
from services.agent.tools.registry import ToolResult
from services.agent.verifier import _FIXTURE_NONCE, OutputVerifier, split_sentences

pytestmark = pytest.mark.unit

_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "agent"
_RULES_PATH = Path(__file__).resolve().parents[3] / "config" / "agent_verifier_rules.json"

#: 兩把尺的名字（與 `OutputVerifier.SELF_TEST_MODES` 同義）。
_MODES = ("nli", "degraded")


def _load_cases(name: str) -> list[dict]:
    return json.loads((_FIXTURES_DIR / name).read_text(encoding="utf-8"))


def _prepare(case: dict):
    """解析階段與產線同一個順序（DSP-029a）。

    ⚠️ `resolved`／`resolve_errors` ⛔ 不在這裡另寫一套算法——那樣測到的就是本檔
    自己的解析，不是系統的解析。nonce 取案內的值（缺省與 `self_test` 同一個），
    測「nonce 不符」的案例靠案內 nonce 與標記裡的 nonce 不同來造。"""
    out = AgentOutput.model_validate(case["agent_output"])
    tool_results = {
        tid: ToolResult.model_validate(tr) for tid, tr in case.get("tool_results", {}).items()
    }
    resolved, resolve_errors = resolve_refs(
        out, tool_results, case.get("nonce") or _FIXTURE_NONCE)
    return out, tool_results, resolved, resolve_errors


def _run(verifier: OutputVerifier, case: dict, mode: str = "nli"):
    """跑一案並回 `VerifyOutcome`（含 verdict 與 degraded 旗標）。

    NLI 模式的分數取自案內 `nli_scores`（與 `self_test` 同一個函式，
    ⛔ 不在本檔重寫一份取分規則）；降級模式用永遠 raise 的假 client。
    """
    out, tool_results, resolved, resolve_errors = _prepare(case)
    keys, pairs = verifier._pairs_for(out, resolved)
    client = (
        FakeNliClient(error=NliUnavailable("test_degraded"))
        if mode == "degraded"
        else FakeNliClient(scores=verifier._fixture_scores(case, keys))
    )
    return verifier._verify_with_client(
        client, out, tool_results, case.get("user_message", ""), case.get("handoff"),
        resolved=resolved, resolve_errors=resolve_errors, keys=keys, pairs=pairs)


def _verdict(verifier: OutputVerifier, case: dict, mode: str = "nli"):
    return _run(verifier, case, mode).verdict


def _expect(case: dict, key: str, mode: str, default=None):
    scoped = f"{key}_{mode}"
    if scoped in case:
        return case[scoped]
    return case.get(key, default)


@pytest.fixture(scope="module")
def rules() -> VerifierRules:
    return VerifierRules.load(_RULES_PATH)


@pytest.fixture(scope="module")
def verifier(rules: VerifierRules) -> OutputVerifier:
    """⚠️ 建構子帶的這個 client **不會被 `_run` 用到**（`_run` 每案自己給一個），
    也不會被 `self_test` 用到（它內建兩組假 client）。放一個永遠 raise 的在這裡
    是刻意的：任何走漏到「用建構子那個 client」的路徑都會立刻變成降級，測得出來。"""
    return OutputVerifier(rules, nli_client=FakeNliClient(error=NliUnavailable("ctor")))


# ---------------------------------------------------------------- 11＋1 拒因正反例

_FABRICATIONS = _load_cases("known_fabrications.json")
_GOOD = _load_cases("known_good.json")
#: DSP-029 r13 #1：**已知擋不住**的捏造句（`expect_ok=True`）。⛔ 它們不是通過的
#: 證據，是「還沒擋住」這件事的可執行紀錄。DSP-033 把其中「需要管理者權限」一句
#: 搬進 known_fabrications（NLI 擋住了）；剩下兩句標 `nli_blind_spot`。
_KNOWN_OPEN = _load_cases("known_open.json")


def test_fabrications_cover_all_reasons():
    """正對照組：先確認 fixture 真的覆蓋 design 元件 6 列的全部拒因，
    否則下面的逐筆核對就算全過也不構成「拒因都測到了」的證據。

    ⚠️ **DSP-029 調整**：`QUOTE_NOT_VERBATIM` 在模型端已**不可達**——引文不再由模型
    抄寫，而是系統依 `(tool_call_id, source, unit)` 從 `Provenance.text` 切出來的，
    「不逐字」這件事在資料上不成立，⛔ 造不出誠實的 fixture。該拒因改由本檔的
    **程式層**測試 `test_resolved_unit_is_always_a_substring_of_provenance` 覆蓋。
    ⚠️ **DSP-033 新增 `NOT_ENTAILED`**（11＋1）。它只在 NLI 模式下可達，
    故這裡比對的是每案的 **NLI 模式**期望值。"""
    expected_reasons = {
        "SENSITIVE_TOPIC", "UNCITED_ASSERTION", "QUOTE_TOO_SHORT",
        "QUOTE_NOT_COVERING", "POLARITY_MISMATCH", "NOT_ENTAILED",
        "SOURCE_NOT_CITABLE", "ROUTE_NOT_ALLOWED",
        "FORBIDDEN_TERM", "HANDOFF_WORD_NO_HANDOFF", "SCHEMA",
    }
    got = {c["expected_reason"] for c in _FABRICATIONS}
    assert got == expected_reasons
    # 正對照：被扣掉的那個拒因**仍在拒因列舉裡**（trace 相容），⛔ 不是被刪掉了。
    from services.agent.output_schema import VerdictReason
    import typing

    assert "QUOTE_NOT_VERBATIM" in typing.get_args(VerdictReason)
    assert "NOT_ENTAILED" in typing.get_args(VerdictReason)


@pytest.mark.parametrize("mode", _MODES)
@pytest.mark.parametrize("case", _FABRICATIONS, ids=[c["id"] for c in _FABRICATIONS])
def test_known_fabrication_rejected_with_expected_reason(verifier, case, mode):
    """⚠️ 少數案例在**降級模式下會被放行**（`expect_ok_degraded: true`）——那不是
    測試放水，是「降級尺比較鬆」這件事的可執行紀錄（例如 NLI 才擋得住的
    `r4_edit_contract_requires_admin_role`）。⛔ 不得為了讓兩模式一致而刪掉它們。"""
    outcome = _run(verifier, case, mode)
    verdict = outcome.verdict
    # ⚠️ 在步③之前就被拒的案（handoff／敏感／結構）根本沒問過 NLI ⇒ 不算降級。
    out, _tr, resolved, _errs = _prepare(case)
    has_pairs = bool(verifier._pairs_for(out, resolved)[1])
    assert outcome.degraded is ((mode == "degraded") and has_pairs)
    want_ok = _expect(case, "expect_ok", mode, False)
    assert verdict.ok is want_ok, f"{case['id']}／{mode}：實得 {verdict.model_dump()}"
    if f"expected_reason_{mode}" in case or "expected_reason" in case:
        assert verdict.reason == _expect(case, "expected_reason", mode)
    # 標了 `expected_schema_cause` 的案（DSP-029 的八種 SCHEMA 子成因）必須對得上——
    # 只比 reason 會假綠：八種結構性失敗全是 `SCHEMA`。
    if "expected_schema_cause" in case:
        assert verdict.schema_cause == case["expected_schema_cause"]
    # ⛔ 無原文：結構化欄位不得裝回答句子（DSP-028：逐筆 text 一一比對）。
    texts = [sentence["text"] for sentence in case["agent_output"]["sentences"]]
    assert verdict.term_id not in texts
    assert "citations" not in case["agent_output"]
    for sentence in case["agent_output"]["sentences"]:
        assert "cite" not in sentence
        assert all(isinstance(r, str) for r in sentence.get("refs", []))


@pytest.mark.parametrize("mode", _MODES)
@pytest.mark.parametrize("case", _GOOD, ids=[c["id"] for c in _GOOD])
def test_known_good_passes(verifier, case, mode):
    """⚠️ 兩案在**降級模式下被誤殺**（`expect_ok_degraded: false`）——那是 DSP-033
    要修的病灶本身（ratio 覆蓋與全極性的誤殺），⛔ 不得把它們從 known_good 移走。"""
    outcome = _run(verifier, case, mode)
    want_ok = _expect(case, "expect_ok", mode, True)
    assert outcome.verdict.ok is want_ok, (
        f"{case['id']}／{mode} 預期 ok={want_ok}，實得 {outcome.verdict.model_dump()}")
    if want_ok is False:
        assert outcome.verdict.reason == _expect(case, "expected_reason", mode)


# ---------------------------------------------------------------- DSP-033 兩把尺

def test_nli_mode_and_degraded_mode_are_actually_different_rulers(verifier):
    """正對照：兩把尺**真的不同**。

    ⚠️ 沒有這條，`test_known_*` 兩個 mode 參數化就可能只是把同一把尺跑了兩遍
    （例如 `_verify_core` 的 `nli_mode` 旗標被誰接錯線），而全部照樣綠。
    這裡指名兩個案例：一個只有 NLI 擋得住、一個只有降級尺會擋（誤殺）。
    """
    only_nli = next(c for c in _FABRICATIONS if c["id"] == "r4_edit_contract_requires_admin_role")
    assert _verdict(verifier, only_nli, "nli").reason == "NOT_ENTAILED"
    assert _verdict(verifier, only_nli, "degraded").ok is True

    only_degraded = next(
        c for c in _GOOD if c["id"] == "good_faithful_paraphrase_rejected_only_by_degraded_ratio")
    assert _verdict(verifier, only_degraded, "nli").ok is True
    assert _verdict(verifier, only_degraded, "degraded").reason == "QUOTE_NOT_COVERING"


def test_floor_is_an_absolute_char_intersection_not_a_ratio(verifier):
    """DSP-033 r18 F-2 (i)：NLI 模式的覆蓋尺**只剩絕對下限**（交集 <4）。

    正對照：`good_faithful_paraphrase...` 交集 5、ratio 需要 6——它在 NLI 模式
    放行，證明 ratio 分支真的退場了；`floor_reject...` 交集 1，兩模式都拒。
    """
    floor_case = next(c for c in _FABRICATIONS if c["id"] == "floor_reject_no_meaningful_overlap")
    for mode in _MODES:
        assert _verdict(verifier, floor_case, mode).reason == "QUOTE_NOT_COVERING"

    ratio_only = next(
        c for c in _GOOD if c["id"] == "good_faithful_paraphrase_rejected_only_by_degraded_ratio")
    assert _verdict(verifier, ratio_only, "nli").ok is True


def test_narrow_polarity_needs_the_same_root_on_both_sides(verifier):
    """DSP-033 r18 F-2 (ii)：窄化極性＝同一 `assertion_terms` 詞根兩側皆出現、
    且恰一側被否定。

    兩個案子合起來才說得清楚「窄化」是什麼：
      * 拒：來源「不支援」vs 句子「支援」——同詞根、恰一側否定；
      * **放行正對照**：來源尾巴多一句無關的「不支援自動排程」——全極性會誤殺，
        窄化極性放行。⛔ 沒有第二個案例，「窄化」在測試上是不可見的。
    """
    reject = next(
        c for c in _FABRICATIONS if c["id"] == "narrow_polarity_same_root_one_side_negated")
    assert _verdict(verifier, reject, "nli").reason == "POLARITY_MISMATCH"

    allow = next(
        c for c in _GOOD
        if c["id"] == "good_narrow_polarity_ignores_unrelated_negation_in_source")
    assert _verdict(verifier, allow, "nli").ok is True
    assert _verdict(verifier, allow, "degraded").reason == "POLARITY_MISMATCH"


def test_polarity_roots_exclude_the_negated_forms(verifier, rules):
    """詞根集合＝`assertion_terms` 扣掉**它自己就是否定形**的那些。

    ⚠️ 兩張表都來自規則集，⛔ 不另立第三份否定詞表——否則規則檔改了、
    詞根卻沒跟著改，而 `rules_sha` 看起來一切正常。
    """
    roots = set(verifier._polarity_roots)
    assert {"支援", "可以", "會", "能", "提供"} <= roots
    assert roots.isdisjoint({"不支援", "不會", "無法", "不能"})
    assert roots == set(rules.assertion_terms) - set(rules.negation_terms)


def test_not_entailed_has_no_term_id_and_carries_the_max_score(verifier):
    """r18 F-15：`NOT_ENTAILED` 的 `term_id` 固定為 None（它不是規則命中）。
    `entail_score` ＝該片段在**所有** ref 上的最大分（F-1 的量詞是「至少一句 ≥ τ」）。"""
    case = json.loads(json.dumps(
        next(c for c in _FABRICATIONS if c["id"] == "nli_not_entailed_extra_condition")))
    verdict = _verdict(verifier, case, "nli")
    assert verdict.reason == "NOT_ENTAILED"
    assert verdict.term_id is None
    assert verdict.entail_score == 0.18

    # 兩個 ref，只有分數較高的那個進 `entail_score`（⛔ 不是最後一個）。
    case["agent_output"]["sentences"][0]["refs"] = [
        f"[{_FIXTURE_NONCE}:t1:kb:9001§0]", f"[{_FIXTURE_NONCE}:t1:kb:9001§0]"]
    case["nli_scores"] = {"0:0:0": 0.31, "0:0:1": 0.07}
    verdict = _verdict(verifier, case, "nli")
    assert verdict.reason == "NOT_ENTAILED"
    assert verdict.entail_score == 0.31


def test_f1_quantifier_one_ref_at_or_above_tau_is_enough(verifier, rules):
    """F-1 量詞：每個 fact 片段**至少一個**解析後來源句 `p_ent ≥ τ` 即過。

    正對照：把那個唯一達標的 ref 的分數壓到 τ 以下就會被拒——否則這條斷言
    只是在說「有兩個 ref 就會過」。
    """
    case = json.loads(json.dumps(
        next(c for c in _FABRICATIONS if c["id"] == "nli_not_entailed_extra_condition")))
    case["agent_output"]["sentences"][0]["refs"] = [
        f"[{_FIXTURE_NONCE}:t1:kb:9001§0]", f"[{_FIXTURE_NONCE}:t1:kb:9001§0]"]
    case["nli_scores"] = {"0:0:0": 0.05, "0:0:1": 0.41}
    assert _verdict(verifier, case, "nli").ok is True

    case["nli_scores"] = {"0:0:0": 0.05, "0:0:1": 0.39}
    assert _verdict(verifier, case, "nli").reason == "NOT_ENTAILED"


def test_tau_comparison_is_on_the_four_decimal_rounded_score(verifier, rules):
    """P2-5：分數四捨五入到 4 位**之後**才與 τ 比較（跨執行緒／批次一致性的前提）。"""
    assert rules.nli_tau == 0.4
    case = json.loads(json.dumps(
        next(c for c in _FABRICATIONS if c["id"] == "nli_not_entailed_extra_condition")))
    case["nli_scores"] = {"*": 0.39999}     # round4 → 0.4 ⇒ 過
    assert _verdict(verifier, case, "nli").ok is True
    case["nli_scores"] = {"*": 0.39994}     # round4 → 0.3999 ⇒ 拒
    assert _verdict(verifier, case, "nli").reason == "NOT_ENTAILED"


def test_missing_pair_score_is_rejected_not_passed(verifier):
    """`None`（該對錯誤，例如 `hypothesis_too_long`）⇒ 拒、`entail_score` 為 None。
    🔴 「算不出分數」⛔ 不得與「分數夠高」同一個結論。"""
    case = next(
        c for c in _FABRICATIONS if c["id"] == "hypothesis_too_long_pair_error_is_rejected")
    verdict = _verdict(verifier, case, "nli")
    assert verdict.reason == "NOT_ENTAILED"
    assert verdict.entail_score is None
    # 正對照：同一案在降級模式（沒有 NLI 這一關）放行——證明拒因確實來自那個 None
    assert _verdict(verifier, case, "degraded").ok is True


@pytest.mark.parametrize(
    "error,expect_capped",
    [(NliUnavailable("timeout"), False), (NliPairsCapped("too many"), True)],
)
def test_client_failure_degrades_and_still_produces_a_verdict(verifier, error, expect_capped):
    """DSP-033 可用性：`/nli` 不可用 ⇒ 降級、verdict 照常產生，⛔ 不 raise、⛔ 不全轉人。
    `NliPairsCapped` 另外標 `pairs_capped`（F-4：與逾時分開計）。"""
    case = next(c for c in _GOOD if c["id"] == "good_fact_with_valid_citation")
    out, tool_results, resolved, resolve_errors = _prepare(case)
    keys, pairs = verifier._pairs_for(out, resolved)
    outcome = verifier._verify_with_client(
        FakeNliClient(error=error), out, tool_results, "", None,
        resolved=resolved, resolve_errors=resolve_errors, keys=keys, pairs=pairs)
    assert outcome.verdict.ok is True
    assert outcome.degraded is True
    assert outcome.pairs_capped is expect_capped


def test_score_length_mismatch_degrades(verifier):
    """F-11：`len(scores) != len(pairs)` ⇒ 降級。
    ⛔ 不得靠 `zip` 的截斷行為靜靜錯位配對——錯位的分數比沒有分數更糟。"""
    case = next(c for c in _GOOD if c["id"] == "good_fact_with_valid_citation")
    out, tool_results, resolved, resolve_errors = _prepare(case)
    keys, pairs = verifier._pairs_for(out, resolved)
    assert pairs, "正對照失敗：這一案沒有任何句對，長度不符測不到"
    outcome = verifier._verify_with_client(
        FakeNliClient(scores=[0.9] * (len(pairs) + 1)), out, tool_results, "", None,
        resolved=resolved, resolve_errors=resolve_errors, keys=keys, pairs=pairs)
    assert outcome.degraded is True


def test_pair_key_includes_the_fragment_index(verifier):
    """r18 F-11：配對鍵是 `(筆, 片段, ref)`。

    ⚠️ 少了片段索引，同一筆的兩個片段對同一個 ref 的分數會互相蓋掉——而那正是
    「跨片段夾帶捏造」要用的縫。這裡用一筆兩片段共用一個 ref 的案例：
    只把**第二個**片段的分數壓到 τ 以下，必須拒。
    """
    case = next(
        c for c in _GOOD if c["id"] == "good_two_fragments_one_entry_same_citation_covers_both")
    out, _tr, resolved, _errs = _prepare(case)
    keys, pairs = verifier._pairs_for(out, resolved)
    assert len({k[1] for k in keys}) >= 2, f"正對照失敗：這一案沒有兩個片段（keys={keys}）"

    case2 = json.loads(json.dumps(case))
    case2["nli_scores"] = {f"{keys[-1][0]}:{keys[-1][1]}:{keys[-1][2]}": 0.05, "*": 0.99}
    assert _verdict(verifier, case2, "nli").reason == "NOT_ENTAILED"


def test_handoff_and_sensitive_turns_ask_nothing_of_nli(verifier):
    """步①就 return 的回合 ⛔ 不收句對：敏感題的捏造 sentences 不該平白撐爆
    `NLI_MAX_PAIRS=12`，也不該把知識庫原文送出容器。"""
    for cid in ("good_handoff_with_fabricated_sentences", "sensitive_customer_reference"):
        case = next(c for c in _GOOD + _FABRICATIONS if c["id"] == cid)
        out, _tr, resolved, _errs = _prepare(case)
        assert verifier._pairs_for(out, resolved) == ([], []), cid
    # 正對照：一般回合**有**句對——否則上面只是在說「這個函式永遠回空」。
    good = next(c for c in _GOOD if c["id"] == "good_fact_with_valid_citation")
    out, _tr, resolved, _errs = _prepare(good)
    assert verifier._pairs_for(out, resolved)[1]


# ---------------------------------------------------------------- design 元件 6 例句

def test_impure_question_without_citation_is_rejected(verifier):
    """「支援批次匯入合約，請問您有幾間？」子句命中 assertion_terms（支援）⇒ 降級 fact ⇒ 需 refs。"""
    case = next(c for c in _FABRICATIONS if c["id"] == "impure_question_uncited")
    verdict = _verdict(verifier, case)
    assert verdict.ok is False
    assert verdict.reason == "UNCITED_ASSERTION"


def test_impure_question_with_valid_citation_passes(verifier):
    """同一句型，補上有效引用後應放行——證明降級只影響「要不要引用」，不是整句一律拒。"""
    case = next(c for c in _GOOD if c["id"] == "good_impure_question_with_citation")
    assert _verdict(verifier, case).ok is True


# ---------------------------------------------------------------- 針對性場景（brief 列點逐條對應 fixture id）

@pytest.mark.parametrize(
    "case_id,expected_reason",
    [
        # DSP-033：來源說「可以」、句子說「無法」——窄化極性看不到共同詞根，改由 NLI 擋
        ("polarity_mismatch", "NOT_ENTAILED"),
        ("quote_not_covering", "QUOTE_NOT_COVERING"),         # 通用引用不覆蓋句子內容（floor）
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
        # DSP-033：指到同來源無關句——floor 過得了，改由 NLI 擋
        ("unit_points_to_unrelated_sentence", "NOT_ENTAILED"),
        # DSP-029a 新增的四種 refs 病灶
        ("ref_nonce_from_another_turn", "SCHEMA"),
        ("ref_ambiguous_same_source_two_texts_in_one_tool_result", "SCHEMA"),
        ("fact_entry_with_empty_refs_while_another_entry_is_cited", "UNCITED_ASSERTION"),
        ("ref_points_to_kb_search_snippet_not_citable", "SOURCE_NOT_CITABLE"),
        # DSP-029a：`_canonicalize_outline_sources` 退役後改判的 DSP-021 兩案
        ("outline_source_with_title_suffix_no_longer_canonicalized", "SCHEMA"),
        ("outline_source_missing_prefix_no_longer_canonicalized", "SCHEMA"),
        # DSP-033 新增
        ("floor_reject_no_meaningful_overlap", "QUOTE_NOT_COVERING"),
        ("narrow_polarity_same_root_one_side_negated", "POLARITY_MISMATCH"),
        ("nli_not_entailed_extra_condition", "NOT_ENTAILED"),
        ("hypothesis_too_long_pair_error_is_rejected", "NOT_ENTAILED"),
        ("r4_edit_contract_requires_admin_role", "NOT_ENTAILED"),
    ],
)
def test_specific_named_scenarios(verifier, case_id, expected_reason):
    case = next(c for c in _FABRICATIONS if c["id"] == case_id)
    verdict = _verdict(verifier, case, "nli")
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
    verdict = _verdict(verifier, case)
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
    verdict = _verdict(verifier, case)
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
    assert _verdict(verifier, case).reason == "QUOTE_NOT_COVERING"

    trimmed = json.loads(json.dumps(case))          # 深拷貝，⛔ 不改到原 fixture 物件
    entry = trimmed["agent_output"]["sentences"][0]
    entry["text"] = "物件資料可以透過範本檔案批次匯入。"
    assert _verdict(verifier, trimmed).ok is True


def test_self_test_raises_when_expected_reason_drifts(verifier, tmp_path):
    """r11 安全審 F-3：`self_test` 只比 `ok` 會假綠——轉換若把違規性質改掉
    （本來測 QUOTE_NOT_COVERING、變成 SCHEMA），`ok=False` 照樣成立。

    正對照：先確認原封不動的三份 fixture 會通過；再只改 `expected_reason` 一個鍵，
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


def test_self_test_runs_both_rulers(verifier, tmp_path):
    """DSP-033 P1-2：自證跑**兩種模式**。

    反證：把一個「只有降級尺會誤殺」的 known_good 案的降級期望改成放行，
    self_test 必須 raise——若不 raise，代表降級那一遍根本沒跑。
    """
    assert verifier.SELF_TEST_MODES == ("nli", "degraded")
    good = json.loads(json.dumps(_GOOD))
    target = next(
        c for c in good if c["id"] == "good_faithful_paraphrase_rejected_only_by_degraded_ratio")
    target["expect_ok_degraded"] = True
    (tmp_path / "known_fabrications.json").write_text(
        json.dumps(_FABRICATIONS, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "known_good.json").write_text(
        json.dumps(good, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "known_open.json").write_text(
        json.dumps(_KNOWN_OPEN, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(RuntimeError):
        verifier.self_test(tmp_path)


def test_assertion_terms_cover_the_product_capability_verbs_and_not_the_over_broad_ones():
    """r11 安全審 F-2：補的是**產品能力動詞**這個封閉子集；
    「有／是／已／將」刻意 OPEN（會把「您有幾間？」降成 fact，推高誤殺）。"""
    rules = VerifierRules.load(_RULES_PATH)
    assert {"支持", "包含", "內建", "整合", "自動"} <= set(rules.assertion_terms)
    assert {"有", "是", "已", "將"}.isdisjoint(set(rules.assertion_terms))
    assert rules.version == "1.4.0"
    # DSP-033：τ 進規則集（版本化，才跟得上 `rules_sha`）；ratio 欄位退場。
    assert rules.nli_tau == 0.40
    assert not hasattr(rules, "min_coverage_ratio")
    raw = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
    assert "min_coverage_ratio" not in raw
    assert raw["nli_tau"] == 0.4


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
    assert n == len(_KNOWN_OPEN) == 2, "DSP-033 把 R4 第三句搬進 known_fabrications 後剩兩句"


@pytest.mark.parametrize("mode", _MODES)
@pytest.mark.parametrize("case", _KNOWN_OPEN, ids=[c["id"] for c in _KNOWN_OPEN])
def test_known_open_cases_are_still_passing(verifier, case, mode):
    """r13 #1：這兩句**現在確實會被放行**，本測試把「還沒擋住」寫成事實。

    ⚠️ DSP-033 F-1 業主裁定 (a)：τ=0.40 下它們的 p_ent 是 0.92／0.44 ⇒ NLI 也擋不住，
    故標 `nli_blind_spot: true` 留在本檔。⛔ 不得宣稱已擋、⛔ 不得調 τ 救自證。
    哪天真的被擋住，這條會紅——那時的正確處置是把案例搬去 `known_fabrications.json`
    並改斷言，⛔ 不是放寬新規則來讓這條繼續綠。"""
    assert case["known_open"] is True
    assert case["nli_blind_spot"] is True
    assert case["open_since"] and case["closed_by"]
    verdict = _verdict(verifier, case, mode)
    assert verdict.ok is True, (
        f"{case['id']}／{mode} 由未擋轉為已擋——請把它搬去 known_fabrications.json，"
        f"⛔ 不要放寬規則。實得 {verdict.model_dump()}"
    )


def test_known_open_blind_spot_scores_are_above_tau(verifier, rules):
    """正對照：兩句的實測 p_ent 真的在 τ 之上——否則「NLI 盲點」這個標籤
    只是一句沒有根據的宣稱。"""
    for case in _KNOWN_OPEN:
        score = case["nli_scores"]["*"]
        assert score >= rules.nli_tau, (case["id"], score)


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


def test_degraded_ratio_threshold_is_a_program_constant_not_a_rule(verifier):
    """DSP-033 v7：降級模式的相對門檻固定為程式常數 0.5，⛔ 不再從規則集讀。

    正對照：同一案在 NLI 模式放行、降級模式被 ratio 拒——證明那個常數
    真的在生效（而不是兩邊都用了絕對下限）。"""
    from services.agent.verifier import _DEGRADED_COVERAGE_RATIO

    assert _DEGRADED_COVERAGE_RATIO == 0.5
    case = next(
        c for c in _GOOD if c["id"] == "good_faithful_paraphrase_rejected_only_by_degraded_ratio")
    assert _verdict(verifier, case, "nli").ok is True
    assert _verdict(verifier, case, "degraded").reason == "QUOTE_NOT_COVERING"


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
