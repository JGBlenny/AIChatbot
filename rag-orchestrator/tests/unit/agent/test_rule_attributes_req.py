"""unit：**Verifier 規則自帶屬性**（Plan `inputs/plan-structural-refactor-20260910.md` §0 R2）。

R2 是**行為不變的結構整理**：把「受眾鍵／`document_turn` 布林／模式集合」三套各自為政
的機制收成一件事——每條規則自帶 `{id, pattern, class, audiences, turn_types}`，
`_is_observed` 只查一張 `class × mode` 表。

本檔的六節（缺任一節，這次整理都可能悄悄改了判定而沒有人知道）：
(a) 出貨規則檔 2.0.0 的每條規則屬性齊全、值域封閉，且與**舊七張表**逐條對帳；
(b) `class × mode` 與 R2 前的三個常數（`_GROUNDING_OBSERVE_REASONS`／
    `_GROUNDING_OBSERVE_SCHEMA_CAUSES`／`polarity_source == "term"` 特例）**逐位等價**
    ——舊常數在本檔留一份字面副本當對照組，⛔ 不從程式 import 當標準答案（那會變成
    「自己對自己」）；
(c) 新入口 `ctx=` 與舊 kwarg `audience=`／`document_turn=` **同輸入同 verdict**；
(d) 1.x 規則檔**拒載**；
(e) 舊 `term_id` 索引 → 新 `RuleSpec.id` 的**一一對應全覆蓋**（對照物是
    `tests/fixtures/agent/rules_1_6_2.json`，＝改版前那一份規則檔的逐字副本）；
(f) `VerifierVerdict.observed_counts` 與 `observed` 一致。

另有 (g) **變異正對照**：改任何一條規則的 `audiences`／`turn_types`／`class`，本檔必紅。

離線、不接觸真 DB／真 LLM。
"""
from __future__ import annotations

import copy
import json
import re
from collections import Counter
from pathlib import Path
from typing import Optional, get_args

import pytest

from services.agent.identity import Audience
from services.agent.output_schema import (
    RULE_CLASSES,
    RULE_ID_PATTERN,
    RULE_NAMESPACES,
    TERM_ID_PATTERN,
    TURN_TYPES,
    AgentOutput,
    RuleSpec,
    VerdictReason,
    VerifierRules,
    VerifierVerdict,
    VerifyContext,
)
from services.agent.provenance_units import resolve_refs
from services.agent.tools.registry import ToolResult
from services.agent.verifier import (
    _FIXTURE_NONCE,
    _GROUNDING_OBSERVE_REASONS,
    _GROUNDING_OBSERVE_SCHEMA_CAUSES,
    DEFAULT_VERIFIER_MODE,
    VERIFIER_MODES,
    OutputVerifier,
    verdict_class,
)

_REQ = "knowledge-outline-and-intent-architecture:R2-rule-attributes"
pytestmark = [pytest.mark.unit, pytest.mark.req(_REQ)]

_ROOT = Path(__file__).resolve().parents[3]
_RULES_PATH = _ROOT / "config" / "agent_verifier_rules.json"
_FIXTURES_DIR = _ROOT / "tests" / "fixtures" / "agent"
#: R2 前那一份規則檔的**逐字副本**（Plan §2：改版時保留 1.6.2 供 term_id 對照）。
_LEGACY_RULES_PATH = _FIXTURES_DIR / "rules_1_6_2.json"

_ALL_AUDIENCES = sorted(get_args(Audience))
_ALL_TURN_TYPES = list(TURN_TYPES)

#: 七張表：namespace → (規則檔頂層鍵, 預期 class, 預期 turn_types, 受眾權威鍵)。
#: ⚠️ 這張表是本檔**自己寫的預期**，⛔ 不從 `verifier._TABLE_DEFAULTS` import——
#: 那樣「程式改了預期跟著改」，對帳就什麼都證明不了。
_EXPECTED_TABLES: dict[str, tuple[str, str, list[str], Optional[str]]] = {
    "sensitive": ("sensitive_patterns", "safety", _ALL_TURN_TYPES, "sensitive_patterns_audiences"),
    "negation": ("negation_terms", "grounding", _ALL_TURN_TYPES, None),
    "pair": ("negation_status_pairs", "contract", _ALL_TURN_TYPES, None),
    "forbid": ("forbid_terms", "safety", _ALL_TURN_TYPES, None),
    "docturn": ("document_turn_forbid_terms", "safety", ["document"], None),
    "route": ("allowed_routes", "safety", _ALL_TURN_TYPES, "route_check_audiences"),
    "qsensitive": ("question_sensitive_patterns", "safety", _ALL_TURN_TYPES, None),
}


@pytest.fixture(scope="module")
def raw() -> dict:
    return json.loads(_RULES_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def rules() -> VerifierRules:
    return VerifierRules.load(_RULES_PATH)


@pytest.fixture(scope="module")
def verifier(rules: VerifierRules) -> OutputVerifier:
    return OutputVerifier(rules)


# ══════════════════════════════════════════════════════════════════
# (a) 屬性齊全、值域封閉、與舊七張表逐條對帳
# ══════════════════════════════════════════════════════════════════

def test_shipped_ruleset_is_version_2_and_declares_rules(raw):
    """正對照組：先確認**檔案裡真的有** `rules` 這個陣列且非空。

    沒有這一條，下面每一條「逐條對帳」都可能只是在對兩個空集合，而空集合恆等。"""
    assert raw["version"] == "2.0.0"
    assert isinstance(raw.get("rules"), list) and raw["rules"], (
        "規則檔沒有 `rules` 陣列 ⇒ 本檔每一條對帳都失去意義（正對照不成立）")


def test_every_rule_declares_the_five_attributes_with_closed_value_domains(raw):
    """每條規則 `{id, pattern, class, audiences, turn_types}` 五個鍵不多不少，值域封閉。"""
    for entry in raw["rules"]:
        assert set(entry) == {"id", "pattern", "class", "audiences", "turn_types"}, entry
        assert re.match(RULE_ID_PATTERN, entry["id"]), entry["id"]
        assert entry["id"].split(":", 1)[0] in RULE_NAMESPACES, entry["id"]
        assert entry["class"] in RULE_CLASSES, entry
        assert entry["audiences"] and set(entry["audiences"]) <= set(_ALL_AUDIENCES), entry
        assert entry["turn_types"] and set(entry["turn_types"]) <= set(TURN_TYPES), entry
        # pattern 的形狀跟著表走：pair 是 {neg, status}，其餘是字串
        if entry["id"].startswith("pair:"):
            assert set(entry["pattern"]) == {"neg", "status"}, entry
        else:
            assert isinstance(entry["pattern"], str) and entry["pattern"], entry


def test_rule_ids_are_unique_and_contiguous_per_table(raw):
    """id 是「表＋表內索引」⇒ 同表必須是 0..n-1 連號、全域不重複。

    ⚠️ 連號是 `term_id` 對得回規則的前提：跳號代表某一條被刪了卻沒有重新編號，
    歷史 trace 會整批對到錯的規則。"""
    ids = [e["id"] for e in raw["rules"]]
    assert len(ids) == len(set(ids)), "id 重複"
    by_ns: dict[str, list[int]] = {}
    for rule_id in ids:
        ns, _, index = rule_id.partition(":")
        by_ns.setdefault(ns, []).append(int(index))
    for ns, indices in by_ns.items():
        assert sorted(indices) == list(range(len(indices))), (ns, sorted(indices))


def _reconcile(raw_rules: dict) -> None:
    """(a) 的對帳本體——`rules[]` 與**舊七張表**逐條相符。

    抽成函式是為了讓 (g) 的變異正對照能拿同一段邏輯去證明「改了就會紅」。
    ⛔ 不得改成只比長度：長度相同、內容漂掉正是最難發現的那種。
    """
    declared: dict[str, dict] = {e["id"]: e for e in raw_rules["rules"]}
    total = 0
    for ns, (field, cls, turns, audience_field) in _EXPECTED_TABLES.items():
        table = raw_rules.get(field) or []
        total += len(table)
        expected_auds = (list(raw_rules[audience_field]) if audience_field
                         and raw_rules.get(audience_field) is not None else _ALL_AUDIENCES)
        for index, value in enumerate(table):
            entry = declared.get(f"{ns}:{index}")
            assert entry is not None, f"{ns}:{index} 沒有屬性宣告"
            assert entry["pattern"] == value, (ns, index, entry["pattern"], value)
            assert entry["class"] == cls, (ns, index, entry["class"])
            assert entry["turn_types"] == turns, (ns, index, entry["turn_types"])
            assert entry["audiences"] == expected_auds, (ns, index, entry["audiences"])
    assert total == len(raw_rules["rules"]), (
        f"舊七張表共 {total} 條、新條目 {len(raw_rules['rules'])} 條——條數對不上")


def test_declared_rules_reconcile_with_the_seven_flat_tables(raw):
    """驗收「規則條數對帳（舊七表條數＝新條目數）」＋逐條 pattern／class／
    turn_types／audiences 相符。"""
    _reconcile(raw)


def test_rule_counts_match_the_seven_tables_one_by_one(raw):
    """把總數拆開逐表報：全部對不上時看得出是哪一張表漂了。"""
    counts = Counter(e["id"].split(":", 1)[0] for e in raw["rules"])
    for ns, (field, _cls, _turns, _aud) in _EXPECTED_TABLES.items():
        assert counts[ns] == len(raw.get(field) or []), (ns, counts[ns], field)


def test_document_turn_is_the_only_table_scoped_to_document_turns(raw):
    """`turn_types` 這個維度就是 R2 前的 `document_turn` 布林：
    只有 `docturn` 那張表限定 `document`，其餘七表一律全回合。

    正對照組：`docturn` 這張表**真的存在且非空**——否則「只有它限定」恆成立。"""
    scoped = {e["id"] for e in raw["rules"] if e["turn_types"] != _ALL_TURN_TYPES}
    assert scoped, "沒有任何一條限定回合型態 ⇒ 這條斷言什麼都沒證明"
    assert all(rule_id.startswith("docturn:") for rule_id in scoped), scoped
    assert all(e["turn_types"] == ["document"]
               for e in raw["rules"] if e["id"].startswith("docturn:"))


def test_only_presales_gates_are_audience_scoped(raw):
    """`audiences` 這個維度就是 R2 前的兩個受眾鍵：只有答案側敏感樣式與導流白名單
    縮到 `prospect`（W9-11／W9 情境①），其餘一律全受眾。"""
    scoped = {e["id"] for e in raw["rules"] if e["audiences"] != _ALL_AUDIENCES}
    assert scoped, "沒有任何一條縮受眾 ⇒ 這條斷言什麼都沒證明（售前守門的放寬整個消失了？）"
    assert all(rule_id.split(":", 1)[0] in ("sensitive", "route") for rule_id in scoped), scoped
    assert all(e["audiences"] == ["prospect"] for e in raw["rules"]
               if e["id"].split(":", 1)[0] in ("sensitive", "route"))


def test_runtime_rule_set_matches_the_declared_attributes(rules, verifier):
    """載進來的判定用規則集（`OutputVerifier._rule_set`）與規則檔宣告逐條相同。

    ⚠️ 這一條把「檔案寫得對」與「程式真的照它跑」分開報——pydantic 白名單會靜默
    忽略未宣告鍵，只驗檔案的話，`VerifierRules` 忘了宣告 `rules` 欄位時本檔照樣全綠。"""
    runtime = {rule.spec.id: rule.spec for rule in verifier._rule_set}
    declared = {spec.id: spec for spec in rules.rules}
    assert set(runtime) == set(declared), set(runtime) ^ set(declared)
    for rule_id, spec in declared.items():
        assert runtime[rule_id].rule_class == spec.rule_class, rule_id
        assert runtime[rule_id].turn_types == spec.turn_types, rule_id
        assert runtime[rule_id].audiences == spec.audiences, rule_id
        assert runtime[rule_id].pattern == spec.pattern, rule_id


@pytest.mark.parametrize("audience", [None, "prospect", "property_manager", "system_admin", "typo"])
def test_rules_for_agrees_with_the_legacy_audience_gate(verifier, audience):
    """`rules_for("sensitive", ctx)` 與 R2 前那道整表閘（`_sensitive_patterns_apply`）
    對每一種受眾狀態（缺值／值域內兩種／值域外兩種）給同一個答案。"""
    applies = verifier._sensitive_patterns_apply(audience)
    picked = verifier.rules_for("sensitive", VerifyContext(audience=audience))
    assert bool(picked) is applies, (audience, len(picked))
    if applies:
        assert len(picked) == len(verifier.rules.sensitive_patterns)


# ══════════════════════════════════════════════════════════════════
# (b) class × mode 與 R2 前的三個常數逐位等價
# ══════════════════════════════════════════════════════════════════

#: R2 **前**的觀察集合，本檔的**字面副本**（⛔ 不從 verifier import 當標準答案）。
_LEGACY_GROUNDING_OBSERVE_REASONS = frozenset({
    "UNCITED_ASSERTION", "QUOTE_TOO_SHORT", "QUOTE_NOT_COVERING", "SOURCE_NOT_CITABLE",
})
_LEGACY_GROUNDING_OBSERVE_SCHEMA_CAUSES = frozenset({
    "ref_invalid", "ref_source_not_found", "ref_ambiguous", "unit_out_of_range",
})

_SCHEMA_CAUSES: tuple[Optional[str], ...] = get_args(
    get_args(VerifierVerdict.model_fields["schema_cause"].annotation)[0]) + (None,)
_REASONS: tuple[Optional[str], ...] = get_args(VerdictReason) + (None,)
_POLARITY_SOURCES: tuple[Optional[str], ...] = ("term", "pair", None)


def _legacy_is_observed(mode: str, verdict: VerifierVerdict) -> bool:
    """R2 **前**的 `OutputVerifier._is_observed`，逐字搬進本檔當對照組。"""
    if mode == "enforce":
        return False
    if mode == "observe_only":
        return True
    if verdict.reason in _LEGACY_GROUNDING_OBSERVE_REASONS:
        return True
    if verdict.reason == "POLARITY_MISMATCH" and verdict.polarity_source == "term":
        return True
    return (verdict.reason == "SCHEMA"
            and verdict.schema_cause in _LEGACY_GROUNDING_OBSERVE_SCHEMA_CAUSES)


def test_the_legacy_constants_in_this_file_still_match_the_module(verifier):
    """對照組自身的正對照：本檔的字面副本必須等於模組裡那兩個常數。

    ⚠️ 沒有這一條，副本與模組各自演化時，(b) 只會證明「新舊實作都照著一份**過時的**
    對照組跑」。"""
    assert _LEGACY_GROUNDING_OBSERVE_REASONS == _GROUNDING_OBSERVE_REASONS
    assert _LEGACY_GROUNDING_OBSERVE_SCHEMA_CAUSES == _GROUNDING_OBSERVE_SCHEMA_CAUSES


def _all_verdicts() -> list[VerifierVerdict]:
    out: list[VerifierVerdict] = []
    for reason in _REASONS:
        if reason == "SCHEMA":
            out += [VerifierVerdict(ok=False, reason=reason, schema_cause=cause)
                    for cause in _SCHEMA_CAUSES]
        elif reason == "POLARITY_MISMATCH":
            out += [VerifierVerdict(ok=False, reason=reason, polarity_source=src)
                    for src in _POLARITY_SOURCES]
        else:
            out.append(VerifierVerdict(ok=False, reason=reason))
    return out


@pytest.mark.parametrize("mode", VERIFIER_MODES)
def test_class_by_mode_table_is_bit_for_bit_the_legacy_behaviour(rules, mode):
    """三個模式 × 全部拒因（`SCHEMA` 展開八個子成因、`POLARITY_MISMATCH` 展開三種
    來源、外加 `reason=None`）逐格比對——任何一格不同即紅。"""
    verifier = OutputVerifier(rules, mode=mode)
    for verdict in _all_verdicts():
        assert verifier._is_observed(verdict) == _legacy_is_observed(mode, verdict), (
            mode, verdict.reason, verdict.schema_cause, verdict.polarity_source)


def test_the_comparison_is_not_vacuous():
    """對照組自身會分辨：`grounding_observe` 下**既有**觀察的、也有照擋的。

    沒有這一條，上面那組 parametrize 可能只是「兩邊都恆 False」而全綠。"""
    observed = [v for v in _all_verdicts() if _legacy_is_observed("grounding_observe", v)]
    blocked = [v for v in _all_verdicts() if not _legacy_is_observed("grounding_observe", v)]
    assert observed and blocked, (len(observed), len(blocked))


def test_verdict_class_is_a_closed_total_function():
    """每個 verdict 都拿得到一個封閉值域內的 class（⛔ 不得回 None／自由字串）；
    且缺值方向是 `safety`＝照擋。"""
    for verdict in _all_verdicts():
        assert verdict_class(verdict) in RULE_CLASSES, verdict.model_dump()
    assert verdict_class(VerifierVerdict(ok=False, reason=None)) == "safety"
    unknown = VerifierVerdict.model_construct(ok=False, reason="NOT_A_REASON")
    assert verdict_class(unknown) == "safety", "未知拒因的缺值方向必須是照擋"


def test_declared_rule_class_agrees_with_the_verdict_class_it_produces(raw):
    """規則檔宣告的 `class` 與該規則實際產生的 verdict 的 class 必須一致。

    ⚠️ 判定讀的是 `verdict_class()`（程式端），規則檔那一欄是**宣告**；兩者對不上
    代表有人改了其中一邊，而症狀（某一類在觀察模式下的歸屬變了）不會有別的徵兆。"""
    expected = {
        "sensitive": verdict_class(VerifierVerdict(ok=False, reason="SENSITIVE_TOPIC")),
        "forbid": verdict_class(VerifierVerdict(ok=False, reason="FORBIDDEN_TERM")),
        "docturn": verdict_class(VerifierVerdict(ok=False, reason="FORBIDDEN_TERM")),
        "route": verdict_class(VerifierVerdict(ok=False, reason="ROUTE_NOT_ALLOWED")),
        "negation": verdict_class(VerifierVerdict(
            ok=False, reason="POLARITY_MISMATCH", polarity_source="term")),
        "pair": verdict_class(VerifierVerdict(
            ok=False, reason="POLARITY_MISMATCH", polarity_source="pair")),
    }
    for entry in raw["rules"]:
        ns = entry["id"].split(":", 1)[0]
        if ns in expected:
            assert entry["class"] == expected[ns], entry


# ══════════════════════════════════════════════════════════════════
# (b') 三向 fixtures：class × mode 的行為面
# ══════════════════════════════════════════════════════════════════

_CLASS_MODE_CASES = json.loads(
    (_FIXTURES_DIR / "known_class_mode.json").read_text(encoding="utf-8"))


def _run_case(rules: VerifierRules, case: dict) -> VerifierVerdict:
    """與產線同一條路：解析 → 驗證。⛔ 不在這裡另寫一套解析。"""
    out = AgentOutput.model_validate(case["agent_output"])
    tool_results = {
        tid: ToolResult.model_validate(tr) for tid, tr in case.get("tool_results", {}).items()
    }
    nonce = case.get("nonce") or _FIXTURE_NONCE
    resolved, resolve_errors = resolve_refs(out, tool_results, nonce)
    verifier = OutputVerifier(rules, mode=case.get("mode", DEFAULT_VERIFIER_MODE))
    return verifier.verify(
        out, tool_results, case.get("user_message", ""), case.get("handoff"),
        resolved=resolved, resolve_errors=resolve_errors,
        ctx=VerifyContext(audience=case.get("audience"),
                          turn_type=("document" if case.get("document_turn") else "general"),
                          nonce=nonce))


def test_class_mode_fixture_covers_all_three_modes_and_all_three_classes():
    """正對照組：這份 fixture 真的把三個模式與三個 class 都蓋到了。

    沒有這一條，下面那組 parametrize 可能只跑了一個模式而看起來很完整。"""
    modes = {c.get("mode", DEFAULT_VERIFIER_MODE) for c in _CLASS_MODE_CASES}
    assert modes == set(VERIFIER_MODES), modes
    assert any("mode" not in c for c in _CLASS_MODE_CASES), "缺值方向（沒有 mode 鍵）沒有被蓋到"
    classes = {c["id"].split("_", 1)[0] for c in _CLASS_MODE_CASES}
    assert {"grounding", "contract", "safety"} <= classes, classes


@pytest.mark.parametrize("case", _CLASS_MODE_CASES, ids=[c["id"] for c in _CLASS_MODE_CASES])
def test_class_mode_fixture_cases(rules, case):
    verdict = _run_case(rules, case)
    assert verdict.ok is case["expect_ok"], (case["id"], verdict.model_dump())
    assert verdict.reason == case["expected_reason"], (case["id"], verdict.model_dump())
    if "expected_schema_cause" in case:
        assert verdict.schema_cause == case["expected_schema_cause"], case["id"]
    assert verdict.observed == case["expected_observed"], (case["id"], verdict.observed)


# ══════════════════════════════════════════════════════════════════
# (c) `ctx=` 與舊 kwarg 等價
# ══════════════════════════════════════════════════════════════════

_LEGACY_FIXTURE_FILES = ("known_fabrications.json", "known_good.json", "known_open.json")
_LEGACY_CASES = [
    case
    for name in _LEGACY_FIXTURE_FILES
    for case in json.loads((_FIXTURES_DIR / name).read_text(encoding="utf-8"))
]


def _verify_both_ways(verifier: OutputVerifier, case: dict, audience, document_turn):
    out = AgentOutput.model_validate(case["agent_output"])
    tool_results = {
        tid: ToolResult.model_validate(tr) for tid, tr in case.get("tool_results", {}).items()
    }
    nonce = case.get("nonce") or _FIXTURE_NONCE
    resolved, resolve_errors = resolve_refs(out, tool_results, nonce)
    common = dict(resolved=resolved, resolve_errors=resolve_errors)
    legacy = verifier.verify(out, tool_results, case.get("user_message", ""),
                             case.get("handoff"), audience=audience,
                             document_turn=document_turn, **common)
    with_ctx = verifier.verify(
        out, tool_results, case.get("user_message", ""), case.get("handoff"),
        ctx=VerifyContext(audience=audience,
                          turn_type="document" if document_turn else "general"),
        **common)
    return legacy, with_ctx


def test_ctx_and_legacy_kwargs_agree_on_every_shipped_fixture_case(verifier):
    """三份出貨 fixture 的每一案，兩條路徑的 verdict **逐欄**相同。"""
    assert _LEGACY_CASES, "fixture 讀不到 ⇒ 這條什麼都沒證明"
    for case in _LEGACY_CASES:
        legacy, with_ctx = _verify_both_ways(
            verifier, case, case.get("audience"), bool(case.get("document_turn", False)))
        assert legacy.model_dump() == with_ctx.model_dump(), case.get("id")


@pytest.mark.parametrize("audience", [None, "prospect", "property_manager", "system_admin"])
@pytest.mark.parametrize("document_turn", [False, True])
def test_ctx_and_legacy_kwargs_agree_across_the_audience_and_turn_matrix(
        verifier, audience, document_turn):
    """把兩個維度攤成矩陣（含值域外的 `system_admin` 與文件回合），逐格比對。

    正對照：矩陣裡至少要有一格真的被擋，否則「兩邊相同」可能只是兩邊都放行。"""
    seen_blocked = False
    for case in _LEGACY_CASES:
        legacy, with_ctx = _verify_both_ways(verifier, case, audience, document_turn)
        assert legacy.model_dump() == with_ctx.model_dump(), case.get("id")
        seen_blocked = seen_blocked or not legacy.ok
    assert seen_blocked, (audience, document_turn)


def test_ctx_wins_when_both_are_given(verifier):
    """`ctx` 有值以它為準（⛔ 不合併、⛔ 不 raise）——拿一個「受眾放行 vs 照擋」
    會給出不同答案的案子來證明是 `ctx` 在決定。"""
    case = next(c for c in _LEGACY_CASES if c.get("id") == "audience_prospect_amount_still_sensitive")
    out = AgentOutput.model_validate(case["agent_output"])
    tool_results = {
        tid: ToolResult.model_validate(tr) for tid, tr in case.get("tool_results", {}).items()
    }
    nonce = case.get("nonce") or _FIXTURE_NONCE
    resolved, resolve_errors = resolve_refs(out, tool_results, nonce)
    common = dict(resolved=resolved, resolve_errors=resolve_errors)

    def _v(**kwargs):
        return verifier.verify(out, tool_results, case.get("user_message", ""),
                               case.get("handoff"), **common, **kwargs)

    # 正對照：兩種受眾本來就會給不同判定
    assert _v(audience="prospect").ok is False
    assert _v(audience="property_manager").ok is True
    # ctx 說 pm、舊 kwarg 說 prospect ⇒ 以 ctx 為準
    assert _v(audience="prospect", ctx=VerifyContext(audience="property_manager")).ok is True


def test_document_turn_kwarg_maps_to_the_document_turn_type(verifier):
    """`document_turn=True` ⇒ `turn_type="document"`（⛔ 不是別的值）。"""
    out = AgentOutput.model_validate({
        "kind": "ask",
        "sentences": [{"text": "要不要我幫您建立一張帳單？", "kind": "question", "refs": []}],
        "fact_class": "other", "ask_target": "confirm_intent",
    })
    resolved, resolve_errors = resolve_refs(out, {}, _FIXTURE_NONCE)
    common = dict(resolved=resolved, resolve_errors=resolve_errors)
    blocked = verifier.verify(out, {}, "", None, document_turn=True, **common)
    assert blocked.ok is False and blocked.reason == "FORBIDDEN_TERM"
    assert verifier.verify(out, {}, "", None,
                           ctx=VerifyContext(turn_type="document"),
                           **common).model_dump() == blocked.model_dump()
    # 正對照：一般回合不擋（⛔ 這張表沒有溢出到全回合）
    assert verifier.verify(out, {}, "", None,
                           ctx=VerifyContext(turn_type="general"), **common).ok is True


def test_verify_context_turn_type_is_a_closed_domain():
    """`turn_type` 打錯字要**炸**：它的缺值方向是少擋，靜默落回 `general` 等於閘沒開。"""
    from pydantic import ValidationError

    VerifyContext(turn_type="document")  # 正對照組
    with pytest.raises(ValidationError):
        VerifyContext(turn_type="documnet")


def test_verify_context_audience_accepts_out_of_domain_strings():
    """受眾相反：值域外的字串必須**進得來**，才輪得到「未知＝缺值＝照擋」那條判定。"""
    assert VerifyContext(audience="system_admin").audience == "system_admin"


# ══════════════════════════════════════════════════════════════════
# (d) 舊版規則檔拒載
# ══════════════════════════════════════════════════════════════════

def test_legacy_1_x_ruleset_is_refused(tmp_path):
    """1.x 一律拒載，且訊息指得出要 2.0.0。

    ⚠️ 失敗方向刻意是「起不來」：舊檔沒有 `rules` 宣告，載得起來的話每條規則
    都退回程式端預設屬性，而「屬性宣告整份消失」不會有任何徵兆。"""
    with pytest.raises(ValueError, match="2.0.0"):
        VerifierRules.load(_LEGACY_RULES_PATH)


def test_it_is_the_version_that_is_refused_not_the_shape(tmp_path, raw):
    """反證「其實是舊檔的形狀載不起來」：拿**出貨那份**只改版本號 ⇒ 一樣拒載。"""
    downgraded = copy.deepcopy(raw)
    downgraded["version"] = "1.6.2"
    path = tmp_path / "rules_downgraded.json"
    path.write_text(json.dumps(downgraded, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="2.0.0"):
        VerifierRules.load(path)
    # 正對照：同一份內容版本號放回 2.0.0 就載得起來（⇒ 擋的是版本，不是內容）
    downgraded["version"] = "2.0.0"
    path.write_text(json.dumps(downgraded, ensure_ascii=False), encoding="utf-8")
    assert VerifierRules.load(path).version == "2.0.0"


def test_shipped_ruleset_still_loads(rules):
    """正對照組：拒載那條不是「什麼都載不起來」。"""
    assert rules.version == "2.0.0" and rules.rules


# ══════════════════════════════════════════════════════════════════
# (e) 舊索引 → 新 id 一一對應全覆蓋
# ══════════════════════════════════════════════════════════════════

#: R2 前的 `term_id` 產生規則（`verifier._rule_id`／`_pair_rule_id`／`_doc_turn_rule_id`）
#: ——本檔的字面副本，⛔ 不從程式 import（程式那三個基底已經廢掉了）。
#: ⚠️ 值是 `(拒因, term_id)`：舊 `term_id` **單獨不唯一**（`rule#0` 同時是敏感樣式第 0 條
#: 與禁詞第 0 條），要配 `reason` 才定位得到規則——這正是 `_PAIR_TERM_ID_BASE=1000`／
#: `_DOC_TURN_TERM_ID_BASE=2000` 當初存在的理由（同一個 reason 對到兩張表時得錯開）。
#: 新的 namespace id 不需要基底，因為 namespace 本身就帶著「哪一張表」。
_LEGACY_TERM_ID = {
    "sensitive": lambda i: ("SENSITIVE_TOPIC", f"rule#{i}"),
    "negation": lambda i: ("POLARITY_MISMATCH", f"rule#{i}"),
    "forbid": lambda i: ("FORBIDDEN_TERM", f"rule#{i}"),
    "pair": lambda i: ("POLARITY_MISMATCH", f"rule#{1000 + i}"),
    "docturn": lambda i: ("FORBIDDEN_TERM", f"rule#{2000 + i}"),
}


@pytest.fixture(scope="module")
def legacy_raw() -> dict:
    return json.loads(_LEGACY_RULES_PATH.read_text(encoding="utf-8"))


def test_legacy_fixture_really_is_the_1_6_2_ruleset(legacy_raw, raw):
    """正對照組：對照物必須真的是**改版前那一份**（版本 1.6.2、七張表都在、
    且每一張表與出貨那份逐字相同——R2 是行為不變的整理，表本身 ⛔ 一個字都沒動）。"""
    assert legacy_raw["version"] == "1.6.2"
    assert "rules" not in legacy_raw, "1.6.2 不該有屬性宣告，否則它不是改版前那一份"
    for ns, (field, _cls, _turns, _aud) in _EXPECTED_TABLES.items():
        assert field in legacy_raw, (ns, field)
        assert legacy_raw[field] == raw[field], f"{field} 在 R2 被動到了（R2 ⛔ 不改規則字面）"


def test_every_legacy_term_id_maps_to_exactly_one_new_rule_id(legacy_raw, rules):
    """舊 `term_id` → 新 `RuleSpec.id` 是**雙射**：每一條舊規則都有唯一的新 id，
    且沒有任何新 id 是憑空長出來的。"""
    new_ids = {spec.id for spec in rules.rules}
    mapping: dict[tuple[str, str], str] = {}
    for ns, make in _LEGACY_TERM_ID.items():
        field = _EXPECTED_TABLES[ns][0]
        table = legacy_raw.get(field) or []
        assert table, f"{field} 是空的 ⇒ 這一表的對照什麼都沒證明"
        for index in range(len(table)):
            legacy_key = make(index)
            new_id = f"{ns}:{index}"
            assert new_id in new_ids, (legacy_key, new_id)
            assert legacy_key not in mapping, f"舊 (reason, term_id) {legacy_key} 撞號"
            mapping[legacy_key] = new_id
    assert len(mapping) == len(set(mapping.values())) == sum(
        len(legacy_raw[_EXPECTED_TABLES[ns][0]]) for ns in _LEGACY_TERM_ID)
    # 覆蓋：五張會產生 term_id 的表全數在對照裡（route／qsensitive 不填 term_id）
    assert set(_LEGACY_TERM_ID) == {"sensitive", "negation", "forbid", "pair", "docturn"}


def test_the_two_magic_bases_are_gone_from_the_wire_ids(verifier):
    """`_PAIR_TERM_ID_BASE=1000`／`_DOC_TURN_TERM_ID_BASE=2000` 廢除的可執行證據：
    這兩張表的 wire `term_id` 已經不是 `rule#<大數>`，而是 namespace id。

    ⚠️ `sensitive`／`negation`／`forbid` 三表**刻意仍是 `rule#<表內索引>`**
    （`test_agent_turn_unit_req.py` 與 `trace_view.rule_index` 都釘著它）——
    改用 namespace id 是 R2b。"""
    wire = {rule.spec.id: rule.term_id for rule in verifier._rule_set}
    assert wire["pair:0"] == "pair:0" and wire["docturn:0"] == "docturn:0"
    assert wire["sensitive:0"] == "rule#0" and wire["forbid:1"] == "rule#1"
    assert wire["negation:0"] == "rule#0"
    # route／qsensitive 不填 term_id（前者的 verdict 沒有 term，後者不經 verify()）
    assert wire["route:0"] is None and wire["qsensitive:0"] is None
    # 每一個 wire 值都必須通過型別上的封閉樣式（⛔ 字面詞塞不進來）
    for rule_id, term_id in wire.items():
        if term_id is not None:
            assert re.match(TERM_ID_PATTERN, term_id), (rule_id, term_id)


def test_term_id_pattern_still_rejects_literal_terms():
    """放寬的是**形狀**、⛔ 不是性質：任何字面詞／regex 一個字都塞不進 `term_id`。"""
    from pydantic import ValidationError

    for good in ("rule#0", "rule#1000", "pair:12", "docturn:1", "sensitive:3"):
        VerifierVerdict(ok=False, reason="FORBIDDEN_TERM", term_id=good)
    for bad in ("終身保固", "literal-term", "pair:", "pair:x", "rule#", "Rule#7", "pair:1 保證"):
        with pytest.raises(ValidationError):
            VerifierVerdict(ok=False, reason="FORBIDDEN_TERM", term_id=bad)


# ══════════════════════════════════════════════════════════════════
# (f) observed_counts 與 observed 一致
# ══════════════════════════════════════════════════════════════════

def test_observed_counts_is_derived_from_observed(rules):
    """`observed_counts` ＝ `Counter(observed)`。

    正對照：至少要有一案真的觀察到東西，否則「兩個空 dict 相等」什麼都沒證明。"""
    seen_non_empty = False
    for case in _CLASS_MODE_CASES:
        verdict = _run_case(rules, case)
        assert verdict.observed_counts == dict(Counter(verdict.observed)), case["id"]
        seen_non_empty = seen_non_empty or bool(verdict.observed_counts)
    assert seen_non_empty, "沒有任何一案觀察到東西 ⇒ 這條斷言什麼都沒證明"


def test_observed_counts_carries_only_enumerated_values(rules):
    """⛔ 不得攜帶模型文字或來源原文——它會落 `decision_snapshot`／trace。"""
    allowed = set(get_args(VerdictReason)) | {
        f"SCHEMA:{c}" for c in _SCHEMA_CAUSES if c} | {
        "POLARITY_MISMATCH:term", "POLARITY_MISMATCH:pair"}
    for case in _CLASS_MODE_CASES:
        verdict = _run_case(rules, case)
        assert set(verdict.observed_counts) <= allowed, (case["id"], verdict.observed_counts)
        assert all(isinstance(v, int) for v in verdict.observed_counts.values())


def test_observed_counts_is_not_serialised_into_the_verdict_dump(rules):
    """⚠️ 刻意是純 `@property`、⛔ 不是 `computed_field`：verdict 的 `model_dump()`
    是 `decision_snapshot`／trace 的輸入形狀，多一個鍵等於在沒有人審過白名單的
    情況下改了外流面（R1b 才是接線那一片）。"""
    verdict = _run_case(rules, _CLASS_MODE_CASES[1])
    assert verdict.observed_counts, "正對照：這一案本來就該有觀察值"
    assert "observed_counts" not in verdict.model_dump()


# ══════════════════════════════════════════════════════════════════
# (g) 變異正對照：改屬性 ⇒ 必紅
# ══════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("field,mutated", [
    ("audiences", ["tenant"]),
    ("turn_types", ["document"]),
    ("class", "grounding"),
    ("pattern", "改過的樣式"),
])
def test_mutating_any_rule_attribute_turns_the_reconciliation_red(raw, field, mutated):
    """把**任一條**規則的屬性改掉，(a) 的對帳必紅。

    ⚠️ 沒有這一組，(a) 可能只是在比對兩份都由同一支腳本產生的資料，改了也不會有人知道。"""
    mutant = copy.deepcopy(raw)
    target = next(e for e in mutant["rules"] if e["id"] == "sensitive:0")
    assert target[field] != mutated, "變異前後相同 ⇒ 這條什麼都沒證明"
    target[field] = mutated
    with pytest.raises(AssertionError):
        _reconcile(mutant)


def test_mutating_a_rules_audiences_changes_the_verdict(rules):
    """行為面的變異正對照：把敏感樣式的受眾縮成只剩 `tenant`，pm 之外連
    `prospect` 都不再被這張表擋（而中性句仍放行 ⇒ 尺沒壞）。"""
    narrowed = rules.model_copy(update={"sensitive_patterns_audiences": ["tenant"]})
    verifier = OutputVerifier(narrowed)
    # ⚠️ 載體用**純問句**（句尾「？」、子句不含 assertion_terms）⇒ 步②免引用，
    #   句子不會先死在 UNCITED_ASSERTION 而讓 `ok=False` 假綠。
    out = AgentOutput.model_validate({
        "kind": "answer",
        "sentences": [{"text": "月租費是3000元嗎？", "kind": "question", "refs": []}],
        "fact_class": "feature",
    })
    resolved, resolve_errors = resolve_refs(out, {}, _FIXTURE_NONCE)
    common = dict(resolved=resolved, resolve_errors=resolve_errors)
    assert verifier.verify(out, {}, "", None, audience="prospect", **common).ok is True
    # 正對照：沒縮之前，同一句同一個受眾是被擋的
    assert OutputVerifier(rules).verify(
        out, {}, "", None, audience="prospect", **common).reason == "SENSITIVE_TOPIC"
    # 正對照：縮成 tenant 之後，tenant 仍然被擋（⇒ 這張表沒有整個消失）
    assert verifier.verify(out, {}, "", None, audience="tenant", **common).ok is False


def test_narrowing_a_rules_turn_types_changes_the_verdict(rules):
    """同上，換 `turn_types` 這個維度：把文件回合那張表放寬成全回合，
    一般回合的同一句就會被擋（⇒ 這個維度真的在判定路徑上）。"""
    widened = OutputVerifier(rules)
    for rule in widened._rule_set:
        if rule.namespace == "docturn":
            object.__setattr__(rule.spec, "turn_types", ["general", "document"])
    widened._by_namespace["docturn"] = [
        r for r in widened._rule_set if r.namespace == "docturn"]
    out = AgentOutput.model_validate({
        "kind": "ask",
        "sentences": [{"text": "要不要我幫您建立一張帳單？", "kind": "question", "refs": []}],
        "fact_class": "other", "ask_target": "confirm_intent",
    })
    resolved, resolve_errors = resolve_refs(out, {}, _FIXTURE_NONCE)
    common = dict(resolved=resolved, resolve_errors=resolve_errors)
    assert widened.verify(out, {}, "", None, **common).reason == "FORBIDDEN_TERM"
    # 正對照：沒放寬的那把尺，一般回合放行
    assert OutputVerifier(rules).verify(out, {}, "", None, **common).ok is True


def test_rule_spec_rejects_out_of_domain_attributes():
    """屬性的值域釘在型別上：class／turn_types／id 打錯字在建構當下就炸。"""
    from pydantic import ValidationError

    RuleSpec.model_validate({  # 正對照組
        "id": "sensitive:0", "pattern": "x", "class": "safety",
        "audiences": ["prospect"], "turn_types": ["general"]})
    for bad in (
        {"id": "unknown:0", "pattern": "x", "class": "safety",
         "audiences": ["prospect"], "turn_types": ["general"]},
        {"id": "sensitive:0", "pattern": "x", "class": "danger",
         "audiences": ["prospect"], "turn_types": ["general"]},
        {"id": "sensitive:0", "pattern": "x", "class": "safety",
         "audiences": ["prospect"], "turn_types": ["whenever"]},
    ):
        with pytest.raises(ValidationError):
            RuleSpec.model_validate(bad)
